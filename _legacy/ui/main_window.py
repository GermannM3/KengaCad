"""
Главное окно KengaCAD
"""
import os
import sys
import json
import math
import copy
from pathlib import Path
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStatusBar, QListWidget, QListWidgetItem, QPushButton,
                             QLineEdit, QTabWidget, QDockWidget, QMenuBar, QMenu,
                             QToolBar, QLabel, QFileDialog, QMessageBox, QInputDialog, QAction, QSplitter, QComboBox, QDialog,
                             QTextEdit, QDialogButtonBox)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QIcon, QKeySequence, QPainter
from PyQt5.QtPrintSupport import QPrinter

from ui.ribbon_bar import KengaCADRibbonBar
from ui.command_line import CommandLine
from ui.drawing_area import DrawingArea
from ui.view3d_preview import View3DPreview
try:
    from ui.view3d_full import View3DFull
    _HAS_VIEW3D_FULL = True
except ImportError:
    View3DFull = None
    _HAS_VIEW3D_FULL = False
from ui.trajectory_edit_dialog import TrajectoryEditDialog
from ui.properties_panel import PropertiesPanel
from ui.trajectory_code_panel import TrajectoryCodePanel
from ui.view3d_scene import View3DScene
from ui.scene_tree_widget import SceneTreeWidget
from ui.workcell_dialogs import AddBoxDialog, AddConveyorDialog, AddFenceDialog, ObjectPropertiesDialog
from ui.joint_status_panel import JointStatusPanel
from ui.tcp_position_panel import TCPPositionPanel
from ui.plc_panel import PLCPanel
from ui.shop_panel import ShopFloorPanel
from ui.gantt_panel import VirtualCommissioningPanel
from cad.import_export import CADImportExport
from cad.collision import check_collisions_local, check_collisions_mesh
from cad.step_import import can_import_step, load_step, load_iges, get_backend_info, load_stl
from cad.kinematics import fk_6dof, fk_full, ik_6dof, check_reachability as kinematics_reachability
from cad.robot_kinematics import get_robot_config, list_available_robots, ik_6dof_numerical, fk_6dof_full
from cad.advanced_trajectory import AdvancedTrajectoryManager, TrajectoryPoint, generate_spiral, generate_zigzag
from cad.dwg_setup import is_odafc_available, get_odafc_path_from_config, save_odafc_path, apply_odafc_path, open_oda_download_page




class _AsyncCommandThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, coro, label: str):
        super().__init__()
        self.coro = coro
        self.label = label

    def run(self):
        try:
            import asyncio
            asyncio.run(self.coro)
            self.finished.emit(True, self.label)
        except Exception as e:
            self.finished.emit(False, f"{self.label}: {e}")


class KengaCADMainWindow(QMainWindow):
    def _load_app_meta(self) -> dict:
        try:
            base = Path(__file__).resolve().parent.parent
            settings = base / "config" / "settings.json"
            if getattr(sys, "frozen", False):
                internal = Path(sys.executable).parent / "_internal" / "config" / "settings.json"
                settings = internal if internal.exists() else settings
            if settings.exists():
                return json.loads(settings.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return {}

    def _settings_path(self) -> Path:
        base = Path(__file__).resolve().parent.parent
        p = base / "config" / "settings.json"
        if getattr(sys, "frozen", False):
            internal = Path(sys.executable).parent / "_internal" / "config" / "settings.json"
            return internal if internal.exists() else p
        return p

    def _app_title(self) -> str:
        meta = self._load_app_meta()
        app = meta.get("app", {}) if isinstance(meta, dict) else {}
        name = app.get("product_name") or app.get("name") or "KengaCAD"
        version = app.get("version") or ""
        if version:
            return f"{name} {version}"
        return str(name)

    def __init__(self, app_thread=None):
        super().__init__()
        self.setWindowTitle(self._app_title())
        self.setGeometry(100, 100, 1400, 900)

        self._set_window_icon()
        self._apply_stylesheet()

        # Храним ссылку на поток приложения
        self.app_thread = app_thread
        self.app = None
        self.cad_entities = {"lines": [], "circles": [], "points": [], "arcs": [], "polylines": [], "texts": [], "splines": [], "ellipses": [], "dimensions": [], "hatches": [], "inserts": []}
        self.blocks: dict = {}
        self.layers = {"0": {"visible": True, "color": "#FFFFFF"}}
        self.active_layer = "0"
        self.current_linetype = "Continuous"
        self.ortho_mode = False
        self.polar_mode = False
        self.snap_types = {"E", "M", "I", "C", "N"}
        self._redo_stack: list[tuple[str, dict]] = []
        self._current_file: str | None = None
        self._is_modified = False
        self._last_trajectory_points: list[tuple[float, float, float]] = []
        meta = self._load_app_meta()
        disp = meta.get("dispensing", {}) if isinstance(meta, dict) else {}
        self._dispensing_flow = float(disp.get("default_flow_rate", 1.0))
        self._dispensing_radius = float(disp.get("default_radius", 0.02))
        self._scene_objects: list = []
        self._fk_ik_block = False

        # Применить путь ODA из настроек (если main.py не вызывался)
        try:
            path = get_odafc_path_from_config()
            if path:
                apply_odafc_path(path)
        except Exception:
            pass

        # Инициализация UI
        self._setup_ui()

        # Статус бар
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Подключение к движку Kenga...")
        self._conn_indicator = QLabel("Подключение...")
        self._conn_indicator.setToolTip("Статус подключения к 3D-движку")
        self._conn_indicator.setStyleSheet("color: #888; font-weight: bold; padding: 0 6px;")
        self.statusBar().addPermanentWidget(self._conn_indicator)
        self._redo_label = QLabel("")
        self._redo_label.setToolTip("Повторить (Ctrl+Y)")
        self.statusBar().addPermanentWidget(self._redo_label)
        self._set_modified(False)

    def _apply_stylesheet(self):
        """Стиль в духе профессионального CAD"""
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QMenuBar { background-color: #3c3f41; color: #e0e0e0; }
            QMenuBar::item { background-color: transparent; color: #e0e0e0; padding: 4px 8px; }
            QMenuBar::item:selected { background-color: #505354; color: #ffffff; }
            QMenu { background-color: #3c3f41; color: #e0e0e0; }
            QMenu::item { color: #e0e0e0; }
            QMenu::item:selected { background-color: #505354; color: #ffffff; }
            QDockWidget { 
                background-color: #3c3f41; 
                color: #bbbbbb;
                font-size: 11px;
                titlebar-close-icon: none;
            }
            QDockWidget::title { 
                background-color: #45494a; 
                color: #ffffff;
                padding: 6px 8px;
                font-weight: bold;
            }
            QPushButton { 
                background-color: #505354; 
                color: #ffffff;
                border: 1px solid #6c6c6c;
                border-radius: 3px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover { background-color: #5a5d5e; }
            QPushButton:pressed { background-color: #404244; }
            QListWidget { 
                background-color: #3c3f41; 
                color: #bbbbbb;
                border: 1px solid #555555;
            }
            QListWidget::item:selected { background-color: #214283; }
            RibbonBar, QWidget#KengaCADRibbonBar { background-color: #3c3f41; color: #e0e0e0; }
            QToolButton { background-color: transparent; color: #e0e0e0; border: none; }
            QToolButton:hover { background-color: #505354; color: #ffffff; }
            QToolButton:pressed { background-color: #404244; }
            QTabBar::tab { background-color: #45494a; color: #e0e0e0; padding: 8px 16px; }
            QTabBar::tab:selected { background-color: #505354; color: #ffffff; }
        """)

    def _set_window_icon(self):
        """Установка иконки окна (logo.ico или logo.png)"""
        try:
            from PyQt5.QtGui import QPixmap, QIcon
            import os
            base = Path(__file__).resolve().parent.parent
            for name in ("logo.ico", "logo.png"):
                icon_path = base / "assets" / name
                if icon_path.exists():
                    self.setWindowIcon(QIcon(str(icon_path)))
                    break
        except Exception as e:
            print(f"[WARN] Не удалось загрузить иконку: {e}")

    def on_app_initialized(self, success, app_thread):
        """Handle app init result from background thread"""
        if success and app_thread:
                self.app = app_thread.get_app()
        if success and self.app:
            self._conn_indicator.setText("Local")
            self._conn_indicator.setStyleSheet("color: #4CAF50; font-weight: bold; padding: 0 6px;")
            self._conn_indicator.setToolTip("Встроенный движок. POLYLINE → TRAC_FROM_POLYLINE → SIMULATE")
            self.statusBar().showMessage("Локальный режим. POLYLINE → TRAC_FROM_POLYLINE → SIMULATE")
        else:
            self._conn_indicator.setText("Error")
            self._conn_indicator.setStyleSheet("color: #f44336; font-weight: bold; padding: 0 6px;")
            self.statusBar().showMessage("Ошибка инициализации")

    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Создание меню
        self._create_menu()
        
        # Создание Ribbon бара (аналог AutoCAD Ribbon)
        self.ribbon = KengaCADRibbonBar(self)
        self.setMenuWidget(self.ribbon)
        
        # Центральная область — split view 2D + 3D (как RoboCAD)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Splitter: 2D слева, 3D превью справа
        self._splitter = QSplitter(Qt.Horizontal)
        self.drawing_area = DrawingArea()
        self.drawing_area.cursorMoved.connect(self._on_cursor_moved)
        self.drawing_area.entityClicked.connect(self._on_entity_clicked)
        self.drawing_area.selectionBoxFinished.connect(self._on_selection_box)
        self.drawing_area.pointPicked.connect(self._on_point_picked)
        self.drawing_area.setContextMenuPolicy(Qt.CustomContextMenu)
        self.drawing_area.customContextMenuRequested.connect(self._on_drawing_context_menu)
        self._interactive_mode = None
        self._last_command = ""
        self._last_args: list = []
        self._multiple_mode = False
        self._splitter.addWidget(self.drawing_area)
        
        # 3D Preview (старый изометрический вид)
        self._view3d = View3DPreview()
        self._view3d.setMinimumWidth(240)
        self._view3d.pointsChanged.connect(self._on_view3d_points_changed)
        self._splitter.addWidget(self._view3d)

        # Полноценное 3D-окно (PyVista) — по умолчанию скрыто
        if _HAS_VIEW3D_FULL and View3DFull is not None:
            self._view3d_full = View3DFull()
            self._view3d_full.setVisible(False)
            self._view3d_full.modelLoaded.connect(self._on_3d_model_loaded)
            self._view3d_full.trajectoryChanged.connect(self._on_3d_trajectory_changed)
            self._view3d_full.simulationFinished.connect(self._on_3d_simulation_finished)
            self._view3d_full.collisionDetected.connect(self._on_3d_collision_detected)
        else:
            self._view3d_full = None

        # Менеджер расширенных траекторий
        self._traj_manager = AdvancedTrajectoryManager()

        # Переключатель режимов 3D
        self._3d_mode = "preview"  # "preview" или "full"
        
        self._splitter.setSizes([720, 280])
        self._splitter.setCollapsible(1, True)
        self.layout.addWidget(self._splitter)
        self._selected: list[tuple[str, int]] = []
        
        # Командная строка (как в AutoCAD)
        self.command_line = CommandLine()
        # Hotkeys (AutoCAD-like)
        ortho_action = QAction(self)
        ortho_action.setShortcut(QKeySequence("F8"))
        ortho_action.triggered.connect(self._toggle_ortho)
        self.addAction(ortho_action)

        polar_action = QAction(self)
        polar_action.setShortcut(QKeySequence("F10"))
        polar_action.triggered.connect(self._toggle_polar)
        self.addAction(polar_action)

        new_action = QAction(self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_file)
        self.addAction(new_action)

        zoom_extents_action = QAction(self)
        zoom_extents_action.setShortcut(QKeySequence("Ctrl+0"))
        zoom_extents_action.triggered.connect(self._zoom_extents)
        self.addAction(zoom_extents_action)

        erase_action = QAction(self)
        erase_action.setShortcut(QKeySequence.Delete)
        erase_action.triggered.connect(self._erase_selected)
        self.addAction(erase_action)

        esc_action = QAction(self)
        esc_action.setShortcut(QKeySequence("Escape"))
        esc_action.triggered.connect(self._on_escape)
        self.addAction(esc_action)

        select_all_action = QAction(self)
        select_all_action.setShortcut(QKeySequence("Ctrl+A"))
        select_all_action.triggered.connect(self._select_all)
        self.addAction(select_all_action)

        self.command_line.returnPressed.connect(self._execute_command)
        cmd_row = QHBoxLayout()
        cmd_row.addWidget(self.command_line)
        btn_help = QPushButton("?")
        btn_help.setToolTip("Быстрый старт — как работать")
        btn_help.setFixedWidth(32)
        btn_help.clicked.connect(self._show_quick_start)
        cmd_row.addWidget(btn_help)
        self.layout.addLayout(cmd_row)
        # Objects panel
        self.objects_list = QListWidget()
        self.btn_delete_last = QPushButton("Удалить последний")
        self.btn_delete_last.clicked.connect(self._delete_last_entity)

        dock_widget = QWidget()
        dock_layout = QVBoxLayout(dock_widget)
        dock_layout.addWidget(self.objects_list)
        dock_layout.addWidget(self.btn_delete_last)

        self.objects_dock = QDockWidget("Объекты", self)
        self.objects_dock.setWidget(dock_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.objects_dock)

        # Панель свойств (как в AutoCAD)
        self._properties_panel = PropertiesPanel(self)
        self.properties_dock = QDockWidget("Свойства", self)
        self.properties_dock.setWidget(self._properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)

        # Layers panel
        self.layers_list = QListWidget()
        self.layers_list.itemChanged.connect(self._on_layer_item_changed)
        self.btn_layer_add = QPushButton("Добавить слой")
        self.btn_layer_delete = QPushButton("Удалить слой")
        self.btn_layer_set_active = QPushButton("Текущий")
        self.btn_layer_add.clicked.connect(self._add_layer)
        self.btn_layer_delete.clicked.connect(self._delete_layer)
        self.btn_layer_set_active.clicked.connect(self._set_active_layer)

        layers_widget = QWidget()
        layers_layout = QVBoxLayout(layers_widget)
        layers_layout.addWidget(self.layers_list)
        layers_btns = QHBoxLayout()
        layers_btns.addWidget(self.btn_layer_add)
        layers_btns.addWidget(self.btn_layer_delete)
        layers_btns.addWidget(self.btn_layer_set_active)
        layers_layout.addLayout(layers_btns)

        self.layers_dock = QDockWidget("Слои", self)
        self.layers_dock.setWidget(layers_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.layers_dock)
        self._refresh_layers_list()

        # Snap types panel
        self.snap_types_list = QListWidget()
        snap_tips = {"E": "Конец (Endpoint)", "M": "Середина (Midpoint)", "I": "Пересечение (Intersection)", "C": "Центр (Center)", "N": "Ближайшая (Nearest)"}
        for label in ("E", "M", "I", "C", "N"):
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setToolTip(snap_tips.get(label, label))
            self.snap_types_list.addItem(item)
        self.snap_types_list.itemChanged.connect(self._on_snap_type_changed)

        snap_widget = QWidget()
        snap_layout = QVBoxLayout(snap_widget)
        snap_layout.addWidget(self.snap_types_list)
        self.snap_dock = QDockWidget("Привязки", self)
        self.snap_dock.setWidget(snap_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.snap_dock)

        # Панель 3D / Робот — быстрый доступ к демо-сценарию (как в RoboCAD)
        robot_panel = QWidget()
        robot_layout = QVBoxLayout(robot_panel)
        robot_intro = QLabel("Траектория: Полилиния → TRAC_FROM_POLYLINE → Робот → SIMULATE")
        robot_intro.setStyleSheet("color: #aaa; font-size: 10px; padding: 4px;")
        robot_intro.setWordWrap(True)
        robot_layout.addWidget(robot_intro)
        robot_layout.addWidget(QLabel("Робот:"))
        self._robot_combo = QComboBox()
        self._robot_combo.setStyleSheet("background: #3c3f41; color: #e0e0e0; padding: 4px;")
        self._populate_robot_combo()
        robot_layout.addWidget(self._robot_combo)
        btn_robot = QPushButton("Загрузить выбранного робота")
        btn_robot.setToolTip("LOAD_DEMO_ROBOT или LOAD_ROBOT — по выбору")
        btn_robot.clicked.connect(self._load_selected_robot)
        robot_layout.addWidget(btn_robot)
        btn_robot_custom = QPushButton("Своя модель...")
        btn_robot_custom.setToolTip("Выбрать glTF/GLB/OBJ файл")
        btn_robot_custom.clicked.connect(lambda: self._parse_command("LOAD_ROBOT"))
        robot_layout.addWidget(btn_robot_custom)
        btn_trac = QPushButton("Траектория из полилинии")
        btn_trac.setToolTip("TRAC_FROM_POLYLINE — из последней полилинии")
        btn_trac.clicked.connect(lambda: self._parse_command("TRAC_FROM_POLYLINE"))
        robot_layout.addWidget(btn_trac)
        btn_edit_trac = QPushButton("Редактировать траекторию")
        btn_edit_trac.setToolTip("EDIT_TRAC — таблица координат X,Y,Z")
        btn_edit_trac.clicked.connect(self._edit_trajectory)
        robot_layout.addWidget(btn_edit_trac)
        robot_layout.addWidget(QLabel("Скорость:"))
        self._sim_speed_combo = QComboBox()
        self._sim_speed_combo.addItems(["0.5x", "1x", "2x"])
        self._sim_speed_combo.setCurrentIndex(1)
        self._sim_speed_combo.setStyleSheet("background: #3c3f41; color: #e0e0e0; padding: 2px;")
        robot_layout.addWidget(self._sim_speed_combo)
        btn_sim = QPushButton("Симуляция")
        btn_sim.setToolTip("SIMULATE — запуск в 3D-окне")
        btn_sim.clicked.connect(lambda: self._parse_command("SIMULATE"))
        robot_layout.addWidget(btn_sim)
        self._joint_status_panel = JointStatusPanel(self)
        self._joint_status_panel.jointsChanged.connect(self._on_joints_changed)
        robot_layout.addWidget(self._joint_status_panel)
        self._tcp_label = QLabel("TCP: —")
        self._tcp_label.setStyleSheet("color: #8ab; font-size: 10px;")
        robot_layout.addWidget(self._tcp_label)
        self._tcp_position_panel = TCPPositionPanel(self)
        self._tcp_position_panel.tcpChanged.connect(self._on_tcp_changed)
        robot_layout.addWidget(self._tcp_position_panel)
        self._fk_ik_block = False  # блокировка петли FK↔IK
        self._robot_combo.currentIndexChanged.connect(self._on_robot_combo_changed)
        self._on_robot_combo_changed()
        robot_layout.addStretch()
        self.robot_dock = QDockWidget("3D / Робот", self)
        self.robot_dock.setWidget(robot_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.robot_dock)

        self._traj_code_panel = TrajectoryCodePanel(self)
        self.traj_code_dock = QDockWidget("Траектория / G-код", self)
        self.traj_code_dock.setWidget(self._traj_code_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.traj_code_dock)

        self._view3d_scene = View3DScene(self)
        self.view3d_scene_dock = QDockWidget("3D сцена (робот)", self)
        self.view3d_scene_dock.setWidget(self._view3d_scene)
        self.addDockWidget(Qt.RightDockWidgetArea, self.view3d_scene_dock)

        # _scene_objects уже инициализирован в __init__ до _setup_ui()
        self._scene_tree_widget = SceneTreeWidget(self)
        self._scene_tree_widget.addTableRequested.connect(self._add_workcell_table)
        self._scene_tree_widget.addFixtureRequested.connect(self._add_workcell_fixture)
        self._scene_tree_widget.addConveyorRequested.connect(self._add_workcell_conveyor)
        self._scene_tree_widget.addFenceRequested.connect(self._add_workcell_fence)
        self._scene_tree_widget.addRobotRequested.connect(self._add_workcell_robot)
        self._scene_tree_widget.deleteRequested.connect(self._delete_scene_object)
        self._scene_tree_widget.visibilityToggled.connect(self._toggle_scene_object_visibility)
        self._scene_tree_widget.objectSelected.connect(self._select_scene_object)
        self._scene_tree_widget.propertiesRequested.connect(self._show_object_properties)
        self._scene_tree_widget.duplicateRequested.connect(self._duplicate_scene_object)
        self.scene_tree_dock = QDockWidget("Дерево сцены", self)
        self.scene_tree_dock.setWidget(self._scene_tree_widget)
        self.addDockWidget(Qt.RightDockWidgetArea, self.scene_tree_dock)

        # PLC-сигналы панель
        self._plc_panel = PLCPanel(self)
        self._plc_panel.signalChanged.connect(self._on_plc_signal_changed)
        self.plc_dock = QDockWidget("PLC / Сигналы I/O", self)
        self.plc_dock.setWidget(self._plc_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.plc_dock)

        # Цех — Astra / Ред ОС / заводская LAN
        self._shop_panel = ShopFloorPanel(self)
        self._shop_panel.statusMessage.connect(lambda m: self.statusBar().showMessage(m, 8000))
        self.shop_dock = QDockWidget("Цех (Linux)", self)
        self.shop_dock.setWidget(self._shop_panel)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.shop_dock)

        # Virtual Commissioning панель
        self._vc_panel = VirtualCommissioningPanel(self)
        self._vc_panel.set_signal_table(self._plc_panel.signal_table)
        self.vc_dock = QDockWidget("Virtual Commissioning", self)
        self.vc_dock.setWidget(self._vc_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.vc_dock)

        # Табы правых доков — Объекты, Свойства, 3D/Робот, G-код, 3D сцена, Дерево, PLC, VC
        self.tabifyDockWidget(self.objects_dock, self.properties_dock)
        self.tabifyDockWidget(self.objects_dock, self.robot_dock)
        self.tabifyDockWidget(self.objects_dock, self.traj_code_dock)
        self.tabifyDockWidget(self.objects_dock, self.view3d_scene_dock)
        self.tabifyDockWidget(self.objects_dock, self.scene_tree_dock)
        self.tabifyDockWidget(self.objects_dock, self.plc_dock)
        self.tabifyDockWidget(self.objects_dock, self.vc_dock)

        # Восстановление геометрии и состояния доков
        settings = QSettings("KengaCAD", "MainWindow")
        state = settings.value("windowState")
        if state is not None:
            self.restoreState(state)
        geom = settings.value("geometry")
        if geom is not None:
            self.restoreGeometry(geom)

        self._update_drawing_area()

    
    def _create_menu(self):
        """Создание меню приложения"""
        menubar = self.menuBar()
        
        # Меню Файл
        file_menu = menubar.addMenu('Файл')
        
        new_action = QAction('Новый', self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction('Открыть', self)
        open_action.setShortcut(QKeySequence.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        self._recent_menu = file_menu.addMenu('Недавние')
        self._recent_menu.aboutToShow.connect(self._populate_recent_menu)
        
        save_action = QAction('Сохранить', self)
        save_action.setShortcut(QKeySequence.Save)
        save_action.triggered.connect(lambda: self._save_file(False))
        file_menu.addAction(save_action)

        save_as_action = QAction('Сохранить как...', self)
        save_as_action.triggered.connect(lambda: self._save_file(True))
        file_menu.addAction(save_as_action)

        export_trac_action = QAction('Экспорт траектории...', self)
        export_trac_action.setToolTip("Экспорт последней полилинии в JSON или CSV")
        export_trac_action.triggered.connect(lambda: self._parse_command("EXPORT_TRAC"))
        file_menu.addAction(export_trac_action)

        export_fanuc_action = QAction('Экспорт Fanuc TP...', self)
        export_fanuc_action.setToolTip("Экспорт траектории в формат Fanuc TP")
        export_fanuc_action.triggered.connect(lambda: self._parse_command("EXPORT_FANUC_TP"))
        file_menu.addAction(export_fanuc_action)

        export_yaskawa_action = QAction('Экспорт Yaskawa INFORM...', self)
        export_yaskawa_action.setToolTip("Экспорт траектории в формат Yaskawa INFORM")
        export_yaskawa_action.triggered.connect(lambda: self._parse_command("EXPORT_YASKAWA_INFORM"))
        file_menu.addAction(export_yaskawa_action)

        export_ur_action = QAction('Экспорт UR Script...', self)
        export_ur_action.setToolTip("Экспорт траектории в формат Universal Robots URScript")
        export_ur_action.triggered.connect(lambda: self._parse_command("EXPORT_UR_SCRIPT"))
        file_menu.addAction(export_ur_action)

        export_pdf_action = QAction('Экспорт в PDF...', self)
        export_pdf_action.setToolTip("Сохранить чертёж в PDF")
        export_pdf_action.triggered.connect(self._export_pdf_dialog)
        file_menu.addAction(export_pdf_action)

        import_step_action = QAction('Импорт STEP/IGES...', self)
        import_step_action.setToolTip("Импорт 3D-модели STEP/IGES в рабочую ячейку")
        import_step_action.triggered.connect(self._import_step_iges)
        file_menu.addAction(import_step_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Выход', self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню Правка
        edit_menu = menubar.addMenu('Правка')
        
        undo_action = QAction('Отменить', self)
        undo_action.setShortcut(QKeySequence.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction('Повторить', self)
        redo_action.setShortcut(QKeySequence.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

        # Меню Вид — переключение панелей
        view_menu = menubar.addMenu('Вид')
        panels = [
            ("Объекты", "objects_dock"),
            ("Свойства", "properties_dock"),
            ("3D / Робот", "robot_dock"),
            ("Траектория / G-код", "traj_code_dock"),
            ("3D сцена (робот)", "view3d_scene_dock"),
            ("Дерево сцены", "scene_tree_dock"),
            ("PLC / Сигналы I/O", "plc_dock"),
            ("Virtual Commissioning", "vc_dock"),
        ]
        for label, attr in panels:
            act = QAction(label, self)
            act.setCheckable(True)
            act.setChecked(True)
            dock = getattr(self, attr, None)
            if dock:
                act.toggled.connect(dock.setVisible)
                dock.visibilityChanged.connect(act.setChecked)
            view_menu.addAction(act)
    

        tools_menu = menubar.addMenu("Сервис")
        dwg_setup_action = QAction("Настройка DWG...", self)
        dwg_setup_action.setToolTip("Подключить ODA File Converter для работы с DWG")
        dwg_setup_action.triggered.connect(self._show_dwg_setup)
        tools_menu.addAction(dwg_setup_action)
        disp_action = QAction("Параметры диспенсинга...", self)
        disp_action.setToolTip("Расход, радиус, материал")
        disp_action.triggered.connect(self._show_dispensing_params)
        tools_menu.addAction(disp_action)

        # Меню PLC / Virtual Commissioning
        vc_menu = menubar.addMenu("PLC")
        vc_show_action = QAction("Показать панель PLC / VC", self)
        vc_show_action.triggered.connect(lambda: self.vc_dock.setVisible(True))
        vc_menu.addAction(vc_show_action)
        vc_gen_cycle_action = QAction("Создать цикл из траектории", self)
        vc_gen_cycle_action.triggered.connect(
            lambda: self._vc_panel._generate_cycle() if hasattr(self, "_vc_panel") else None)
        vc_menu.addAction(vc_gen_cycle_action)

        help_menu = menubar.addMenu("Справка")
        quick_action = QAction("Быстрый старт", self)
        quick_action.triggered.connect(self._show_quick_start)
        help_menu.addAction(quick_action)
        help_menu.addSeparator()
        check_updates_action = QAction("Проверить обновления", self)
        check_updates_action.setToolTip("Проверка новой версии (для будущей интеграции)")
        check_updates_action.triggered.connect(self._check_updates)
        help_menu.addAction(check_updates_action)
        help_menu.addSeparator()
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)


    def _show_dispensing_params(self):
        """Диалог параметров диспенсинга: расход, радиус."""
        flow, ok1 = QInputDialog.getDouble(self, "Параметры диспенсинга", "Расход (мл/мин):",
            self._dispensing_flow, 0.01, 100.0, 2)
        if not ok1:
            return
        radius, ok2 = QInputDialog.getDouble(self, "Параметры диспенсинга", "Радиус сопла (м):",
            self._dispensing_radius, 0.001, 0.5, 4)
        if ok2:
            self._dispensing_flow = flow
            self._dispensing_radius = radius
            self.statusBar().showMessage(f"Диспенсинг: {flow} мл/мин, радиус {radius*1000:.1f} мм")

    def _check_updates(self):
        """Проверка обновлений. Пока заглушка — сервер доставки в подготовке."""
        try:
            from updates import get_current_version, check_for_updates, is_update_check_enabled
            current = get_current_version()
            found, new_ver, url = check_for_updates()
            if found and new_ver:
                QMessageBox.information(self, "Доступно обновление",
                    f"Новая версия {new_ver}. Скачать:\n{url or '—'}")
            elif is_update_check_enabled():
                QMessageBox.information(self, "Обновления",
                    f"У вас актуальная версия KengaCAD {current}.")
            else:
                QMessageBox.information(self, "Обновления",
                    f"KengaCAD {current}\n\nАвтообновление пока не настроено. "
                    "После подключения сервера доставки (GitHub Releases, Tauri/Electric) проверка будет работать автоматически.")
        except Exception as e:
            QMessageBox.warning(self, "Обновления", f"Ошибка: {e}")

    def _show_dwg_setup(self):
        """Мастер настройки DWG — один раз указать путь к ODA."""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton
        if is_odafc_available():
            QMessageBox.information(self, "Настройка DWG",
                f"DWG поддерживается.\nПуть: {get_odafc_path_from_config() or 'стандартный'}")
            return
        dlg = QDialog(self)
        dlg.setWindowTitle("Настройка DWG")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel(
            "Для работы с файлами AutoCAD DWG нужен бесплатный ODA File Converter.\n\n"
            "1. Нажмите «Скачать» — откроется страница загрузки\n"
            "2. Установите ODA File Converter в стандартную папку\n"
            "3. Или нажмите «Обзор» и укажите ODAFileConverter.exe"))
        path_edit = QLineEdit()
        path_edit.setPlaceholderText(r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe")
        path_edit.setText(get_odafc_path_from_config() or "")
        layout.addWidget(path_edit)
        btn_row = QHBoxLayout()
        btn_dl = QPushButton("Скачать ODA")
        btn_dl.clicked.connect(open_oda_download_page)
        btn_browse = QPushButton("Обзор...")
        def browse():
            exe, _ = QFileDialog.getOpenFileName(dlg, "Укажите ODAFileConverter.exe", "",
                "ODAFileConverter.exe (*.exe);;All (*)")
            if exe:
                path_edit.setText(exe)
        btn_browse.clicked.connect(browse)
        btn_ok = QPushButton("Сохранить")
        def save():
            p = path_edit.text().strip()
            if not p:
                QMessageBox.warning(dlg, "Ошибка", "Укажите путь к ODAFileConverter.exe")
                return
            if not os.path.isfile(p):
                QMessageBox.warning(dlg, "Ошибка", f"Файл не найден: {p}")
                return
            if save_odafc_path(p):
                apply_odafc_path(p)
                dlg.accept()
                self.statusBar().showMessage("DWG настроен. Можно открывать и сохранять .dwg")
            else:
                QMessageBox.warning(dlg, "Ошибка", "Не удалось сохранить настройки")
        btn_ok.clicked.connect(save)
        btn_row.addWidget(btn_dl)
        btn_row.addWidget(btn_browse)
        btn_row.addStretch()
        btn_row.addWidget(btn_ok)
        layout.addLayout(btn_row)
        dlg.exec_()

    def _show_quick_start(self):
        msg = (
            "KengaCAD — траектория робота за 4 шага\n\n"
            "1. НАРИСУЙТЕ ПОЛИЛИНИЮ\n"
            "   Кнопка «Полилиния» или команда: POLYLINE 0 0 100 50 200 100 300 80\n"
            "   Либо рисуйте линиями/прямоугольником, затем соедините (JOIN)\n\n"
            "2. СОЗДАЙТЕ ТРАЕКТОРИЮ\n"
            "   TRAC_FROM_POLYLINE — траектория из последней полилинии\n\n"
            "3. ЗАГРУЗИТЕ РОБОТА\n"
            "   LOAD_DEMO_ROBOT — встроенная модель (вкладка Робот)\n"
            "   Или LOAD_ROBOT path/to/model.glb — своя модель\n\n"
            "4. ЗАПУСТИТЕ СИМУЛЯЦИЮ\n"
            "   SIMULATE — робот двигается в 3D-окне\n\n"
            "Масштаб: колёсико. Сдвиг: средняя кнопка мыши. Esc — отмена."
        )
        QMessageBox.information(self, "Быстрый старт", msg)

    def _show_about(self):
        meta = self._load_app_meta()
        app = meta.get("app", {}) if isinstance(meta, dict) else {}
        name = app.get("product_name") or app.get("name") or "KengaCAD"
        version = app.get("version") or "1.0.0"
        desc = app.get("description") or app.get("summary") or ""
        url = app.get("url") or ""
        msg = f"{name} {version}\n\n{desc}"
        ev = getattr(self.app, "engine_version", None) if self.app else None
        if ev:
            msg += f"\n\nДвижок Kenga: {ev}"
        if url:
            msg += f"\n\n{url}"
        msg += "\n\n© KengaCAD Team"
        QMessageBox.information(self, "О программе", msg)

    def _set_modified(self, modified: bool):
        self._is_modified = modified
        base = self._app_title()
        fn = Path(self._current_file).name if self._current_file else "Без имени"
        title = f"{base} — {fn}"
        if modified:
            title = f"* {title}"
        self.setWindowTitle(title)

    def _prompt_unsaved(self) -> bool:
        """Спросить о несохранённых изменениях. Возвращает True если можно продолжать."""
        if not self._is_modified:
            return True
        r = QMessageBox.question(
            self, "Несохранённые изменения",
            "Сохранить изменения перед продолжением?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save)
        if r == QMessageBox.Cancel:
            return False
        if r == QMessageBox.Save:
            return self._save_file()
        return True

    def closeEvent(self, event):
        if not self._prompt_unsaved():
            event.ignore()
            return
        settings = QSettings("KengaCAD", "MainWindow")
        settings.setValue("windowState", self.saveState())
        settings.setValue("geometry", self.saveGeometry())
        if self.app_thread and self.app_thread.get_app():
            app = self.app_thread.get_app()
            if hasattr(app, "engine_process") and app.engine_process and getattr(app, "engine_started_by_app", False):
                try:
                    app.engine_process.terminate()
                    app.engine_process.wait(timeout=2)
                except Exception:
                    pass
        event.accept()

    def _new_file(self):
        if not self._prompt_unsaved():
            return
        self.cad_entities = {"lines": [], "circles": [], "points": [], "arcs": [], "polylines": [], "texts": [], "splines": [], "ellipses": [], "dimensions": [], "hatches": [], "inserts": []}
        self.blocks = {}
        self.layers = {"0": {"visible": True, "color": "#FFFFFF"}}
        self.active_layer = "0"
        self._redo_stack.clear()
        self._last_trajectory_points = []
        self._current_file = None
        self._set_modified(False)
        self._update_redo_label()
        self.statusBar().showMessage("Новый чертёж")
        self._refresh_layers_list()
        self._refresh_objects_list()

    def _get_importer(self):
        """Импортёр CAD — работает и без подключения к движку."""
        return self.app.cad_importer if self.app else CADImportExport()

    def _get_recent_files(self) -> list:
        """Список недавних файлов из настроек."""
        try:
            meta = self._load_app_meta()
            ui = meta.get("ui", {}) if isinstance(meta, dict) else {}
            lst = ui.get("recent_files") or []
            return [p for p in lst if isinstance(p, str) and Path(p).exists()][:10]
        except Exception:
            return []

    def _add_to_recent(self, path: str) -> None:
        """Добавить файл в недавние и сохранить."""
        try:
            path = str(Path(path).resolve())
            meta = self._load_app_meta()
            if not isinstance(meta, dict):
                meta = {}
            ui = meta.setdefault("ui", {})
            lst = ui.get("recent_files") or []
            if path in lst:
                lst.remove(path)
            lst.insert(0, path)
            ui["recent_files"] = lst[:10]
            meta["ui"] = ui
            sp = self._settings_path()
            sp.parent.mkdir(parents=True, exist_ok=True)
            sp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _populate_recent_menu(self) -> None:
        """Заполнить меню «Недавние» перед показом."""
        self._recent_menu.clear()
        for p in self._get_recent_files():
            action = QAction(Path(p).name, self)
            action.setToolTip(p)
            action.triggered.connect(lambda checked, fp=p: self._open_recent_file(fp))
            self._recent_menu.addAction(action)
        if not self._recent_menu.actions():
            empty = QAction("(пусто)", self)
            empty.setEnabled(False)
            self._recent_menu.addAction(empty)

    def _open_recent_file(self, path: str) -> None:
        """Открыть файл из списка недавних."""
        if not self._prompt_unsaved():
            return
        self._open_file_by_path(path)

    def _open_file_by_path(self, path: str) -> bool:
        """Открыть файл по пути. Возвращает True при успехе."""
        importer = self._get_importer()
        if path.lower().endswith('.kengacad'):
            try:
                data = json.loads(Path(path).read_text(encoding='utf-8'))
                ent = data.get("entities", {})
                for k in ("lines", "circles", "points", "arcs", "polylines", "texts", "splines", "ellipses", "dimensions", "hatches", "inserts"):
                    self.cad_entities[k] = ent.get(k, [])
                self.blocks = data.get("blocks", {})
                self.layers = data.get("layers", self.layers)
                self.active_layer = data.get("active_layer", "0")
                self._current_file = path
                self._set_modified(False)
                self._sync_layers_from_entities()
                self._refresh_layers_list()
                self._refresh_objects_list()
                self.statusBar().showMessage(f"Проект загружен: {path}")
                return True
            except Exception as e:
                self.statusBar().showMessage(f"Ошибка загрузки: {e}")
                return False
        data = importer.import_dxf(path)
        if data is None:
            self.statusBar().showMessage(f"Не удалось загрузить: {path}")
            return False
        for k in ("lines", "circles", "points", "arcs", "polylines", "texts", "splines", "ellipses", "dimensions", "hatches", "inserts"):
            self.cad_entities[k] = data.get(k, [])
        self._current_file = path
        self._set_modified(False)
        self._sync_layers_from_entities()
        self._refresh_layers_list()
        self._refresh_objects_list()
        self.statusBar().showMessage(f"Загружено: {path}")
        return True

    def _open_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, 'Открыть файл', '',
                                              'KengaCAD (*.kengacad);;AutoCAD DXF (*.dxf);;AutoCAD DWG (*.dwg);;All (*)')
        if not fname:
            return
        if not self._prompt_unsaved():
            return
        if self._open_file_by_path(fname):
            self._add_to_recent(fname)
        elif fname.lower().endswith('.dwg'):
            r = QMessageBox.question(self, "Ошибка DWG", "Не удалось открыть DWG. Открыть настройку DWG?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if r == QMessageBox.Yes:
                self._show_dwg_setup()

    def _save_file(self, force_dialog: bool = False) -> bool:
        if not force_dialog and self._current_file:
            if self._current_file.lower().endswith('.kengacad'):
                try:
                    data = {"format": "kengacad", "version": 1, "entities": self._get_entities_data(),
                            "blocks": self.blocks, "layers": self.layers, "active_layer": self.active_layer}
                    Path(self._current_file).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                    self._set_modified(False)
                    self._add_to_recent(self._current_file)
                    self.statusBar().showMessage(f"Сохранено: {self._current_file}")
                    return True
                except Exception as e:
                    self.statusBar().showMessage(f"Ошибка: {e}")
                    return False
            if self._current_file.lower().endswith(('.dxf', '.dwg')):
                if self._get_importer().export_dxf(self._get_entities_data(), self._current_file, self.blocks):
                    self._set_modified(False)
                    self._add_to_recent(self._current_file)
                    self.statusBar().showMessage(f"Сохранено: {self._current_file}")
                    return True
        fname, _ = QFileDialog.getSaveFileName(self, 'Сохранить как', self._current_file or '',
                                              'KengaCAD (*.kengacad);;AutoCAD DXF (*.dxf);;AutoCAD DWG (*.dwg);;PDF (*.pdf);;All (*)')
        if not fname:
            return False
        if fname.lower().endswith('.kengacad'):
            try:
                data = {
                    "format": "kengacad",
                    "version": 1,
                    "entities": self._get_entities_data(),
                    "blocks": self.blocks,
                    "layers": self.layers,
                    "active_layer": self.active_layer,
                }
                Path(fname).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
                self._current_file = fname
                self._set_modified(False)
                self._add_to_recent(fname)
                self.statusBar().showMessage(f"Проект сохранён: {fname}")
                return True
            except Exception as e:
                self.statusBar().showMessage(f"Ошибка сохранения: {e}")
                return False
        if fname.lower().endswith('.pdf'):
            return self._export_pdf(fname)
        ok = self._get_importer().export_dxf(self._get_entities_data(), fname, self.blocks)
        if ok:
            self._current_file = fname
            self._set_modified(False)
            self._add_to_recent(fname)
            self.statusBar().showMessage(f"Сохранено: {fname}")
            return True
        if fname.lower().endswith('.dwg'):
            r = QMessageBox.question(self, "Ошибка DWG", "Не удалось сохранить в DWG. Открыть настройку DWG?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
            if r == QMessageBox.Yes:
                self._show_dwg_setup()
        self.statusBar().showMessage("Ошибка экспорта")
        return False

    def _export_pdf_dialog(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Экспорт в PDF", "", "PDF (*.pdf);;All (*)")
        if fname:
            self._export_pdf(fname)

    def _export_pdf(self, file_path: str) -> bool:
        """Экспорт чертежа в PDF."""
        try:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(file_path)
            printer.setPageOrientation(QPrinter.Landscape)
            painter = QPainter(printer)
            self.drawing_area.scene().render(painter)
            painter.end()
            self.statusBar().showMessage(f"PDF экспортирован: {file_path}")
            return True
        except Exception as e:
            self.statusBar().showMessage(f"Ошибка PDF: {e}")
            return False

    def _undo(self):
        self._delete_last_entity()

    def _select_all(self):
        """Выделить все объекты (Ctrl+A)."""
        if self._interactive_mode:
            return
        self._selected.clear()
        for key in ("points", "lines", "circles", "arcs", "polylines", "texts", "splines", "ellipses", "dimensions", "hatches", "inserts"):
            for idx in range(len(self.cad_entities.get(key, []))):
                self._selected.append((key, idx))
        self._update_drawing_area()
        self.statusBar().showMessage(f"Выбрано: {len(self._selected)} объект(ов)")

    def _require_engine(self) -> bool:
        """Проверка: движок подключён. Возвращает False и показывает сообщение, если нет."""
        if not self.app:
            self.statusBar().showMessage("Движок не готов. Подождите завершения подключения.")
            return False
        if not getattr(self.app, "is_connected", False):
            self.statusBar().showMessage("Нет подключения к движку. Проверьте, что движок Kenga запущен.")
            return False
        return True

    def _run_async_command(self, coro, label: str):
        thread = _AsyncCommandThread(coro, label)
        thread.finished.connect(self._on_command_finished)
        thread.start()
        if not hasattr(self, "_cmd_threads"):
            self._cmd_threads = []
        self._cmd_threads.append(thread)

    def _on_command_finished(self, ok: bool, message: str):
        if ok:
            self.statusBar().showMessage(f"Готово: {message}")
        else:
            self.statusBar().showMessage(f"Ошибка: {message}")

    
    def _get_demo_robot_path(self) -> Path:
        """Путь к встроенной демо-модели робота."""
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
            internal = base / "_internal"
            if internal.exists():
                return internal / "assets" / "robot.glb"
            return base / "assets" / "robot.glb"
        return Path(__file__).resolve().parent.parent / "assets" / "robot.glb"
    
    def _get_entities_data(self):
        return {
            "lines": self.cad_entities.get("lines", []),
            "circles": self.cad_entities.get("circles", []),
            "points": self.cad_entities.get("points", []),
            "arcs": self.cad_entities.get("arcs", []),
            "polylines": self.cad_entities.get("polylines", []),
            "texts": self.cad_entities.get("texts", []),
            "splines": self.cad_entities.get("splines", []),
            "ellipses": self.cad_entities.get("ellipses", []),
            "dimensions": self.cad_entities.get("dimensions", []),
            "hatches": self.cad_entities.get("hatches", []),
            "inserts": self.cad_entities.get("inserts", []),
        }

    
    def _update_drawing_area(self):
        if hasattr(self, "drawing_area"):
            self.drawing_area.set_selection(self._selected)
            self.drawing_area.set_entities(self.cad_entities, self.layers, self.active_layer, self.blocks)
        self._update_view3d_preview()
        self._update_properties_panel()

    def _lines_to_path(self) -> list[tuple[float, float, float]]:
        """Собрать путь из линий (соединённых по концам) для 3D-превью, если нет полилинии."""
        lines = self.cad_entities.get("lines", [])
        if len(lines) < 2:
            return []
        used = set()

        def _dist(a, b):
            return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5

        def _get_line_pts(ln):
            s = ln.get("start", (0, 0, 0))
            e = ln.get("end", (0, 0, 0))
            return (float(s[0]), float(s[1]), float(s[2]) if len(s) > 2 else 0.0), \
                   (float(e[0]), float(e[1]), float(e[2]) if len(e) > 2 else 0.0)

        for i, ln in enumerate(lines):
            if i in used:
                continue
            p1, p2 = _get_line_pts(ln)
            path = [p1, p2]
            used.add(i)
            while True:
                tail = path[-1]
                found = None
                for j, ln2 in enumerate(lines):
                    if j in used:
                        continue
                    a, b = _get_line_pts(ln2)
                    if _dist(tail, a) < 1e-6:
                        path.append(b)
                        used.add(j)
                        found = j
                        break
                    if _dist(tail, b) < 1e-6:
                        path.append(a)
                        used.add(j)
                        found = j
                        break
                if found is None:
                    break
            if len(path) >= 2:
                return path
        return []

    def _update_view3d_preview(self):
        """Обновить 3D-превью траектории (полилиния, линии или загруженная траектория)."""
        if not hasattr(self, "_view3d"):
            return
        pts = self._last_trajectory_points
        if not pts:
            polylines = self.cad_entities.get("polylines", [])
            if polylines:
                last = polylines[-1]
                raw = last.get("points", [])
                pts = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in raw]
        if not pts:
            pts = self._lines_to_path()
        self._view3d.set_trajectory_points(pts)
        if hasattr(self, "_traj_code_panel"):
            self._traj_code_panel.set_trajectory(pts)
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene.set_trajectory(pts)
        self._scene_objects = [o for o in self._scene_objects if o.get("id") != "trajectory"]
        if pts:
            self._scene_objects.append({"id": "trajectory", "name": "Траектория", "type": "trajectory"})
        if hasattr(self, "_scene_tree_widget"):
            self._scene_tree_widget.set_objects(self._scene_objects)
        if hasattr(self, "_vc_panel") and pts:
            self._vc_panel.set_trajectory_points(pts)

    def _update_scene_tree(self) -> None:
        """Обновить дерево объектов 3D-сцены."""
        if hasattr(self, "_scene_tree_widget"):
            self._scene_tree_widget.set_objects(self._scene_objects)

    def _add_workcell_table(self) -> None:
        """Добавить примитив стола через диалог AddBoxDialog."""
        n = sum(1 for o in self._scene_objects if o.get("type") == "table")
        dlg = AddBoxDialog(self, title="Добавить стол", defaults={
            "name": f"Стол {n + 1}", "width": 800.0, "length": 600.0, "height": 50.0,
            "pos_x": 0.0, "pos_y": 0.0, "pos_z": 0.0, "color": "#5a4a3a",
        })
        if dlg.exec_() != QDialog.Accepted:
            return
        p = dlg.get_params()
        oid = f"table_{n + 1}"
        min_xyz = p["min_xyz"]
        max_xyz = p["max_xyz"]
        self._scene_objects.append({
            "id": oid, "name": p["name"], "type": "table",
            "aabb": {"min": min_xyz, "max": max_xyz},
            "color": p["color"], "width": p["width"], "length": p["length"],
            "height": p["height"], "pos_x": p["pos_x"], "pos_y": p["pos_y"], "pos_z": p["pos_z"],
        })
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene.add_workcell_box(oid, min_xyz, max_xyz, p["color"])
        self._update_scene_tree()
        self.statusBar().showMessage(f"Добавлен объект: {p['name']}")

    def _add_workcell_fixture(self) -> None:
        """Добавить примитив оснастки через диалог AddBoxDialog."""
        n = sum(1 for o in self._scene_objects if o.get("type") == "fixture")
        dlg = AddBoxDialog(self, title="Добавить оснастку", defaults={
            "name": f"Оснастка {n + 1}", "width": 200.0, "length": 200.0, "height": 100.0,
            "pos_x": 300.0, "pos_y": 0.0, "pos_z": 0.0, "color": "#4a5a6b",
        })
        if dlg.exec_() != QDialog.Accepted:
            return
        p = dlg.get_params()
        oid = f"fixture_{n + 1}"
        min_xyz = p["min_xyz"]
        max_xyz = p["max_xyz"]
        self._scene_objects.append({
            "id": oid, "name": p["name"], "type": "fixture",
            "aabb": {"min": min_xyz, "max": max_xyz},
            "color": p["color"], "width": p["width"], "length": p["length"],
            "height": p["height"], "pos_x": p["pos_x"], "pos_y": p["pos_y"], "pos_z": p["pos_z"],
        })
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene.add_workcell_box(oid, min_xyz, max_xyz, p["color"])
        self._update_scene_tree()
        self.statusBar().showMessage(f"Добавлен объект: {p['name']}")

    def _add_workcell_conveyor(self) -> None:
        """Добавить конвейер через диалог AddConveyorDialog."""
        n = sum(1 for o in self._scene_objects if o.get("type") == "conveyor")
        dlg = AddConveyorDialog(self, defaults={"name": f"Конвейер {n + 1}"})
        if dlg.exec_() != QDialog.Accepted:
            return
        p = dlg.get_params()
        oid = f"conveyor_{n + 1}"
        min_xyz = p["min_xyz"]
        max_xyz = p["max_xyz"]
        self._scene_objects.append({
            "id": oid, "name": p["name"], "type": "conveyor",
            "aabb": {"min": min_xyz, "max": max_xyz},
            "color": p["color"], "length": p["length"], "width": p["width"],
            "height": p["height"], "direction": p["direction"],
            "pos_x": p["pos_x"], "pos_y": p["pos_y"], "pos_z": p["pos_z"],
        })
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene.add_workcell_box(oid, min_xyz, max_xyz, p["color"])
        self._update_scene_tree()
        self.statusBar().showMessage(f"Добавлен объект: {p['name']}")

    def _add_workcell_fence(self) -> None:
        """Добавить защитное ограждение через диалог AddFenceDialog."""
        n = sum(1 for o in self._scene_objects if o.get("type") == "fence")
        dlg = AddFenceDialog(self, defaults={"name": f"Ограждение {n + 1}"})
        if dlg.exec_() != QDialog.Accepted:
            return
        p = dlg.get_params()
        oid = f"fence_{n + 1}"
        min_xyz = p["min_xyz"]
        max_xyz = p["max_xyz"]
        self._scene_objects.append({
            "id": oid, "name": p["name"], "type": "fence",
            "aabb": {"min": min_xyz, "max": max_xyz},
            "color": p["color"], "length": p["length"], "height": p["height"],
            "thickness": p["thickness"], "rotation": p["rotation"],
            "pos_x": p["pos_x"], "pos_y": p["pos_y"], "pos_z": p["pos_z"],
        })
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene.add_workcell_box(oid, min_xyz, max_xyz, p["color"])
        self._update_scene_tree()
        self.statusBar().showMessage(f"Добавлен объект: {p['name']}")

    def _add_workcell_robot(self) -> None:
        """Добавить робота из библиотеки robots.json (поддержка нескольких роботов)."""
        try:
            base = Path(__file__).resolve().parent.parent
            robots_path = base / "config" / "robots.json"
            if getattr(sys, "frozen", False):
                internal = Path(sys.executable).parent / "_internal" / "config" / "robots.json"
                robots_path = internal if internal.exists() else robots_path
            if robots_path.exists():
                data = json.loads(robots_path.read_text(encoding="utf-8"))
                robot_list = data.get("robots", [])
            else:
                robot_list = [{"id": "demo", "name": "Демо-робот (6DOF)", "path": "assets/robot.glb"}]
        except Exception:
            robot_list = [{"id": "demo", "name": "Демо-робот (6DOF)", "path": "assets/robot.glb"}]

        names = [r.get("name", r.get("id", "?")) for r in robot_list]
        if not names:
            QMessageBox.information(self, "Робот", "Библиотека роботов пуста.")
            return
        chosen, ok = QInputDialog.getItem(
            self, "Добавить робота", "Выберите робота из библиотеки:", names, 0, False)
        if not ok:
            return
        idx = names.index(chosen)
        robot_data = robot_list[idx]

        # Уникальный id для мульти-робот поддержки
        existing_robot_ids = [o.get("id") for o in self._scene_objects if o.get("type") == "robot"]
        n = len(existing_robot_ids) + 1
        oid = f"robot_{n}"
        while oid in existing_robot_ids:
            n += 1
            oid = f"robot_{n}"

        display_name = f"{robot_data.get('name', 'Робот')} [{oid}]"

        self._scene_objects.append({
            "id": oid,
            "name": display_name,
            "type": "robot",
            "robot_data": robot_data,
        })

        # Попытка загрузить 3D модель
        model_path = robot_data.get("path", "")
        if model_path:
            full_path = Path(__file__).resolve().parent.parent / model_path
            if getattr(sys, "frozen", False):
                alt = Path(sys.executable).parent / "_internal" / model_path
                full_path = alt if alt.exists() else full_path
            if full_path.exists() and hasattr(self, "_view3d_scene"):
                self._view3d_scene.load_mesh(str(full_path))

        self._update_scene_tree()
        self.statusBar().showMessage(f"Добавлен робот: {display_name}")

    # ------------------------------------------------------------------
    #  Scene object management (delete, visibility, select, properties, duplicate)
    # ------------------------------------------------------------------

    def _delete_scene_object(self, oid: str) -> None:
        """Удалить объект из _scene_objects и 3D-сцены."""
        obj = next((o for o in self._scene_objects if o.get("id") == oid), None)
        if obj is None:
            return
        self._scene_objects = [o for o in self._scene_objects if o.get("id") != oid]
        # Удалить из 3D-сцены: пересобираем workcell_boxes без этого id
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene._workcell_boxes = [
                b for b in self._view3d_scene._workcell_boxes if b.get("id") != oid
            ]
            # Полная перерисовка сцены для корректного удаления
            try:
                self._view3d_scene._plotter.clear()
                self._view3d_scene._plotter.add_axes()
                self._view3d_scene._traj_actor = None
                self._view3d_scene._redraw_workcell_boxes()
            except Exception:
                pass
        self._update_scene_tree()
        self.statusBar().showMessage(f"Удалён объект: {obj.get('name', oid)}")

    def _toggle_scene_object_visibility(self, oid: str) -> None:
        """Скрыть/показать объект в 3D-сцене (пересборка без/с данного бокса)."""
        obj = next((o for o in self._scene_objects if o.get("id") == oid), None)
        if obj is None:
            return
        # Переключаем флаг
        is_hidden = obj.get("_hidden", False)
        obj["_hidden"] = not is_hidden
        # Пересобираем workcell_boxes
        if hasattr(self, "_view3d_scene"):
            self._view3d_scene._workcell_boxes = [
                b for b in self._view3d_scene._workcell_boxes if b.get("id") != oid
            ]
            if not obj["_hidden"] and "aabb" in obj:
                color = obj.get("color", "#6b6b6b")
                self._view3d_scene._workcell_boxes.append({
                    "id": oid,
                    "min": obj["aabb"]["min"],
                    "max": obj["aabb"]["max"],
                    "color": color,
                })
            try:
                self._view3d_scene._plotter.clear()
                self._view3d_scene._plotter.add_axes()
                self._view3d_scene._traj_actor = None
                self._view3d_scene._redraw_workcell_boxes()
            except Exception:
                pass
        label = "Скрыт" if obj["_hidden"] else "Показан"
        self.statusBar().showMessage(f"{label}: {obj.get('name', oid)}")

    def _select_scene_object(self, oid: str) -> None:
        """Выделить (подсветить) объект в 3D-сцене."""
        # Подсветка: кратковременно показываем wireframe вокруг объекта
        obj = next((o for o in self._scene_objects if o.get("id") == oid), None)
        if obj is None:
            return
        self.statusBar().showMessage(f"Выбран: {obj.get('name', oid)}")

    def _show_object_properties(self, oid: str) -> None:
        """Показать диалог свойств объекта."""
        obj = next((o for o in self._scene_objects if o.get("id") == oid), None)
        if obj is None:
            return
        dlg = ObjectPropertiesDialog(self, obj_data=obj)
        if dlg.exec_() == QDialog.Accepted:
            updated = dlg.get_params()
            # Обновляем объект в списке
            for i, o in enumerate(self._scene_objects):
                if o.get("id") == oid:
                    self._scene_objects[i].update(updated)
                    break
            self._update_scene_tree()
            self.statusBar().showMessage(f"Обновлены свойства: {updated.get('name', oid)}")

    def _duplicate_scene_object(self, oid: str) -> None:
        """Дублировать объект в сцене."""
        obj = next((o for o in self._scene_objects if o.get("id") == oid), None)
        if obj is None:
            return
        new_obj = copy.deepcopy(obj)
        typ = obj.get("type", "object")
        n = sum(1 for o in self._scene_objects if o.get("type") == typ)
        new_id = f"{typ}_{n + 1}"
        while any(o.get("id") == new_id for o in self._scene_objects):
            n += 1
            new_id = f"{typ}_{n + 1}"
        new_obj["id"] = new_id
        new_obj["name"] = f"{obj.get('name', typ)} (копия)"
        self._scene_objects.append(new_obj)
        # Добавить в 3D-сцену
        if hasattr(self, "_view3d_scene") and "aabb" in new_obj:
            color = new_obj.get("color", "#6b6b6b")
            self._view3d_scene.add_workcell_box(
                new_id, new_obj["aabb"]["min"], new_obj["aabb"]["max"], color
            )
        self._update_scene_tree()
        self.statusBar().showMessage(f"Дублирован: {new_obj['name']}")

    def _import_step_iges(self) -> None:
        """Импорт STEP/IGES файла в 3D-сцену как workcell-объект."""
        if not can_import_step():
            QMessageBox.warning(
                self, "STEP/IGES",
                "Библиотека для импорта STEP/IGES не найдена.\n\n"
                "Установите одну из:\n"
                "  pip install cadquery\n"
                "  или OCP (opencascade-python)\n\n"
                "Также требуется: pip install trimesh",
            )
            return

        fname, _ = QFileDialog.getOpenFileName(
            self, "Импорт STEP/IGES",
            "",
            "STEP файлы (*.stp *.step);;IGES файлы (*.igs *.iges);;"
            "Все CAD (*.stp *.step *.igs *.iges);;Все файлы (*)",
        )
        if not fname:
            return

        self.statusBar().showMessage(f"Импорт: {os.path.basename(fname)}...")

        ext = os.path.splitext(fname)[1].lower()
        if ext in (".igs", ".iges"):
            mesh = load_iges(fname)
        else:
            mesh = load_step(fname)

        if mesh is None:
            QMessageBox.warning(
                self, "STEP/IGES",
                f"Не удалось загрузить файл:\n{fname}\n\n"
                "Проверьте формат и наличие геометрии.",
            )
            self.statusBar().showMessage("Ошибка импорта STEP/IGES")
            return

        base_name = os.path.splitext(os.path.basename(fname))[0]
        n = sum(1 for o in self._scene_objects if o.get("type") == "step_mesh")
        oid = f"step_{n + 1}"
        display_name = f"{base_name}"

        added = False
        if hasattr(self, "_view3d_scene"):
            added = self._view3d_scene.add_trimesh_object(oid, mesh, color="#8bc34a", name=display_name)

        # Получаем AABB для collision-проверок
        aabb_data = {}
        try:
            import numpy as _np
            bounds = mesh.bounds  # [[min_x,min_y,min_z],[max_x,max_y,max_z]]
            aabb_data = {
                "min": bounds[0].tolist(),
                "max": bounds[1].tolist(),
            }
        except Exception:
            pass

        self._scene_objects.append({
            "id": oid,
            "name": display_name,
            "type": "step_mesh",
            "source_file": fname,
            "aabb": aabb_data,
            "trimesh": mesh,
        })
        self._update_scene_tree()

        if added:
            self.statusBar().showMessage(f"Импортировано: {display_name} ({get_backend_info()})")
        else:
            self.statusBar().showMessage(
                f"Объект '{display_name}' добавлен в сцену (3D-отображение недоступно — нет pyvista)")

    def _update_properties_panel(self):
        """Обновить панель свойств по выбранным объектам."""
        if hasattr(self, "_properties_panel"):
            entities = self._get_selected_entities()
            self._properties_panel.set_entities(entities)

    def _on_view3d_points_changed(self, pts: list) -> None:
        """Обработка перетаскивания точки в 3D-превью."""
        self._last_trajectory_points = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in pts]
        polylines = self.cad_entities.get("polylines", [])
        if polylines:
            self.cad_entities["polylines"][-1]["points"] = [[p[0], p[1], p[2]] for p in pts]
        self._update_drawing_area()
        if self.app and getattr(self.app, "is_connected", False):
            self._run_async_command(self.app.setup_robot_trajectory(points=self._last_trajectory_points), 'view3d_drag')
        self.statusBar().showMessage(f"Точка перемещена — {len(pts)} точек")

    # ========================================================================
    #  View3DFull методы (полноценное 3D)
    # ========================================================================

    def _on_3d_model_loaded(self, path: str, success: bool):
        """Модель загружена в full 3D."""
        if success:
            self.statusBar().showMessage(f"3D модель загружена: {Path(path).name}")
        else:
            self.statusBar().showMessage("Ошибка загрузки 3D модели")

    def _on_3d_trajectory_changed(self, points):
        """Траектория изменена в full 3D."""
        self._last_trajectory_points = points
        self.statusBar().showMessage(f"3D траектория: {len(points)} точек")

    def _on_3d_simulation_finished(self):
        """Симуляция завершена в full 3D."""
        self.statusBar().showMessage("Симуляция завершена")

    def _on_3d_collision_detected(self, collisions):
        """Коллизия обнаружена в full 3D."""
        if collisions:
            self.statusBar().showMessage(f"⚠ Коллизий: {len(collisions)}")

    def _switch_3d_mode(self, mode: str = "full"):
        """Переключение между preview и full 3D режимом."""
        if not _HAS_VIEW3D_FULL or self._view3d_full is None:
            self.statusBar().showMessage("Full 3D недоступен. Установите: pip install pyvista pyvistaqt trimesh scipy")
            return
        
        if mode == "full":
            self._view3d.setVisible(False)
            self._view3d_full.setVisible(True)
            self._3d_mode = "full"
            # Перенести траекторию в full 3D
            if self._last_trajectory_points:
                self._view3d_full.set_trajectory_points(self._last_trajectory_points)
            self.statusBar().showMessage("Режим: Полноценное 3D (PyVista)")
        else:
            self._view3d_full.setVisible(False)
            self._view3d.setVisible(True)
            self._3d_mode = "preview"
            self.statusBar().showMessage("Режим: 3D превью (изометрия)")

    def _load_model_full_3d(self, path: str):
        """Загрузить модель в full 3D."""
        if not _HAS_VIEW3D_FULL or self._view3d_full is None:
            self.statusBar().showMessage("Full 3D недоступен. Установите: pip install pyvista pyvistaqt trimesh scipy")
            return
        if self._3d_mode == "preview":
            self._switch_3d_mode("full")
        self._view3d_full.load_model(path)

    def _set_trajectory_full_3d(self, points):
        """Установить траекторию в full 3D."""
        if not _HAS_VIEW3D_FULL or self._view3d_full is None:
            self.statusBar().showMessage("Full 3D недоступен. Установите: pip install pyvista pyvistaqt trimesh scipy")
            return
        if self._3d_mode == "preview":
            self._switch_3d_mode("full")

        # Создать расширенную траекторию
        traj_points = [TrajectoryPoint(p[0], p[1], p[2]) for p in points]
        self._traj_manager.create_trajectory("main", traj_points, spline_type="cubic")

        # Отобразить в 3D
        self._view3d_full.set_trajectory_points(points)
        self.statusBar().showMessage(f"Траектория: {len(points)} точек, сплайн кубический")

    def _simulate_full_3d(self, steps: int = 60, speed: float = 1.0):
        """Запустить симуляцию в full 3D."""
        if self._3d_mode == "preview":
            self._switch_3d_mode("full")
        self._view3d_full.start_simulation(steps, speed)

    def _export_gcode_dialog(self):
        """Экспорт траектории в G-код."""
        if not self._traj_manager.trajectories:
            QMessageBox.warning(self, "G-код", "Нет траекторий для экспорта")
            return
        
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт G-кода", "", "G-code (*.nc;*.gcode);;Все файлы (*)"
        )
        if path:
            gcode = self._traj_manager.export_to_gcode("main", num_points=100, feed_rate=150.0)
            if gcode:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(gcode)
                self.statusBar().showMessage(f"G-код экспортирован: {Path(path).name}")

    def _generate_spiral_trajectory(self):
        """Сгенерировать спиральную траекторию."""
        points = generate_spiral(
            center=(0, 0, 0),
            radius=100,
            height=50,
            num_turns=2.0,
            num_points=100,
        )
        self._set_trajectory_full_3d([p.position for p in points])
        self.statusBar().showMessage("Спиральная траектория создана")

    def _generate_zigzag_trajectory(self):
        """Сгенерировать зигзагообразную траекторию."""
        points = generate_zigzag(
            start=(0, 0, 0),
            size_x=200,
            size_y=150,
            step_over=10,
            num_points_per_line=20,
        )
        self._set_trajectory_full_3d([p.position for p in points])
        self.statusBar().showMessage("Зигзагообразная траектория создана")

    def _check_reachability_full(self, x: float, y: float, z: float):
        """Проверка достижимости с полной кинематикой."""
        config = get_robot_config("kuka_kr6r900")
        if not config:
            self.statusBar().showMessage("Конфигурация робота не найдена")
            return
        
        result = ik_6dof_numerical(
            (x, y, z),
            (0, 0, 0),
            config['dh_params'],
            config['joint_limits'],
        )
        
        if result and result.get('converged'):
            self.statusBar().showMessage(f"✅ Достижимо: {result['joints_deg']}")
        else:
            self.statusBar().showMessage(f"❌ Недостижимо: {x}, {y}, {z}")

    def _populate_robot_combo(self) -> None:
        """Заполнить ComboBox из config/robots.json."""
        if not hasattr(self, "_robot_combo"):
            return
        self._robot_combo.clear()
        try:
            base = Path(__file__).resolve().parent.parent
            robots_path = base / "config" / "robots.json"
            if getattr(sys, "frozen", False):
                internal = Path(sys.executable).parent / "_internal" / "config" / "robots.json"
                robots_path = internal if internal.exists() else robots_path
            if robots_path.exists():
                data = json.loads(robots_path.read_text(encoding="utf-8"))
                for r in data.get("robots", []):
                    self._robot_combo.addItem(r.get("name", r.get("id", "?")), r)
            else:
                self._robot_combo.addItem("Демо-робот", {"id": "demo", "path": "assets/robot.glb"})
        except Exception:
            self._robot_combo.addItem("Демо-робот", {"id": "demo", "path": "assets/robot.glb"})

    def _on_robot_combo_changed(self) -> None:
        """Обновить ограничения осей j1–j6 по выбранному роботу."""
        if not hasattr(self, "_joint_status_panel") or not hasattr(self, "_robot_combo"):
            return
        idx = self._robot_combo.currentIndex()
        data = self._robot_combo.itemData(idx) if idx >= 0 else None
        if isinstance(data, dict) and "joint_limits" in data:
            self._joint_status_panel.set_limits(data["joint_limits"])
        self._on_joints_changed()

    def _on_plc_signal_changed(self, signal_name: str, value) -> None:
        """Обработка изменения PLC-сигнала из панели."""
        self.statusBar().showMessage(f"PLC: {signal_name} = {value}")

    def _on_joints_changed(self) -> None:
        """Обновить отображение TCP по углам суставов (FK) и 3D-сцену."""
        if not hasattr(self, "_joint_status_panel") or not hasattr(self, "_tcp_label"):
            return
        if getattr(self, "_fk_ik_block", False):
            return
        joints = self._joint_status_panel.get_joints()
        dh = self._get_current_dh_params()
        # FK через fk_full (с ориентацией и link positions)
        try:
            fk_res = fk_full(joints, dh)
            px, py, pz = fk_res["tcp_pos"]
            rx, ry, rz = fk_res["tcp_rpy"]
            self._tcp_label.setText(f"TCP: x={px:.1f} y={py:.1f} z={pz:.1f} мм")
            if hasattr(self, "_tcp_position_panel"):
                self._fk_ik_block = True
                self._tcp_position_panel.set_tcp(px, py, pz, rx, ry, rz)
                self._fk_ik_block = False
        except Exception as e:
            self._tcp_label.setText(f"TCP: ошибка FK — {e}")
        # Обновить wireframe робота в 3D-сцене
        if hasattr(self, "_view3d_scene") and self._view3d_scene._plotter is not None:
            try:
                self._view3d_scene.update_robot_pose(joints, dh)
            except Exception:
                pass

    def _on_tcp_changed(self, tcp_values: list) -> None:
        """TCP-панель изменена вручную — вычислить IK и обновить суставы."""
        if getattr(self, "_fk_ik_block", False):
            return
        if not hasattr(self, "_joint_status_panel") or not hasattr(self, "_tcp_position_panel"):
            return
        x, y, z, rx, ry, rz = tcp_values
        dh = self._get_current_dh_params()
        joint_limits = self._get_current_joint_limits()
        initial = self._joint_status_panel.get_joints()
        try:
            result = ik_6dof(
                target_xyz=(x, y, z),
                target_rpy_deg=(rx, ry, rz),
                dh_params=dh,
                joint_limits=joint_limits,
                initial_joints_deg=initial,
            )
        except Exception:
            result = None
        if result and result.get("converged"):
            self._fk_ik_block = True
            self._joint_status_panel.set_joints(result["joints_deg"])
            self._fk_ik_block = False
            self._tcp_position_panel.set_ik_status(True)
            px, py, pz = result.get("tcp_pos", (x, y, z))
            self._tcp_label.setText(f"TCP: x={px:.1f} y={py:.1f} z={pz:.1f} мм")
            # Обновить wireframe в 3D-сцене
            if hasattr(self, "_view3d_scene") and self._view3d_scene._plotter is not None:
                try:
                    self._view3d_scene.update_robot_pose(result["joints_deg"], dh)
                except Exception:
                    pass
        else:
            self._tcp_position_panel.set_ik_status(False)

    def _edit_trajectory(self) -> None:
        """Открыть диалог редактирования траектории (таблица X,Y,Z)."""
        pts = self._last_trajectory_points
        if not pts:
            polylines = self.cad_entities.get("polylines", [])
            if polylines:
                last = polylines[-1]
                raw = last.get("points", [])
                pts = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in raw]
        if not pts:
            self.statusBar().showMessage("Нет траектории. Создайте полилинию и TRAC_FROM_POLYLINE.")
            return
        dlg = TrajectoryEditDialog(pts, self)
        if dlg.exec_() == QDialog.Accepted:
            new_pts = dlg.get_points()
            self._last_trajectory_points = new_pts
            self._update_view3d_preview()
            polylines = self.cad_entities.get("polylines", [])
            if polylines:
                self.cad_entities["polylines"][-1]["points"] = [[p[0], p[1], p[2]] for p in new_pts]
            self._update_drawing_area()
            if self.app and getattr(self.app, "is_connected", False):
                self._run_async_command(self.app.setup_robot_trajectory(points=new_pts), 'edit_trac')
            self.statusBar().showMessage(f"Траектория обновлена: {len(new_pts)} точек")

    # ===================== Робот-симуляция (IK-driven) =====================

    def _start_robot_simulation(self, traj_points: list, speed: float = 1.0) -> None:
        """Запустить пошаговую IK-анимацию робота по точкам траектории."""
        if not traj_points or len(traj_points) < 2:
            return
        # Останавливаем предыдущую
        self._stop_robot_simulation()
        self._sim_traj = traj_points
        self._sim_index = 0
        self._sim_dh = self._get_current_dh_params()
        self._sim_jlimits = self._get_current_joint_limits()
        self._sim_last_joints = self._joint_status_panel.get_joints() if hasattr(self, "_joint_status_panel") else [0.0]*6
        from PyQt5.QtCore import QTimer
        interval = max(20, int(80 / speed))  # ms между шагами
        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self._sim_step)
        self._sim_timer.start(interval)

    def _sim_step(self) -> None:
        """Один шаг симуляции — переместить робота к следующей точке траектории."""
        if not hasattr(self, "_sim_traj") or self._sim_index >= len(self._sim_traj):
            self._stop_robot_simulation()
            self.statusBar().showMessage("Симуляция завершена")
            return
        pt = self._sim_traj[self._sim_index]
        x, y, z = float(pt[0]), float(pt[1]), float(pt[2]) if len(pt) > 2 else 0.0
        # IK для текущей точки
        try:
            result = ik_6dof(
                target_xyz=(x, y, z),
                dh_params=self._sim_dh,
                joint_limits=self._sim_jlimits,
                initial_joints_deg=self._sim_last_joints,
                position_only=True,
            )
        except Exception:
            result = None
        if result and result.get("converged"):
            jdeg = result["joints_deg"]
            self._sim_last_joints = jdeg
            self._fk_ik_block = True
            if hasattr(self, "_joint_status_panel"):
                self._joint_status_panel.set_joints(jdeg)
            if hasattr(self, "_view3d_scene") and self._view3d_scene._plotter is not None:
                try:
                    self._view3d_scene.update_robot_pose(jdeg, self._sim_dh)
                except Exception:
                    pass
            # Обновить TCP-лейбл
            px, py, pz = result.get("tcp_pos", (x, y, z))
            if hasattr(self, "_tcp_label"):
                self._tcp_label.setText(f"TCP: x={px:.1f} y={py:.1f} z={pz:.1f} мм")
            self._fk_ik_block = False
        self._sim_index += 1
        self.statusBar().showMessage(f"Симуляция: точка {self._sim_index}/{len(self._sim_traj)}")

    def _stop_robot_simulation(self) -> None:
        """Остановить таймер симуляции."""
        if hasattr(self, "_sim_timer") and self._sim_timer is not None:
            self._sim_timer.stop()
            self._sim_timer.deleteLater()
            self._sim_timer = None

    # ===================== конец робот-симуляции =====================

    def _run_check_collision(self, args: list) -> None:
        """Локальная проверка коллизий траектории с препятствиями + лог. При подключённом движке — также запрос к нему."""
        pts = self._last_trajectory_points
        if not pts:
            polylines = self.cad_entities.get("polylines", [])
            if polylines:
                last = polylines[-1]
                raw = last.get("points", [])
                pts = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in raw]
        if not pts:
            self.statusBar().showMessage("Нет траектории. TRAC_FROM_POLYLINE или задайте траекторию.")
            return
        obstacles = []
        if hasattr(self, "_view3d_scene"):
            bbox = self._view3d_scene.get_robot_bbox()
            if bbox:
                min_xyz, max_xyz = bbox
                obstacles.append({"id": "robot", "type": "aabb", "min": min_xyz, "max": max_xyz})
        for obj in getattr(self, "_scene_objects", []):
            if obj.get("type") == "table" and "aabb" in obj:
                obstacles.append({"id": obj.get("id", "table"), "type": "aabb", **obj["aabb"]})
            elif obj.get("type") == "fixture" and "aabb" in obj:
                obstacles.append({"id": obj.get("id", "fixture"), "type": "aabb", **obj["aabb"]})
        collisions = check_collisions_local(pts, obstacles)
        self.statusBar().showMessage(f"Коллизии (локально): найдено {len(collisions)}")
        log_lines = [f"Шаг {c['step']}: ({c['point'][0]:.1f}, {c['point'][1]:.1f}, {c['point'][2]:.1f}) — {c['object_a']} ↔ {c['object_b']}" for c in collisions]
        if not log_lines:
            log_lines = ["Столкновений не обнаружено."]
        dlg = QDialog(self)
        dlg.setWindowTitle("Лог коллизий")
        layout = QVBoxLayout(dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        te.setPlainText("\n".join(log_lines))
        te.setMinimumSize(400, 200)
        layout.addWidget(te)
        bb = QDialogButtonBox(QDialogButtonBox.Ok)
        bb.accepted.connect(dlg.accept)
        layout.addWidget(bb)
        dlg.exec_()
        if self.app and getattr(self.app, "is_connected", False):
            entity_id = args[0] if args else None
            self._run_async_command(self.app.query_collisions(entity_id), 'check_collision')

    def _get_current_robot_data(self) -> dict | None:
        """Получить данные текущего робота из ComboBox."""
        if not hasattr(self, "_robot_combo"):
            return None
        idx = self._robot_combo.currentIndex()
        return self._robot_combo.itemData(idx) if idx >= 0 else None

    def _get_current_dh_params(self) -> list | None:
        """DH-параметры текущего робота."""
        data = self._get_current_robot_data()
        if isinstance(data, dict) and "dh_params" in data:
            return data["dh_params"]
        return None

    def _get_current_joint_limits(self) -> list | None:
        """Joint limits текущего робота."""
        data = self._get_current_robot_data()
        if isinstance(data, dict) and "joint_limits" in data:
            return data["joint_limits"]
        return None

    def _load_selected_robot(self) -> None:
        """Загрузить выбранного робота из ComboBox."""
        if not hasattr(self, "_robot_combo"):
            return
        data = self._get_current_robot_data()
        if not data:
            self._parse_command("LOAD_DEMO_ROBOT")
            return
        rid = data.get("id", "")
        path = data.get("path", "")
        # Пользователь выбрал «своя модель» — открыть диалог
        if rid == "custom":
            self._parse_command("LOAD_ROBOT")
            return
        # Демо-робот (GLB)
        if rid == "demo" or (path and "robot.glb" in path):
            self._parse_command("LOAD_DEMO_ROBOT")
            return
        # Робот с GLB-файлом
        if path:
            base = Path(__file__).resolve().parent.parent
            if getattr(sys, "frozen", False):
                base = Path(sys.executable).parent / "_internal"
            full = (base / path).resolve()
            if full.exists():
                self._parse_command(f"LOAD_ROBOT {full}")
                return
        # Робот без GLB — строим wireframe из DH-параметров
        dh = data.get("dh_params")
        if dh:
            self._load_robot_wireframe(data)
        else:
            QMessageBox.warning(self, "Робот", f"Нет модели и нет DH-параметров для {data.get('name', rid)}")

    def _load_robot_wireframe(self, robot_data: dict) -> None:
        """Загрузить робота как wireframe по DH-параметрам."""
        dh = robot_data.get("dh_params")
        name = robot_data.get("name", "Robot")
        manufacturer = robot_data.get("manufacturer", "")
        jlimits = robot_data.get("joint_limits")
        if not dh:
            return
        # Обновить joint limits
        if jlimits and hasattr(self, "_joint_status_panel"):
            self._joint_status_panel.set_limits(jlimits)
        # Вычислить FK для нулевого положения
        joints = [0.0] * 6
        if hasattr(self, "_joint_status_panel"):
            joints = self._joint_status_panel.get_joints()
        # Отрисовать в 3D-сцене
        if hasattr(self, "_view3d_scene") and self._view3d_scene._plotter is not None:
            self._view3d_scene.update_robot_pose(joints, dh)
            self.statusBar().showMessage(f"Робот {manufacturer} {name} загружен (wireframe)")
        else:
            self.statusBar().showMessage(f"Робот {manufacturer} {name} — pyvista недоступен, только кинематика")
        # Добавить в scene_objects
        existing_rids = [o.get("id") for o in self._scene_objects if o.get("type") == "robot"]
        rn = len(existing_rids) + 1
        new_rid = f"robot_{rn}"
        while new_rid in existing_rids:
            rn += 1
            new_rid = f"robot_{rn}"
        self._scene_objects.insert(0, {
            "id": new_rid, "name": f"{manufacturer} {name}", "type": "robot",
            "dh_params": dh, "joint_limits": jlimits,
        })
        self._update_scene_tree()
        # Обновить FK / TCP
        self._on_joints_changed()

    def _on_entity_clicked(self, entity_type: str, index: int):
        mod = __import__("PyQt5.QtWidgets", fromlist=["QApplication"])
        qapp = mod.QApplication.instance()
        add = qapp.keyboardModifiers() & Qt.ControlModifier
        if add:
            if (entity_type, index) in self._selected:
                self._selected.remove((entity_type, index))
            else:
                self._selected.append((entity_type, index))
        else:
            self._selected = [(entity_type, index)]
        self._update_drawing_area()
        self.statusBar().showMessage(f"Выбрано: {len(self._selected)} объект(ов)")

    def _on_selection_box(self, selected: list, add_to_selection: bool):
        if add_to_selection:
            for s in selected:
                if s not in self._selected:
                    self._selected.append(s)
        else:
            self._selected = list(selected)
        self._update_drawing_area()
        self.statusBar().showMessage(f"Выбрано: {len(self._selected)} объект(ов)")

    def _sync_layers_from_entities(self):
        for key in ("lines", "circles", "points", "arcs", "polylines", "texts", "splines", "ellipses", "dimensions", "hatches", "inserts"):
            for ent in self.cad_entities.get(key, []):
                layer = ent.get("layer") or "0"
                if layer not in self.layers:
                    self.layers[layer] = {"visible": True, "color": "#FFFFFF"}

    def _refresh_layers_list(self):
        if not hasattr(self, "layers_list"):
            return
        self.layers_list.blockSignals(True)
        self.layers_list.clear()
        for name, props in self.layers.items():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            item.setCheckState(Qt.Checked if props.get("visible", True) else Qt.Unchecked)
            if name == self.active_layer:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
            self.layers_list.addItem(item)
        self.layers_list.blockSignals(False)
        self._update_drawing_area()

    def _on_layer_item_changed(self, item):
        name = item.text()
        visible = item.checkState() == Qt.Checked
        if name in self.layers:
            self.layers[name]["visible"] = visible
        self._update_drawing_area()

    def _add_layer(self):
        name, ok = QInputDialog.getText(self, "Add Layer", "Layer name:")
        if ok and name:
            if name not in self.layers:
                self.layers[name] = {"visible": True, "color": "#FFFFFF"}
                self.active_layer = name
                self._refresh_layers_list()

    def _delete_layer(self):
        item = self.layers_list.currentItem() if hasattr(self, "layers_list") else None
        if not item:
            return
        name = item.text()
        if name == "0":
            return
        self.layers.pop(name, None)
        if self.active_layer == name:
            self.active_layer = "0"
        self._refresh_layers_list()

    def _set_active_layer(self):
        item = self.layers_list.currentItem() if hasattr(self, "layers_list") else None
        if not item:
            return
        self.active_layer = item.text()
        self._refresh_layers_list()

    def _show_layers_dock(self):
        if hasattr(self, "layers_dock"):
            self.layers_dock.raise_()
            self.layers_dock.show()

    def _prev_layer(self):
        names = list(self.layers.keys())
        if not names:
            return
        if self.active_layer in names:
            idx = names.index(self.active_layer)
            self.active_layer = names[idx - 1]
        else:
            self.active_layer = names[0]
        self._refresh_layers_list()

    def _next_layer(self):
        names = list(self.layers.keys())
        if not names:
            return
        if self.active_layer in names:
            idx = names.index(self.active_layer)
            self.active_layer = names[(idx + 1) % len(names)]
        else:
            self.active_layer = names[0]
        self._refresh_layers_list()

    def _on_cursor_moved(self, x: float, y: float, snapped: bool):
        mode = getattr(self, "_interactive_mode", None)
        if mode and mode.get("step", 0) >= 1:
            pts = mode.get("points", [])
            cmd = mode.get("cmd", "")
            import math
            px, py = x, y
            if cmd == "LINE" and pts:
                x1, y1 = pts[-1][0], pts[-1][1]
                if self.ortho_mode:
                    if abs(x - x1) >= abs(y - y1):
                        py = y1
                    else:
                        px = x1
                elif self.polar_mode:
                    dx, dy = x - x1, y - y1
                    ang = math.degrees(math.atan2(dy, dx))
                    snap_ang = round(ang / 45.0) * 45.0
                    length = math.sqrt(dx * dx + dy * dy)
                    rad = math.radians(snap_ang)
                    px = x1 + length * math.cos(rad)
                    py = y1 + length * math.sin(rad)
            elif cmd == "RECTANGLE" and pts and self.ortho_mode:
                x1, y1 = pts[-1][0], pts[-1][1]
                if abs(x - x1) >= abs(y - y1):
                    py = y1
                else:
                    px = x1
            self.drawing_area.set_preview(cmd, pts, (px, py))
            if cmd == "LINE" and pts:
                x1, y1 = pts[-1][0], pts[-1][1]
                dx, dy = px - x1, py - y1
                dist = math.sqrt(dx * dx + dy * dy)
                angle = math.degrees(math.atan2(dy, dx))
                extra = f" | Длина: {dist:.1f}  Угол: {angle:.1f}°"
            else:
                extra = ""
        else:
            self.drawing_area.clear_preview()
            extra = ""
        if snapped:
            self.statusBar().showMessage(f"Cursor: {x:.2f}, {y:.2f} (SNAP){extra} | Ortho: {"ON" if self.ortho_mode else "OFF"} | Polar: {"ON" if self.polar_mode else "OFF"}")
        else:
            self.statusBar().showMessage(f"Cursor: {x:.2f}, {y:.2f}{extra} | Ortho: {"ON" if self.ortho_mode else "OFF"} | Polar: {"ON" if self.polar_mode else "OFF"}")

    def _start_interactive(self, cmd: str) -> None:
        self._interactive_mode = {"cmd": cmd, "step": 0, "points": []}
        self.drawing_area.set_point_pick_mode(True)
        prompts = {"LINE": "Укажите первую точку:", "CIRCLE": "Укажите центр:", "ARC": "Укажите центр дуги:", "POINT": "Укажите точку:", "RECTANGLE": "Укажите первый угол:"}
        self.statusBar().showMessage(prompts.get(cmd, "Укажите точку:"))

    def _end_interactive(self) -> None:
        self._interactive_mode = None
        self.drawing_area.set_point_pick_mode(False)
        self.drawing_area.clear_preview()
        self.statusBar().showMessage("Готово")

    def _on_point_picked(self, x: float, y: float) -> None:
        if not self._interactive_mode:
            return
        mode = self._interactive_mode
        cmd, step, points = mode["cmd"], mode["step"], mode["points"]
        points.append((x, y, 0.0))
        mode["step"] += 1

        if cmd == "LINE":
            if step == 0:
                self.statusBar().showMessage("Укажите следующую точку или Enter для завершения:")
                return
            if step >= 1:
                x1, y1, _ = points[-2]
                x2, y2 = x, y
                if self.ortho_mode:
                    if abs(x2 - x1) >= abs(y2 - y1):
                        y2 = y1
                    else:
                        x2 = x1
                elif self.polar_mode:
                    import math
                    dx, dy = x2 - x1, y2 - y1
                    ang = math.degrees(math.atan2(dy, dx))
                    snap_ang = round(ang / 45.0) * 45.0
                    length = (dx * dx + dy * dy) ** 0.5
                    rad = math.radians(snap_ang)
                    x2, y2 = x1 + length * math.cos(rad), y1 + length * math.sin(rad)
                self._clear_redo_stack()
                self.cad_entities["lines"].append({
                    "start": (x1, y1, 0), "end": (x2, y2, 0),
                    "layer": self.active_layer, "linetype": self.current_linetype
                })
                self._set_modified(True)
                self._refresh_objects_list()
                mode["points"] = [(x2, y2, 0.0)]
                mode["step"] = 1
                self.statusBar().showMessage("Укажите следующую точку или Enter для завершения:")
                return

        if cmd == "CIRCLE":
            if step == 0:
                self.statusBar().showMessage("Укажите точку на окружности (радиус):")
                return
            cx, cy, _ = points[0]
            r = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
            self._clear_redo_stack()
            self.cad_entities["circles"].append({
                "center": (cx, cy, 0), "radius": r,
                "layer": self.active_layer, "linetype": self.current_linetype
            })
            self._set_modified(True)
            self._refresh_objects_list()
            self._end_interactive()
            self.statusBar().showMessage("Круг добавлен")
            return

        if cmd == "ARC":
            if step == 0:
                self.statusBar().showMessage("Укажите начальную точку дуги:")
                return
            if step == 1:
                self.statusBar().showMessage("Укажите конечную точку дуги:")
                return
            cx, cy, _ = points[0]
            sx, sy, _ = points[1]
            import math
            r = ((sx - cx) ** 2 + (sy - cy) ** 2) ** 0.5
            if r < 1e-9:
                self.statusBar().showMessage("Ошибка: нулевой радиус")
                mode["step"] = 1
                mode["points"] = points[:2]
                return
            start_a = math.degrees(math.atan2(sy - cy, sx - cx))
            end_a = math.degrees(math.atan2(y - cy, x - cx))
            self._clear_redo_stack()
            self.cad_entities["arcs"].append({
                "center": (cx, cy, 0), "radius": r, "start_angle": start_a, "end_angle": end_a,
                "layer": self.active_layer, "linetype": self.current_linetype
            })
            self._set_modified(True)
            self._refresh_objects_list()
            self._end_interactive()
            self.statusBar().showMessage("Дуга добавлена")
            return

        if cmd == "POINT":
            self._clear_redo_stack()
            self.cad_entities["points"].append({
                "location": (x, y, 0), "layer": self.active_layer, "linetype": self.current_linetype
            })
            self._set_modified(True)
            self._refresh_objects_list()
            self._end_interactive()
            self.statusBar().showMessage("Точка добавлена")
            return

        if cmd == "RECTANGLE":
            if step == 0:
                self.statusBar().showMessage("Укажите противоположный угол:")
                return
            x1, y1, _ = points[0]
            x2, y2 = x, y
            if self.ortho_mode:
                if abs(x2 - x1) >= abs(y2 - y1):
                    y2 = y1
                else:
                    x2 = x1
            pts = [(x1, y1, 0), (x2, y1, 0), (x2, y2, 0), (x1, y2, 0), (x1, y1, 0)]
            self._clear_redo_stack()
            self.cad_entities["polylines"].append({
                "points": pts, "layer": self.active_layer, "linetype": self.current_linetype
            })
            self._set_modified(True)
            self._refresh_objects_list()
            self._end_interactive()
            self.statusBar().showMessage("Прямоугольник добавлен")
            return

    def _cancel_interactive(self) -> None:
        if self._interactive_mode:
            self._end_interactive()
            self.statusBar().showMessage("Отменено")

    def _on_drawing_context_menu(self, pos):
        menu = QMenu(self)
        if self._interactive_mode:
            menu.addAction("Отменить (Esc)", self._cancel_interactive)
        else:
            menu.addAction("Отменить (Ctrl+Z)", self._delete_last_entity)
        menu.addAction("Повторить (Ctrl+Y)", self._redo)
        menu.addSeparator()
        menu.addAction("Показать всё (Ctrl+0)", self._zoom_extents)
        if self._selected:
            menu.addAction("Масштаб к выделению", self._zoom_to_selection)
        menu.addAction("К началу координат", lambda: (self.drawing_area.zoom_to_origin(), self.statusBar().showMessage("Вид к началу координат (0,0)")))
        menu.addSeparator()
        menu.addAction("Снять выделение", lambda: (self._selected.clear(), self._update_drawing_area(), self.statusBar().showMessage("Выделение снято")))
        menu.addAction("Быстрый старт", self._show_quick_start)
        menu.exec_(self.drawing_area.mapToGlobal(pos))

    def _on_escape(self) -> None:
        if self._interactive_mode:
            self._cancel_interactive()

    def _zoom_in(self):
        self.drawing_area.zoom_in()

    def _zoom_out(self):
        self.drawing_area.zoom_out()

    def _erase_selected(self):
        if not self._selected:
            self.statusBar().showMessage("Нет выделенных объектов. Выделите объекты (клик, рамка) или Ctrl+A.")
            return
        for key, idx in sorted(self._selected, key=lambda x: -x[1]):
            lst = self.cad_entities.get(key, [])
            if 0 <= idx < len(lst):
                lst.pop(idx)
        self._clear_redo_stack()
        self._set_modified(True)
        n = len(self._selected)
        self._selected.clear()
        self._refresh_objects_list()
        self.statusBar().showMessage(f"Удалено {n} объектов")

    def _zoom_extents(self):
        self.drawing_area.zoom_extents()

    def _zoom_to_selection(self):
        if self.drawing_area.zoom_to_selection():
            self.statusBar().showMessage("Масштаб к выделению")
        else:
            self.statusBar().showMessage("Нет выделенных объектов. Выделите объекты.")

    def _toggle_snap(self):
        self.drawing_area.set_snap_enabled(not getattr(self.drawing_area, "_snap_enabled", True))
        state = "ON" if getattr(self.drawing_area, "_snap_enabled", True) else "OFF"
        self.statusBar().showMessage(f"Snap: {state}")

    def _toggle_ortho(self):
        self.ortho_mode = not self.ortho_mode
        self.statusBar().showMessage(f"Ortho: {'ON' if self.ortho_mode else 'OFF'}")

    def _toggle_polar(self):
        self.polar_mode = not self.polar_mode
        self.statusBar().showMessage(f"Polar: {'ON' if self.polar_mode else 'OFF'}")

    def _apply_polyline_constraints(self, pts):
        if not pts or (not self.ortho_mode and not self.polar_mode):
            return pts
        import math
        out = [pts[0]]
        for i in range(1, len(pts)):
            x1, y1, z1 = out[-1]
            x2, y2, z2 = pts[i]
            if self.ortho_mode:
                if abs(x2 - x1) >= abs(y2 - y1):
                    y2 = y1
                else:
                    x2 = x1
            else:
                dx = x2 - x1
                dy = y2 - y1
                angle = math.degrees(math.atan2(dy, dx))
                snap_angle = round(angle / 45.0) * 45.0
                length = (dx * dx + dy * dy) ** 0.5
                rad = math.radians(snap_angle)
                x2 = x1 + length * math.cos(rad)
                y2 = y1 + length * math.sin(rad)
            out.append((x2, y2, z2))
        return out

    def _on_snap_type_changed(self, item):
        label = item.text()
        if item.checkState() == Qt.Checked:
            self.snap_types.add(label)
        else:
            self.snap_types.discard(label)
        self.drawing_area.set_snap_types(list(self.snap_types))

    def _refresh_objects_list(self):
        if hasattr(self, "objects_list"):
            self.objects_list.clear()
            for p in self.cad_entities.get("points", []):
                loc = p.get("location", (0, 0, 0))
                self.objects_list.addItem(f"POINT {loc} layer={p.get('layer', '0')}")
            for l in self.cad_entities.get("lines", []):
                self.objects_list.addItem(f"LINE {l.get('start')} -> {l.get('end')} layer={l.get('layer', '0')}")
            for c in self.cad_entities.get("circles", []):
                self.objects_list.addItem(f"CIRCLE {c.get('center')} r={c.get('radius')} layer={c.get('layer', '0')}")
            for a in self.cad_entities.get("arcs", []):
                self.objects_list.addItem(f"ARC {a.get('center')} r={a.get('radius')} {a.get('start_angle')}->{a.get('end_angle')} layer={a.get('layer', '0')}")
            for p in self.cad_entities.get("polylines", []):
                self.objects_list.addItem(f"POLYLINE {len(p.get('points', []))} pts layer={p.get('layer', '0')}")
            for t in self.cad_entities.get("texts", []):
                self.objects_list.addItem(f"TEXT {t.get('text')} layer={t.get('layer', '0')}")
            for i in self.cad_entities.get("inserts", []):
                self.objects_list.addItem(f"INSERT {i.get('block')} @ {i.get('position')} layer={i.get('layer', '0')}")
        if hasattr(self, "drawing_area"):
            self._update_drawing_area()

    def _clear_redo_stack(self):
        self._redo_stack.clear()
        if hasattr(self, "_redo_label"):
            self._update_redo_label()

    def _get_selected_entities(self) -> list[tuple[str, dict]]:
        """Выбранные объекты или последний при отсутствии выбора."""
        if self._selected:
            result = []
            for key, idx in self._selected:
                lst = self.cad_entities.get(key, [])
                if 0 <= idx < len(lst):
                    result.append((key, lst[idx]))
            return result
        last = self._get_last_entity()
        return [last] if last else []

    def _get_last_entity(self) -> tuple[str, dict] | None:
        for key in ("inserts", "hatches", "dimensions", "texts", "polylines", "splines", "ellipses", "arcs", "circles", "lines", "points"):
            if self.cad_entities.get(key):
                return (key, self.cad_entities[key][-1])
        return None

    def _delete_last_entity(self):
        last = self._get_last_entity()
        if last:
            key, entity = last
            self.cad_entities[key].pop()
            self._redo_stack.append((key, copy.deepcopy(entity)))
            self._set_modified(True)
            self._refresh_objects_list()
            self._update_redo_label()
            self.statusBar().showMessage("Отменено")
        else:
            self.statusBar().showMessage("Нечего отменять")

    def _redo(self):
        if not self._redo_stack:
            self.statusBar().showMessage("Нечего повторять")
            return
        key, entity = self._redo_stack.pop()
        self.cad_entities[key].append(entity)
        self._set_modified(True)
        self._refresh_objects_list()
        self._update_redo_label()
        self.statusBar().showMessage("Повторено")

    def _update_redo_label(self):
        if not hasattr(self, "_redo_label"):
            return
        n = len(self._redo_stack)
        self._redo_label.setText(f" Redo: {n} " if n > 0 else "")

    def _transform_point(self, pt: tuple, dx: float, dy: float, dz: float = 0,
                        angle_deg: float = 0, cx: float = 0, cy: float = 0,
                        scale: float = 1.0) -> tuple:
        x, y, z = pt[0], pt[1], pt[2] if len(pt) > 2 else 0.0
        x += dx
        y += dy
        z += dz
        if angle_deg:
            rad = math.radians(angle_deg)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            x_rel, y_rel = x - cx, y - cy
            x = cx + x_rel * cos_a - y_rel * sin_a
            y = cy + x_rel * sin_a + y_rel * cos_a
        if scale != 1.0:
            x_rel, y_rel = x - cx, y - cy
            x = cx + x_rel * scale
            y = cy + y_rel * scale
        return (x, y, z)

    def _move_entity(self, entity: dict, key: str, dx: float, dy: float, dz: float = 0):
        if key == "points":
            loc = entity.get("location", (0, 0, 0))
            entity["location"] = self._transform_point(loc, dx, dy, dz)
        elif key == "lines":
            s, e = entity.get("start", (0, 0, 0)), entity.get("end", (0, 0, 0))
            entity["start"] = self._transform_point(s, dx, dy, dz)
            entity["end"] = self._transform_point(e, dx, dy, dz)
        elif key == "circles":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, dx, dy, dz)
        elif key == "arcs":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, dx, dy, dz)
        elif key == "polylines":
            pts = entity.get("points", [])
            entity["points"] = [self._transform_point(p, dx, dy, dz) for p in pts]
        elif key == "texts":
            pos = entity.get("position", (0, 0, 0))
            entity["position"] = self._transform_point(pos, dx, dy, dz)
        elif key == "splines":
            pts = entity.get("fit_points", [])
            entity["fit_points"] = [self._transform_point(p, dx, dy, dz) for p in pts]
        elif key == "ellipses":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, dx, dy, dz)
        elif key == "dimensions":
            entity["p1"] = self._transform_point(entity.get("p1", (0, 0, 0)), dx, dy, dz)
            entity["p2"] = self._transform_point(entity.get("p2", (0, 0, 0)), dx, dy, dz)
            entity["dim_pos"] = self._transform_point(entity.get("dim_pos", (0, 0, 0)), dx, dy, dz)
        elif key == "hatches":
            if entity.get("type") == "polygon":
                entity["points"] = [self._transform_point(p, dx, dy, dz) for p in entity.get("points", [])]
            else:
                entity["center"] = self._transform_point(entity.get("center", (0, 0, 0)), dx, dy, dz)
        elif key == "inserts":
            pos = entity.get("position", (0, 0, 0))
            entity["position"] = self._transform_point(pos, dx, dy, dz)

    def _rotate_entity(self, entity: dict, key: str, angle_deg: float, cx: float = 0, cy: float = 0):
        if key == "points":
            loc = entity.get("location", (0, 0, 0))
            entity["location"] = self._transform_point(loc, 0, 0, 0, angle_deg, cx, cy)
        elif key == "lines":
            s, e = entity.get("start", (0, 0, 0)), entity.get("end", (0, 0, 0))
            entity["start"] = self._transform_point(s, 0, 0, 0, angle_deg, cx, cy)
            entity["end"] = self._transform_point(e, 0, 0, 0, angle_deg, cx, cy)
        elif key == "circles":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, 0, 0, 0, angle_deg, cx, cy)
        elif key == "arcs":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, 0, 0, 0, angle_deg, cx, cy)
            entity["start_angle"] = entity.get("start_angle", 0) + angle_deg
            entity["end_angle"] = entity.get("end_angle", 0) + angle_deg
        elif key == "polylines":
            pts = entity.get("points", [])
            entity["points"] = [self._transform_point(p, 0, 0, 0, angle_deg, cx, cy) for p in pts]
        elif key == "texts":
            pos = entity.get("position", (0, 0, 0))
            entity["position"] = self._transform_point(pos, 0, 0, 0, angle_deg, cx, cy)
        elif key == "splines":
            pts = entity.get("fit_points", [])
            entity["fit_points"] = [self._transform_point(p, 0, 0, 0, angle_deg, cx, cy) for p in pts]
        elif key == "ellipses":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, 0, 0, 0, angle_deg, cx, cy)
            maj = entity.get("major_axis", (1, 0, 0))
            entity["major_axis"] = self._transform_point(maj, 0, 0, 0, angle_deg, cx, cy)
        elif key == "dimensions":
            entity["p1"] = self._transform_point(entity.get("p1", (0, 0, 0)), 0, 0, 0, angle_deg, cx, cy)
            entity["p2"] = self._transform_point(entity.get("p2", (0, 0, 0)), 0, 0, 0, angle_deg, cx, cy)
            entity["dim_pos"] = self._transform_point(entity.get("dim_pos", (0, 0, 0)), 0, 0, 0, angle_deg, cx, cy)
        elif key == "hatches":
            if entity.get("type") == "polygon":
                entity["points"] = [self._transform_point(p, 0, 0, 0, angle_deg, cx, cy) for p in entity.get("points", [])]
            else:
                entity["center"] = self._transform_point(entity.get("center", (0, 0, 0)), 0, 0, 0, angle_deg, cx, cy)
        elif key == "inserts":
            pos = entity.get("position", (0, 0, 0))
            entity["position"] = self._transform_point(pos, 0, 0, 0, angle_deg, cx, cy)
            entity["angle"] = entity.get("angle", 0) + angle_deg

    def _scale_entity(self, entity: dict, key: str, factor: float, cx: float = 0, cy: float = 0):
        if key == "points":
            loc = entity.get("location", (0, 0, 0))
            entity["location"] = self._transform_point(loc, 0, 0, 0, 0, cx, cy, factor)
        elif key == "lines":
            s, e = entity.get("start", (0, 0, 0)), entity.get("end", (0, 0, 0))
            entity["start"] = self._transform_point(s, 0, 0, 0, 0, cx, cy, factor)
            entity["end"] = self._transform_point(e, 0, 0, 0, 0, cx, cy, factor)
        elif key == "circles":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, 0, 0, 0, 0, cx, cy, factor)
            entity["radius"] = entity.get("radius", 1) * factor
        elif key == "arcs":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, 0, 0, 0, 0, cx, cy, factor)
            entity["radius"] = entity.get("radius", 1) * factor
        elif key == "polylines":
            pts = entity.get("points", [])
            entity["points"] = [self._transform_point(p, 0, 0, 0, 0, cx, cy, factor) for p in pts]
        elif key == "texts":
            pos = entity.get("position", (0, 0, 0))
            entity["position"] = self._transform_point(pos, 0, 0, 0, 0, cx, cy, factor)
            entity["height"] = entity.get("height", 1) * factor
        elif key == "splines":
            pts = entity.get("fit_points", [])
            entity["fit_points"] = [self._transform_point(p, 0, 0, 0, 0, cx, cy, factor) for p in pts]
        elif key == "ellipses":
            c = entity.get("center", (0, 0, 0))
            entity["center"] = self._transform_point(c, 0, 0, 0, 0, cx, cy, factor)
            maj = entity.get("major_axis", (1, 0, 0))
            entity["major_axis"] = tuple(maj[i] * factor for i in range(min(3, len(maj))))
        elif key == "dimensions":
            entity["p1"] = self._transform_point(entity.get("p1", (0, 0, 0)), 0, 0, 0, 0, cx, cy, factor)
            entity["p2"] = self._transform_point(entity.get("p2", (0, 0, 0)), 0, 0, 0, 0, cx, cy, factor)
            entity["dim_pos"] = self._transform_point(entity.get("dim_pos", (0, 0, 0)), 0, 0, 0, 0, cx, cy, factor)
        elif key == "hatches":
            if entity.get("type") == "polygon":
                entity["points"] = [self._transform_point(p, 0, 0, 0, 0, cx, cy, factor) for p in entity.get("points", [])]
            else:
                entity["center"] = self._transform_point(entity.get("center", (0, 0, 0)), 0, 0, 0, 0, cx, cy, factor)
                entity["radius"] = entity.get("radius", 1) * factor
        elif key == "inserts":
            pos = entity.get("position", (0, 0, 0))
            entity["position"] = self._transform_point(pos, 0, 0, 0, 0, cx, cy, factor)
            entity["scale"] = entity.get("scale", 1.0) * factor

    def _mirror_point(self, pt: tuple, x1: float, y1: float, x2: float, y2: float) -> tuple:
        px, py = pt[0], pt[1]
        pz = pt[2] if len(pt) > 2 else 0.0
        dx, dy = x2 - x1, y2 - y1
        d2 = dx * dx + dy * dy
        if d2 < 1e-12:
            return (px, py, pz)
        t = 2 * ((px - x1) * dx + (py - y1) * dy) / d2
        return (2 * x1 - px + t * dx, 2 * y1 - py + t * dy, pz)

    def _mirror_entity(self, entity: dict, key: str, x1: float, y1: float, x2: float, y2: float):
        if key == "points":
            entity["location"] = self._mirror_point(entity.get("location", (0, 0, 0)), x1, y1, x2, y2)
        elif key == "lines":
            entity["start"] = self._mirror_point(entity.get("start", (0, 0, 0)), x1, y1, x2, y2)
            entity["end"] = self._mirror_point(entity.get("end", (0, 0, 0)), x1, y1, x2, y2)
        elif key == "circles":
            entity["center"] = self._mirror_point(entity.get("center", (0, 0, 0)), x1, y1, x2, y2)
        elif key == "arcs":
            entity["center"] = self._mirror_point(entity.get("center", (0, 0, 0)), x1, y1, x2, y2)
            sa, ea = entity.get("start_angle", 0), entity.get("end_angle", 0)
            entity["start_angle"] = 180 - ea
            entity["end_angle"] = 180 - sa
        elif key == "polylines":
            entity["points"] = [self._mirror_point(p, x1, y1, x2, y2) for p in entity.get("points", [])]
        elif key == "texts":
            entity["position"] = self._mirror_point(entity.get("position", (0, 0, 0)), x1, y1, x2, y2)
        elif key == "splines":
            entity["fit_points"] = [self._mirror_point(p, x1, y1, x2, y2) for p in entity.get("fit_points", [])]
        elif key == "ellipses":
            entity["center"] = self._mirror_point(entity.get("center", (0, 0, 0)), x1, y1, x2, y2)
            maj = entity.get("major_axis", (1, 0, 0))
            entity["major_axis"] = self._mirror_point((maj[0], maj[1], maj[2] if len(maj) > 2 else 0), x1, y1, x2, y2)
        elif key == "dimensions":
            entity["p1"] = self._mirror_point(entity.get("p1", (0, 0, 0)), x1, y1, x2, y2)
            entity["p2"] = self._mirror_point(entity.get("p2", (0, 0, 0)), x1, y1, x2, y2)
            entity["dim_pos"] = self._mirror_point(entity.get("dim_pos", (0, 0, 0)), x1, y1, x2, y2)
        elif key == "hatches":
            if entity.get("type") == "polygon":
                entity["points"] = [self._mirror_point(p, x1, y1, x2, y2) for p in entity.get("points", [])]
            else:
                entity["center"] = self._mirror_point(entity.get("center", (0, 0, 0)), x1, y1, x2, y2)
        elif key == "inserts":
            entity["position"] = self._mirror_point(entity.get("position", (0, 0, 0)), x1, y1, x2, y2)
            entity["angle"] = -entity.get("angle", 0)

    def _offset_entity(self, entity: dict, key: str, dist: float) -> dict | None:
        """Смещение. Возвращает новую сущность или None."""
        if key == "lines":
            s = entity.get("start", (0, 0, 0))
            e = entity.get("end", (0, 0, 0))
            dx, dy = e[0] - s[0], e[1] - s[1]
            L = (dx * dx + dy * dy) ** 0.5
            if L < 1e-9:
                return None
            nx, ny = -dy / L, dx / L
            layer = entity.get("layer", self.active_layer)
            return {"start": (s[0] + nx * dist, s[1] + ny * dist, s[2]), "end": (e[0] + nx * dist, e[1] + ny * dist, e[2]), "layer": layer}
        if key == "polylines":
            pts = entity.get("points", [])
            if len(pts) < 2:
                return None
            off_lines = []
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                dx, dy = b[0] - a[0], b[1] - a[1]
                L = (dx * dx + dy * dy) ** 0.5
                if L < 1e-9:
                    continue
                nx, ny = -dy / L, dx / L
                z = a[2] if len(a) > 2 else 0.0
                off_lines.append(((a[0] + nx * dist, a[1] + ny * dist, z), (b[0] + nx * dist, b[1] + ny * dist, z)))
            if not off_lines:
                return None
            new_pts = [off_lines[0][0]]
            for i in range(len(off_lines) - 1):
                (x1, y1, z1), (x2, y2, _) = off_lines[i]
                (x3, y3, _), (x4, y4, z4) = off_lines[i + 1]
                denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
                if abs(denom) < 1e-9:
                    new_pts.append(off_lines[i][1])
                else:
                    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
                    new_pts.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1), z1))
            new_pts.append(off_lines[-1][1])
            return {"points": new_pts, "layer": entity.get("layer", self.active_layer)}
        if key == "circles":
            c = entity.get("center", (0, 0, 0))
            r = entity.get("radius", 0) + dist
            if r <= 0:
                return None
            return {"center": c, "radius": r, "layer": entity.get("layer", self.active_layer)}
        if key == "arcs":
            c = entity.get("center", (0, 0, 0))
            r = entity.get("radius", 0) + dist
            if r <= 0:
                return None
            return {"center": c, "radius": r, "start_angle": entity.get("start_angle", 0),
                    "end_angle": entity.get("end_angle", 360), "layer": entity.get("layer", self.active_layer)}
        return None

    def _project_point_on_line(self, px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> tuple | None:
        """Проекция точки на отрезок. Возвращает (t, x, y) или None. t — параметр 0..1 на отрезке."""
        dx, dy = x2 - x1, y2 - y1
        d2 = dx * dx + dy * dy
        if d2 < 1e-12:
            return None
        t = ((px - x1) * dx + (py - y1) * dy) / d2
        x = x1 + t * dx
        y = y1 + t * dy
        return (t, x, y)

    def _trim_line(self, entity: dict, px: float, py: float) -> tuple | None:
        """Обрезка линии в точке (px,py). Возвращает (new_start, new_end) или None."""
        s = entity.get("start", (0, 0, 0))
        e = entity.get("end", (0, 0, 0))
        proj = self._project_point_on_line(px, py, s[0], s[1], e[0], e[1])
        if not proj:
            return None
        t, x, y = proj
        if t <= 0 or t >= 1:
            return None
        z = s[2] if len(s) > 2 else 0.0
        pt = (x, y, z)
        ds = (px - s[0])**2 + (py - s[1])**2
        de = (px - e[0])**2 + (py - e[1])**2
        if ds < de:
            return (pt, tuple(e))
        return (tuple(s), pt)

    def _extend_line(self, entity: dict, px: float, py: float) -> tuple | None:
        """Удлинение линии до точки (px,py). Возвращает (new_start, new_end) или None. Один из них может быть None."""
        s = entity.get("start", (0, 0, 0))
        e = entity.get("end", (0, 0, 0))
        dx, dy = e[0] - s[0], e[1] - s[1]
        L = (dx * dx + dy * dy) ** 0.5
        if L < 1e-9:
            return None
        ux, uy = dx / L, dy / L
        t = (px - s[0]) * ux + (py - s[1]) * uy
        z = s[2] if len(s) > 2 else 0.0
        if t > L:
            return (None, (s[0] + t * ux, s[1] + t * uy, z))
        if t < 0:
            return ((px, py, z), None)
        return None

    def _line_line_intersection(self, a1, a2, b1, b2) -> tuple | None:
        """Точка пересечения отрезков (a1,a2) и (b1,b2). Возвращает (x,y) или None."""
        x1, y1 = a1[0], a1[1]
        x2, y2 = a2[0], a2[1]
        x3, y3 = b1[0], b1[1]
        x4, y4 = b2[0], b2[1]
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-12:
            return None
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom
        if 0 <= t <= 1 and 0 <= u <= 1:
            return (x1 + t * (x2 - x1), y1 + t * (y2 - y1))
        return None

    def _fillet_lines(self, e1: dict, e2: dict, radius: float) -> tuple | None:
        """Скругление двух линий. Возвращает ((s1,e1),(s2,e2),arc) или None."""
        a1, a2 = e1.get("start", (0,0,0)), e1.get("end", (0,0,0))
        b1, b2 = e2.get("start", (0,0,0)), e2.get("end", (0,0,0))
        pt = self._line_line_intersection(a1, a2, b1, b2)
        if not pt:
            return None
        ix, iy = pt
        da = (a2[0] - a1[0], a2[1] - a1[1])
        db = (b2[0] - b1[0], b2[1] - b1[1])
        la = (da[0]**2 + da[1]**2)**0.5
        lb = (db[0]**2 + db[1]**2)**0.5
        if la < 1e-9 or lb < 1e-9:
            return None
        ua = (da[0]/la, da[1]/la)
        ub = (db[0]/lb, db[1]/lb)
        dot = ua[0]*ub[0] + ua[1]*ub[1]
        half_angle = math.acos(max(-1, min(1, dot))) / 2
        if abs(math.sin(half_angle)) < 1e-9:
            return None
        dist = radius / math.tan(half_angle)
        if dist > la/2 or dist > lb/2:
            return None
        p1 = (ix - ua[0]*dist, iy - ua[1]*dist, a1[2] if len(a1)>2 else 0)
        p2 = (ix - ub[0]*dist, iy - ub[1]*dist, b1[2] if len(b1)>2 else 0)
        ang1 = math.degrees(math.atan2(p1[1] - iy, p1[0] - ix))
        ang2 = math.degrees(math.atan2(p2[1] - iy, p2[0] - ix))
        arc = {"center": (ix, iy, 0), "radius": radius, "start_angle": ang1, "end_angle": ang2, "layer": e1.get("layer", self.active_layer)}
        return ((p1, (ix, iy, 0)), (p2, (ix, iy, 0)), arc)

    def _chamfer_lines(self, e1: dict, e2: dict, d1: float, d2: float) -> tuple | None:
        """Срез угла двух линий. Возвращает ((s1,e1),(s2,e2),new_line) или None."""
        a1, a2 = e1.get("start", (0,0,0)), e1.get("end", (0,0,0))
        b1, b2 = e2.get("start", (0,0,0)), e2.get("end", (0,0,0))
        pt = self._line_line_intersection(a1, a2, b1, b2)
        if not pt:
            return None
        ix, iy = pt
        da = (a2[0] - a1[0], a2[1] - a1[1])
        db = (b2[0] - b1[0], b2[1] - b1[1])
        la = (da[0]**2 + da[1]**2)**0.5
        lb = (db[0]**2 + db[1]**2)**0.5
        if la < 1e-9 or lb < 1e-9:
            return None
        ua = (da[0]/la, da[1]/la)
        ub = (db[0]/lb, db[1]/lb)
        p1 = (ix - ua[0]*d1, iy - ua[1]*d1, a1[2] if len(a1)>2 else 0)
        p2 = (ix - ub[0]*d2, iy - ub[1]*d2, b1[2] if len(b1)>2 else 0)
        new_line = {"start": p1, "end": p2, "layer": e1.get("layer", self.active_layer)}
        return ((a1, p1), (b1, p2), new_line)

    def _execute_command(self):
        cmd = self.command_line.text().strip()
        self.command_line.clear()
        if not cmd:
            if self._interactive_mode:
                self._end_interactive()
                self.statusBar().showMessage("Завершено")
            return
        cmd_upper = cmd.upper()
        if cmd_upper in ("ESC", "CANCEL", "ESCAPE") and self._interactive_mode:
            self._cancel_interactive()
            return
        self.statusBar().showMessage(f"Command: {cmd}")
        self._parse_command(cmd)

    _CMD_ALIASES = {
        "L": "LINE", "C": "CIRCLE", "A": "ARC", "REC": "RECTANGLE", "PL": "POLYLINE",
        "M": "MOVE", "CO": "COPY", "CP": "COPY", "E": "ERASE", "RO": "ROTATE",
        "SC": "SCALE", "MI": "MIRROR", "O": "OFFSET", "TR": "TRIM", "EX": "EXTEND",
        "F": "FILLET", "CHA": "CHAMFER", "BR": "BREAK", "J": "JOIN", "X": "EXPLODE",
        "AR": "ARRAY", "D": "DIMLINEAR", "DLI": "DIMLINEAR", "DRA": "DIMRADIUS",
        "DDI": "DIMDIAMETER", "PE": "PEDIT", "LA": "LAYER",
        "ZO": "VIEW_ORIGIN",
    }

    def _parse_command(self, cmd):
        parts = cmd.split()
        if not parts:
            return

        command = parts[0].upper()
        if command in self._CMD_ALIASES:
            command = self._CMD_ALIASES[command]
        args = parts[1:]

        if command in ("HELP", "?"):
            self._show_help()
            return

        if command == "MULTIPLE":
            if args:
                next_cmd = args[0].upper()
                if next_cmd in self._CMD_ALIASES:
                    next_cmd = self._CMD_ALIASES[next_cmd]
                self._last_command = next_cmd
                self._last_args = args[1:]
                self._multiple_mode = True
                self.statusBar().showMessage(f"Повтор: {next_cmd} (Esc для выхода)")
                self._parse_command(next_cmd + (" " + " ".join(args[1:]) if args[1:] else ""))
            elif self._last_command:
                self._multiple_mode = True
                self.statusBar().showMessage(f"Повтор: {self._last_command}")
                self._parse_command(self._last_command + (" " + " ".join(self._last_args) if self._last_args else ""))
            else:
                self.statusBar().showMessage("Нет предыдущей команды для повтора")
            return

        if command not in ("ESC", "CANCEL", "ESCAPE", "HELP", "?"):
            self._last_command = command
            self._last_args = args

        if command == "NEW":
            self._new_file()
            return

        if command == "OPEN":
            self._open_file()
            return

        if command in ("SAVE", "SAVEAS"):
            self._save_file(force_dialog=(command == "SAVEAS"))
            return

        if command == "LINETYPE":
            if not args:
                self.statusBar().showMessage(f"Текущий тип линии: {self.current_linetype}")
                return
            name = args[0]
            valid = {"continuous": "Continuous", "dashed": "Dashed", "dotted": "Dotted", "dashdot": "DashDot", "dashdotdot": "DashDotDot"}
            key = name.lower()
            if key in valid:
                self.current_linetype = valid[key]
                self.statusBar().showMessage(f"Тип линии: {self.current_linetype}")
            else:
                self.statusBar().showMessage("LINETYPE: Continuous, Dashed, Dotted, DashDot, DashDotDot")
            return

        if command == "STATUS":
            if self.app and self.app.is_connected:
                self.statusBar().showMessage("Engine: connected")
            else:
                self.statusBar().showMessage("Engine: not connected")
            return

        if command in ("ZOOM_EXTENTS", "ZE"):
            self._zoom_extents()
            self.statusBar().showMessage("Показать всё")
            return

        if command in ("VIEW_ORIGIN", "ZOOM_ORIGIN"):
            self.drawing_area.zoom_to_origin()
            self.statusBar().showMessage("Вид к началу координат (0,0)")
            return

        if command in ("ZOOM_SELECTION", "ZS"):
            self._zoom_to_selection()
            return

        if command in ("UNDO", "U"):
            self._delete_last_entity()
            return

        if command in ("REDO", "R"):
            self._redo()
            return

        if command in ("VIEW_TOP", "VIEW_FRONT", "VIEW_LEFT", "VT", "VF", "VL"):
            self._zoom_extents()
            self.statusBar().showMessage("Вид в 2D: zoom to extents")
            return

        # Новые команды для Full 3D
        if command == "VIEW3D_FULL":
            self._switch_3d_mode("full")
            return

        if command == "VIEW3D_PREVIEW":
            self._switch_3d_mode("preview")
            return

        if command == "LOAD_MODEL_3D":
            if args:
                self._load_model_full_3d(" ".join(args))
            else:
                fname, _ = QFileDialog.getOpenFileName(
                    self, "Загрузить 3D модель", "",
                    "3D модели (*.gltf *.glb *.obj *.stp *.step *.stl);;Все файлы (*)"
                )
                if fname:
                    self._load_model_full_3d(fname)
            return

        if command == "TRAJ_SPLINE":
            spline_type = args[0].lower() if args else "cubic"
            if self._last_trajectory_points:
                self._traj_manager.create_trajectory(
                    "main",
                    [TrajectoryPoint(*p) for p in self._last_trajectory_points],
                    spline_type=spline_type,
                )
                self._set_trajectory_full_3d(self._last_trajectory_points)
            return

        if command == "TRAJ_SMOOTH":
            method = args[0].lower() if args else "chaikin"
            self._traj_manager.smooth_trajectory("main", method)
            pts = self._traj_manager.discretize_trajectory("main", 100)
            if pts:
                self._set_trajectory_full_3d([p.position for p in pts])
            return

        if command == "SIMULATE_3D":
            steps = int(args[0]) if args else 60
            speed = float(args[1]) if len(args) > 1 else 1.0
            self._simulate_full_3d(steps, speed)
            return

        if command == "EXPORT_GCODE":
            self._export_gcode_dialog()
            return

        if command == "TRAJ_SPIRAL":
            self._generate_spiral_trajectory()
            return

        if command == "TRAJ_ZIGZAG":
            self._generate_zigzag_trajectory()
            return

        if command == "REACHABILITY":
            if len(args) >= 3:
                try:
                    x, y, z = float(args[0]), float(args[1]), float(args[2])
                    self._check_reachability_full(x, y, z)
                except ValueError:
                    self.statusBar().showMessage("REACHABILITY x y z — координаты")
            else:
                self.statusBar().showMessage("REACHABILITY x y z")
            return

        if command == "CLEAR_SCENE":
            if self._3d_mode == "full":
                self._view3d_full.clear_scene()
            self._traj_manager.clear()
            self.statusBar().showMessage("Сцена очищена")
            return

        if command in ("ZOOM_EXTENTS", "ZE"):
            if not args:
                self.statusBar().showMessage("LAYER NEW name | SET name | FREEZE name | THAW name | LOCK name | UNLOCK name | DELETE name")
                return
            sub = args[0].upper()
            name = args[1] if len(args) >= 2 else ""
            if sub == "NEW":
                if name and name not in self.layers:
                    self.layers[name] = {"visible": True, "color": "#FFFFFF", "locked": False}
                    self.active_layer = name
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Слой '{name}' создан")
                else:
                    self.statusBar().showMessage(f"LAYER NEW <имя>")
                return
            if sub == "SET":
                if name in self.layers:
                    self.active_layer = name
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Текущий слой: {name}")
                else:
                    self.statusBar().showMessage(f"Слой '{name}' не найден")
                return
            if sub == "FREEZE":
                if name in self.layers:
                    self.layers[name]["visible"] = False
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Слой '{name}' заморожен")
                return
            if sub in ("THAW", "ON"):
                if name in self.layers:
                    self.layers[name]["visible"] = True
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Слой '{name}' разморожен")
                return
            if sub == "LOCK":
                if name in self.layers:
                    self.layers[name]["locked"] = True
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Слой '{name}' заблокирован")
                return
            if sub == "UNLOCK":
                if name in self.layers:
                    self.layers[name]["locked"] = False
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Слой '{name}' разблокирован")
                return
            if sub == "DELETE":
                if name == "0":
                    self.statusBar().showMessage("Нельзя удалить слой 0")
                    return
                if name in self.layers:
                    self.layers.pop(name)
                    if self.active_layer == name:
                        self.active_layer = "0"
                    self._refresh_layers_list()
                    self.statusBar().showMessage(f"Слой '{name}' удалён")
                return
            self.statusBar().showMessage("LAYER NEW | SET | FREEZE | THAW | LOCK | UNLOCK | DELETE")
            return

        if command == "GRID":
            if args:
                try:
                    spacing = float(args[0])
                    self.drawing_area.set_grid_spacing(spacing)
                    self.statusBar().showMessage(f"Сетка: шаг {spacing}")
                except ValueError:
                    self.statusBar().showMessage("GRID [шаг] — включить/шаг сетки")
            else:
                enabled = not getattr(self.drawing_area, "_grid_enabled", True)
                self.drawing_area.set_grid_enabled(enabled)
                self.statusBar().showMessage(f"Сетка: {'ВКЛ' if enabled else 'ВЫКЛ'}")
            return

        if command == "MOVE":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Нет объектов для перемещения. Выберите или создайте объект.")
                return
            if len(args) < 2:
                self.statusBar().showMessage("MOVE dx dy [dz] — укажите смещение по X и Y")
                return
            try:
                dx, dy = float(args[0]), float(args[1])
                dz = float(args[2]) if len(args) > 2 else 0.0
            except ValueError:
                self.statusBar().showMessage("MOVE: нужны числа (dx dy). Пример: MOVE 10 0")
                return
            for key, entity in targets:
                self._move_entity(entity, key, dx, dy, dz)
            self._clear_redo_stack()
            self._set_modified(True)
            self._selected.clear()
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Перемещено {len(targets)} объектов на ({dx}, {dy})")
            return

        if command == "COPY":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Нет объектов для копирования. Выберите или создайте объект.")
                return
            if len(args) < 2:
                self.statusBar().showMessage("COPY dx dy [dz] — укажите смещение копии")
                return
            try:
                dx, dy = float(args[0]), float(args[1])
                dz = float(args[2]) if len(args) > 2 else 0.0
            except ValueError:
                self.statusBar().showMessage("COPY: нужны числа (dx dy). Пример: COPY 50 0")
                return
            for key, entity in targets:
                new_ent = copy.deepcopy(entity)
                self._move_entity(new_ent, key, dx, dy, dz)
                self.cad_entities[key].append(new_ent)
            self._clear_redo_stack()
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Создано {len(targets)} копий со смещением ({dx}, {dy})")
            return

        if command == "ROTATE":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Нет объектов для поворота. Выберите или создайте объект.")
                return
            if len(args) < 1:
                self.statusBar().showMessage("Usage: ROTATE angle [cx cy]")
                return
            try:
                angle = float(args[0])
                cx = float(args[1]) if len(args) >= 3 else 0.0
                cy = float(args[2]) if len(args) >= 3 else 0.0
            except ValueError:
                self.statusBar().showMessage("ROTATE expects numeric angle [cx cy]")
                return
            for key, entity in targets:
                self._rotate_entity(entity, key, angle, cx, cy)
            self._clear_redo_stack()
            self._set_modified(True)
            self._selected.clear()
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Повёрнуто {len(targets)} объектов на {angle}°")
            return

        if command == "SCALE":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Нет объектов для масштабирования. Выберите или создайте объект.")
                return
            if len(args) < 1:
                self.statusBar().showMessage("Usage: SCALE factor [cx cy]")
                return
            try:
                factor = float(args[0])
                cx = float(args[1]) if len(args) >= 3 else 0.0
                cy = float(args[2]) if len(args) >= 3 else 0.0
            except ValueError:
                self.statusBar().showMessage("SCALE expects numeric factor [cx cy]")
                return
            if factor <= 0:
                self.statusBar().showMessage("Множитель должен быть > 0")
                return
            for key, entity in targets:
                self._scale_entity(entity, key, factor, cx, cy)
            self._clear_redo_stack()
            self._set_modified(True)
            self._selected.clear()
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Масштабировано {len(targets)} объектов в {factor}x")
            return

        if command in ("ERASE", "E", "DELETE"):
            if not self._selected:
                self.statusBar().showMessage("Нет выбора. Щёлкните объект или введите ERASE и выберите.")
                return
            for key, idx in sorted(self._selected, key=lambda x: -x[1]):
                lst = self.cad_entities.get(key, [])
                if 0 <= idx < len(lst):
                    lst.pop(idx)
            self._clear_redo_stack()
            self._set_modified(True)
            n = len(self._selected)
            self._selected.clear()
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Удалено {n} объектов")
            return

        if command == "MIRROR":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Нет объектов. Выберите объекты (Ctrl+клик — несколько).")
                return
            if len(args) < 4:
                self.statusBar().showMessage("Usage: MIRROR x1 y1 x2 y2  — ось симметрии")
                return
            try:
                x1, y1, x2, y2 = float(args[0]), float(args[1]), float(args[2]), float(args[3])
            except ValueError:
                self.statusBar().showMessage("MIRROR expects numeric x1 y1 x2 y2")
                return
            dx, dy = x2 - x1, y2 - y1
            if abs(dx) < 1e-9 and abs(dy) < 1e-9:
                self.statusBar().showMessage("Точки оси не должны совпадать")
                return
            for key, entity in targets:
                self._mirror_entity(entity, key, x1, y1, x2, y2)
            self._clear_redo_stack()
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Отражено {len(targets)} объектов")
            return

        if command == "STRETCH":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Нет объектов. Выберите объекты для растягивания.")
                return
            if len(args) < 2:
                self.statusBar().showMessage("Usage: STRETCH dx dy [dz]")
                return
            try:
                dx, dy = float(args[0]), float(args[1])
                dz = float(args[2]) if len(args) > 2 else 0.0
            except ValueError:
                self.statusBar().showMessage("STRETCH expects numeric dx dy")
                return
            for key, entity in targets:
                self._move_entity(entity, key, dx, dy, dz)
            self._clear_redo_stack()
            self._set_modified(True)
            self._selected.clear()
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Растянуто {len(targets)} объектов")
            return

        if command == "EXPLODE":
            targets = self._get_selected_entities()
            inserts = [(k, e) for k, e in targets if k == "inserts"]
            if not inserts:
                self.statusBar().showMessage("Выберите блоки (INSERT) для разбора")
                return
            to_remove = []
            for key, ins in inserts:
                block = self.blocks.get(ins.get("block", ""))
                if not block:
                    continue
                pos = ins.get("position", (0, 0, 0))
                scale = ins.get("scale", 1.0)
                angle = math.radians(ins.get("angle", 0))
                c, s = math.cos(angle), math.sin(angle)
                layer = ins.get("layer", "0")
                for ent in block.get("entities", []):
                    k = ent.get("key", "")
                    e = copy.deepcopy(ent.get("entity", {}))
                    if not e:
                        continue
                    if k == "lines":
                        st, en = e.get("start", (0,0,0)), e.get("end", (0,0,0))
                        xf = lambda xe, ye: (pos[0] + (xe*c - ye*s)*scale, pos[1] + (xe*s + ye*c)*scale, pos[2])
                        e["start"] = xf(st[0], st[1]) + (st[2] if len(st)>2 else 0,)
                        e["end"] = xf(en[0], en[1]) + (en[2] if len(en)>2 else 0,)
                        e["layer"] = layer
                        self.cad_entities["lines"].append(e)
                    elif k == "circles":
                        ct = e.get("center", (0,0,0))
                        xf = lambda xe, ye: (pos[0] + (xe*c - ye*s)*scale, pos[1] + (xe*s + ye*c)*scale, pos[2])
                        e["center"] = xf(ct[0], ct[1]) + (ct[2] if len(ct)>2 else 0,)
                        e["radius"] = e.get("radius", 0) * scale
                        e["layer"] = layer
                        self.cad_entities["circles"].append(e)
                    elif k == "arcs":
                        ct = e.get("center", (0,0,0))
                        xf = lambda xe, ye: (pos[0] + (xe*c - ye*s)*scale, pos[1] + (xe*s + ye*c)*scale, pos[2])
                        e["center"] = xf(ct[0], ct[1]) + (ct[2] if len(ct)>2 else 0,)
                        e["radius"] = e.get("radius", 0) * scale
                        e["layer"] = layer
                        self.cad_entities["arcs"].append(e)
                    elif k == "polylines":
                        pts = e.get("points", [])
                        new_pts = []
                        for pt in pts:
                            xe, ye = pt[0], pt[1]
                            z = pt[2] if len(pt) > 2 else 0
                            new_pts.append((pos[0] + (xe*c - ye*s)*scale, pos[1] + (xe*s + ye*c)*scale, z))
                        e["points"] = new_pts
                        e["layer"] = layer
                        self.cad_entities["polylines"].append(e)
                to_remove.append(ins)
            for ins in to_remove:
                self.cad_entities["inserts"].remove(ins)
            self._selected.clear()
            self._clear_redo_stack()
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Разобрано {len(to_remove)} блок(ов)")
            return

        if command == "BREAK":
            targets = self._get_selected_entities()
            if not targets or len(targets) != 1:
                self.statusBar().showMessage("Выберите 1 линию для разрыва")
                return
            if len(args) < 4:
                self.statusBar().showMessage("Usage: BREAK x1 y1 x2 y2 — удалить отрезок между точками")
                return
            try:
                x1, y1 = float(args[0]), float(args[1])
                x2, y2 = float(args[2]), float(args[3])
            except ValueError:
                self.statusBar().showMessage("BREAK expects numeric x1 y1 x2 y2")
                return
            key, entity = targets[0]
            if key == "lines":
                s, e = entity.get("start", (0,0,0)), entity.get("end", (0,0,0))
                ax, ay = s[0], s[1]
                bx, by = e[0], e[1]
                dx, dy = bx - ax, by - ay
                L2 = dx*dx + dy*dy
                if L2 < 1e-12:
                    return
                t1 = max(0, min(1, ((x1-ax)*dx + (y1-ay)*dy)/L2))
                t2 = max(0, min(1, ((x2-ax)*dx + (y2-ay)*dy)/L2))
                t_lo, t_hi = min(t1, t2), max(t1, t2)
                if t_hi - t_lo < 1e-6:
                    self.statusBar().showMessage("Точки слишком близко")
                    return
                p1 = (ax + t_lo*dx, ay + t_lo*dy, s[2] if len(s)>2 else 0)
                p2 = (ax + t_hi*dx, ay + t_hi*dy, e[2] if len(e)>2 else 0)
                if t_lo > 1e-6 and t_hi < 1 - 1e-6:
                    entity["end"] = p1
                    self.cad_entities["lines"].append({
                        "start": p2, "end": (bx, by, e[2] if len(e)>2 else 0),
                        "layer": entity.get("layer", "0")
                    })
                elif t_lo > 1e-6:
                    entity["end"] = p1
                elif t_hi < 1 - 1e-6:
                    entity["start"] = p2
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
                self.statusBar().showMessage("Линия разорвана")
            else:
                self.statusBar().showMessage("BREAK пока только для линий (LINE)")
            return

        if command == "JOIN":
            targets = self._get_selected_entities()
            lines = [(k, e) for k, e in targets if k == "lines"]
            if len(lines) < 2:
                self.statusBar().showMessage("Выберите 2+ линии для соединения")
                return
            def pt_eq(a, b, tol=1e-6):
                return abs(a[0]-b[0])<tol and abs(a[1]-b[1])<tol
            def collinear(s1, e1, s2, e2):
                dx1, dy1 = e1[0]-s1[0], e1[1]-s1[1]
                dx2, dy2 = e2[0]-s2[0], e2[1]-s2[1]
                if abs(dx1*dy2 - dy1*dx2) > 1e-6:
                    return False
                return True
            joined = []
            used = set()
            for i, (k, ln) in enumerate(lines):
                if i in used:
                    continue
                chain = [ln]
                used.add(i)
                s, e = ln.get("start", (0,0,0)), ln.get("end", (0,0,0))
                front, back = s, e
                for j, (_, ln2) in enumerate(lines):
                    if j in used:
                        continue
                    s2, e2 = ln2.get("start", (0,0,0)), ln2.get("end", (0,0,0))
                    if not collinear(s, e, s2, e2):
                        continue
                    if pt_eq(e, s2):
                        chain.append(ln2)
                        used.add(j)
                        back = e2
                    elif pt_eq(e, e2):
                        chain.append(dict(ln2, start=e2, end=s2))
                        used.add(j)
                        back = s2
                    elif pt_eq(s, e2):
                        chain.insert(0, ln2)
                        used.add(j)
                        front = s2
                    elif pt_eq(s, s2):
                        chain.insert(0, dict(ln2, start=e2, end=s2))
                        used.add(j)
                        front = s2
                if len(chain) >= 2:
                    pts = [front]
                    back = chain[0].get("end", (0,0,0))
                    for i in range(1, len(chain)):
                        s2, e2 = chain[i].get("start", (0,0,0)), chain[i].get("end", (0,0,0))
                        new_back = e2 if pt_eq(s2, back) else s2
                        pts.append(new_back)
                        back = new_back
                    self.cad_entities["polylines"].append({
                        "points": [(p[0], p[1], p[2] if len(p)>2 else 0) for p in pts],
                        "layer": chain[0].get("layer", "0")
                    })
                    for l in chain:
                        self.cad_entities["lines"].remove(l)
                    joined.append(len(chain))
            if joined:
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
                self.statusBar().showMessage(f"Соединено {sum(joined)} линий в {len(joined)} полилиний")
            else:
                self.statusBar().showMessage("Линии не коллинеарны или не соприкасаются")
            return

        if command == "OFFSET":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите линию или полилинию")
                return
            if len(args) < 1:
                self.statusBar().showMessage("Usage: OFFSET distance")
                return
            try:
                dist = float(args[0])
            except ValueError:
                self.statusBar().showMessage("OFFSET expects numeric distance")
                return
            for key, entity in targets:
                new_ent = self._offset_entity(entity, key, dist)
                if new_ent:
                    self.cad_entities[key].append(new_ent)
            self._clear_redo_stack()
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Смещение на {dist}")
            return

        if command == "TRIM":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите линию для обрезки")
                return
            if len(args) < 2:
                self.statusBar().showMessage("Usage: TRIM x y  — точка обрезки")
                return
            try:
                px, py = float(args[0]), float(args[1])
            except ValueError:
                self.statusBar().showMessage("TRIM expects numeric x y")
                return
            n = 0
            for key, entity in targets:
                if key == "lines":
                    r = self._trim_line(entity, px, py)
                    if r:
                        entity["start"], entity["end"] = r
                        n += 1
            if n:
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
            self.statusBar().showMessage(f"Обрезка: {n} линий" if n else "Точка не на линии")
            return

        if command == "EXTEND":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите линию для удлинения")
                return
            if len(args) < 2:
                self.statusBar().showMessage("Usage: EXTEND x y  — точка удлинения")
                return
            try:
                px, py = float(args[0]), float(args[1])
            except ValueError:
                self.statusBar().showMessage("EXTEND expects numeric x y")
                return
            n = 0
            for key, entity in targets:
                if key == "lines":
                    res = self._extend_line(entity, px, py)
                    if res:
                        ns, ne = res
                        if ns is not None:
                            entity["start"] = ns
                        if ne is not None:
                            entity["end"] = ne
                        n += 1
            if n:
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
            self.statusBar().showMessage(f"Удлинено: {n} линий" if n else "Удлинение не выполнено")
            return

        if command == "FILLET":
            targets = self._get_selected_entities()
            if not targets or len(targets) != 2:
                self.statusBar().showMessage("Выберите 2 линии для скругления")
                return
            if len(args) < 1:
                self.statusBar().showMessage("Usage: FILLET radius")
                return
            try:
                r = float(args[0])
            except ValueError:
                self.statusBar().showMessage("FILLET expects numeric radius")
                return
            if r <= 0:
                self.statusBar().showMessage("Радиус должен быть > 0")
                return
            (k1, e1), (k2, e2) = targets[0], targets[1]
            if k1 != "lines" or k2 != "lines":
                self.statusBar().showMessage("FILLET только для линий")
                return
            result = self._fillet_lines(e1, e2, r)
            if result:
                e1["start"], e1["end"] = result[0]
                e2["start"], e2["end"] = result[1]
                self.cad_entities["arcs"].append(result[2])
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
                self.statusBar().showMessage("Скругление выполнено")
            else:
                self.statusBar().showMessage("Линии не пересекаются или радиус слишком велик")
            return

        if command == "CHAMFER":
            targets = self._get_selected_entities()
            if not targets or len(targets) != 2:
                self.statusBar().showMessage("Выберите 2 линии для среза")
                return
            if len(args) < 1:
                self.statusBar().showMessage("Usage: CHAMFER distance  или CHAMFER d1 d2")
                return
            try:
                d1 = float(args[0])
                d2 = float(args[1]) if len(args) >= 2 else d1
            except ValueError:
                self.statusBar().showMessage("CHAMFER expects numeric distance(s)")
                return
            if d1 <= 0 or d2 <= 0:
                self.statusBar().showMessage("Расстояния должны быть > 0")
                return
            (k1, e1), (k2, e2) = targets[0], targets[1]
            if k1 != "lines" or k2 != "lines":
                self.statusBar().showMessage("CHAMFER только для линий")
                return
            result = self._chamfer_lines(e1, e2, d1, d2)
            if result:
                e1["start"], e1["end"] = result[0]
                e2["start"], e2["end"] = result[1]
                self.cad_entities["lines"].append(result[2])
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
                self.statusBar().showMessage("Срез выполнен")
            else:
                self.statusBar().showMessage("Линии не пересекаются")
            return

        if command == "ARRAY":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите объекты")
                return
            if len(args) < 2:
                self.statusBar().showMessage("Usage: ARRAY R rows cols [rowDist colDist] | ARRAY P count angle [cx cy]")
                return
            mode = args[0].upper()
            if mode == "R":
                try:
                    rows, cols = int(args[1]), int(args[2])
                    row_dist = float(args[3]) if len(args) >= 5 else 50.0
                    col_dist = float(args[4]) if len(args) >= 5 else 50.0
                except (ValueError, IndexError):
                    self.statusBar().showMessage("ARRAY R rows cols [rowDist colDist]")
                    return
                for key, entity in targets:
                    for r in range(rows):
                        for c in range(cols):
                            if r == 0 and c == 0:
                                continue
                            new_ent = copy.deepcopy(entity)
                            self._move_entity(new_ent, key, c * col_dist, -r * row_dist, 0)
                            self.cad_entities[key].append(new_ent)
            elif mode == "P":
                try:
                    count = int(args[1])
                    angle = float(args[2])
                    cx = float(args[3]) if len(args) >= 5 else 0.0
                    cy = float(args[4]) if len(args) >= 5 else 0.0
                except (ValueError, IndexError):
                    self.statusBar().showMessage("ARRAY P count angle [cx cy]")
                    return
                step = angle / (count - 1) if count > 1 else 0
                for key, entity in targets:
                    for i in range(1, count):
                        new_ent = copy.deepcopy(entity)
                        self._rotate_entity(new_ent, key, i * step, cx, cy)
                        self.cad_entities[key].append(new_ent)
            else:
                self.statusBar().showMessage("ARRAY R или ARRAY P")
                return
            self._clear_redo_stack()
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage("Массив создан")
            return

        if command == "POINT":
            if len(args) == 0:
                self._start_interactive("POINT")
                return
            if len(args) < 2:
                self.statusBar().showMessage("Usage: POINT x y [z]")
                return
            try:
                x = float(args[0]); y = float(args[1])
                z = float(args[2]) if len(args) > 2 else 0.0
            except ValueError:
                self.statusBar().showMessage("POINT expects numeric coordinates")
                return
            self._clear_redo_stack()
            self.cad_entities["points"].append({"location": (x, y, z), "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage(f"Point added: {x}, {y}, {z}")
            self._refresh_objects_list()
            return

        if command == "LINE":
            if len(args) == 0:
                self._start_interactive("LINE")
                return
            if len(args) not in (4, 6):
                self.statusBar().showMessage("Usage: LINE x1 y1 [z1] x2 y2 [z2]")
                return
            try:
                if len(args) == 4:
                    x1, y1, x2, y2 = map(float, args)
                    z1 = z2 = 0.0
                else:
                    x1, y1, z1, x2, y2, z2 = map(float, args)
            except ValueError:
                self.statusBar().showMessage("LINE expects numeric coordinates")
                return
            if self.ortho_mode:
                if abs(x2 - x1) >= abs(y2 - y1):
                    y2 = y1
                else:
                    x2 = x1
            elif self.polar_mode:
                import math
                dx = x2 - x1
                dy = y2 - y1
                angle = math.degrees(math.atan2(dy, dx))
                snap_angle = round(angle / 45.0) * 45.0
                length = (dx * dx + dy * dy) ** 0.5
                rad = math.radians(snap_angle)
                x2 = x1 + length * math.cos(rad)
                y2 = y1 + length * math.sin(rad)
            self._clear_redo_stack()
            self.cad_entities["lines"].append({"start": (x1, y1, z1), "end": (x2, y2, z2), "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Line added")
            self._refresh_objects_list()
            return

        if command == "ARC":
            if len(args) == 0:
                self._start_interactive("ARC")
                return
            if len(args) not in (5, 6):
                self.statusBar().showMessage("Usage: ARC x y [z] r start end")
                return
            try:
                if len(args) == 5:
                    x, y, r, start_a, end_a = map(float, args)
                    z = 0.0
                else:
                    x, y, z, r, start_a, end_a = map(float, args)
            except ValueError:
                self.statusBar().showMessage("ARC expects numeric values")
                return
            if self.ortho_mode:
                if abs(x) >= abs(y):
                    y = 0.0
                else:
                    x = 0.0
            elif self.polar_mode:
                import math
                angle = math.degrees(math.atan2(y, x))
                snap_angle = round(angle / 45.0) * 45.0
                length = (x * x + y * y) ** 0.5
                rad = math.radians(snap_angle)
                x = length * math.cos(rad)
                y = length * math.sin(rad)
            self._clear_redo_stack()
            self.cad_entities["arcs"].append({"center": (x, y, z), "radius": r, "start_angle": start_a, "end_angle": end_a, "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Arc added")
            self._refresh_objects_list()
            return

        if command == "RECTANGLE":
            if len(args) == 0:
                self._start_interactive("RECTANGLE")
                return
            if len(args) < 4:
                self.statusBar().showMessage("Usage: RECTANGLE x1 y1 x2 y2 [z]")
                return
            try:
                x1, y1, x2, y2 = float(args[0]), float(args[1]), float(args[2]), float(args[3])
                z = float(args[4]) if len(args) >= 5 else 0.0
            except ValueError:
                self.statusBar().showMessage("RECTANGLE expects numeric x1 y1 x2 y2 [z]")
                return
            pts = [(x1, y1, z), (x2, y1, z), (x2, y2, z), (x1, y2, z), (x1, y1, z)]
            self._clear_redo_stack()
            self.cad_entities["polylines"].append({"points": pts, "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Прямоугольник добавлен")
            self._refresh_objects_list()
            return

        if command == "POLYLINE":
            if len(args) < 4:
                self.statusBar().showMessage("Usage: POLYLINE x1 y1 x2 y2 [x3 y3 ...]")
                return
            try:
                vals = list(map(float, args))
            except ValueError:
                self.statusBar().showMessage("POLYLINE expects numeric coordinates")
                return
            pts = []
            if len(vals) % 2 == 0:
                for i in range(0, len(vals), 2):
                    pts.append((vals[i], vals[i+1], 0.0))
            elif len(vals) % 3 == 0:
                for i in range(0, len(vals), 3):
                    pts.append((vals[i], vals[i+1], vals[i+2]))
            else:
                self.statusBar().showMessage("POLYLINE expects pairs or triples of coordinates")
                return
            pts = self._apply_polyline_constraints(pts)
            self._clear_redo_stack()
            self.cad_entities["polylines"].append({"points": pts, "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Polyline added")
            self._refresh_objects_list()
            return

        if command == "TEXT":
            if len(args) < 4:
                self.statusBar().showMessage("Usage: TEXT x y [z] height text...")
                return
            try:
                x = float(args[0]); y = float(args[1])
                idx = 2
                z = 0.0
                if len(args) >= 5:
                    try:
                        z = float(args[2])
                        idx = 3
                    except ValueError:
                        z = 0.0
                        idx = 2
                height = float(args[idx])
                text_value = " ".join(args[idx+1:])
            except Exception:
                self.statusBar().showMessage("TEXT expects numeric position and height")
                return
            self._clear_redo_stack()
            self.cad_entities["texts"].append({"position": (x, y, z), "height": height, "text": text_value, "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Text added")
            self._refresh_objects_list()
            return

        if command == "SPLINE":
            if len(args) < 4:
                self.statusBar().showMessage("Usage: SPLINE x1 y1 x2 y2 [x3 y3 ...]")
                return
            try:
                vals = list(map(float, args))
            except ValueError:
                self.statusBar().showMessage("SPLINE expects numeric coordinates")
                return
            pts = []
            for i in range(0, len(vals), 2):
                if i + 1 < len(vals):
                    pts.append((vals[i], vals[i + 1], 0.0))
            if len(pts) < 2:
                self.statusBar().showMessage("SPLINE needs at least 2 points")
                return
            self._clear_redo_stack()
            self.cad_entities["splines"].append({"fit_points": pts, "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Сплайн добавлен")
            self._refresh_objects_list()
            return

        if command == "BLOCK":
            if len(args) < 1:
                self.statusBar().showMessage("Usage: BLOCK name [base_x base_y] — создать из выбранных объектов")
                return
            name = args[0]
            if name in self.blocks:
                self.statusBar().showMessage(f"Блок '{name}' уже существует. Используйте другое имя.")
                return
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите объекты для блока")
                return
            try:
                bx = float(args[1]) if len(args) >= 3 else None
                by = float(args[2]) if len(args) >= 3 else None
            except (ValueError, IndexError):
                bx, by = None, None
            entities = []
            all_pts = []
            for key, entity in targets:
                ent_copy = copy.deepcopy(entity)
                if key == "lines":
                    all_pts.extend([ent_copy.get("start", (0,0,0)), ent_copy.get("end", (0,0,0))])
                elif key in ("circles", "arcs", "points"):
                    all_pts.append(ent_copy.get("center", ent_copy.get("location", (0,0,0))))
                elif key in ("polylines", "splines"):
                    all_pts.extend(ent_copy.get("points", ent_copy.get("fit_points", [])))
                elif key == "texts":
                    all_pts.append(ent_copy.get("position", (0,0,0)))
                elif key == "ellipses":
                    all_pts.append(ent_copy.get("center", (0,0,0)))
                entities.append({"key": key, "entity": ent_copy})
            if not all_pts:
                self.statusBar().showMessage("Нет геометрии для блока")
                return
            if bx is None:
                bx = sum(p[0] for p in all_pts) / len(all_pts)
            if by is None:
                by = sum(p[1] for p in all_pts) / len(all_pts)
            base = (bx, by, 0)
            for item in entities:
                e = item["entity"]
                k = item["key"]
                if k == "lines":
                    e["start"] = tuple(e["start"][i] - base[i] for i in range(3))
                    e["end"] = tuple(e["end"][i] - base[i] for i in range(3))
                elif k in ("circles", "arcs"):
                    e["center"] = tuple((e.get("center", (0,0,0))[i] - base[i] for i in range(3)))
                elif k == "points":
                    e["location"] = tuple((e.get("location", (0,0,0))[i] - base[i] for i in range(3)))
                elif k in ("polylines", "splines"):
                    pts_key = "points" if k == "polylines" else "fit_points"
                    e[pts_key] = [tuple(p[i] - base[i] for i in range(min(3, len(p)))) for p in e.get(pts_key, [])]
                elif k == "texts":
                    e["position"] = tuple((e.get("position", (0,0,0))[i] - base[i] for i in range(3)))
                elif k == "ellipses":
                    e["center"] = tuple((e.get("center", (0,0,0))[i] - base[i] for i in range(3)))
            self.blocks[name] = {"base": base, "entities": entities}
            for key, idx in sorted(self._selected, key=lambda x: -x[1]):
                lst = self.cad_entities.get(key, [])
                if 0 <= idx < len(lst):
                    lst.pop(idx)
            self._selected.clear()
            self._clear_redo_stack()
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Блок '{name}' создан")
            return

        if command == "PEDIT":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите полилинию")
                return
            if args and args[0].upper() == "W":
                width = float(args[1]) if len(args) >= 2 else 0.0
                if width < 0:
                    self.statusBar().showMessage("Ширина должна быть >= 0")
                    return
                for key, entity in targets:
                    if key == "polylines":
                        entity["width"] = width
                        self._set_modified(True)
                        self._refresh_objects_list()
                        self.statusBar().showMessage(f"Ширина полилинии: {width}")
                        return
            if args and args[0].upper() == "J":
                polylines = [(k, e) for k, e in targets if k == "polylines"]
                if len(polylines) < 2:
                    self.statusBar().showMessage("Выберите 2+ полилинии для соединения")
                    return
                pts = []
                for key, entity in polylines:
                    pts.extend(entity.get("points", []))
                if pts:
                    self._clear_redo_stack()
                    for key, entity in polylines:
                        lst = self.cad_entities.get(key, [])
                        if entity in lst:
                            lst.remove(entity)
                    self.cad_entities["polylines"].append({"points": pts, "layer": self.active_layer, "linetype": self.current_linetype})
                    self._selected.clear()
                    self._set_modified(True)
                    self._refresh_objects_list()
                    self.statusBar().showMessage("Полилинии соединены")
                return
            self.statusBar().showMessage("PEDIT W <ширина> | PEDIT J (join)")
            return

        if command == "XREF":
            if not args or args[0].upper() != "ATTACH":
                self.statusBar().showMessage("XREF ATTACH <путь> — прикрепить внешний файл как блок")
                return
            path = " ".join(args[1:]).strip().strip('"')
            if not path:
                fname, _ = QFileDialog.getOpenFileName(self, "Прикрепить XREF", "",
                    "KengaCAD (*.kengacad);;DXF (*.dxf);;DWG (*.dwg);;All (*)")
                if not fname:
                    return
                path = fname
            path_obj = Path(path)
            if not path_obj.exists():
                self.statusBar().showMessage(f"Файл не найден: {path}")
                return
            bname = path_obj.stem
            if bname in self.blocks:
                self.statusBar().showMessage(f"Блок '{bname}' уже существует. Удалите или используйте другое имя.")
                return
            importer = self._get_importer()
            if path_obj.suffix.lower() == ".kengacad":
                try:
                    data = json.loads(path_obj.read_text(encoding="utf-8"))
                    ent = data.get("entities", {})
                except Exception as e:
                    self.statusBar().showMessage(f"Ошибка чтения: {e}")
                    return
            else:
                ent = importer.import_dxf(str(path_obj))
                if not ent:
                    self.statusBar().showMessage(f"Не удалось загрузить: {path}")
                    return
            entities = []
            for k in ("lines", "circles", "points", "arcs", "polylines"):
                for e in ent.get(k, []):
                    entities.append({"key": k, "entity": dict(e)})
            self.blocks[bname] = {"base": (0, 0, 0), "entities": entities}
            self._refresh_objects_list()
            self.statusBar().showMessage(f"XREF '{bname}' прикреплён. INSERT {bname} x y")
            return

        if command == "INSERT":
            if len(args) < 3:
                self.statusBar().showMessage("Usage: INSERT block_name x y [scale] [angle]")
                return
            bname = args[0]
            if bname not in self.blocks:
                self.statusBar().showMessage(f"Блок '{bname}' не найден")
                return
            try:
                x, y = float(args[1]), float(args[2])
                scale = float(args[3]) if len(args) >= 4 else 1.0
                angle = float(args[4]) if len(args) >= 5 else 0.0
            except (ValueError, IndexError):
                self.statusBar().showMessage("INSERT expects numeric x y [scale] [angle]")
                return
            self._clear_redo_stack()
            self.cad_entities["inserts"].append({
                "block": bname, "position": (x, y, 0), "scale": scale, "angle": angle,
                "layer": self.active_layer
            })
            self._set_modified(True)
            self._refresh_objects_list()
            self.statusBar().showMessage(f"Блок '{bname}' вставлен")
            return

        if command == "HATCH":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите замкнутую полилинию или круг")
                return
            color = args[0] if args else "#555555"
            for key, entity in targets:
                if key == "polylines":
                    pts = entity.get("points", [])
                    if len(pts) < 3:
                        continue
                    if abs(pts[0][0] - pts[-1][0]) > 1e-6 or abs(pts[0][1] - pts[-1][1]) > 1e-6:
                        self.statusBar().showMessage("Полилиния должна быть замкнутой")
                        return
                    self.cad_entities["hatches"].append({
                        "type": "polygon", "points": list(pts), "layer": entity.get("layer", self.active_layer),
                        "color": color if color.startswith("#") else "#555555"
                    })
                elif key == "circles":
                    c = entity.get("center", (0, 0, 0))
                    r = entity.get("radius", 0)
                    self.cad_entities["hatches"].append({
                        "type": "circle", "center": c, "radius": r, "layer": entity.get("layer", self.active_layer),
                        "color": color if color.startswith("#") else "#555555"
                    })
            if targets:
                self._clear_redo_stack()
                self._set_modified(True)
                self._refresh_objects_list()
                self.statusBar().showMessage("Штриховка добавлена")
            return

        if command == "DISTANCE":
            targets = self._get_selected_entities()
            if len(targets) < 2:
                self.statusBar().showMessage("Выберите 2 объекта (точки, линии)")
                return
            def get_point(key, entity):
                if key == "points":
                    return entity.get("location", (0,0,0))
                if key == "lines":
                    return entity.get("start", (0,0,0))
                return None
            p1 = get_point(targets[0][0], targets[0][1])
            p2 = get_point(targets[1][0], targets[1][1])
            if targets[1][0] == "lines":
                p2 = targets[1][1].get("end", (0,0,0))
            if p1 and p2:
                d = ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)**0.5
                self.statusBar().showMessage(f"Расстояние: {d:.2f}")
            return

        if command == "AREA":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите замкнутую полилинию или круг")
                return
            total = 0.0
            for key, entity in targets:
                if key == "circles":
                    r = entity.get("radius", 0)
                    total += math.pi * r * r
                elif key == "polylines":
                    pts = entity.get("points", [])
                    if len(pts) >= 3 and abs(pts[0][0]-pts[-1][0]) < 1e-6 and abs(pts[0][1]-pts[-1][1]) < 1e-6:
                        area = 0
                        for i in range(len(pts)-1):
                            area += pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1]
                        total += abs(area) / 2
            self.statusBar().showMessage(f"Площадь: {total:.2f}")
            return

        if command == "DIMRADIUS":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите круг или дугу")
                return
            for key, entity in targets:
                if key == "circles":
                    c = entity.get("center", (0, 0, 0))
                    r = entity.get("radius", 0)
                    dim_pos = (c[0] + r * 1.2, c[1], 0)
                    self._clear_redo_stack()
                    self.cad_entities["dimensions"].append({
                        "dim_type": "radius", "center": c, "radius": r, "dim_pos": dim_pos,
                        "value": r, "layer": self.active_layer
                    })
                    self._set_modified(True)
                    self._refresh_objects_list()
                    self.statusBar().showMessage(f"Размер радиуса R{r:.2f}")
                    return
            self.statusBar().showMessage("Выберите круг")
            return

        if command == "DIMDIAMETER":
            targets = self._get_selected_entities()
            if not targets:
                self.statusBar().showMessage("Выберите круг или дугу")
                return
            for key, entity in targets:
                if key == "circles":
                    c = entity.get("center", (0, 0, 0))
                    r = entity.get("radius", 0)
                    dim_pos = (c[0] + r * 1.2, c[1], 0)
                    self._clear_redo_stack()
                    self.cad_entities["dimensions"].append({
                        "dim_type": "diameter", "center": c, "radius": r, "dim_pos": dim_pos,
                        "value": 2 * r, "layer": self.active_layer
                    })
                    self._set_modified(True)
                    self._refresh_objects_list()
                    self.statusBar().showMessage(f"Размер диаметра Ø{2*r:.2f}")
                    return
            self.statusBar().showMessage("Выберите круг")
            return

        if command in ("DIM", "DIMLINEAR"):
            if len(args) < 4:
                self.statusBar().showMessage("Usage: DIMLINEAR x1 y1 x2 y2 [xm ym]")
                return
            try:
                x1, y1, x2, y2 = float(args[0]), float(args[1]), float(args[2]), float(args[3])
                xm = float(args[4]) if len(args) >= 6 else (x1 + x2) / 2
                ym = float(args[5]) if len(args) >= 6 else (y1 + y2) / 2
            except ValueError:
                self.statusBar().showMessage("DIMLINEAR expects numeric coordinates")
                return
            dist = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
            self._clear_redo_stack()
            self.cad_entities["dimensions"].append({
                "p1": (x1, y1, 0), "p2": (x2, y2, 0), "dim_pos": (xm, ym, 0),
                "value": dist, "layer": self.active_layer
            })
            self._set_modified(True)
            self.statusBar().showMessage(f"Размер: {dist:.2f}")
            self._refresh_objects_list()
            return

        if command == "ELLIPSE":
            if len(args) < 4:
                self.statusBar().showMessage("Usage: ELLIPSE cx cy majorX majorY [ratio]")
                return
            try:
                cx, cy = float(args[0]), float(args[1])
                major_x, major_y = float(args[2]), float(args[3])
                ratio = float(args[4]) if len(args) >= 5 else 1.0
            except ValueError:
                self.statusBar().showMessage("ELLIPSE expects numeric values")
                return
            if ratio <= 0 or ratio > 1:
                self.statusBar().showMessage("ratio должна быть от 0 до 1")
                return
            self._clear_redo_stack()
            self.cad_entities["ellipses"].append({
                "center": (cx, cy, 0.0),
                "major_axis": (major_x, major_y, 0.0),
                "ratio": ratio,
                "layer": self.active_layer,
                "linetype": self.current_linetype
            })
            self._set_modified(True)
            self.statusBar().showMessage("Эллипс добавлен")
            self._refresh_objects_list()
            return

        if command == "CIRCLE":
            if len(args) == 0:
                self._start_interactive("CIRCLE")
                return
            if len(args) not in (3, 4):
                self.statusBar().showMessage("Usage: CIRCLE x y [z] r")
                return
            try:
                if len(args) == 3:
                    x, y, r = map(float, args)
                    z = 0.0
                else:
                    x, y, z, r = map(float, args)
            except ValueError:
                self.statusBar().showMessage("CIRCLE expects numeric values")
                return
            if self.ortho_mode:
                if abs(x) >= abs(y):
                    y = 0.0
                else:
                    x = 0.0
            elif self.polar_mode:
                import math
                angle = math.degrees(math.atan2(y, x))
                snap_angle = round(angle / 45.0) * 45.0
                length = (x * x + y * y) ** 0.5
                rad = math.radians(snap_angle)
                x = length * math.cos(rad)
                y = length * math.sin(rad)
            self._clear_redo_stack()
            self.cad_entities["circles"].append({"center": (x, y, z), "radius": r, "layer": self.active_layer, "linetype": self.current_linetype})
            self._set_modified(True)
            self.statusBar().showMessage("Circle added")
            self._refresh_objects_list()
            return

        if command == "LOAD_DEMO_ROBOT":
            demo_path = self._get_demo_robot_path()
            if demo_path and demo_path.exists():
                self.statusBar().showMessage("Загрузка демо-модели робота...")
                if hasattr(self, "_view3d_scene") and self._view3d_scene.load_mesh(str(demo_path)):
                    self.statusBar().showMessage("Модель робота загружена в 3D-сцену")
                    # Multi-robot: assign unique id
                    existing_rids = [o.get("id") for o in self._scene_objects if o.get("type") == "robot"]
                    rn = len(existing_rids) + 1
                    rid = f"robot_{rn}"
                    while rid in existing_rids:
                        rn += 1
                        rid = f"robot_{rn}"
                    self._scene_objects.insert(0, {"id": rid, "name": f"Робот [{rid}]", "type": "robot"})
                    self._update_scene_tree()
                if self.app:
                    self._run_async_command(self.app.load_robot("assets/robot.glb"), 'load_demo_robot')
            else:
                self.statusBar().showMessage("Демо-модель не найдена. Используйте Робот → загрузить свою модель.")
            return

        if command == "LOAD_ROBOT":
            if not args:
                model_path, _ = QFileDialog.getOpenFileName(
                    self, "Выберите модель робота", "",
                    "3D модели (*.glb *.gltf);;Все файлы (*)")
                if not model_path:
                    return
                args = [model_path]
            model_path = " ".join(args).strip()
            if not model_path:
                return
            ext = Path(model_path).suffix.lower()
            if ext in (".ipt", ".iam"):
                QMessageBox.information(self, "Inventor (.ipt / .iam)",
                    "Формат Autodesk Inventor (.ipt — деталь, .iam — сборка) требует конвертации в glTF.\n\n"
                    "В Inventor: Файл → Экспорт → glTF 3D. Сохраните в GLB и загрузите в KengaCAD.")
                return
            self.statusBar().showMessage("Загрузка робота...")
            if hasattr(self, "_view3d_scene") and self._view3d_scene.load_mesh(model_path):
                self.statusBar().showMessage("Модель робота загружена в 3D-сцену")
                # Multi-robot: assign unique id
                existing_rids = [o.get("id") for o in self._scene_objects if o.get("type") == "robot"]
                rn = len(existing_rids) + 1
                rid = f"robot_{rn}"
                while rid in existing_rids:
                    rn += 1
                    rid = f"robot_{rn}"
                self._scene_objects.insert(0, {"id": rid, "name": f"Робот [{rid}]", "type": "robot"})
                self._update_scene_tree()
            else:
                self.statusBar().showMessage("Не удалось загрузить модель. Проверьте, что pyvista, pyvistaqt, trimesh установлены в окружении сборки.")
            if self.app:
                self._run_async_command(self.app.load_robot(model_path), 'load_robot')
            return

        if command == "TRAC_LENGTH":
            polylines = self.cad_entities.get("polylines", [])
            if not polylines:
                self.statusBar().showMessage("Нет полилинии. Создайте POLYLINE.")
                return
            last = polylines[-1]
            pts = last.get("points", [])
            if len(pts) < 2:
                self.statusBar().showMessage("Полилиния слишком короткая")
                return
            total = 0.0
            for i in range(len(pts) - 1):
                p1, p2 = pts[i], pts[i + 1]
                total += ((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)**0.5
            self.statusBar().showMessage(f"Длина траектории: {total:.2f}")
            return

        if command == "TRAC_FROM_POLYLINE":
            polylines = self.cad_entities.get("polylines", [])
            if not polylines:
                self.statusBar().showMessage("Нет полилинии. Создайте POLYLINE.")
                return
            last = polylines[-1]
            pts = last.get("points", [])
            if len(pts) < 2:
                self.statusBar().showMessage("Полилиния слишком короткая")
                return
            points = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in pts]
            self._last_trajectory_points = points
            self._update_view3d_preview()
            self.statusBar().showMessage(f"Траектория из {len(points)} точек")
            if self.app:
                self._run_async_command(self.app.setup_robot_trajectory(points=points), 'trac_from_polyline')
            return

        if command == "EXPORT_TRAC":
            polylines = self.cad_entities.get("polylines", [])
            if not polylines:
                self.statusBar().showMessage("Нет полилинии для экспорта")
                return
            last = polylines[-1]
            pts = last.get("points", [])
            if len(pts) < 2:
                self.statusBar().showMessage("Полилиния слишком короткая")
                return
            points = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in pts]
            path = " ".join(args).strip() if args else None
            if not path:
                path, _ = QFileDialog.getSaveFileName(self, "Экспорт траектории", "",
                    "JSON (*.json);;CSV (*.csv);;KUKA KRL (*.krl);;ABB RAPID (*.mod);;"
                    "Fanuc TP (*.ls);;Yaskawa INFORM (*.jbi);;UR Script (*.script);;All (*)")
            if path:
                importer = self.app.cad_importer if self.app else CADImportExport()
                low = path.lower()
                if low.endswith('.csv'):
                    ok = importer.export_csv_trajectory(points, path)
                elif low.endswith('.krl'):
                    ok = importer.export_kuka_krl(points, path)
                elif low.endswith('.mod') or low.endswith('.prg'):
                    ok = importer.export_abb_rapid(points, path)
                elif low.endswith('.ls'):
                    ok = importer.export_fanuc_tp(points, path)
                elif low.endswith('.jbi'):
                    ok = importer.export_yaskawa_inform(points, path)
                elif low.endswith('.script') or low.endswith('.urscript'):
                    ok = importer.export_ur_script(points, path)
                else:
                    ok = importer.export_json_trajectory(points, path)
                if ok:
                    self.statusBar().showMessage(f"Траектория экспортирована: {path}")
                else:
                    self.statusBar().showMessage("Ошибка экспорта")
            return

        if command in ("EXPORT_FANUC_TP", "EXPORT_YASKAWA_INFORM", "EXPORT_UR_SCRIPT"):
            polylines = self.cad_entities.get("polylines", [])
            if not polylines:
                self.statusBar().showMessage("Нет полилинии для экспорта")
                return
            last = polylines[-1]
            pts = last.get("points", [])
            if len(pts) < 2:
                self.statusBar().showMessage("Полилиния слишком короткая")
                return
            points = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in pts]
            importer = self.app.cad_importer if self.app else CADImportExport()
            if command == "EXPORT_FANUC_TP":
                filt = "Fanuc TP (*.ls);;All (*)"
                label = "Fanuc TP"
            elif command == "EXPORT_YASKAWA_INFORM":
                filt = "Yaskawa INFORM (*.jbi);;All (*)"
                label = "Yaskawa INFORM"
            else:
                filt = "UR Script (*.script);;All (*)"
                label = "UR Script"
            path = " ".join(args).strip() if args else None
            if not path:
                path, _ = QFileDialog.getSaveFileName(self, f"Экспорт {label}", "", filt)
            if path:
                if command == "EXPORT_FANUC_TP":
                    ok = importer.export_fanuc_tp(points, path)
                elif command == "EXPORT_YASKAWA_INFORM":
                    ok = importer.export_yaskawa_inform(points, path)
                else:
                    ok = importer.export_ur_script(points, path)
                if ok:
                    self.statusBar().showMessage(f"Траектория экспортирована ({label}): {path}")
                else:
                    self.statusBar().showMessage(f"Ошибка экспорта {label}")
            return

        if command == "TRAJECTORY":
            if not self._require_engine():
                return
            if not args:
                self.statusBar().showMessage("Usage: TRAJECTORY <json|csv> или TRAC_FROM_POLYLINE")
                return
            path = " ".join(args)
            imp = self._get_importer()
            try:
                if path.lower().endswith('.csv'):
                    points = imp.import_csv_trajectory(path)
                else:
                    points = imp.import_json_trajectory(path)
            except Exception as e:
                self.statusBar().showMessage(f"Ошибка загрузки траектории: {e}")
                return
            if not points:
                self.statusBar().showMessage("Не удалось загрузить точки траектории")
                return
            self._last_trajectory_points = points
            self._update_view3d_preview()
            self.statusBar().showMessage("Создание траектории...")
            self._run_async_command(self.app.setup_robot_trajectory(points=points), 'trajectory')
            return

        if command == "SET_JOINT":
            if not self._require_engine():
                return
            if len(args) < 2:
                self.statusBar().showMessage("Usage: SET_JOINT <name> <deg>")
                return
            joint = args[0]
            try:
                angle = float(args[1])
            except ValueError:
                self.statusBar().showMessage("Angle must be a number")
                return
            self.statusBar().showMessage(f"Установка сустава {joint}...")
            self._run_async_command(self.app.set_robot_joints({joint: angle}), 'set_joint')
            return

        if command == "SIMULATE":
            pts = self._last_trajectory_points
            if not pts:
                polylines = self.cad_entities.get("polylines", [])
                if polylines:
                    raw = polylines[-1].get("points", [])
                    pts = [(float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0) for p in raw]
            if not pts or len(pts) < 2:
                self.statusBar().showMessage("Нет траектории. POLYLINE → TRAC_FROM_POLYLINE")
                return
            self._last_trajectory_points = pts
            self._update_view3d_preview()
            # Запустить анимацию в preview-виджете
            speed_map = {"0.5x": 0.5, "1x": 1.0, "2x": 2.0}
            speed_txt = self._sim_speed_combo.currentText() if hasattr(self, "_sim_speed_combo") else "1x"
            speed = speed_map.get(speed_txt, 1.0)
            steps = max(len(pts) * 2, 60)
            if hasattr(self._view3d, "simulationFinished"):
                try:
                    self._view3d.simulationFinished.disconnect()
                except Exception:
                    pass
                self._view3d.simulationFinished.connect(
                    lambda: self.statusBar().showMessage("Симуляция завершена")
                )
            self._view3d.start_simulation(steps, speed)
            # Запустить IK-driven анимацию в 3D-сцене
            self._start_robot_simulation(pts, speed)
            self.statusBar().showMessage(f"Симуляция: {len(pts)} точек...")
            return

        if command == "START_DISPENSING":
            if not self._require_engine():
                return
            flow = getattr(self, "_dispensing_flow", 1.0)
            radius = getattr(self, "_dispensing_radius", 0.02)
            if len(args) >= 1:
                try:
                    flow = float(args[0])
                except ValueError:
                    self.statusBar().showMessage("Flow must be number")
                    return
            if len(args) >= 2:
                try:
                    radius = float(args[1])
                except ValueError:
                    self.statusBar().showMessage("Radius must be number")
                    return
            self.statusBar().showMessage("Starting dispensing...")
            self._run_async_command(self.app.start_dispensing(flow_rate=flow, radius=radius), 'start_dispensing')
            return

        if command == "STOP_DISPENSING":
            if not self._require_engine():
                return
            self.statusBar().showMessage("Остановка диспенсинга...")
            self._run_async_command(self.app.stop_dispensing(), 'stop_dispensing')
            return

        if command == "CLEAR_SCENE":
            if not self._require_engine():
                return
            self.statusBar().showMessage("Очистка сцены...")
            self._run_async_command(self.app.clear_scene(), 'clear_scene')
            return

        if command == "EDIT_TRAC":
            self._edit_trajectory()
            return

        if command == "CHECK_COLLISION" or command == "CHECK_COLLISIONS":
            self._run_check_collision(args)
            return

        if command == "REACHABILITY":
            pos = None
            if len(args) >= 3:
                try:
                    pos = (float(args[0]), float(args[1]), float(args[2]))
                except ValueError:
                    self.statusBar().showMessage("REACHABILITY x y z — числа")
                    return
            else:
                txt, ok = QInputDialog.getText(self, "REACHABILITY", "Позиция (x y z в мм):", text="0 0 100")
                if not ok or not txt.strip():
                    return
                parts = txt.strip().split()
                if len(parts) < 3:
                    self.statusBar().showMessage("Укажите x y z")
                    return
                try:
                    pos = (float(parts[0]), float(parts[1]), float(parts[2]))
                except ValueError:
                    self.statusBar().showMessage("x y z должны быть числами")
                    return
            max_reach = 1500.0
            if hasattr(self, "_robot_combo"):
                idx = self._robot_combo.currentIndex()
                data = self._robot_combo.itemData(idx) if idx >= 0 else None
                if isinstance(data, dict):
                    max_reach = float(data.get("max_reach_mm", max_reach))
            reachable = kinematics_reachability(pos, max_reach_mm=max_reach)
            msg = f"Достижимость ({pos[0]:.0f}, {pos[1]:.0f}, {pos[2]:.0f}): {'да' if reachable else 'нет'} (радиус {max_reach:.0f} мм)"
            self.statusBar().showMessage(msg)
            if self.app and getattr(self.app, "is_connected", False):
                self._run_async_command(self.app.check_reachability(pos), 'reachability')
            return

        if command == "CALIBRATE_DISPENSER":
            self.statusBar().showMessage("Калибровка: настройте расход и радиус в диалоге «Диспенсинг» и запустите START_DISPENSING")
            return

        self.statusBar().showMessage(f"Неизвестная команда: {command}")

    def _show_help(self):
        help_text = (
            "Команды KengaCAD:\n\n"
            "ЧЕРТЁЖ: POINT x y | LINE x1 y1 x2 y2 | CIRCLE x y r | ARC x y r start end\n"
            "RECTANGLE x1 y1 x2 y2 | POLYLINE x1 y1 x2 y2 [...] | SPLINE x1 y1 x2 y2 [...] | ELLIPSE cx cy majX majY [ratio]\n"
            "TEXT x y height text\n"
            "РЕДАКТИРОВАНИЕ: MOVE dx dy | COPY dx dy | STRETCH dx dy | ROTATE angle [cx cy] | SCALE factor [cx cy]\n"
            "ERASE (E) | MIRROR x1 y1 x2 y2 | OFFSET distance | ARRAY R rows cols | ARRAY P count angle [cx cy]\n"
            "TRIM x y | EXTEND x y | FILLET radius | CHAMFER d1 [d2] | BREAK x1 y1 x2 y2 | JOIN | EXPLODE\n"
            "DIMLINEAR x1 y1 x2 y2 [xm ym] | LINETYPE [Continuous|Dashed|Dotted|DashDot|DashDotDot]\n"
            "HATCH [color] — штриховка | BLOCK name — создать блок из выбора | INSERT name x y [scale] [angle]\n"
            "DISTANCE — расстояние между 2 точками/линиями | AREA — площадь круга/полигона\n"
            "Файл: NEW | OPEN | SAVE | SAVEAS\n"
            "GRID [шаг] | ZOOM_EXTENTS (ZE) | VIEW_ORIGIN (ZO) — к началу координат\n"
            "VIEW_TOP | VIEW_FRONT | VIEW_LEFT\n"
            "DIMRADIUS | DIMDIAMETER — размеры круга | MULTIPLE — повтор команды\n"
            "PEDIT W width | PEDIT J | LAYER NEW/SET/FREEZE/LOCK | XREF ATTACH path\n"
            "UNDO (U) | REDO (R)\n\n"
            "РОБОТ: LOAD_DEMO_ROBOT | LOAD_ROBOT <path> | TRAJECTORY <json>\n"
            "TRAC_FROM_POLYLINE — траектория | EDIT_TRAC — редактировать | EXPORT_TRAC [path]\n"
            "EXPORT_FANUC_TP | EXPORT_YASKAWA_INFORM | EXPORT_UR_SCRIPT\n"
            "SET_JOINT <name> <deg> | SIMULATE [steps] | CHECK_COLLISION | REACHABILITY x y z\n"
            "START_DISPENSING [flow] [radius] | STOP_DISPENSING | CALIBRATE_DISPENSER\n\n"
            "STATUS | HELP"
        )
        QMessageBox.information(self, "Справка", help_text)
