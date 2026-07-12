"""
Полноценное 3D-окно KengaCAD на базе pyvista/pyvistaqt.
Поддержка:
  - 3D-визуализация траекторий, роботов, сцены
  - Загрузка моделей glTF/GLB/OBJ/STEP
  - Интерактивная камера (вращение, панорамирование, зум)
  - Сетка координат, оси, освещение
  - Анимация траекторий
  - Обнаружение коллизий (визуализация)
"""
import sys
from typing import List, Tuple, Optional, Dict, Any
from pathlib import Path

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QMenu
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QColor

import pyvista as pv
from pyvistaqt import QtInteractor

# Проверка доступности trimesh для загрузки моделей
try:
    import trimesh
    _HAS_TRIMESH = True
except ImportError:
    _HAS_TRIMESH = False

# Проверка numpy
try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False


class _ModelLoaderThread(QThread):
    """Поток для загрузки 3D-моделей без блокировки UI."""
    loaded = pyqtSignal(object, str)  # mesh, path
    error = pyqtSignal(str)  # error message

    def __init__(self, path: str):
        super().__init__()
        self.path = path

    def run(self):
        try:
            if not _HAS_TRIMESH:
                self.error.emit("trimesh не установлен. Установите: pip install trimesh")
                return

            mesh = trimesh.load(self.path, force='mesh')
            if isinstance(mesh, trimesh.Scene):
                # Объединить все меши из сцены
                meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
                if meshes:
                    mesh = trimesh.util.concatenate(meshes)
                else:
                    self.error.emit("Пустая сцена или недопустимый формат")
                    return

            # Конвертировать в pyvista
            pv_mesh = pv.wrap(mesh)
            self.loaded.emit(pv_mesh, self.path)
        except Exception as e:
            self.error.emit(f"Ошибка загрузки: {e}")


class View3DFull(QWidget):
    """Полноценное 3D-окно с pyvista."""

    modelLoaded = pyqtSignal(str, bool)  # path, success
    trajectoryChanged = pyqtSignal(list)
    simulationFinished = pyqtSignal()
    collisionDetected = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._trajectory_points: List[Tuple[float, float, float]] = []
        self._loaded_models: Dict[str, Any] = {}
        self._trajectory_actor = None
        self._points_actors = []
        self._grid_actor = None
        self._axes_actor = None
        self._simulation_timer: Optional[QTimer] = None
        self._sim_step = -1
        self._sim_marker = None

        self._setup_ui()
        self._setup_scene()

    def _setup_ui(self):
        """Настройка UI."""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Панель управления
        control_panel = self._create_control_panel()
        self.layout.addWidget(control_panel)

        # 3D виджет
        self.vl = QHBoxLayout()
        self.plotter = QtInteractor(self)
        self.vl.addWidget(self.plotter.interactor)
        self.layout.addLayout(self.vl)

        # Статус бар
        self._status_label = QLabel("3D сцена готова")
        self._status_label.setStyleSheet("color: #888; padding: 4px; background: #2b2b2b;")
        self.layout.addWidget(self._status_label)

    def _create_control_panel(self) -> QWidget:
        """Панель управления 3D-сценой."""
        panel = QWidget()
        panel.setStyleSheet("background: #3c3f41; padding: 4px;")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)

        # Загрузка модели
        self._load_btn = QPushButton("📂 Загрузить модель")
        self._load_btn.setToolTip("Загрузить 3D-модель (glTF/GLB/OBJ/STEP)")
        self._load_btn.clicked.connect(self._on_load_model)
        layout.addWidget(self._load_btn)

        # Выбор вида
        self._view_combo = QComboBox()
        self._view_combo.addItems(["Изометрия", "Сверху", "Спереди", "Слева", "Справа", "Снизу", "Сзади"])
        self._view_combo.setCurrentIndex(0)
        self._view_combo.setStyleSheet("background: #505354; color: #e0e0e0; padding: 2px;")
        self._view_combo.currentIndexChanged.connect(self._on_view_changed)
        layout.addWidget(self._view_combo)

        # Сетка
        self._grid_btn = QPushButton("🔲 Сетка")
        self._grid_btn.setCheckable(True)
        self._grid_btn.setChecked(True)
        self._grid_btn.clicked.connect(self._toggle_grid)
        layout.addWidget(self._grid_btn)

        # Оси
        self._axes_btn = QPushButton("📏 Оси")
        self._axes_btn.setCheckable(True)
        self._axes_btn.setChecked(True)
        self._axes_btn.clicked.connect(self._toggle_axes)
        layout.addWidget(self._axes_btn)

        # Сброс камеры
        self._reset_cam_btn = QPushButton("🔄 Сброс вида")
        self._reset_cam_btn.clicked.connect(self._reset_camera)
        layout.addWidget(self._reset_cam_btn)

        layout.addStretch()

        # Статус
        self._objects_label = QLabel("Объектов: 0")
        self._objects_label.setStyleSheet("color: #4CAF50; padding: 0 8px;")
        layout.addWidget(self._objects_label)

        return panel

    def _setup_scene(self):
        """Инициализация 3D-сцены."""
        self.plotter.set_background('#1e1e1e')
        self.plotter.enable_anti_aliasing()

        # Освещение
        self.plotter.add_light((1, 1, 1), color='white', intensity=1.0)
        self.plotter.add_light((-1, -1, 1), color='white', intensity=0.5)

        # Сетка
        self._grid_actor = self.plotter.add_grid_axes(
            grid_size=(2000, 2000, 0),
            line_width=1.0,
            color='#404040',
        )

        # Оси координат
        self._axes_actor = self.plotter.add_axes(
            line_width=3,
            color_x='#FF0000',
            color_y='#00FF00',
            color_z='#0000FF',
        )

        # Камера
        self._reset_camera()

        self._update_status()

    def _reset_camera(self):
        """Сброс камеры к виду по умолчанию."""
        self.plotter.camera_position = 'iso'
        self.plotter.camera.zoom = 0.8
        self.plotter.render()

    def _on_view_changed(self, index: int):
        """Изменение вида камеры."""
        views = ['iso', 'xy', 'xz', 'yz', '-yz', '-xy', '-xz']
        if index < len(views):
            self.plotter.camera_position = views[index]
            self.plotter.render()

    def _toggle_grid(self, checked: bool):
        """Показать/скрыть сетку."""
        if self._grid_actor:
            self._grid_actor.SetVisibility(checked)
            self.plotter.render()

    def _toggle_axes(self, checked: bool):
        """Показать/скрыть оси."""
        if self._axes_actor:
            self._axes_actor.SetVisibility(checked)
            self.plotter.render()

    def _on_load_model(self):
        """Загрузка 3D-модели."""
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить 3D-модель", "",
            "3D модели (*.gltf *.glb *.obj *.stp *.step);;glTF (*.gltf *.glb);;OBJ (*.obj);;STEP (*.stp *.step);;Все (*)"
        )
        if path:
            self.load_model(path)

    def load_model(self, path: str) -> bool:
        """Загрузить 3D-модель в сцену."""
        if not _HAS_TRIMESH:
            self._status_label.setText("Ошибка: trimesh не установлен")
            return False

        self._status_label.setText(f"Загрузка {Path(path).name}...")
        self._loader = _ModelLoaderThread(path)
        self._loader.loaded.connect(self._on_model_loaded)
        self._loader.error.connect(self._on_model_error)
        self._loader.start()
        return True

    def _on_model_loaded(self, mesh, path: str):
        """Модель загружена."""
        try:
            # Добавить в сцену
            actor = self.plotter.add_mesh(
                mesh,
                name=Path(path).stem,
                color='#808080',
                metallic=0.3,
                roughness=0.7,
            )
            self._loaded_models[path] = actor
            self._update_status()
            self._status_label.setText(f"✅ {Path(path).name}")
            self.modelLoaded.emit(path, True)
        except Exception as e:
            self._on_model_error(str(e))

    def _on_model_error(self, error: str):
        """Ошибка загрузки модели."""
        self._status_label.setText(f"❌ {error}")
        self.modelLoaded.emit("", False)

    def set_trajectory_points(self, points: List[Tuple[float, float, float]]):
        """Установить точки траектории."""
        self._trajectory_points = list(points) if points else []

        # Удалить старую траекторию
        if self._trajectory_actor:
            self.plotter.remove_actor(self._trajectory_actor)
        for actor in self._points_actors:
            self.plotter.remove_actor(actor)
        self._points_actors = []

        if not self._trajectory_points or len(self._trajectory_points) < 2:
            self.plotter.render()
            self.trajectoryChanged.emit(self._trajectory_points)
            return

        if not _HAS_NP:
            return

        # Создать линию траектории
        points_np = np.array(self._trajectory_points)
        lines = np.column_stack([
            np.arange(len(self._trajectory_points) - 1),
            np.arange(1, len(self._trajectory_points))
        ])
        lines = np.hstack([np.full((lines.shape[0], 1), 2), lines]).ravel()

        poly = pv.PolyData(points_np, lines)
        self._trajectory_actor = self.plotter.add_mesh(
            poly,
            name="trajectory",
            color='#4FC3F7',
            line_width=4,
            render_lines_as_tubes=True,
        )

        # Точки
        for i, pt in enumerate(self._trajectory_points):
            sphere = pv.Sphere(radius=3, center=pt)
            color = '#FF5722' if i == 0 else ('#4CAF50' if i == len(self._trajectory_points) - 1 else '#2196F3')
            actor = self.plotter.add_mesh(
                sphere,
                name=f"point_{i}",
                color=color,
            )
            self._points_actors.append(actor)

        self.plotter.render()
        self.trajectoryChanged.emit(self._trajectory_points)
        self._update_status()

    def start_simulation(self, steps: int = 60, speed: float = 1.0):
        """Запустить симуляцию движения по траектории."""
        if not self._trajectory_points or len(self._trajectory_points) < 2:
            return False

        self._stop_simulation()

        # Создать маркер
        if self._sim_marker:
            self.plotter.remove_actor(self._sim_marker)
        self._sim_marker = self.plotter.add_mesh(
            pv.Sphere(radius=5, center=self._trajectory_points[0]),
            name="sim_marker",
            color='#FFEB3B',
            emissive=True,
        )

        self._sim_step = 0
        self._sim_total = min(steps, len(self._trajectory_points))
        interval = max(16, int(50 / max(0.1, speed)))

        self._simulation_timer = QTimer(self)
        self._simulation_timer.timeout.connect(self._on_sim_tick)
        self._simulation_timer.start(interval)

        self._status_label.setText(f"▶ Симуляция {self._sim_step + 1}/{self._sim_total}")
        return True

    def _stop_simulation(self):
        """Остановить симуляцию."""
        if self._simulation_timer:
            self._simulation_timer.stop()
            self._simulation_timer.deleteLater()
            self._simulation_timer = None
        self._sim_step = -1
        if self._sim_marker:
            self.plotter.remove_actor(self._sim_marker)
            self._sim_marker = None
        self.plotter.render()
        self.simulationFinished.emit()

    def _on_sim_tick(self):
        """Тик симуляции."""
        if self._sim_step >= 0 and self._sim_step < len(self._trajectory_points):
            pt = self._trajectory_points[self._sim_step]
            if self._sim_marker:
                self.plotter.remove_actor(self._sim_marker)
                self._sim_marker = self.plotter.add_mesh(
                    pv.Sphere(radius=5, center=pt),
                    name="sim_marker",
                    color='#FFEB3B',
                    emissive=True,
                )
            self._status_label.setText(f"▶ Симуляция {self._sim_step + 1}/{self._sim_total}")
            self.plotter.render()

        self._sim_step += 1
        if self._sim_step >= self._sim_total:
            self._stop_simulation()

    def add_robot_model(self, entity_id: str, joints_config: Dict = None):
        """Добавить упрощённую модель робота (схематично)."""
        if not _HAS_NP:
            return

        # Базовая платформа
        base = pv.Cylinder(center=(0, 0, 50), radius=30, height=100)
        self.plotter.add_mesh(base, name=f"{entity_id}_base", color='#607D8B')

        # Звенья (схематично)
        colors = ['#FF5722', '#FF9800', '#FFC107', '#FFEB3B', '#8BC34A', '#4CAF50']
        positions = [
            (0, 0, 150), (100, 0, 150), (200, 0, 150),
            (300, 0, 150), (400, 0, 150), (500, 0, 150)
        ]

        for i, pos in enumerate(positions):
            link = pv.Sphere(radius=20, center=pos)
            self.plotter.add_mesh(link, name=f"{entity_id}_link_{i}", color=colors[i])

        # TCP маркер
        tcp = pv.Cone(center=(600, 0, 150), direction=(1, 0, 0), height=40, radius=10)
        self.plotter.add_mesh(tcp, name=f"{entity_id}_tcp", color='#F44336')

        self._update_status()

    def visualize_collisions(self, collisions: List[Dict]):
        """Визуализировать коллизии."""
        if not collisions:
            return

        for i, col in enumerate(collisions):
            point = col.get('point', (0, 0, 0))
            sphere = pv.Sphere(radius=15, center=point)
            self.plotter.add_mesh(
                sphere,
                name=f"collision_{i}",
                color='#F44336',
                opacity=0.7,
            )

        self.collisionDetected.emit(collisions)
        self._status_label.setText(f"⚠ Найдено коллизий: {len(collisions)}")
        self.plotter.render()

    def clear_scene(self):
        """Очистить сцену."""
        for name in list(self._loaded_models.keys()):
            if name in self.plotter.renderer.actors:
                self.plotter.remove_actor(name)
        self._loaded_models.clear()

        if self._trajectory_actor:
            self.plotter.remove_actor(self._trajectory_actor)
            self._trajectory_actor = None

        for actor in self._points_actors:
            self.plotter.remove_actor(actor)
        self._points_actors = []

        self._trajectory_points = []
        self._stop_simulation()
        self._update_status()
        self.plotter.render()

    def _update_status(self):
        """Обновить статус бар."""
        count = len(self._loaded_models) + (1 if self._trajectory_actor else 0)
        self._objects_label.setText(f"Объектов: {count}")

    def contextMenuEvent(self, event):
        """Контекстное меню."""
        menu = QMenu(self)

        menu.addAction("🔄 Сброс вида", self._reset_camera)
        menu.addAction("📸 Скриншот", self._take_screenshot)
        menu.addSeparator()
        menu.addAction("🗑 Очистить сцену", self.clear_scene)

        if self._sim_step >= 0:
            menu.addAction("⏹ Остановить симуляцию", self._stop_simulation)

        menu.exec_(event.globalPos())

    def _take_screenshot(self):
        """Сделать скриншот."""
        from PyQt5.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить скриншот", "", "PNG (*.png);;JPEG (*.jpg);;Все (*)"
        )
        if path:
            self.plotter.screenshot(path)
            self._status_label.setText(f"📸 Скриншот: {Path(path).name}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'plotter'):
            self.plotter.render()
