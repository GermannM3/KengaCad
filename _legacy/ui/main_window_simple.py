"""
Упрощённое главное окно KengaCAD (без pyqtribbon)
"""
import os
import sys
import json
from pathlib import Path
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QStatusBar, QListWidget, QListWidgetItem, QPushButton,
                             QLineEdit, QMenuBar, QMenu, QLabel, QFileDialog, QMessageBox, QAction, QSplitter, QComboBox, QToolBar)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QIcon, QKeySequence

from ui.command_line import CommandLine
from ui.drawing_area import DrawingArea
from ui.view3d_preview import View3DPreview
from ui.properties_panel import PropertiesPanel
from cad.import_export import CADImportExport


class KengaCADMainWindowSimple(QMainWindow):
    def __init__(self, app_thread=None):
        super().__init__()
        self.setWindowTitle("KengaCAD v2.0.0")
        self.setGeometry(100, 100, 1400, 900)

        self.app_thread = app_thread
        self.app = None
        self.cad_entities = {"lines": [], "circles": [], "points": [], "arcs": [], "polylines": [], "texts": []}
        self.layers = {"0": {"visible": True, "color": "#FFFFFF"}}
        self.active_layer = "0"
        self._last_trajectory_points = []

        self._setup_ui()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("KengaCAD готов к работе")

    def _setup_ui(self):
        # Меню
        self._create_menu()

        # Панель инструментов
        self._create_toolbar()

        # Центральная область
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Splitter: 2D слева, 3D превью справа
        self._splitter = QSplitter(Qt.Horizontal)
        self.drawing_area = DrawingArea()
        self.drawing_area.cursorMoved.connect(self._on_cursor_moved)
        self._splitter.addWidget(self.drawing_area)
        
        self._view3d = View3DPreview()
        self._view3d.setMinimumWidth(240)
        self._view3d.pointsChanged.connect(self._on_view3d_points_changed)
        self._splitter.addWidget(self._view3d)
        
        self._splitter.setSizes([720, 280])
        self.layout.addWidget(self._splitter)

        # Командная строка
        self.command_line = CommandLine()
        self.command_line.returnPressed.connect(self._execute_command)
        self.layout.addWidget(self.command_line)

        # Панель объектов
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

        # Панель свойств
        self._properties_panel = PropertiesPanel(self)
        self.properties_dock = QDockWidget("Свойства", self)
        self.properties_dock.setWidget(self._properties_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)

        # Панель робота
        robot_panel = QWidget()
        robot_layout = QVBoxLayout(robot_panel)
        robot_layout.addWidget(QLabel("Робот:"))
        self._robot_combo = QComboBox()
        self._robot_combo.addItems(["Демо-робот", "KUKA KR6", "ABB IRB120"])
        robot_layout.addWidget(self._robot_combo)
        
        btn_robot = QPushButton("Загрузить робота")
        btn_robot.clicked.connect(self._load_demo_robot)
        robot_layout.addWidget(btn_robot)
        
        btn_trac = QPushButton("Траектория из полилинии")
        btn_trac.clicked.connect(lambda: self._parse_command("TRAC_FROM_POLYLINE"))
        robot_layout.addWidget(btn_trac)
        
        btn_sim = QPushButton("Симуляция")
        btn_sim.clicked.connect(lambda: self._parse_command("SIMULATE"))
        robot_layout.addWidget(btn_sim)
        
        self.robot_dock = QDockWidget("3D / Робот", self)
        self.robot_dock.setWidget(robot_panel)
        self.addDockWidget(Qt.RightDockWidgetArea, self.robot_dock)

        self._update_drawing_area()

    def _create_menu(self):
        menubar = self.menuBar()

        # Файл
        file_menu = menubar.addMenu('Файл')
        file_menu.addAction('Новый', self._new_file).setShortcut(QKeySequence.New)
        file_menu.addAction('Открыть', self._open_file).setShortcut(QKeySequence.Open)
        file_menu.addAction('Сохранить', lambda: self._save_file(False)).setShortcut(QKeySequence.Save)
        file_menu.addAction('Сохранить как...', lambda: self._save_file(True))
        file_menu.addSeparator()
        file_menu.addAction('Выход', self.close)

        # Правка
        edit_menu = menubar.addMenu('Правка')
        edit_menu.addAction('Отменить', self._undo).setShortcut(QKeySequence.Undo)
        edit_menu.addAction('Повторить', self._redo).setShortcut(QKeySequence.Redo)

        # Вид
        view_menu = menubar.addMenu('Вид')
        view_menu.addAction('Показать всё', self._zoom_extents).setShortcut(QKeySequence("Ctrl+0"))
        view_menu.addAction('Вид сверху', lambda: self._parse_command("VIEW_TOP"))
        view_menu.addAction('Вид спереди', lambda: self._parse_command("VIEW_FRONT"))

        # Робот
        robot_menu = menubar.addMenu('Робот')
        robot_menu.addAction('Загрузить робота', self._load_demo_robot)
        robot_menu.addAction('Траектория из полилинии', lambda: self._parse_command("TRAC_FROM_POLYLINE"))
        robot_menu.addAction('Симуляция', lambda: self._parse_command("SIMULATE"))
        robot_menu.addSeparator()
        robot_menu.addAction('Экспорт G-код', lambda: self._parse_command("EXPORT_GCODE"))

        # Справка
        help_menu = menubar.addMenu('Справка')
        help_menu.addAction('О программе', self._show_about)
        help_menu.addAction('Команды', lambda: self._parse_command("HELP"))

    def _create_toolbar(self):
        toolbar = QToolBar("Инструменты")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        toolbar.addAction("Новый", self._new_file)
        toolbar.addAction("Открыть", self._open_file)
        toolbar.addAction("Сохранить", lambda: self._save_file(False))
        toolbar.addSeparator()
        toolbar.addAction("Линия", lambda: self._parse_command("LINE"))
        toolbar.addAction("Круг", lambda: self._parse_command("CIRCLE"))
        toolbar.addAction("Полилиния", lambda: self._parse_command("POLYLINE"))
        toolbar.addSeparator()
        toolbar.addAction("Переместить", lambda: self._parse_command("MOVE"))
        toolbar.addAction("Копировать", lambda: self._parse_command("COPY"))
        toolbar.addAction("Удалить", self._delete_last_entity)

    def on_app_initialized(self, success, app_thread):
        if success and app_thread:
            self.app = app_thread.get_app()
            self.statusBar().showMessage("KengaCAD готов к работе")

    def _execute_command(self):
        cmd = self.command_line.text()
        self._parse_command(cmd)
        self.command_line.clear()

    def _parse_command(self, cmd):
        parts = cmd.split()
        if not parts:
            return
        command = parts[0].upper()
        args = parts[1:]

        if command in ("HELP", "?"):
            self._show_help()
            return

        if command == "LINE":
            self.statusBar().showMessage("LINE: укажите две точки мышью или LINE x1 y1 x2 y2")
        elif command == "CIRCLE":
            self.statusBar().showMessage("CIRCLE: укажите центр и радиус или CIRCLE x y r")
        elif command == "POLYLINE":
            self.statusBar().showMessage("POLYLINE: укажите точки или POLYLINE x1 y1 x2 y2 ...")
        elif command == "TRAC_FROM_POLYLINE":
            self.statusBar().showMessage("Траектория создана из последней полилинии")
        elif command == "SIMULATE":
            self.statusBar().showMessage("Симуляция запущена")
        elif command == "EXPORT_GCODE":
            self.statusBar().showMessage("G-код экспортирован")
        elif command == "VIEW_TOP":
            self.statusBar().showMessage("Вид сверху")
        elif command == "VIEW_FRONT":
            self.statusBar().showMessage("Вид спереди")
        else:
            self.statusBar().showMessage(f"Команда: {command}")

    def _new_file(self):
        self.cad_entities = {"lines": [], "circles": [], "points": [], "arcs": [], "polylines": [], "texts": []}
        self._update_drawing_area()
        self.statusBar().showMessage("Новый файл создан")

    def _open_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Открыть файл", "", "DXF Files (*.dxf);;All Files (*)")
        if fname:
            self.statusBar().showMessage(f"Открыт: {fname}")

    def _save_file(self, force_dialog=False):
        self.statusBar().showMessage("Файл сохранён")

    def _undo(self):
        self._delete_last_entity()

    def _redo(self):
        self.statusBar().showMessage("Повтор")

    def _zoom_extents(self):
        self.drawing_area.zoom_extents()

    def _delete_last_entity(self):
        self.statusBar().showMessage("Удалён последний объект")

    def _load_demo_robot(self):
        self._parse_command("LOAD_DEMO_ROBOT")

    def _update_drawing_area(self):
        self.drawing_area.entities = self.cad_entities
        self.drawing_area.update()

    def _on_cursor_moved(self, x, y):
        self.statusBar().showMessage(f"X: {x:.2f}, Y: {y:.2f}")

    def _on_view3d_points_changed(self, pts):
        self._last_trajectory_points = pts

    def _show_help(self):
        QMessageBox.information(self, "Справка", 
            "KengaCAD v2.0.0\n\n"
            "Команды:\n"
            "  LINE - линия\n"
            "  CIRCLE - окружность\n"
            "  POLYLINE - полилиния\n"
            "  TRAC_FROM_POLYLINE - траектория из полилинии\n"
            "  SIMULATE - симуляция\n"
            "  EXPORT_GCODE - экспорт в G-код")

    def _show_about(self):
        QMessageBox.information(self, "О программе",
            "KengaCAD v2.0.0\n\n"
            "CAD/CAM система для роботов\n\n"
            "2026")


# Импортируем QDockWidget
from PyQt5.QtWidgets import QDockWidget
