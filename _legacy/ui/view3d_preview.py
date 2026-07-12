"""
3D-превью траектории — встроенный вид в стиле RoboCAD (2D и 3D в одном окне).
Рисует траекторию в изометрической проекции. Поддержка перетаскивания точек.
Локальная симуляция: анимация маркера вдоль траектории.
"""
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QButtonGroup, QMenu
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QFont


HIT_RADIUS = 10

VIEW_ISO, VIEW_TOP, VIEW_FRONT, VIEW_RIGHT = "iso", "top", "front", "right"


def _project_iso(x: float, y: float, z: float, cx: float, cy: float, scale: float) -> tuple:
    """Изометрическая проекция: X вправо, Y вверх, Z вперёд."""
    sx = cx + (x - y) * 0.866 * scale
    sy = cy - z * scale - (x + y) * 0.5 * scale
    return (sx, sy)


def _project_top(x: float, y: float, z: float, cx: float, cy: float, scale: float) -> tuple:
    """Вид сверху (XY): X вправо, Y вверх."""
    return (cx + x * scale, cy - y * scale)


def _project_front(x: float, y: float, z: float, cx: float, cy: float, scale: float) -> tuple:
    """Вид спереди (XZ): X вправо, Z вверх."""
    return (cx + x * scale, cy - z * scale)


def _project_right(x: float, y: float, z: float, cx: float, cy: float, scale: float) -> tuple:
    """Вид справа (YZ): Y вправо, Z вверх."""
    return (cx + y * scale, cy - z * scale)


class View3DPreview(QWidget):
    """Виджет превью траектории в 3D (изометрия). Поддержка перетаскивания точек."""

    pointsChanged = pyqtSignal(list)
    simulationFinished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._points: list[tuple[float, float, float]] = []
        self._scale = 8.0
        self._view_mode = VIEW_ISO
        self._project_fn = _project_iso
        self._drag_idx: int | None = None
        self._drag_start: tuple[float, float] | None = None
        self._iso_cx = self._iso_cy = self._iso_scale = self._iso_mx = self._iso_my = self._iso_mz = 0.0
        self._sim_step: int = -1
        self._sim_total: int = 0
        self._sim_timer: QTimer | None = None
        self.setMinimumSize(200, 150)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444;")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Перетащите точку для редактирования траектории")
        self._setup_view_buttons()

    def _setup_view_buttons(self):
        """ViewCube: кнопки выбора вида."""
        self._view_btns = QWidget(self)
        self._view_btns.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self._view_btns)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        self._btn_grp = QButtonGroup(self)
        for mid, label, tooltip in [
            (VIEW_ISO, "ISO", "Изометрия"),
            (VIEW_TOP, "TOP", "Вид сверху"),
            (VIEW_FRONT, "FRONT", "Вид спереди"),
            (VIEW_RIGHT, "RIGHT", "Вид справа"),
        ]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedSize(36, 22)
            btn.setStyleSheet("""
                QPushButton { background: #3c3f41; color: #aaa; border: 1px solid #555; font-size: 9px; }
                QPushButton:checked { background: #505354; color: #fff; }
                QPushButton:hover { background: #4a4d4f; }
            """)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, m=mid: self._set_view(m))
            self._btn_grp.addButton(btn)
            layout.addWidget(btn)
            if mid == VIEW_ISO:
                btn.setChecked(True)
        self._view_btns.setFixedHeight(28)

    def _set_view(self, mode: str):
        self._view_mode = mode
        self._project_fn = {
            VIEW_ISO: _project_iso,
            VIEW_TOP: _project_top,
            VIEW_FRONT: _project_front,
            VIEW_RIGHT: _project_right,
        }.get(mode, _project_iso)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._view_btns.setGeometry(self.width() - 160, 4, 156, 28)

    def set_trajectory_points(self, points: list[tuple[float, float, float]]) -> None:
        """Установить точки траектории для отображения."""
        self._points = list(points) if points else []
        self._stop_simulation()
        self.update()

    def start_simulation(self, steps: int = 60, speed: float = 1.0) -> bool:
        """Запустить локальную симуляцию. speed: 0.5=медленно, 1=норма, 2=быстро."""
        if not self._points or len(self._points) < 2:
            return False
        self._stop_simulation()
        self._sim_total = min(steps, len(self._points))
        self._sim_step = 0
        interval = max(16, int(50 / max(0.1, speed)))
        self._sim_timer = QTimer(self)
        self._sim_timer.timeout.connect(self._on_sim_tick)
        self._sim_timer.start(interval)
        self.update()
        return True

    def _stop_simulation(self) -> None:
        if self._sim_timer:
            self._sim_timer.stop()
            self._sim_timer.deleteLater()
            self._sim_timer = None
        self._sim_step = -1

    def _on_sim_tick(self) -> None:
        self.update()
        self._sim_step += 1
        if self._sim_step >= self._sim_total:
            self._stop_simulation()
            self.simulationFinished.emit()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w, h = self.width(), self.height()
        cx, cy = w // 2, h // 2

        # Заголовок (слева, чтобы не перекрывать ViewCube)
        painter.setPen(QColor("#888"))
        painter.setFont(QFont("", 9))
        if self._sim_step >= 0:
            title = f"Симуляция {self._sim_step + 1}/{self._sim_total}"
        elif self._points:
            title = f"3D — {len(self._points)} точек"
        else:
            title = "3D Превью"
        painter.drawText(QRectF(4, 4, w - 165, 18), Qt.AlignLeft | Qt.AlignVCenter, title)

        cy += 12

        # Оси
        axis_pen = QPen(QColor("#404040"))
        axis_pen.setWidthF(1.0)
        proj = self._project_fn
        o = proj(0, 0, 0, cx, cy, self._scale)
        x = proj(50, 0, 0, cx, cy, self._scale)
        y = proj(0, 50, 0, cx, cy, self._scale)
        z = proj(0, 0, 50, cx, cy, self._scale)
        painter.setPen(axis_pen)
        painter.drawLine(int(o[0]), int(o[1]), int(x[0]), int(x[1]))
        painter.drawLine(int(o[0]), int(o[1]), int(y[0]), int(y[1]))
        painter.drawLine(int(o[0]), int(o[1]), int(z[0]), int(z[1]))

        if not self._points:
            painter.setPen(QColor("#555"))
            painter.setFont(QFont("", 9))
            painter.drawText(QRectF(0, h // 2 - 20, w, 40), Qt.AlignCenter,
                "TRAC_FROM_POLYLINE → траектория")
            return

        # Масштаб под данные
        pts = self._points
        if len(pts) >= 2:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            zs = [p[2] for p in pts]
            r = max(
                max(xs) - min(xs) if xs else 1,
                max(ys) - min(ys) if ys else 1,
                max(zs) - min(zs) if zs else 1,
                1
            )
            scale = min(w, h) * 0.6 / max(r, 1)
            mx = sum(xs) / len(xs)
            my = sum(ys) / len(ys)
            mz = sum(zs) / len(zs)
        else:
            scale = self._scale
            mx = my = mz = 0

        # Линия траектории
        pen = QPen(QColor("#4FC3F7"))
        pen.setWidthF(2.5)
        painter.setPen(pen)
        proj = self._project_fn
        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            s1 = proj(p1[0] - mx, p1[1] - my, p1[2] - mz, cx, cy, scale)
            s2 = proj(p2[0] - mx, p2[1] - my, p2[2] - mz, cx, cy, scale)
            painter.drawLine(int(s1[0]), int(s1[1]), int(s2[0]), int(s2[1]))

        # Точки
        self._iso_cx, self._iso_cy = cx, cy
        self._iso_scale = scale
        self._iso_mx, self._iso_my, self._iso_mz = mx, my, mz
        painter.setBrush(QBrush(QColor("#4FC3F7")))
        painter.setPen(QPen(QColor("#2196F3"), 1))
        sim_highlight = min(self._sim_step, len(pts) - 1) if self._sim_step >= 0 else -1
        for i, p in enumerate(pts):
            s = proj(p[0] - mx, p[1] - my, p[2] - mz, cx, cy, scale)
            r = 12 if i == sim_highlight else 6
            painter.drawEllipse(QPointF(s[0], s[1]), r, r)

    def _hit_test(self, px: float, py: float) -> int | None:
        """Индекс ближайшей точки в радиусе HIT_RADIUS, или None."""
        if not self._points or self._iso_scale <= 0:
            return None
        best = None
        best_d = HIT_RADIUS ** 2
        for i, p in enumerate(self._points):
            s = self._project_fn(p[0] - self._iso_mx, p[1] - self._iso_my, p[2] - self._iso_mz,
                                 self._iso_cx, self._iso_cy, self._iso_scale)
            d = (px - s[0]) ** 2 + (py - s[1]) ** 2
            if d < best_d:
                best_d = d
                best = i
        return best

    def _screen_to_world_delta(self, dx: float, dy: float) -> tuple[float, float, float]:
        """Преобразовать пиксельный сдвиг в приращение мировых координат (изометрия)."""
        s = self._iso_scale
        if s <= 0:
            return (0, 0, 0)
        dx_world = dx / (0.866 * s)
        dz_world = -dy / s
        return (dx_world, 0.0, dz_world)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self._points:
            idx = self._hit_test(event.pos().x(), event.pos().y())
            if idx is not None:
                self._drag_idx = idx
                self._drag_start = (event.pos().x(), event.pos().y())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_idx is not None and self._drag_start is not None:
            dx = event.pos().x() - self._drag_start[0]
            dy = event.pos().y() - self._drag_start[1]
            dw = self._screen_to_world_delta(dx, dy)
            pts = list(self._points)
            p = pts[self._drag_idx]
            pts[self._drag_idx] = (p[0] + dw[0], p[1] + dw[1], p[2] + dw[2])
            self._points = pts
            self._drag_start = (event.pos().x(), event.pos().y())
            self.update()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_idx is not None:
            self._drag_idx = None
            self._drag_start = None
            self.pointsChanged.emit(list(self._points))
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event):
        if self._sim_step >= 0:
            menu = QMenu(self)
            def _stop():
                self._stop_simulation()
                self.simulationFinished.emit()
            menu.addAction("Остановить симуляцию", _stop)
            menu.exec_(event.globalPos())
        else:
            super().contextMenuEvent(event)
