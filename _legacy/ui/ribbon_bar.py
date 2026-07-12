"""
Ribbon бар для KengaCAD (аналог AutoCAD Ribbon)
"""
from pathlib import Path
from PyQt5.QtWidgets import QWidget, QFileDialog, QInputDialog, QToolButton
from pyqtribbon.ribbonbar import RibbonBar
from pyqtribbon.ribbonbar import RibbonMenu
from pyqtribbon.panel import RibbonPanel
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QPen, QPainterPath, QBrush, QFont
from PyQt5.QtCore import Qt, QPointF, QRectF, QTimer


class KengaCADRibbonBar(RibbonBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.setObjectName("KengaCADRibbonBar")
        self._apply_dark_theme()
        self._setup_file_menu()
        self._connect_help_button()
        
        # Создание вкладок
        self._create_home_tab()
        self._create_insert_tab()
        self._create_annotate_tab()
        self._create_view_tab()
        self._create_simulate_tab()
        self._create_robot_tab()
        
        # Создание Quick Access Toolbar
        self._create_quick_access_toolbar()
    
    
    def _apply_dark_theme(self):
        """Светлый текст для тёмной темы — читаемость верхнего меню."""
        dark = """
        RibbonBar, RibbonTitleWidget, RibbonStackedWidget {
            background-color: #3c3f41 !important;
            color: #e0e0e0 !important;
        }
        RibbonTabBar::tab {
            color: #e0e0e0 !important;
            background-color: transparent !important;
        }
        RibbonTabBar::tab:selected {
            color: #ffffff !important;
            border-bottom: 3px solid #4a9eff !important;
        }
        RibbonTabBar::tab:hover:!selected {
            color: #ffffff !important;
        }
        QToolBar, QToolButton {
            background-color: transparent !important;
            color: #e0e0e0 !important;
        }
        QToolButton:hover {
            color: #ffffff !important;
            background-color: #505354 !important;
        }
        RibbonCategory, RibbonPanel, RibbonPanelTitle {
            background-color: #3c3f41 !important;
            color: #e0e0e0 !important;
        }
        RibbonPanelTitle {
            color: #d0d0d0 !important;
        }
        RibbonToolButton, RibbonGalleryButton, RibbonToolButton QLabel, RibbonGalleryButton QLabel {
            background-color: transparent !important;
            color: #e0e0e0 !important;
        }
        RibbonToolButton:hover, RibbonGalleryButton:hover {
            background-color: #505354 !important;
            color: #ffffff !important;
        }
        QMenu, RibbonPopupWidget {
            background-color: #3c3f41 !important;
            color: #e0e0e0 !important;
        }
        QMenu::item:selected {
            background-color: #505354 !important;
            color: #ffffff !important;
        }
        QLabel {
            color: #e0e0e0 !important;
        }
        """
        self.setStyleSheet(self.styleSheet() + dark)
        self._fix_tabbar_readability()

    def _fix_tabbar_readability(self):
        """TabBar.changeColor перезаписывает стили — возвращаем светлый текст для вкладок."""
        def reapply():
            tb = self.tabBar()
            if tb:
                tb.setStyleSheet("""
                RibbonTabBar::tab { color: #e0e0e0 !important; }
                RibbonTabBar::tab:selected { color: #ffffff !important; border-bottom: 3px solid #4a9eff !important; }
                RibbonTabBar::tab:hover:!selected { color: #ffffff !important; }
                """)
        self.tabBar().currentChanged.connect(lambda _: QTimer.singleShot(0, reapply))
        QTimer.singleShot(50, reapply)

    def _connect_help_button(self):
        """Кнопка «?» справа — открывает справку."""
        self.helpButtonClicked.connect(self._on_help_clicked)
        self.helpRibbonButton().setToolTip("Быстрый старт — как работать")

    def _on_help_clicked(self, _checked=False):
        if self.main_window and hasattr(self.main_window, "_show_quick_start"):
            self.main_window._show_quick_start()

    def _on_new_file(self):
        if self.main_window:
            self.main_window._new_file()

    def _setup_file_menu(self):
        """Меню Файл для кнопки приложения (иконка слева)."""
        file_menu = self.addFileMenu()
        file_menu.addAction("Новый", lambda: self.main_window._new_file() if self.main_window else None)
        file_menu.addAction("Открыть", lambda: self.main_window._open_file() if self.main_window else None)
        file_menu.addAction("Сохранить", lambda: self.main_window._save_file() if self.main_window else None)
        file_menu.addSeparator()
        file_menu.addAction("Выход", lambda: self.main_window.close() if self.main_window else None)
        btn = self.applicationOptionButton()
        btn.setText("KengaCAD")
        btn.setToolTip("Меню KengaCAD")
        base = Path(__file__).resolve().parent.parent
        for name in ("logo.png", "logo.ico"):
            if (base / "assets" / name).exists():
                btn.setIcon(QIcon(str(base / "assets" / name)))
                break

    def _send_command(self, cmd: str):
        if not self.main_window:
            return

        if cmd == "LOAD_ROBOT":
            fname, _ = QFileDialog.getOpenFileName(self, "Загрузить модель робота", "",
                "3D модели (*.gltf *.glb *.obj *.ipt *.iam);;glTF (*.gltf *.glb);;Inventor (*.ipt *.iam);;OBJ (*.obj);;All (*)")
            if fname:
                self.main_window._parse_command(f"LOAD_ROBOT {fname}")
            return

        if cmd == "LOAD_DEMO_ROBOT":
            self.main_window._parse_command("LOAD_DEMO_ROBOT")
            return

        if cmd == "TRAJECTORY":
            fname, _ = QFileDialog.getOpenFileName(self, "Load trajectory", "",
                                                  "JSON files (*.json);;All files (*)")
            if fname:
                self.main_window._parse_command(f"TRAJECTORY {fname}")
            return

        if cmd == "POINT":
            self.main_window._parse_command("POINT")
            return

        if cmd == "LINE":
            self.main_window._parse_command("LINE")
            return

        if cmd == "CIRCLE":
            self.main_window._parse_command("CIRCLE")
            return

        if cmd == "ARC":
            self.main_window._parse_command("ARC")
            return

        if cmd == "POLYLINE":
            text, ok = QInputDialog.getText(self, "Polyline", "Enter x1 y1 x2 y2 [x3 y3 ...]:")
            if ok and text.strip():
                self.main_window._parse_command(f"POLYLINE {text}")
            return

        if cmd == "TEXT":
            text, ok = QInputDialog.getText(self, "Текст", "Введите x y [z] высота текст:")
            if ok and text.strip():
                self.main_window._parse_command(f"TEXT {text}")
            return

        if cmd == "SET_JOINT":
            joint, ok1 = QInputDialog.getText(self, "Сустав", "Имя сустава (например Joint1):")
            if ok1 and joint.strip():
                angle, ok2 = QInputDialog.getText(self, "Угол", "Угол в градусах:")
                if ok2 and angle.strip():
                    self.main_window._parse_command(f"SET_JOINT {joint} {angle}")
            return

        if cmd == "START_DISPENSING":
            flow, ok = QInputDialog.getText(self, "Диспенсинг", "Расход (мл/мин):", text="1.0")
            if ok:
                flow = flow.strip() or "1.0"
                radius, ok2 = QInputDialog.getText(self, "Диспенсинг", "Радиус (м):", text="0.02")
                radius = (radius.strip() or "0.02") if ok2 else "0.02"
                self.main_window._parse_command(f"START_DISPENSING {flow} {radius}")
            return

        if cmd == "CALIBRATE_DISPENSER":
            self.main_window._parse_command("CALIBRATE_DISPENSER")
            return

        if cmd == "MOVE":
            text, ok = QInputDialog.getText(self, "Перемещение", "Смещение dx dy [dz] (последний объект):", text="0 0")
            if ok and text.strip():
                self.main_window._parse_command(f"MOVE {text}")
            return

        if cmd == "COPY":
            text, ok = QInputDialog.getText(self, "Копирование", "Смещение dx dy [dz] для копии:", text="10 10")
            if ok and text.strip():
                self.main_window._parse_command(f"COPY {text}")
            return

        if cmd == "ROTATE":
            text, ok = QInputDialog.getText(self, "Поворот", "Угол [cx cy] в градусах (последний объект):", text="90")
            if ok and text.strip():
                self.main_window._parse_command(f"ROTATE {text}")
            return

        if cmd == "SCALE":
            text, ok = QInputDialog.getText(self, "Масштаб", "Множитель [cx cy]:", text="2")
            if ok and text.strip():
                self.main_window._parse_command(f"SCALE {text}")
            return

        if cmd in ("VIEW_TOP", "VIEW_FRONT", "VIEW_LEFT"):
            self.main_window._parse_command(cmd)
            return

        self.main_window._parse_command(cmd)

    def _set_mode_state(self, mode: str, state: bool):
        if mode == "ortho":
            self.main_window.ortho_mode = state
            self.main_window.statusBar().showMessage(f"Ortho: {'ON' if state else 'OFF'}")
        elif mode == "polar":
            self.main_window.polar_mode = state
            self.main_window.statusBar().showMessage(f"Polar: {'ON' if state else 'OFF'}")

    def _create_quick_access_toolbar(self):
        """Создание Quick Access Toolbar. Первая кнопка — лого (меню Файл), вторая — «Новый» (документ)."""
        qat = self.quickAccessToolBar()
        new_icon = self._create_cad_icon("document", "#00E676")
        new_btn = QToolButton()
        new_btn.setIcon(new_icon)
        new_btn.setToolTip("Новый (Ctrl+N)")
        new_btn.setAutoRaise(True)
        new_btn.clicked.connect(self._on_new_file)
        qat.addWidget(new_btn)
        open_icon = self._create_cad_icon("folder", "#42A5F5")
        open_btn = qat.addAction(open_icon, "Открыть")
        open_btn.triggered.connect(lambda: self.main_window._open_file() if self.main_window else None)
        save_icon = self._create_cad_icon("document", "#42A5F5")
        save_btn = qat.addAction(save_icon, "Сохранить")
        save_btn.triggered.connect(lambda: self.main_window._save_file() if self.main_window else None)
        undo_icon = self._create_cad_icon("undo", "#FFB74D")
        undo_btn = qat.addAction(undo_icon, "Отменить")
        undo_btn.triggered.connect(lambda: self.main_window._undo() if self.main_window else None)
        redo_icon = self._create_cad_icon("redo", "#FFB74D")
        redo_btn = qat.addAction(redo_icon, "Повторить")
        redo_btn.triggered.connect(lambda: self.main_window._redo() if self.main_window else None)
    
    def _create_home_tab(self):
        """Создание вкладки Home"""
        home_tab = self.addCategory("Главная")

        # Панель Рисование
        draw_panel = home_tab.addPanel("Рисование")
        self._add_draw_buttons(draw_panel)

        # Панель Редактирование
        modify_panel = home_tab.addPanel("Редактирование")
        self._add_modify_buttons(modify_panel)

        # Панель Слои
        layers_panel = home_tab.addPanel("Слои")
        self._add_layers_buttons(layers_panel)

        # Панель Свойства
        properties_panel = home_tab.addPanel("Свойства")
        self._add_properties_buttons(properties_panel)
    
    def _add_draw_buttons(self, panel):
        """Добавление кнопок рисования"""
        # Кнопка создания траектории
        new_traj_btn = panel.addLargeButton("Новая траектория", icon=self._create_cad_icon("trajectory", "#4CAF50"))
        new_traj_btn.setToolTip("Загрузить траекторию из JSON")
        new_traj_btn.clicked.connect(lambda: self._send_command("TRAJECTORY"))
        
        # Кнопка точки
        point_btn = panel.addSmallButton("Точка", icon=self._create_cad_icon("point", "#2196F3"))
        point_btn.setToolTip("Создать точку")
        point_btn.clicked.connect(lambda: self._send_command("POINT"))
        
        # Кнопка линии
        line_btn = panel.addSmallButton("Линия", icon=self._create_cad_icon("line", "#2196F3"))
        line_btn.setToolTip("Линия (L) — укажите точки мышью или LINE x1 y1 x2 y2")
        line_btn.clicked.connect(lambda: self._send_command("LINE"))
        
        # Кнопка окружности
        circle_btn = panel.addSmallButton("Окружность", icon=self._create_cad_icon("circle", "#2196F3"))
        circle_btn.setToolTip("Окружность (C) — центр и радиус мышью или CIRCLE x y r")
        circle_btn.clicked.connect(lambda: self._send_command("CIRCLE"))
        
        # Кнопка дуги
        arc_btn = panel.addSmallButton("Дуга", icon=self._create_cad_icon("arc", "#2196F3"))
        arc_btn.setToolTip("Дуга (A) — центр, начало, конец мышью или ARC x y r start end")
        arc_btn.clicked.connect(lambda: self._send_command("ARC"))

        # Кнопка прямоугольника
        rect_btn = panel.addSmallButton("Прямоугольник", icon=self._create_cad_icon("rectangle", "#2196F3"))
        rect_btn.setToolTip("Прямоугольник — укажите два угла мышью или RECTANGLE x1 y1 x2 y2")
        rect_btn.clicked.connect(lambda: self._send_command("RECTANGLE"))

        # Кнопка полилинии
        pline_btn = panel.addSmallButton("Полилиния", icon=self._create_cad_icon("polyline", "#2196F3"))
        pline_btn.setToolTip("Полилиния (PL) — POLYLINE x1 y1 x2 y2 ... Enter для замыкания")
        pline_btn.clicked.connect(lambda: self._send_command("POLYLINE"))

        trac_poly_btn = panel.addSmallButton("Траектория из пути", icon=self._create_cad_icon("trajectory", "#4CAF50"))
        trac_poly_btn.setToolTip("Создать траекторию робота из последней полилинии")
        trac_poly_btn.clicked.connect(lambda: self._send_command("TRAC_FROM_POLYLINE"))

        # Кнопка текста
        text_btn = panel.addSmallButton("Текст", icon=self._create_cad_icon("text", "#FFEB3B"))
        text_btn.setToolTip("Добавить текст")
        text_btn.clicked.connect(lambda: self._send_command("TEXT"))

    def _add_modify_buttons(self, panel):
        """Добавление кнопок редактирования"""
        move_btn = panel.addLargeButton("Переместить", icon=self._create_cad_icon("move", "#FF9800"))
        move_btn.setToolTip("Переместить объекты (MOVE)")
        move_btn.clicked.connect(lambda: self._send_command("MOVE"))

        copy_btn = panel.addSmallButton("Копировать", icon=self._create_cad_icon("copy", "#FF9800"))
        copy_btn.setToolTip("Копировать объекты")
        copy_btn.clicked.connect(lambda: self._send_command("COPY"))

        rotate_btn = panel.addSmallButton("Повернуть", icon=self._create_cad_icon("rotate", "#FF9800"))
        rotate_btn.setToolTip("Повернуть объекты")
        rotate_btn.clicked.connect(lambda: self._send_command("ROTATE"))

        scale_btn = panel.addSmallButton("Масштаб", icon=self._create_cad_icon("scale", "#FF9800"))
        scale_btn.setToolTip("Масштабировать объекты")
        scale_btn.clicked.connect(lambda: self._send_command("SCALE"))

        delete_btn = panel.addSmallButton("Удалить", icon=self._create_cad_icon("delete", "#F44336"))
        delete_btn.setToolTip("Удалить последний объект (UNDO)")
        delete_btn.clicked.connect(lambda: self.main_window._delete_last_entity() if self.main_window else None)
    
    def _add_layers_buttons(self, panel):
        """Добавление кнопок слоев"""
        layer_props_btn = panel.addLargeButton("Свойства слоев", icon=self._create_cad_icon("document", "#9E9E9E"))
        layer_props_btn.setToolTip("Открыть панель слоёв")
        layer_props_btn.clicked.connect(lambda: self.main_window._show_layers_dock() if self.main_window else None)

        layer_prev_btn = panel.addSmallButton("Предыдущий", icon=self._create_cad_icon("view_top", "#9E9E9E"))
        layer_prev_btn.setToolTip("Выбрать предыдущий слой")
        layer_prev_btn.clicked.connect(lambda: self.main_window._prev_layer() if self.main_window else None)

        layer_next_btn = panel.addSmallButton("Следующий", icon=self._create_cad_icon("view_top", "#9E9E9E"))
        layer_next_btn.setToolTip("Выбрать следующий слой")
        layer_next_btn.clicked.connect(lambda: self.main_window._next_layer() if self.main_window else None)
    
    def _add_properties_buttons(self, panel):
        """Добавление кнопок свойств"""
        props_btn = panel.addLargeButton("Свойства", icon=self._create_cad_icon("document", "#795548"))
        props_btn.setToolTip("Открыть панель объектов")
        props_btn.clicked.connect(lambda: self._focus_objects_dock() if self.main_window else None)

        match_btn = panel.addSmallButton("Сопоставить", icon=self._create_cad_icon("copy", "#795548"))
        match_btn.setToolTip("Сопоставить свойства (в разработке)")
        match_btn.clicked.connect(lambda: self._send_command("STATUS"))

        quick_select_btn = panel.addSmallButton("Объекты", icon=self._create_cad_icon("document", "#795548"))
        quick_select_btn.setToolTip("Панель объектов")
        quick_select_btn.clicked.connect(lambda: self._focus_objects_dock() if self.main_window else None)

    def _focus_objects_dock(self):
        if self.main_window and hasattr(self.main_window, "objects_dock"):
            self.main_window.objects_dock.raise_()
            self.main_window.objects_dock.show()
    
    def _create_insert_tab(self):
        """Создание вкладки Вставка"""
        insert_tab = self.addCategory("Вставка")

        # Панель Блоки
        blocks_panel = insert_tab.addPanel("Блоки")
        insert_block_btn = blocks_panel.addLargeButton("Импорт DXF", icon=self._create_cad_icon("folder", "#4CAF50"))
        insert_block_btn.setToolTip("Импортировать чертёж DXF")
        insert_block_btn.clicked.connect(lambda: self.main_window._open_file() if self.main_window else None)

        # Панель Компоненты
        components_panel = insert_tab.addPanel("Компоненты")
        insert_robot_btn = components_panel.addLargeButton("Робот", icon=self._create_cad_icon("robot", "#2196F3"))
        insert_robot_btn.setToolTip("Загрузить свою модель робота (glTF/GLB/OBJ)")
        insert_robot_btn.clicked.connect(lambda: self._send_command("LOAD_ROBOT"))

        demo_robot_btn = components_panel.addSmallButton("Демо-модель", icon=self._create_cad_icon("robot", "#4CAF50"))
        demo_robot_btn.setToolTip("Загрузить встроенную демо-модель робота")
        demo_robot_btn.clicked.connect(lambda: self._send_command("LOAD_DEMO_ROBOT"))

        insert_part_btn = components_panel.addSmallButton("Деталь", icon=self._create_cad_icon("robot", "#2196F3"))
        insert_part_btn.setToolTip("Вставить деталь (glTF/GLB)")
        insert_part_btn.clicked.connect(lambda: self._send_command("LOAD_ROBOT"))

        insert_assembly_btn = components_panel.addSmallButton("Сборка", icon=self._create_cad_icon("robot", "#2196F3"))
        insert_assembly_btn.setToolTip("Вставить сборку (в разработке)")
        insert_assembly_btn.clicked.connect(lambda: self._send_command("LOAD_ROBOT"))
    
    def _create_annotate_tab(self):
        """Создание вкладки Аннотации"""
        annotate_tab = self.addCategory("Аннотации")

        text_panel = annotate_tab.addPanel("Текст")
        text_btn = text_panel.addLargeButton("Текст", icon=self._create_cad_icon("text", "#FFEB3B"))
        text_btn.setToolTip("Добавить текст")
        text_btn.clicked.connect(lambda: self._send_command("TEXT"))

        dim_panel = annotate_tab.addPanel("Размеры")
        dim_btn = dim_panel.addLargeButton("Размер", icon=self._create_cad_icon("scale", "#FF9800"))
        dim_btn.setToolTip("Добавить размер (в разработке)")
        dim_btn.clicked.connect(lambda: self.main_window.statusBar().showMessage("Размеры — в разработке") if self.main_window else None)
    
    def _create_view_tab(self):
        """Создание вкладки Вид"""
        view_tab = self.addCategory("Вид")

        nav_panel = view_tab.addPanel("Навигация")
        zoom_extents_btn = nav_panel.addLargeButton("Показать все", icon=self._create_cad_icon("zoom_extents", "#9C27B0"))
        zoom_extents_btn.setToolTip("Показать все объекты (ZE, Ctrl+0)")
        zoom_extents_btn.clicked.connect(lambda: self._send_command("ZOOM_EXTENTS"))

        origin_btn = nav_panel.addSmallButton("К началу координат", icon=self._create_cad_icon("view_top", "#9C27B0"))
        origin_btn.setToolTip("Вернуть вид к началу координат (0,0)")
        origin_btn.clicked.connect(lambda: self._send_command("VIEW_ORIGIN"))

        zoom_sel_btn = nav_panel.addSmallButton("К выделению", icon=self._create_cad_icon("zoom_extents", "#9C27B0"))
        zoom_sel_btn.setToolTip("Масштабировать вид к выделенным объектам")
        zoom_sel_btn.clicked.connect(lambda: self.main_window._zoom_to_selection() if self.main_window else None)

        zoom_in_btn = nav_panel.addSmallButton("Увеличить", icon=self._create_cad_icon("zoom_in", "#9C27B0"))
        zoom_in_btn.setToolTip("Увеличить масштаб")
        zoom_in_btn.clicked.connect(lambda: self.main_window._zoom_in() if self.main_window else None)

        zoom_out_btn = nav_panel.addSmallButton("Уменьшить", icon=self._create_cad_icon("zoom_out", "#9C27B0"))
        zoom_out_btn.setToolTip("Уменьшить масштаб")
        zoom_out_btn.clicked.connect(lambda: self.main_window._zoom_out() if self.main_window else None)

        pan_btn = nav_panel.addSmallButton("Сдвинуть", icon=self._create_cad_icon("move", "#9C27B0"))
        pan_btn.setToolTip("Сдвинуть вид (средняя кнопка мыши)")
        pan_btn.clicked.connect(lambda: self.main_window.statusBar().showMessage("Сдвиг: удерживайте среднюю кнопку мыши") if self.main_window else None)

        views_panel = view_tab.addPanel("Виды")
        top_view_btn = views_panel.addLargeButton("Сверху", icon=self._create_cad_icon("view_top", "#607D8B"))
        top_view_btn.setToolTip("Вид сверху (2D)")
        top_view_btn.clicked.connect(lambda: self._send_command("VIEW_TOP"))

        front_view_btn = views_panel.addSmallButton("Спереди", icon=self._create_cad_icon("view_top", "#607D8B"))
        front_view_btn.setToolTip("Вид спереди")
        front_view_btn.clicked.connect(lambda: self._send_command("VIEW_FRONT"))

        side_view_btn = views_panel.addSmallButton("Сбоку", icon=self._create_cad_icon("view_top", "#607D8B"))
        side_view_btn.setToolTip("Вид сбоку")
        side_view_btn.clicked.connect(lambda: self._send_command("VIEW_LEFT"))

        # 3D режимы
        panel_3d = view_tab.addPanel("3D режим")
        full3d_btn = panel_3d.addLargeButton("Full 3D", icon=self._create_cad_icon("robot", "#4CAF50"))
        full3d_btn.setToolTip("Полноценное 3D (PyVista) — VIEW3D_FULL")
        full3d_btn.clicked.connect(lambda: self._send_command("VIEW3D_FULL"))

        preview3d_btn = panel_3d.addSmallButton("Превью", icon=self._create_cad_icon("robot", "#2196F3"))
        preview3d_btn.setToolTip("3D превью (изометрия) — VIEW3D_PREVIEW")
        preview3d_btn.clicked.connect(lambda: self._send_command("VIEW3D_PREVIEW"))

        load3d_btn = panel_3d.addSmallButton("Загрузить", icon=self._create_cad_icon("folder", "#4CAF50"))
        load3d_btn.setToolTip("Загрузить 3D модель — LOAD_MODEL_3D")
        load3d_btn.clicked.connect(lambda: self._send_command("LOAD_MODEL_3D"))
    
    def _create_simulate_tab(self):
        """Создание вкладки Симуляция"""
        simulate_tab = self.addCategory("Симуляция")

        # Панель Управление
        control_panel = simulate_tab.addPanel("Управление")
        start_sim_btn = control_panel.addLargeButton("Старт", icon=self._create_cad_icon("play", "#4CAF50"))
        start_sim_btn.setToolTip("Запустить симуляцию")
        start_sim_btn.clicked.connect(lambda: self._send_command("SIMULATE"))

        pause_sim_btn = control_panel.addSmallButton("Пауза", icon=self._create_cad_icon("stop", "#FF9800"))
        pause_sim_btn.setToolTip("Приостановить / продолжить симуляцию")
        pause_sim_btn.clicked.connect(lambda: self._send_command("SIM_PAUSE"))

        stop_sim_btn = control_panel.addSmallButton("Стоп", icon=self._create_cad_icon("delete", "#F44336"))
        stop_sim_btn.setToolTip("Остановить симуляцию")
        stop_sim_btn.clicked.connect(lambda: self._send_command("SIM_STOP"))

        reset_sim_btn = control_panel.addSmallButton("Сброс", icon=self._create_cad_icon("rotate", "#2196F3"))
        reset_sim_btn.setToolTip("Сбросить позу робота в нулевое положение")
        reset_sim_btn.clicked.connect(lambda: self._send_command("SIM_RESET"))

        settings_panel = simulate_tab.addPanel("Настройки")
        sim_settings_btn = settings_panel.addLargeButton("Параметры", icon=self._create_cad_icon("document", "#9E9E9E"))
        sim_settings_btn.setToolTip("Настройки симуляции")
        sim_settings_btn.clicked.connect(lambda: self.main_window.statusBar().showMessage("Параметры: SIMULATE [шагов]") if self.main_window else None)
    
    def _create_robot_tab(self):
        """Создание вкладки Робот"""
        robot_tab = self.addCategory("Робот")

        robot_control_panel = robot_tab.addPanel("Управление")
        load_robot_btn = robot_control_panel.addLargeButton("Загрузить", icon=self._create_cad_icon("robot", "#2196F3"))
        load_robot_btn.setToolTip("Загрузить модель робота (glTF/GLB)")
        load_robot_btn.clicked.connect(lambda: self._send_command("LOAD_ROBOT"))

        set_joints_btn = robot_control_panel.addSmallButton("Суставы", icon=self._create_cad_icon("rotate", "#2196F3"))
        set_joints_btn.setToolTip("Установить углы суставов")
        set_joints_btn.clicked.connect(lambda: self._send_command("SET_JOINT"))

        teach_btn = robot_control_panel.addSmallButton("Обучение", icon=self._create_cad_icon("trajectory", "#2196F3"))
        teach_btn.setToolTip("Режим обучения (в разработке)")
        teach_btn.clicked.connect(lambda: self.main_window.statusBar().showMessage("Обучение — в разработке") if self.main_window else None)

        dispensing_panel = robot_tab.addPanel("Диспенсинг")
        start_dispense_btn = dispensing_panel.addLargeButton("Старт", icon=self._create_cad_icon("play", "#FF9800"))
        start_dispense_btn.setToolTip("Начать нанесение мастики")
        start_dispense_btn.clicked.connect(lambda: self._send_command("START_DISPENSING"))

        stop_dispense_btn = dispensing_panel.addSmallButton("Стоп", icon=self._create_cad_icon("stop", "#F44336"))
        stop_dispense_btn.setToolTip("Остановить нанесение мастики")
        stop_dispense_btn.clicked.connect(lambda: self._send_command("STOP_DISPENSING"))

        calibrate_dispense_btn = dispensing_panel.addSmallButton("Калибровка", icon=self._create_cad_icon("scale", "#FF9800"))
        calibrate_dispense_btn.setToolTip("Калибровка диспенсера")
        calibrate_dispense_btn.clicked.connect(lambda: self._send_command("CALIBRATE_DISPENSER"))
    
    def _create_icon(self, color_str, shape="rect"):
        """Создание иконки в стиле AutoCAD — символы инструментов"""
        return self._create_cad_icon(shape, color_str)

    def _create_cad_icon(self, symbol, color_str="#B0B0B0"):
        """Иконки в стиле AutoCAD: линии, дуги, стрелки — без абстрактных квадратов"""
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        pen = QPen(QColor(color_str), 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        def draw_line(x1, y1, x2, y2):
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

        def draw_arc(cx, cy, r, start_deg, span_deg):
            path = QPainterPath()
            r = float(r)
            from math import pi, cos, sin
            start_rad = start_deg * pi / 180
            span_rad = span_deg * pi / 180
            path.moveTo(cx + r * cos(start_rad), cy - r * sin(start_rad))
            path.arcTo(QRectF(cx - r, cy - r, 2 * r, 2 * r), start_deg, span_deg)
            painter.drawPath(path)

        if symbol == "line":
            draw_line(6, 26, 26, 6)
        elif symbol == "circle":
            painter.drawEllipse(6, 6, 20, 20)
        elif symbol == "arc":
            draw_arc(10, 22, 12, 180, 90)
        elif symbol == "polyline":
            draw_line(6, 24, 12, 10)
            draw_line(12, 10, 18, 20)
            draw_line(18, 20, 26, 8)
        elif symbol == "rectangle":
            painter.drawRect(8, 8, 16, 16)
        elif symbol == "point":
            painter.setBrush(QColor(color_str))
            painter.drawEllipse(12, 12, 8, 8)
        elif symbol == "text":
            painter.setFont(QFont("Arial", 14, QFont.Bold))
            painter.drawText(QRectF(4, 4, 24, 24), Qt.AlignCenter, "A")
        elif symbol == "move":
            cx, cy = 16, 16
            for dx, dy in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
                ex, ey = cx + dx * 8, cy + dy * 8
                draw_line(cx, cy, ex, ey)
                if dy < 0:
                    draw_line(ex - 3, ey + 3, ex, ey)
                    draw_line(ex + 3, ey + 3, ex, ey)
                elif dy > 0:
                    draw_line(ex - 3, ey - 3, ex, ey)
                    draw_line(ex + 3, ey - 3, ex, ey)
                elif dx < 0:
                    draw_line(ex + 3, ey - 3, ex, ey)
                    draw_line(ex + 3, ey + 3, ex, ey)
                else:
                    draw_line(ex - 3, ey - 3, ex, ey)
                    draw_line(ex - 3, ey + 3, ex, ey)
        elif symbol == "copy":
            painter.drawRect(8, 10, 12, 14)
            painter.drawRect(12, 6, 12, 14)
        elif symbol == "rotate":
            draw_arc(16, 16, 10, 45, 270)
            draw_line(22, 8, 26, 6)
            draw_line(24, 10, 26, 6)
        elif symbol == "scale":
            draw_line(8, 24, 24, 8)
            draw_line(20, 8, 24, 8)
            draw_line(24, 12, 24, 8)
            draw_line(8, 24, 8, 20)
            draw_line(8, 24, 12, 24)
        elif symbol == "delete":
            draw_line(8, 8, 24, 24)
            draw_line(24, 8, 8, 24)
        elif symbol == "undo":
            draw_arc(16, 16, 10, 45, 225)
            draw_line(8, 12, 6, 10)
            draw_line(6, 14, 6, 10)
        elif symbol == "redo":
            draw_arc(16, 16, 10, 180, 225)
            draw_line(24, 12, 26, 10)
            draw_line(26, 14, 26, 10)
        elif symbol == "trajectory":
            draw_arc(8, 20, 8, 90, 180)
            draw_line(8, 12, 16, 12)
            draw_arc(16, 12, 6, 270, 180)
        elif symbol == "zoom_extents":
            painter.drawRect(8, 10, 12, 12)
            painter.drawLine(18, 8, 26, 16)
            painter.drawLine(26, 14, 26, 16)
            painter.drawLine(24, 16, 26, 16)
        elif symbol == "zoom_in":
            painter.drawRect(10, 10, 12, 12)
            painter.drawLine(16, 6, 16, 10)
            painter.drawLine(14, 8, 18, 8)
            painter.drawLine(16, 16, 16, 20)
            painter.drawLine(14, 18, 18, 18)
        elif symbol == "zoom_out":
            painter.drawRect(10, 10, 12, 12)
            painter.drawLine(14, 16, 18, 16)
        elif symbol == "view_top":
            painter.drawRect(10, 14, 12, 10)
            draw_line(16, 14, 20, 8)
            draw_line(20, 8, 24, 14)
            draw_line(24, 14, 16, 14)
        elif symbol == "document":
            painter.drawRect(8, 6, 14, 18)
            draw_line(10, 10, 18, 10)
            draw_line(10, 14, 16, 14)
        elif symbol == "folder":
            painter.drawRect(8, 12, 16, 12)
            painter.drawLine(8, 12, 12, 8)
            painter.drawLine(12, 8, 20, 8)
        elif symbol == "robot":
            painter.drawRect(10, 18, 4, 6)
            painter.drawRect(18, 18, 4, 6)
            painter.drawRect(14, 10, 4, 10)
            draw_line(16, 10, 16, 6)
        elif symbol == "play":
            painter.drawRect(8, 8, 16, 16)
            painter.setBrush(QColor(color_str))
            path = QPainterPath()
            path.moveTo(12, 10)
            path.lineTo(12, 22)
            path.lineTo(22, 16)
            path.closeSubpath()
            painter.drawPath(path)
        elif symbol == "stop":
            painter.drawRect(10, 10, 12, 12)
        else:
            painter.setBrush(QColor(color_str))
            painter.drawRoundedRect(6, 6, 20, 20, 3, 3)

        painter.end()
        return QIcon(pixmap)
