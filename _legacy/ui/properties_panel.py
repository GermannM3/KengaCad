"""
Панель свойств выбранного объекта — как в AutoCAD / RoboCAD.
Показывает геометрию: длина, площадь, координаты вершин и т.д.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel
from PyQt5.QtCore import Qt
import math


def _format_pt(pt) -> str:
    if not pt:
        return "—"
    x = float(pt[0]) if len(pt) > 0 else 0
    y = float(pt[1]) if len(pt) > 1 else 0
    z = float(pt[2]) if len(pt) > 2 else 0
    return f"{x:.4f}, {y:.4f}, {z:.4f}"


def _polyline_length(pts) -> float:
    if not pts or len(pts) < 2:
        return 0.0
    total = 0.0
    for i in range(len(pts) - 1):
        p1, p2 = pts[i], pts[i + 1]
        x1, y1 = float(p1[0]), float(p1[1])
        x2, y2 = float(p2[0]), float(p2[1])
        total += math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return total


def _polyline_area(pts) -> float:
    """Площадь замкнутой полилинии."""
    if not pts or len(pts) < 3:
        return 0.0
    n = len(pts)
    a = 0.0
    for i in range(n):
        j = (i + 1) % n
        xi, yi = float(pts[i][0]), float(pts[i][1])
        xj, yj = float(pts[j][0]), float(pts[j][1])
        a += xi * yj - xj * yi
    return abs(a) / 2.0


def _line_length(ent) -> float:
    s = ent.get("start", (0, 0, 0))
    e = ent.get("end", (0, 0, 0))
    return math.sqrt(
        (float(e[0]) - float(s[0])) ** 2 +
        (float(e[1]) - float(s[1])) ** 2
    )


class PropertiesPanel(QWidget):
    """Док-виджет с таблицей свойств выбранного объекта."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Свойство", "Значение"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet("""
            QTableWidget { background: #2b2b2b; color: #e0e0e0; gridline-color: #404040; }
            QHeaderView::section { background: #3c3f41; color: #aaa; padding: 4px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        self._empty_label = QLabel("Выберите объект")
        self._empty_label.setStyleSheet("color: #666; padding: 8px;")
        layout.addWidget(self._empty_label)
        layout.addWidget(self._table)
        self._table.setVisible(False)

    def set_entities(self, entities: list[tuple[str, dict]]) -> None:
        """Заполнить панель из списка (key, entity)."""
        if not entities:
            self._empty_label.setVisible(True)
            self._table.setVisible(False)
            return
        self._empty_label.setVisible(False)
        self._table.setVisible(True)
        rows = []
        if len(entities) == 1:
            key, ent = entities[0]
            rows.extend(self._get_props_for(key, ent))
        else:
            rows.append(("Выбрано", str(len(entities)) + " объектов"))
            types = {}
            for key, _ in entities:
                types[key] = types.get(key, 0) + 1
            for k, cnt in types.items():
                rows.append((k.upper(), str(cnt)))
        self._table.setRowCount(len(rows))
        for i, (name, val) in enumerate(rows):
            self._table.setItem(i, 0, QTableWidgetItem(str(name)))
            self._table.setItem(i, 1, QTableWidgetItem(str(val)))

    def _get_props_for(self, key: str, ent: dict) -> list[tuple[str, str]]:
        rows = [("Тип", key.upper())]
        layer = ent.get("layer", "0")
        rows.append(("Слой", layer))
        if key == "lines":
            rows.append(("Начало", _format_pt(ent.get("start"))))
            rows.append(("Конец", _format_pt(ent.get("end"))))
            rows.append(("Длина", f"{_line_length(ent):.4f}"))
        elif key == "polylines":
            pts = ent.get("points", [])
            rows.append(("Вершин", str(len(pts))))
            rows.append(("Замкнутая", "Да" if ent.get("closed") else "Нет"))
            rows.append(("Длина", f"{_polyline_length(pts):.4f}"))
            rows.append(("Площадь", f"{_polyline_area(pts):.4f}"))
            for i, p in enumerate(pts[:3]):
                rows.append((f"Вершина {i + 1}", _format_pt(p)))
            if len(pts) > 3:
                rows.append(("...", f"ещё {len(pts) - 3} точек"))
        elif key == "circles":
            c = ent.get("center", (0, 0, 0))
            r = float(ent.get("radius", 0))
            rows.append(("Центр", _format_pt(c)))
            rows.append(("Радиус", f"{r:.4f}"))
            rows.append(("Длина окружности", f"{2 * math.pi * r:.4f}"))
            rows.append(("Площадь", f"{math.pi * r * r:.4f}"))
        elif key == "arcs":
            c = ent.get("center", (0, 0, 0))
            r = float(ent.get("radius", 0))
            sa = float(ent.get("start_angle", 0))
            ea = float(ent.get("end_angle", 360))
            rows.append(("Центр", _format_pt(c)))
            rows.append(("Радиус", f"{r:.4f}"))
            rows.append(("Начальный угол", f"{sa:.2f}°"))
            rows.append(("Конечный угол", f"{ea:.2f}°"))
        elif key == "points":
            rows.append(("Позиция", _format_pt(ent.get("location"))))
        elif key == "texts":
            rows.append(("Текст", ent.get("text", "")))
        return rows
