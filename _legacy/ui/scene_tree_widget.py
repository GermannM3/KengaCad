"""
Дерево объектов 3D-сцены (Object tree) — как в RoboCAD/RobotExpert.
Отображает иерархию: робот, траектория, столы, оснастка, конвейеры, ограждения, STEP-объекты.
Поддержка: контекстное меню, иконки/цвета по типу, выделение, группировка.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QPushButton,
    QHBoxLayout, QMenu, QAction,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QIcon, QPixmap, QPainter


# ---------------------------------------------------------------------------
#  Цвета и метки по типу объекта
# ---------------------------------------------------------------------------

_TYPE_COLORS: dict = {
    "robot":     "#5599ff",   # blue
    "trajectory": "#66cc66",  # green
    "table":     "#999999",   # gray
    "fixture":   "#999999",   # gray
    "conveyor":  "#999999",   # gray
    "fence":     "#999999",   # gray
    "step_mesh": "#ff9933",   # orange
}

_TYPE_LABELS: dict = {
    "robot":     "Робот",
    "trajectory": "Траектория",
    "table":     "Стол",
    "fixture":   "Оснастка",
    "conveyor":  "Конвейер",
    "fence":     "Ограждение",
    "step_mesh": "STEP",
}


def _color_icon(hex_color: str, size: int = 16) -> QIcon:
    """Создать маленькую квадратную иконку заданного цвета."""
    pm = QPixmap(size, size)
    pm.fill(QColor(hex_color))
    painter = QPainter(pm)
    painter.setPen(QColor("#222222"))
    painter.drawRect(0, 0, size - 1, size - 1)
    painter.end()
    return QIcon(pm)


class SceneTreeWidget(QWidget):
    """Виджет дерева объектов сцены с контекстным меню и сигналами."""

    # --- Existing signals ---
    addTableRequested = pyqtSignal()
    addFixtureRequested = pyqtSignal()

    # --- New signals ---
    addConveyorRequested = pyqtSignal()
    addFenceRequested = pyqtSignal()
    addRobotRequested = pyqtSignal()

    # Context‑menu signals
    propertiesRequested = pyqtSignal(str)   # object id
    deleteRequested = pyqtSignal(str)       # object id
    visibilityToggled = pyqtSignal(str)     # object id
    duplicateRequested = pyqtSignal(str)    # object id

    # Selection signal
    objectSelected = pyqtSignal(str)        # object id

    def __init__(self, parent=None):
        super().__init__(parent)

        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Объект", "Тип"])
        self._tree.setColumnCount(2)
        self._tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.setStyleSheet("""
            QTreeWidget {
                background: #2b2b2b; color: #e0e0e0; border: 1px solid #444;
                font-size: 13px;
            }
            QTreeWidget::item:selected {
                background: #37474f;
            }
            QHeaderView::section {
                background: #3c3f41; color: #aaa; padding: 4px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._tree)

        # --- Кнопки ---
        btn_layout = QHBoxLayout()

        btn_table = QPushButton("Стол")
        btn_table.setToolTip("Добавить примитив стол (бокс) в 3D-сцену")
        btn_table.clicked.connect(self.addTableRequested.emit)

        btn_fixture = QPushButton("Оснастка")
        btn_fixture.setToolTip("Добавить примитив оснастки (бокс) в 3D-сцену")
        btn_fixture.clicked.connect(self.addFixtureRequested.emit)

        btn_conveyor = QPushButton("Конвейер")
        btn_conveyor.setToolTip("Добавить конвейер в 3D-сцену")
        btn_conveyor.clicked.connect(self.addConveyorRequested.emit)

        btn_fence = QPushButton("Ограждение")
        btn_fence.setToolTip("Добавить защитное ограждение в 3D-сцену")
        btn_fence.clicked.connect(self.addFenceRequested.emit)

        btn_robot = QPushButton("+ Робот")
        btn_robot.setToolTip("Добавить робота из библиотеки robots.json")
        btn_robot.clicked.connect(self.addRobotRequested.emit)

        for btn in (btn_table, btn_fixture, btn_conveyor, btn_fence, btn_robot):
            btn.setStyleSheet("""
                QPushButton {
                    background: #3c3f41; color: #ccc; border: 1px solid #555;
                    padding: 3px 6px; border-radius: 3px; font-size: 12px;
                }
                QPushButton:hover { background: #4a4e52; }
                QPushButton:pressed { background: #555; }
            """)

        btn_layout.addWidget(btn_table)
        btn_layout.addWidget(btn_fixture)
        btn_layout.addWidget(btn_conveyor)
        btn_layout.addWidget(btn_fence)
        btn_layout.addWidget(btn_robot)
        layout.addLayout(btn_layout)

        # Хранение текущих объектов для поиска по id
        self._objects: list = []
        # Множество скрытых объектов (для переключения метки)
        self._hidden_ids: set = set()

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def set_objects(self, objects: list) -> None:
        """
        objects: [{"id": str, "name": str, "type": str, "children": [...]}, ...]
        Опционально children — подэлементы (Links, Trajectory) для робота.
        """
        self._objects = list(objects)
        self._tree.clear()
        root = self._tree.invisibleRootItem()

        for obj in objects:
            oid = obj.get("id", "?")
            name = obj.get("name", oid)
            typ = obj.get("type", "")
            type_label = _TYPE_LABELS.get(typ, typ)
            color_hex = _TYPE_COLORS.get(typ, "#cccccc")

            item = QTreeWidgetItem([name, type_label])
            item.setData(0, Qt.UserRole, oid)
            item.setIcon(0, _color_icon(color_hex))
            item.setForeground(0, QBrush(QColor(color_hex)))
            item.setForeground(1, QBrush(QColor("#888888")))

            # Визуальная пометка скрытых
            if oid in self._hidden_ids:
                item.setForeground(0, QBrush(QColor("#555555")))
                item.setForeground(1, QBrush(QColor("#555555")))

            # Группировка: робот имеет подэлементы Links / Trajectory
            if typ == "robot":
                children = obj.get("children", [])
                if not children:
                    # Автоматические дочерние узлы
                    children = [
                        {"name": "Links", "type": "links"},
                        {"name": "Траектория", "type": "trajectory_sub"},
                    ]
                for ch in children:
                    ch_name = ch.get("name", "?")
                    ch_type = ch.get("type", "")
                    ch_item = QTreeWidgetItem([ch_name, ch_type])
                    ch_item.setData(0, Qt.UserRole, f"{oid}/{ch_type}")
                    ch_item.setForeground(0, QBrush(QColor("#aaaaaa")))
                    ch_item.setForeground(1, QBrush(QColor("#666666")))
                    item.addChild(ch_item)

            root.addChild(item)

        self._tree.expandAll()

    # ------------------------------------------------------------------
    #  Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos):
        item = self._tree.itemAt(pos)
        if item is None:
            return
        oid = item.data(0, Qt.UserRole)
        if not oid or "/" in str(oid):
            # Подэлемент — пока без меню
            return

        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #2d2d30; color: #e0e0e0; border: 1px solid #555;
            }
            QMenu::item:selected { background: #3e6b8a; }
        """)

        act_props = QAction("Свойства", self)
        act_props.triggered.connect(lambda: self.propertiesRequested.emit(str(oid)))

        is_hidden = str(oid) in self._hidden_ids
        label_vis = "Показать" if is_hidden else "Скрыть"
        act_vis = QAction(label_vis, self)
        act_vis.triggered.connect(lambda: self._toggle_visibility(str(oid)))

        act_dup = QAction("Дублировать", self)
        act_dup.triggered.connect(lambda: self.duplicateRequested.emit(str(oid)))

        act_del = QAction("Удалить", self)
        act_del.triggered.connect(lambda: self.deleteRequested.emit(str(oid)))

        menu.addAction(act_props)
        menu.addAction(act_vis)
        menu.addAction(act_dup)
        menu.addSeparator()
        menu.addAction(act_del)

        menu.exec_(self._tree.viewport().mapToGlobal(pos))

    def _toggle_visibility(self, oid: str):
        if oid in self._hidden_ids:
            self._hidden_ids.discard(oid)
        else:
            self._hidden_ids.add(oid)
        self.visibilityToggled.emit(oid)
        # Refresh tree to update colors
        self.set_objects(self._objects)

    # ------------------------------------------------------------------
    #  Selection
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item, column):
        oid = item.data(0, Qt.UserRole)
        if oid and "/" not in str(oid):
            self.objectSelected.emit(str(oid))
