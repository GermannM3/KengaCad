"""
Основной класс приложения KengaCAD
"""
import asyncio
import atexit
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from PyQt5.QtWidgets import QApplication, QMessageBox
from engine.websocket_client import KengaWebSocketClient
from engine.local_engine import LocalEngine
from robot.model import RobotModel, DEFAULT_6_AXIS_ROBOT_CONFIG
from cad.trajectory import AdvancedTrajectoryManager
from cad.import_export import CADImportExport


class KengaCADApp:
    def __init__(self):
        self.client: Optional[KengaWebSocketClient] = None
        self.robot: Optional[RobotModel] = None
        self.trajectory_manager: Optional[AdvancedTrajectoryManager] = None
        self.cad_importer: CADImportExport = CADImportExport()
        self.is_connected = False
        self.use_local_engine = True

        self.local_engine = LocalEngine()
        self.default_robot_config = DEFAULT_6_AXIS_ROBOT_CONFIG
        self.engine_process = None
        self.engine_started_by_app = False
        self.engine_version: Optional[str] = None
        self.settings = self._load_settings()

    def _app_id(self) -> str:
        app = self.settings.get("app", {}) if isinstance(self.settings, dict) else {}
        name = app.get("product_name") or app.get("name") or "KengaCAD"
        return str(name).strip() or "KengaCAD"
    
    def _app_root(self) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).parent
        return Path(__file__).resolve().parent

    def _get_internal_root(self) -> Path:
        """Каталог с данными в собранном приложении (PyInstaller --onedir)."""
        root = self._app_root()
        if getattr(sys, "frozen", False):
            internal = root / "_internal"
            if internal.exists():
                return internal
        return root

    def _settings_path(self) -> Path:
        return self._get_internal_root() / "config" / "settings.json"

    def _load_settings(self) -> Dict[str, Any]:
        path = self._settings_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"[WARN] Engine stop error: {e}")
        return {}

    def _app_version(self) -> str:
        app = self.settings.get("app", {}) if isinstance(self.settings, dict) else {}
        version = app.get("version") or ""
        return str(version).strip()


    def _get_user_data_dir(self) -> Path:
        app_id = self._app_id()
        system = platform.system().lower()
        if system.startswith("win"):
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
            return Path(base) / app_id
        return Path.home() / ".local" / "share" / app_id

    def _get_engine_path(self) -> Path:
        engine_settings = self.settings.get("engine", {})
        custom_path = engine_settings.get("engine_path") or engine_settings.get("binary_path")
        if custom_path:
            return Path(custom_path)
        exe_name = "kenga.exe" if platform.system().lower().startswith("win") else "kenga"
        base = self._get_internal_root()
        return base / "engine_bin" / exe_name

    async def _fetch_engine_version(self, websocket_uri: str) -> Optional[str]:
        """GET http://host:port/version → {"version":"v0.2.0"}."""
        def _get():
            try:
                import urllib.request
                parsed = urlparse(websocket_uri)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or 7777
                url = f"http://{host}:{port}/version"
                req = urllib.request.Request(url, headers={"User-Agent": "KengaCAD"})
                with urllib.request.urlopen(req, timeout=2) as r:
                    data = json.loads(r.read().decode())
                    return data.get("version") or None
            except Exception:
                return None
        return await asyncio.get_event_loop().run_in_executor(None, _get)

    def _get_ws_host_port(self, websocket_uri: str) -> str:
        parsed = urlparse(websocket_uri)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 7777
        return f"{host}:{port}"

    def _get_app_assets_dir(self) -> Path:
        """Папка assets приложения (с robot.glb)."""
        root = self._get_internal_root()
        return root / "assets"

    def _ensure_project_files(self, project_dir: Path, scene_rel: str) -> Path:
        project_dir.mkdir(parents=True, exist_ok=True)
        # project.kenga.json — движок ожидает структуру Kenga-проекта
        proj_json = project_dir / "project.kenga.json"
        if not proj_json.exists():
            proj_json.write_text(
                json.dumps(
                    {"name": "KengaCAD", "scenes": [scene_rel], "assetsDir": "assets", "derivedDir": ".kenga/derived"},
                    ensure_ascii=False, indent=2),
                encoding="utf-8")
        assets_dir = project_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        # Копируем robot.glb в проект (движок загружает только из project_dir)
        app_assets = self._get_app_assets_dir()
        robot_src = app_assets / "robot.glb"
        robot_dst = assets_dir / "robot.glb"
        if robot_src.exists() and (not robot_dst.exists() or robot_src.stat().st_mtime > robot_dst.stat().st_mtime):
            import shutil
            shutil.copy2(robot_src, robot_dst)
        scene_path = project_dir / scene_rel
        scene_path.parent.mkdir(parents=True, exist_ok=True)
        if not scene_path.exists():
            scene_data = {"name": "KengaCAD Scene", "entities": []}
            scene_path.write_text(json.dumps(scene_data, ensure_ascii=False, indent=2), encoding="utf-8")
        # kenga import — строит .kenga/assets/index.json для load_model
        engine_path = self._get_engine_path()
        if engine_path.exists() and robot_dst.exists():
            try:
                subprocess.run(
                    [str(engine_path), "import", "--project", str(project_dir), "--auto-assign", "false"],
                    cwd=str(project_dir), capture_output=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower().startswith("win") else 0)
            except Exception:
                pass
        return scene_path

    async def _start_engine(self, websocket_uri: str) -> bool:
        engine_settings = self.settings.get("engine", {})
        if not engine_settings.get("auto_start", True):
            return True

        engine_path = self._get_engine_path()
        if not engine_path.exists():
            print(f"[ERROR] Движок не найден: {engine_path}")
            return False

        project_dir_setting = engine_settings.get("project_dir") or ""
        self._project_dir = Path(project_dir_setting) if project_dir_setting else self._get_user_data_dir() / "project"
        scene_rel = engine_settings.get("scene_relative", "scenes/default.json")
        self._ensure_project_files(self._project_dir, scene_rel)

        ws_host_port = self._get_ws_host_port(websocket_uri)
        cmd = [
            str(engine_path),
            "run",
            "--headless",
            "--project",
            str(self._project_dir),
            "--scene",
            scene_rel,
            "--ws-port",
            ws_host_port,
        ]

        logs_dir = self._get_user_data_dir() / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / "engine.log"
        log_handle = open(log_file, "a", encoding="utf-8")

        creationflags = 0
        if platform.system().lower().startswith("win"):
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            self.engine_process = subprocess.Popen(
                cmd,
                cwd=str(self._project_dir),
                stdout=log_handle,
                stderr=log_handle,
                creationflags=creationflags,
            )
            self.engine_started_by_app = True

            def _kill_engine_on_exit():
                p = self.engine_process
                if p and p.poll() is None:
                    try:
                        p.terminate()
                        p.wait(timeout=2)
                    except Exception:
                        try:
                            p.kill()
                        except Exception:
                            pass

            atexit.register(_kill_engine_on_exit)
            print(f"+ Движок запущен: {engine_path}")
            return True
        except Exception as e:
            print(f"[ERROR] Не удалось запустить движок: {e}")
            return False

    async def _stop_engine(self):
        if not self.engine_process or not self.engine_started_by_app:
            return
        try:
            self.engine_process.terminate()
            await asyncio.sleep(0.5)
            if self.engine_process.poll() is None:
                self.engine_process.kill()
        except Exception as e:
            print(f"[WARN] Engine stop error: {e}")

    async def initialize(self, websocket_uri: str = None):
        """Initialize application — использует встроенный локальный движок (без kenga.exe)."""
        print(f"Initializing {self._app_id()} {self._app_version()}...")

        self.use_local_engine = True
        self.is_connected = True
        self.engine_version = "local"
        self.local_engine = LocalEngine()
        print("Используется встроенный движок (локальный режим)")

        return True

    async def shutdown(self):
        """Shutdown application"""
        self.is_connected = False
        print("KengaCAD shutting down")

    def _prepare_model_path(self, model_path: str) -> Optional[str]:
        """Приводит путь к модели к формату для движка (относительно project_dir)."""
        path = Path(model_path)
        project_dir = getattr(self, "_project_dir", None)
        if not project_dir:
            return model_path
        project_dir = project_dir.resolve()
        if not path.is_absolute():
            path = (project_dir / path).resolve()
        if not path.exists():
            return None
        try:
            if path.is_relative_to(project_dir):
                return str(path.relative_to(project_dir)).replace("\\", "/")
        except (ValueError, AttributeError):
            pass
        import shutil
        assets_dir = project_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        dst = assets_dir / path.name
        shutil.copy2(path, dst)
        engine_path = self._get_engine_path()
        if engine_path.exists():
            try:
                subprocess.run(
                    [str(engine_path), "import", "--project", str(project_dir), "--auto-assign", "false"],
                    cwd=str(project_dir), capture_output=True, timeout=30,
                    creationflags=subprocess.CREATE_NO_WINDOW if platform.system().lower().startswith("win") else 0)
            except Exception:
                pass
        return f"assets/{path.name}".replace("\\", "/")

    async def load_robot(self, model_path: str, entity_id: str = "robot1", 
                       joints_config: Dict = None) -> bool:
        """Загрузка модели робота — в локальном режиме принимаем, 3D-модель не отображается."""
        if self.use_local_engine:
            self.local_engine.load_robot(model_path, entity_id)
            return True
        if not self.is_connected:
            return False
        engine_path = self._prepare_model_path(model_path)
        if not engine_path:
            return False
        if joints_config is None:
            joints_config = self.default_robot_config
        self.robot = RobotModel(self.client, entity_id, joints_config)
        return await self.robot.load_model(engine_path)
    
    async def setup_robot_trajectory(self, entity_id: str = "robot1_trajectory", 
                                   points: list = None) -> bool:
        """Настройка траектории — в локальном режиме сохраняет в LocalEngine."""
        if points is None:
            points = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        self.local_engine.setup_trajectory(points, entity_id)
        return True

    async def run_simulation(self, steps: int = 60) -> bool:
        """Запуск симуляции — в локальном режиме UI анимирует маркер в 3D-превью."""
        return True
    
    async def set_robot_joints(self, angles: Dict[str, float]) -> bool:
        """Установка углов суставов робота"""
        if not self.robot:
            print("Робот не загружен")
            return False
        
        return await self.robot.set_all_joints(angles)
    
    async def get_robot_joints(self) -> Optional[Dict[str, float]]:
        """Получение текущих углов суставов робота"""
        if not self.robot:
            print("Робот не загружен")
            return None
        
        return await self.robot.get_all_joints()
    
    def get_robot_info(self) -> Optional[Dict[str, Any]]:
        """Получение информации о роботе"""
        if not self.robot:
            print("Робот не загружен")
            return None
        
        return self.robot.get_info()
    
    async def start_dispensing(self, flow_rate: float = 1.0, radius: float = 0.02) -> bool:
        """Начать нанесение материала (мастики)"""
        if not self.robot:
            print("Робот не загружен")
            return False
        
        return await self.robot.start_dispensing(flow_rate, radius)
    
    async def stop_dispensing(self) -> bool:
        """Остановить нанесение материала"""
        if not self.robot:
            print("Робот не загружен")
            return False
        
        return await self.robot.stop_dispensing()
    
    async def move_robot_to(self, position: tuple, duration: float = 1.0) -> bool:
        """Перемещение робота в заданную позицию"""
        if not self.robot:
            print("Робот не загружен")
            return False
        
        return await self.robot.move_to_position(position, duration)
    
    async def clear_scene(self) -> bool:
        """Очистка сцены"""
        if not self.client or not self.is_connected:
            print("Нет подключения к движку Kenga")
            return False
        
        try:
            response = await self.client.clear_scene()
            if response.get('ok'):
                print("Сцена очищена")
                return True
            else:
                print(f"Ошибка очистки сцены: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при очистке сцены: {e}")
            return False
    
    async def query_collisions(self, entity_id: str = None) -> Optional[list]:
        """Запрос информации о коллизиях"""
        if not self.client or not self.is_connected:
            print("Нет подключения к движку Kenga")
            return None
        
        try:
            response = await self.client.query_collisions(entity_id)
            if response.get('ok'):
                collisions = response.get('data', {}).get('collisions', [])
                print(f"Найдено {len(collisions)} коллизий")
                return collisions
            else:
                print(f"Ошибка запроса коллизий: {response.get('error', 'Неизвестная ошибка')}")
                return None
        except Exception as e:
            print(f"Ошибка при запросе коллизий: {e}")
            return None

    async def check_reachability(self, pos: tuple, entity_id: str = None) -> Optional[Dict[str, Any]]:
        """Проверка достижимости позиции (обратная кинематика). Требует поддержки движка."""
        if not self.client or not self.is_connected:
            print("Нет подключения к движку Kenga")
            return None
        try:
            response = await self.client.check_reachability(pos, entity_id)
            if response.get('ok'):
                return response.get('data', {})
            return None
        except Exception as e:
            print(f"Ошибка REACHABILITY: {e}")
            return None


# Функция для запуска приложения
async def run_kengacad_app():
    app_instance = KengaCADApp()
    
    # Инициализация приложения
    if not await app_instance.initialize():
        print("Не удалось инициализировать KengaCAD")
        return False
    
    try:
        # Загрузка робота (предполагаем, что файл модели существует)
        # await app_instance.load_robot("assets/robot.gltf", "my_robot")
        
        # Создание траектории
        # await app_instance.setup_robot_trajectory("my_robot_traj", [(0, 0, 0), (1, 1, 0), (2, 0, 0)])
        
        # Запуск симуляции
        # await app_instance.run_simulation(100)
        
        print("KengaCAD успешно запущен и готов к работе")
        return True
        
    except Exception as e:
        print(f"Ошибка в работе приложения: {e}")
        return False
    finally:
        # Завершение работы
        await app_instance.shutdown()


if __name__ == "__main__":
    # Запуск асинхронного приложения
    success = asyncio.run(run_kengacad_app())
    if success:
        print("Приложение KengaCAD завершено успешно")
    else:
        print("Приложение KengaCAD завершено с ошибками")
