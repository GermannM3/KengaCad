"""
Система макросов и скриптов Python для KengaCAD.

Поддержка:
  - Запись и воспроизведение макросов
  - Выполнение Python-скриптов
  - API для автоматизации
  - Библиотека готовых скриптов
"""
import os
import sys
import json
import traceback
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
import importlib.util


@dataclass
class MacroCommand:
    """Одна команда макроса."""
    command: str
    args: List[str] = field(default_factory=list)
    description: str = ""
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict:
        return {
            "command": self.command,
            "args": self.args,
            "description": self.description,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MacroCommand":
        return cls(
            command=data["command"],
            args=data.get("args", []),
            description=data.get("description", ""),
            timestamp=data.get("timestamp", 0),
        )

    def to_string(self) -> str:
        args_str = " ".join(self.args) if self.args else ""
        return f"{self.command} {args_str}".strip()


@dataclass
class Macro:
    """Макрос — последовательность команд."""
    name: str
    description: str = ""
    commands: List[MacroCommand] = field(default_factory=list)
    author: str = ""
    version: str = "1.0"
    created: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "commands": [c.to_dict() for c in self.commands],
            "author": self.author,
            "version": self.version,
            "created": self.created,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Macro":
        macro = cls(
            name=data["name"],
            description=data.get("description", ""),
            author=data.get("author", ""),
            version=data.get("version", "1.0"),
            created=data.get("created", 0),
        )
        macro.commands = [MacroCommand.from_dict(c) for c in data.get("commands", [])]
        return macro

    def save(self, filepath: str) -> bool:
        """Сохранить макрос в файл."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения макроса: {e}")
            return False

    @classmethod
    def load(cls, filepath: str) -> Optional["Macro"]:
        """Загрузить макрос из файла."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except Exception as e:
            print(f"Ошибка загрузки макроса: {e}")
            return None

    def add_command(self, command: str, args: List[str] = None, description: str = ""):
        """Добавить команду в макрос."""
        self.commands.append(MacroCommand(
            command=command,
            args=args or [],
            description=description,
        ))

    def execute(self, executor: Any) -> Dict[str, Any]:
        """
        Выполнить макрос.

        Args:
            executor: объект с методом _parse_command(str)

        Returns:
            {"success": bool, "executed": int, "errors": [...]}
        """
        results = {"success": True, "executed": 0, "errors": []}

        for cmd in self.commands:
            try:
                cmd_str = cmd.to_string()
                if hasattr(executor, '_parse_command'):
                    executor._parse_command(cmd_str)
                elif hasattr(executor, 'execute_command'):
                    executor.execute_command(cmd_str)
                else:
                    results["errors"].append(f"Нет исполнителя для: {cmd_str}")
                    results["success"] = False
                    break

                results["executed"] += 1
            except Exception as e:
                results["errors"].append(f"Ошибка команды '{cmd.command}': {e}")
                results["success"] = False

        return results


class MacroRecorder:
    """Запись макросов."""

    def __init__(self):
        self.is_recording = False
        self.current_macro: Optional[Macro] = None
        self._paused = False

    def start_recording(self, name: str, description: str = ""):
        """Начать запись макроса."""
        self.is_recording = True
        self._paused = False
        self.current_macro = Macro(name=name, description=description)

    def stop_recording(self) -> Optional[Macro]:
        """Остановить запись."""
        self.is_recording = False
        macro = self.current_macro
        self.current_macro = None
        return macro

    def pause_recording(self):
        """Пауза записи."""
        self._paused = True

    def resume_recording(self):
        """Возобновить запись."""
        self._paused = False

    def record_command(self, command: str, args: List[str] = None, description: str = ""):
        """Записать команду."""
        if self.is_recording and not self._paused and self.current_macro:
            self.current_macro.add_command(command, args, description)


class PythonScriptEngine:
    """Движок для выполнения Python-скриптов."""

    def __init__(self, app_context: Any = None):
        """
        Args:
            app_context: контекст приложения (main_window, app_instance)
        """
        self.app_context = app_context
        self.variables: Dict[str, Any] = {}
        self.functions: Dict[str, Callable] = {}
        self._register_builtins()

    def _register_builtins(self):
        """Зарегистрировать встроенные функции."""
        # KengaCAD API
        self.functions.update({
            "command": self._cmd,
            "draw_line": self._draw_line,
            "draw_circle": self._draw_circle,
            "draw_polyline": self._draw_polyline,
            "load_robot": self._load_robot,
            "set_trajectory": self._set_trajectory,
            "simulate": self._simulate,
            "export": self._export,
            "message": self._message,
            "input": self._input,
            "math": __import__("math"),
        })

    def _cmd(self, cmd: str):
        """Выполнить команду KengaCAD."""
        if self.app_context and hasattr(self.app_context, '_parse_command'):
            self.app_context._parse_command(cmd)

    def _draw_line(self, x1: float, y1: float, x2: float, y2: float):
        """Нарисовать линию."""
        self._cmd(f"LINE {x1} {y1} {x2} {y2}")

    def _draw_circle(self, x: float, y: float, r: float):
        """Нарисовать окружность."""
        self._cmd(f"CIRCLE {x} {y} {r}")

    def _draw_polyline(self, *points):
        """Нарисовать полилинию."""
        pts_str = " ".join(f"{x} {y}" for x, y in points)
        self._cmd(f"POLYLINE {pts_str}")

    def _load_robot(self, config: str = "kuka_kr6r900"):
        """Загрузить робота."""
        self._cmd(f"LOAD_ROBOT --config {config}")

    def _set_trajectory(self, *points):
        """Установить траекторию."""
        # Сохранить точки для последующего использования
        self.variables['_trajectory_points'] = points

    def _simulate(self, steps: int = 60):
        """Запустить симуляцию."""
        self._cmd(f"SIMULATE {steps}")

    def _export(self, path: str, format: str = "json"):
        """Экспорт траектории."""
        if format == "gcode":
            self._cmd("EXPORT_GCODE")
        else:
            self._cmd(f"EXPORT_TRAC {path}")

    def _message(self, msg: str):
        """Показать сообщение."""
        print(f"[KengaCAD] {msg}")
        if self.app_context and hasattr(self.app_context, 'statusBar'):
            self.app_context.statusBar().showMessage(msg)

    def _input(self, prompt: str, default: str = "") -> str:
        """Запросить ввод у пользователя."""
        # В реальном приложении использовать диалог
        return self.variables.get('_input_result', default)

    def execute_script(self, script: str) -> Dict[str, Any]:
        """
        Выполнить Python-скрипт.

        Returns:
            {"success": bool, "result": Any, "error": str}
        """
        try:
            # Создать безопасное окружение
            safe_globals = {
                "__builtins__": {
                    "print": print,
                    "len": len,
                    "range": range,
                    "str": str,
                    "int": int,
                    "float": float,
                    "list": list,
                    "dict": dict,
                    "tuple": tuple,
                    "min": min,
                    "max": max,
                    "sum": sum,
                    "abs": abs,
                    "pow": pow,
                    "round": round,
                },
                **self.functions,
                **self.variables,
            }

            local_vars = {}
            exec(script, safe_globals, local_vars)

            # Сохранить переменные
            self.variables.update(local_vars)

            return {
                "success": True,
                "result": local_vars.get('result'),
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc(),
            }

    def execute_file(self, filepath: str) -> Dict[str, Any]:
        """Выполнить скрипт из файла."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                script = f.read()
            return self.execute_script(script)
        except Exception as e:
            return {
                "success": False,
                "error": f"Ошибка чтения файла: {e}",
            }

    def load_module(self, filepath: str, module_name: str = None):
        """
        Загрузить Python-модуль.

        Args:
            filepath: путь к .py файлу
            module_name: имя модуля

        Returns:
            загруженный модуль
        """
        if module_name is None:
            module_name = Path(filepath).stem

        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


class ScriptLibrary:
    """Библиотека готовых скриптов."""

    def __init__(self):
        self.scripts_dir = Path(__file__).parent.parent / "scripts"
        self.scripts_dir.mkdir(exist_ok=True)

    def list_scripts(self) -> List[Dict[str, str]]:
        """Список доступных скриптов."""
        scripts = []
        for f in self.scripts_dir.glob("*.py"):
            scripts.append({
                "name": f.stem,
                "path": str(f),
                "size": f"{f.stat().st_size} bytes",
            })
        return scripts

    def get_script(self, name: str) -> Optional[str]:
        """Получить содержимое скрипта."""
        path = self.scripts_dir / f"{name}.py"
        if path.exists():
            return path.read_text(encoding='utf-8')
        return None

    def save_script(self, name: str, content: str) -> bool:
        """Сохранить скрипт."""
        path = self.scripts_dir / f"{name}.py"
        try:
            path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Ошибка сохранения скрипта: {e}")
            return False

    def create_example_scripts(self):
        """Создать примерные скрипты."""
        examples = {
            "draw_rectangle": '''
# Прямоугольник
def main(width, height):
    command(f"LINE 0 0 {width} 0")
    command(f"LINE {width} 0 {width} {height}")
    command(f"LINE {width} {height} 0 {height}")
    command(f"LINE 0 {height} 0 0")
    result = "Прямоугольник создан"
    return result
''',
            "pattern_bolt_holes": '''
# Массив отверстий под болты
def main(diameter, bolt_circle_diameter, num_holes):
    import math
    radius = bolt_circle_diameter / 2
    for i in range(num_holes):
        angle = 2 * math.pi * i / num_holes
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        command(f"CIRCLE {x} {y} {diameter/2}")
    result = f"Создано {num_holes} отверстий"
    return result
''',
            "spiral_trajectory": '''
# Спиральная траектория
def main(turns=3, radius=100, height=50, points=100):
    import math
    traj = []
    for i in range(points):
        t = i / (points - 1)
        angle = 2 * math.pi * turns * t
        r = radius * t
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        z = height * t
        traj.append((x, y, z))
    
    # Экспорт в G-код
    gcode = ["; Spiral trajectory", "G21", "G90"]
    for i, (x, y, z) in enumerate(traj):
        if i == 0:
            gcode.append(f"G0 X{x:.3f} Y{y:.3f} Z{z:.3f}")
        else:
            gcode.append(f"G1 X{x:.3f} Y{y:.3f} Z{z:.3f}")
    gcode.append("M30")
    
    # Сохранить
    with open("spiral.nc", "w") as f:
        f.write("\\n".join(gcode))
    
    result = "Спираль экспортирована в spiral.nc"
    return result
''',
            "gear_generator": '''
# Простая шестерня
def main(teeth=20, module=2, pressure_angle=20):
    import math
    
    pitch_diameter = teeth * module
    addendum = module
    dedendum = 1.25 * module
    outer_diameter = pitch_diameter + 2 * addendum
    root_diameter = pitch_diameter - 2 * dedendum
    
    points = []
    for i in range(teeth * 4):
        angle = 2 * math.pi * i / (teeth * 4)
        
        # Профиль зуба (упрощённо)
        if i % 4 == 0:
            r = outer_diameter / 2
        elif i % 4 == 1:
            r = pitch_diameter / 2
        elif i % 4 == 2:
            r = root_diameter / 2
        else:
            r = pitch_diameter / 2
        
        x = r * math.cos(angle)
        y = r * math.sin(angle)
        points.append((x, y))
    
    # Создать полилинию
    pts_str = " ".join(f"{x} {y}" for x, y in points)
    command(f"POLYLINE {pts_str}")
    
    result = f"Шестерня с {teeth} зубьями создана"
    return result
''',
            "dxf_batch_export": '''
# Пакетный экспорт в DXF
def main(output_dir="exports"):
    import os
    os.makedirs(output_dir, exist_ok=True)
    
    # Пример: экспорт нескольких слоёв
    layers = ["0", "Dimensions", "Text"]
    for layer in layers:
        filename = f"{output_dir}/layer_{layer}.dxf"
        command(f"EXPORT_DXF {filename} --layer {layer}")
    
    result = f"Экспортировано {len(layers)} файлов"
    return result
''',
        }

        for name, content in examples.items():
            self.save_script(name, content)


class KengaCADScriptAPI:
    """
    Полноценное API для скриптов KengaCAD.

    Пример использования:
        from scripts.api import KengaCAD

        app = KengaCAD()
        app.draw.line(0, 0, 100, 100)
        app.robot.load("kuka_kr6r900")
        app.trajectory.create([(0,0,0), (100,0,50)])
        app.simulate.run()
    """

    def __init__(self, main_window=None):
        self.main_window = main_window
        self.command = self._CommandExecutor(main_window)
        self.draw = self._DrawAPI(main_window)
        self.robot = self._RobotAPI(main_window)
        self.trajectory = self._TrajectoryAPI(main_window)
        self.simulate = self._SimulateAPI(main_window)
        self.export = self._ExportAPI(main_window)
        self.view = self._ViewAPI(main_window)

    class _CommandExecutor:
        def __init__(self, main_window):
            self._window = main_window

        def __call__(self, cmd: str):
            if self._window:
                self._window._parse_command(cmd)

    class _DrawAPI:
        def __init__(self, main_window):
            self._window = main_window

        def line(self, x1, y1, x2, y2):
            self._window._parse_command(f"LINE {x1} {y1} {x2} {y2}")

        def circle(self, x, y, r):
            self._window._parse_command(f"CIRCLE {x} {y} {r}")

        def arc(self, x, y, r, start, end):
            self._window._parse_command(f"ARC {x} {y} {r} {start} {end}")

        def polyline(self, *points):
            pts = " ".join(f"{x} {y}" for x, y in points)
            self._window._parse_command(f"POLYLINE {pts}")

        def rectangle(self, x1, y1, x2, y2):
            self._window._parse_command(f"RECTANGLE {x1} {y1} {x2} {y2}")

    class _RobotAPI:
        def __init__(self, main_window):
            self._window = main_window

        def load(self, config: str = "demo"):
            if config == "demo":
                self._window._parse_command("LOAD_DEMO_ROBOT")
            else:
                self._window._parse_command(f"LOAD_ROBOT --config {config}")

        def set_joint(self, joint: str, angle: float):
            self._window._parse_command(f"SET_JOINT {joint} {angle}")

        def zero(self):
            for j in range(6):
                self._window._parse_command(f"SET_JOINT J{j+1} 0")

    class _TrajectoryAPI:
        def __init__(self, main_window):
            self._window = main_window

        def create(self, points):
            pts_str = " ".join(f"{x} {y} {z}" for x, y, z in points)
            self._window._parse_command(f"POLYLINE {pts_str}")
            self._window._parse_command("TRAC_FROM_POLYLINE")

        def from_polyline(self):
            self._window._parse_command("TRAC_FROM_POLYLINE")

        def smooth(self, method="chaikin"):
            self._window._parse_command(f"TRAJ_SMOOTH {method}")

    class _SimulateAPI:
        def __init__(self, main_window):
            self._window = main_window

        def run(self, steps=60):
            self._window._parse_command(f"SIMULATE {steps}")

        def pause(self):
            self._window._parse_command("SIM_PAUSE")

        def stop(self):
            self._window._parse_command("SIM_STOP")

        def reset(self):
            self._window._parse_command("SIM_RESET")

    class _ExportAPI:
        def __init__(self, main_window):
            self._window = main_window

        def gcode(self, path=None):
            self._window._parse_command("EXPORT_GCODE")

        def krl(self, path):
            self._window._parse_command(f"EXPORT_TRAC {path}.krl")

        def mod(self, path):
            self._window._parse_command(f"EXPORT_TRAC {path}.mod")

    class _ViewAPI:
        def __init__(self, main_window):
            self._window = main_window

        def zoom_extents(self):
            self._window._parse_command("ZOOM_EXTENTS")

        def top(self):
            self._window._parse_command("VIEW_TOP")

        def front(self):
            self._window._parse_command("VIEW_FRONT")

        def full_3d(self):
            self._window._parse_command("VIEW3D_FULL")

        def preview(self):
            self._window._parse_command("VIEW3D_PREVIEW")


# ============================================================================
#  Менеджер макросов и скриптов
# ============================================================================

class ScriptMacroManager:
    """Управление макросами и скриптами."""

    def __init__(self, main_window=None):
        self.main_window = main_window
        self.recorder = MacroRecorder()
        self.script_engine = PythonScriptEngine(main_window)
        self.library = ScriptLibrary()
        self.macros_dir = Path(__file__).parent.parent / "macros"
        self.macros_dir.mkdir(exist_ok=True)

    def start_recording(self, name: str):
        """Начать запись макроса."""
        self.recorder.start_recording(name)

    def stop_recording(self) -> Optional[Macro]:
        """Остановить запись."""
        return self.recorder.stop_recording()

    def record_command(self, command: str, args: List[str] = None):
        """Записать команду (вызывается из main_window)."""
        self.recorder.record_command(command, args)

    def save_macro(self, macro: Macro) -> bool:
        """Сохранить макрос."""
        path = self.macros_dir / f"{macro.name}.json"
        return macro.save(str(path))

    def load_macro(self, name: str) -> Optional[Macro]:
        """Загрузить макрос."""
        path = self.macros_dir / f"{name}.json"
        if path.exists():
            return Macro.load(str(path))
        return None

    def list_macros(self) -> List[str]:
        """Список макросов."""
        return [f.stem for f in self.macros_dir.glob("*.json")]

    def execute_macro(self, name: str) -> Dict[str, Any]:
        """Выполнить макрос."""
        macro = self.load_macro(name)
        if macro and self.main_window:
            return macro.execute(self.main_window)
        return {"success": False, "error": f"Макрос '{name}' не найден"}

    def execute_script(self, script: str) -> Dict[str, Any]:
        """Выполнить скрипт."""
        return self.script_engine.execute_script(script)

    def execute_script_file(self, filepath: str) -> Dict[str, Any]:
        """Выполнить скрипт из файла."""
        return self.script_engine.execute_file(filepath)

    def create_api(self) -> KengaCADScriptAPI:
        """Создать API для скриптов."""
        return KengaCADScriptAPI(self.main_window)


# Инициализация библиотеки примеров
def init_script_library():
    """Создать примерные скрипты."""
    library = ScriptLibrary()
    library.create_example_scripts()
    print("Библиотека скриптов инициализирована")
