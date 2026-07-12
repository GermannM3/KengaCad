"""
Панель траектории в формате G-кода — как в Siemens NX / CAM.
Показывает точки траектории как G1 X Y Z, оценку времени цикла и простой Gantt по сегментам.
"""
import math
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTextEdit, QLabel, QComboBox
from PyQt5.QtCore import Qt


def _segment_length(p1: tuple, p2: tuple) -> float:
    return math.sqrt(
        (float(p2[0]) - float(p1[0])) ** 2
        + (float(p2[1]) - float(p1[1])) ** 2
        + (float(p2[2] if len(p2) > 2 else 0) - float(p1[2] if len(p1) > 2 else 0)) ** 2
    )


def _cycle_time_and_segments(points: list, feed_mm_s: float) -> tuple:
    """Возвращает (общее_время_с, список (индекс_сегмента, длина_мм, время_с, время_накоп_с))."""
    if not points or len(points) < 2 or feed_mm_s <= 0:
        return 0.0, []
    total = 0.0
    segs = []
    for i in range(len(points) - 1):
        L = _segment_length(points[i], points[i + 1])
        t = L / feed_mm_s
        total += t
        segs.append((i, L, t, total))
    return total, segs


class TrajectoryCodePanel(QWidget):
    """Виджет с отображением траектории в виде G-кода, времени цикла и Gantt по сегментам."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._label = QLabel("Траектория (G-код)")
        self._label.setStyleSheet("color: #aaa; font-size: 10px; padding: 4px;")
        self._feed_combo = QComboBox()
        self._feed_combo.addItems(["50 мм/с", "100 мм/с", "200 мм/с", "500 мм/с"])
        self._feed_combo.setCurrentIndex(1)
        self._feed_combo.setStyleSheet("background: #3c3f41; color: #e0e0e0; padding: 2px;")
        self._cycle_label = QLabel("Время цикла: —")
        self._cycle_label.setStyleSheet("color: #8ab; font-size: 10px; padding: 2px;")
        self._gantt_label = QLabel("Gantt (сегменты по времени): —")
        self._gantt_label.setStyleSheet("color: #aaa; font-size: 9px; padding: 2px;")
        self._gantt_label.setWordWrap(True)
        self._text = QTextEdit()
        self._text.setReadOnly(True)
        self._text.setStyleSheet("""
            QTextEdit { background: #1e1e1e; color: #e0e0e0; font-family: Consolas, monospace; font-size: 10px;
                        border: 1px solid #444; }
        """)
        self._text.setPlaceholderText("POLYLINE → TRAC_FROM_POLYLINE")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._label)
        layout.addWidget(QLabel("Скорость подачи:"))
        layout.addWidget(self._feed_combo)
        layout.addWidget(self._cycle_label)
        layout.addWidget(self._gantt_label)
        layout.addWidget(self._text)
        self._points = []
        self._feed_combo.currentIndexChanged.connect(self._update_cycle_display)

    def _feed_mm_s(self) -> float:
        idx = self._feed_combo.currentIndex()
        return [50.0, 100.0, 200.0, 500.0][idx]

    def _update_cycle_display(self) -> None:
        if not self._points:
            self._cycle_label.setText("Время цикла: —")
            self._gantt_label.setText("Gantt (сегменты по времени): —")
            return
        total, segs = _cycle_time_and_segments(self._points, self._feed_mm_s())
        self._cycle_label.setText(f"Время цикла: {total:.2f} с (при {self._feed_mm_s():.0f} мм/с)")
        if not segs:
            self._gantt_label.setText("Gantt: один сегмент")
            return
        parts = [f"сег.{s[0]}: {s[2]:.2f}с" for s in segs[:10]]
        if len(segs) > 10:
            parts.append("...")
        self._gantt_label.setText("Gantt: " + " | ".join(parts))

    def set_trajectory(self, points: list) -> None:
        """Обновить отображение траектории."""
        self._points = list(points) if points else []
        if not self._points:
            self._text.clear()
            self._text.setPlaceholderText("POLYLINE → TRAC_FROM_POLYLINE")
            self._cycle_label.setText("Время цикла: —")
            self._gantt_label.setText("Gantt (сегменты по времени): —")
            return
        lines = []
        lines.append("; KengaCAD — траектория")
        lines.append(f"; {len(self._points)} точек")
        total, _ = _cycle_time_and_segments(self._points, self._feed_mm_s())
        lines.append(f"; Время цикла (при {self._feed_mm_s():.0f} мм/с): {total:.2f} с")
        lines.append("")
        for i, p in enumerate(self._points):
            x, y = float(p[0]), float(p[1])
            z = float(p[2]) if len(p) > 2 else 0.0
            lines.append(f"N{i+1:05d} G1 X{x:.4f} Y{y:.4f} Z{z:.4f}")
        self._text.setPlainText("\n".join(lines))
        self._text.setPlaceholderText("")
        self._update_cycle_display()
