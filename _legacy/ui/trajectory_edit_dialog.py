"""
Диалог редактирования траектории — таблица координат X, Y, Z.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QHeaderView, QMessageBox
)
from PyQt5.QtCore import Qt
from typing import List, Tuple


class TrajectoryEditDialog(QDialog):
    """Диалог редактирования точек траектории."""

    def __init__(self, points: List[Tuple[float, float, float]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Редактирование траектории")
        self.setMinimumSize(400, 300)
        self._points = [list(p) for p in points]
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Точки траектории (X, Y, Z в мм):"))
        self.table = QTableWidget(len(self._points), 3)
        self.table.setHorizontalHeaderLabels(["X", "Y", "Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet("""
            QTableWidget { background: #3c3f41; color: #e0e0e0; gridline-color: #555; }
            QHeaderView::section { background: #45494a; color: #fff; padding: 6px; }
        """)
        for row, p in enumerate(self._points):
            for col in range(3):
                item = QTableWidgetItem(f"{p[col]:.3f}")
                item.setFlags(item.flags() | Qt.ItemIsEditable)
                self.table.setItem(row, col, item)
        layout.addWidget(self.table)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        add_btn = QPushButton("Добавить")
        add_btn.setToolTip("Добавить точку в конец")
        add_btn.clicked.connect(self._add_point)
        insert_btn = QPushButton("Вставить после")
        insert_btn.setToolTip("Вставить точку после выбранной строки")
        insert_btn.clicked.connect(self._insert_after)
        del_btn = QPushButton("Удалить")
        del_btn.setToolTip("Удалить выбранную строку")
        del_btn.clicked.connect(self._delete_selected)
        up_btn = QPushButton("▲")
        up_btn.setToolTip("Переместить вверх")
        up_btn.clicked.connect(self._move_up)
        down_btn = QPushButton("▼")
        down_btn.setToolTip("Переместить вниз")
        down_btn.clicked.connect(self._move_down)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(insert_btn)
        btn_row.addWidget(del_btn)
        btn_row.addWidget(up_btn)
        btn_row.addWidget(down_btn)
        layout.addLayout(btn_row)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._apply_and_close)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        btn_row2 = QHBoxLayout()
        btn_row2.addStretch()
        btn_row2.addWidget(ok_btn)
        btn_row2.addWidget(cancel_btn)
        layout.addLayout(btn_row2)

    def _add_point(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        last = (0.0, 0.0, 0.0)
        if row > 0:
            it0 = self.table.item(row - 1, 0)
            it1 = self.table.item(row - 1, 1)
            it2 = self.table.item(row - 1, 2)
            if it0 and it1 and it2:
                try:
                    last = (float(it0.text()), float(it1.text()), float(it2.text()))
                except ValueError:
                    pass
        for col in range(3):
            item = QTableWidgetItem(f"{last[col]:.3f}")
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.table.setItem(row, col, item)

    def _delete_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)

    def _insert_after(self):
        row = self.table.currentRow()
        if row < 0:
            row = self.table.rowCount() - 1
        insert_at = row + 1
        self.table.insertRow(insert_at)
        p_prev = (0.0, 0.0, 0.0)
        p_next = (0.0, 0.0, 0.0)
        if row >= 0:
            it = [self.table.item(row, c) for c in range(3)]
            if all(it):
                try:
                    p_prev = (float(it[0].text()), float(it[1].text()), float(it[2].text()))
                except ValueError:
                    pass
        if insert_at + 1 < self.table.rowCount():
            it = [self.table.item(insert_at + 1, c) for c in range(3)]
            if all(it):
                try:
                    p_next = (float(it[0].text()), float(it[1].text()), float(it[2].text()))
                except ValueError:
                    pass
        for c in range(3):
            val = (p_prev[c] + p_next[c]) / 2.0
            item = QTableWidgetItem(f"{val:.3f}")
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.table.setItem(insert_at, c, item)
        self.table.setCurrentCell(insert_at, 0)

    def _move_up(self):
        row = self.table.currentRow()
        if row <= 0:
            return
        self._swap_rows(row, row - 1)
        self.table.setCurrentCell(row - 1, 0)

    def _move_down(self):
        row = self.table.currentRow()
        if row < 0 or row >= self.table.rowCount() - 1:
            return
        self._swap_rows(row, row + 1)
        self.table.setCurrentCell(row + 1, 0)

    def _swap_rows(self, r1: int, r2: int):
        vals = []
        for r in (r1, r2):
            it = [self.table.item(r, c) for c in range(3)]
            vals.append([it[c].text() if it[c] else "0" for c in range(3)])
        for c in range(3):
            self.table.item(r1, c).setText(vals[1][c])
            self.table.item(r2, c).setText(vals[0][c])

    def _apply_and_close(self):
        points = []
        for row in range(self.table.rowCount()):
            try:
                x = float(self.table.item(row, 0).text().replace(",", "."))
                y = float(self.table.item(row, 1).text().replace(",", "."))
                z = float(self.table.item(row, 2).text().replace(",", "."))
                points.append((x, y, z))
            except (ValueError, AttributeError):
                QMessageBox.warning(self, "Ошибка",
                    f"Строка {row + 1}: введите числа для X, Y, Z")
                return
        if len(points) < 2:
            QMessageBox.warning(self, "Ошибка", "Нужно минимум 2 точки")
            return
        self._points = points
        self.accept()

    def get_points(self) -> List[Tuple[float, float, float]]:
        return [tuple(p) for p in self._points]
