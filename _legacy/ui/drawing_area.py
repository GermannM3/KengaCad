"""
Drawing area for KengaCAD (basic 2D view with pan/zoom/snap).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from PyQt5.QtWidgets import (
    QGraphicsView,
    QGraphicsScene,
    QGraphicsLineItem,
    QGraphicsEllipseItem,
    QGraphicsPathItem,
    QGraphicsTextItem,
    QGraphicsRectItem,
)
from PyQt5.QtCore import Qt, QPointF, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath, QFont, QPixmap


def _watermark_pixmap() -> Optional[QPixmap]:
    """Загружает логотип для водяного знака."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent / "_internal"
    else:
        base = Path(__file__).resolve().parent.parent
    for name in ("logo.png", "logo.ico"):
        path = base / "assets" / name
        if path.exists():
            px = QPixmap(str(path))
            if not px.isNull():
                return px.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return None


class DrawingArea(QGraphicsView):
    cursorMoved = pyqtSignal(float, float, bool)
    entityClicked = pyqtSignal(str, int)  # entity_type, index
    selectionBoxFinished = pyqtSignal(list, bool)  # [(e_type, idx), ...], add_to_selection
    pointPicked = pyqtSignal(float, float)  # x, y — для интерактивного ввода (AutoCAD-like)

    def __init__(self):
        super().__init__()
        self.setObjectName("DrawingArea")
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(-400, -400, 800, 800)
        self.setScene(self._scene)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setBackgroundBrush(QColor("#2d2d30"))
        self.setDragMode(QGraphicsView.NoDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)

        self._panning = False
        self._pan_start = QPointF()
        self._zoom = 1.0
        self._snap_enabled = True
        self._snap_points: List[Tuple[float, float]] = []
        self._snap_buckets = {}
        self._snap_bucket_size = 25.0
        self._snap_endpoints: List[Tuple[float, float]] = []
        self._snap_midpoints: List[Tuple[float, float]] = []
        self._snap_intersections: List[Tuple[float, float]] = []
        self._snap_segments: List[Tuple[Tuple[float, float], Tuple[float, float]]] = []
        self._snap_circles: List[Tuple[Tuple[float, float], float]] = []
        self._snap_arcs: List[Tuple[Tuple[float, float], float, float, float]] = []
        self._snap_marker = None
        self._snap_marker_label = None
        self._snap_types = {"E", "M", "I", "C", "N"}

        self._entities: Dict = {}
        self._layers: Dict = {"0": {"visible": True}}
        self._active_layer = "0"
        self._selected: List[Tuple[str, int]] = []
        self._watermark: Optional[QPixmap] = _watermark_pixmap()

        self._selection_box_start: Optional[QPointF] = None
        self._selection_box_item: Optional[QGraphicsRectItem] = None
        self._point_pick_mode = False
        self._grid_enabled = True
        self._grid_spacing = 10.0
        self._preview_item = None

    def set_point_pick_mode(self, enabled: bool) -> None:
        self._point_pick_mode = bool(enabled)
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)

    def set_grid_enabled(self, enabled: bool) -> None:
        self._grid_enabled = bool(enabled)
        self.viewport().update()

    def set_grid_spacing(self, spacing: float) -> None:
        self._grid_spacing = max(1.0, float(spacing))
        self.viewport().update()

    def _clear_preview(self) -> None:
        if self._preview_item:
            try:
                if self._preview_item.scene():
                    self._scene.removeItem(self._preview_item)
            except RuntimeError:
                pass
            self._preview_item = None

    def set_preview(self, cmd: str, points: list, current_xy: Tuple[float, float] | None) -> None:
        """Показать резиновую линию/окружность при интерактивном рисовании. Координаты в CAD (y вверх)."""
        self._clear_preview()
        if not current_xy:
            return
        cx, cy = current_xy
        # Сцена: y инвертирован (scene_y = -cad_y)
        def sc(x: float, y: float) -> Tuple[float, float]:
            return (x, -y)

        dash_pen = QPen(QColor("#6ab7ff"))
        dash_pen.setStyle(Qt.DashLine)
        dash_pen.setWidthF(2.0)

        if cmd == "LINE" and len(points) >= 1:
            x1, y1 = points[0][0], points[0][1]
            sx1, sy1 = sc(x1, y1)
            sx2, sy2 = sc(cx, cy)
            line = self._scene.addLine(sx1, sy1, sx2, sy2, dash_pen)
            line.setZValue(9000)
            self._preview_item = line
        elif cmd == "CIRCLE" and len(points) >= 1:
            x1, y1 = points[0][0], points[0][1]
            r = math.sqrt((cx - x1) ** 2 + (cy - y1) ** 2)
            if r > 0.1:
                scx, scy = sc(x1, y1)
                ellipse = self._scene.addEllipse(scx - r, scy - r, r * 2, r * 2, dash_pen)
                ellipse.setZValue(9000)
                self._preview_item = ellipse
        elif cmd == "RECTANGLE" and len(points) >= 1:
            x1, y1 = points[0][0], points[0][1]
            sx1, sy1 = sc(x1, y1)
            sx2, sy2 = sc(cx, cy)
            r = QRectF(min(sx1, sx2), min(sy1, sy2), abs(sx2 - sx1), abs(sy2 - sy1))
            rect = self._scene.addRect(r, dash_pen)
            rect.setZValue(9000)
            self._preview_item = rect
        elif cmd == "ARC" and len(points) >= 1:
            xc, yc = points[0][0], points[0][1]
            r = math.sqrt((cx - xc) ** 2 + (cy - yc) ** 2)
            if r > 0.1:
                scx, scy = sc(xc, yc)
                ellipse = self._scene.addEllipse(scx - r, scy - r, r * 2, r * 2, dash_pen)
                ellipse.setZValue(9000)
                self._preview_item = ellipse

    def clear_preview(self) -> None:
        self._clear_preview()

    def paintEvent(self, event):
        super().paintEvent(event)
        # Оси X, Y и начало координат
        painter = QPainter(self.viewport())
        vrect = self.viewport().rect()
        top_left = self.mapToScene(vrect.topLeft())
        bottom_right = self.mapToScene(vrect.bottomRight())
        x_min, x_max = top_left.x(), bottom_right.x()
        y_min, y_max = top_left.y(), bottom_right.y()
        origin_vp = self.mapFromScene(0, 0)
        ox, oy = int(origin_vp.x()), int(origin_vp.y())
        painter.setPen(QPen(QColor("#5a5a5a"), 2))
        painter.setRenderHint(QPainter.Antialiasing, True)
        if y_min <= 0 <= y_max:
            p1 = self.mapFromScene(x_min, 0)
            p2 = self.mapFromScene(x_max, 0)
            painter.drawLine(int(p1.x()), int(p1.y()), int(p2.x()), int(p2.y()))
        if x_min <= 0 <= x_max:
            p1 = self.mapFromScene(0, y_min)
            p2 = self.mapFromScene(0, y_max)
            painter.drawLine(int(p1.x()), int(p1.y()), int(p2.x()), int(p2.y()))
        painter.setBrush(QColor("#4FC3F7"))
        painter.setPen(QPen(QColor("#4FC3F7"), 1))
        painter.drawEllipse(ox - 4, oy - 4, 8, 8)
        painter.setPen(QColor("#8a8a8a"))
        painter.drawText(ox + 10, oy - 5, "0")
        painter.end()

        if self._grid_enabled and self._grid_spacing > 0:
            painter = QPainter(self.viewport())
            painter.setPen(QPen(QColor("#404040"), 1))
            painter.setRenderHint(QPainter.Antialiasing, False)
            vrect = self.viewport().rect()
            top_left = self.mapToScene(vrect.topLeft())
            bottom_right = self.mapToScene(vrect.bottomRight())
            x1 = int(top_left.x() // self._grid_spacing) * self._grid_spacing
            x2 = int(bottom_right.x() // self._grid_spacing + 1) * self._grid_spacing
            y1 = int(top_left.y() // self._grid_spacing) * self._grid_spacing
            y2 = int(bottom_right.y() // self._grid_spacing + 1) * self._grid_spacing
            x_min, x_max = min(x1, x2), max(x1, x2)
            y_min, y_max = min(y1, y2), max(y1, y2)
            n_x = int((x_max - x_min) / self._grid_spacing) + 1
            n_y = int((y_max - y_min) / self._grid_spacing) + 1
            for i in range(min(n_x, 200)):
                xi = x_min + i * self._grid_spacing
                p1 = self.mapFromScene(xi, y_min)
                p2 = self.mapFromScene(xi, y_max)
                painter.drawLine(int(p1.x()), int(p1.y()), int(p2.x()), int(p2.y()))
            for i in range(min(n_y, 200)):
                yi = y_min + i * self._grid_spacing
                p1 = self.mapFromScene(x_min, yi)
                p2 = self.mapFromScene(x_max, yi)
                painter.drawLine(int(p1.x()), int(p1.y()), int(p2.x()), int(p2.y()))
            painter.end()
        if self._watermark and not self._watermark.isNull():
            painter = QPainter(self.viewport())
            painter.setOpacity(0.15)
            x = self.viewport().width() - self._watermark.width() - 12
            y = self.viewport().height() - self._watermark.height() - 12
            painter.drawPixmap(x, y, self._watermark)
            painter.end()

        if self._is_empty():
            painter = QPainter(self.viewport())
            painter.setPen(QColor("#6a6a6a"))
            font = QFont()
            font.setPointSize(11)
            painter.setFont(font)
            cx, cy = self.viewport().width() // 2, self.viewport().height() // 2
            texts = [
                "Траектория робота — 4 шага",
                "1. Нарисуйте полилинию (кнопка Полилиния или полигон мышью)",
                "2. TRAC_FROM_POLYLINE — траектория из полилинии",
                "3. LOAD_DEMO_ROBOT — загрузить робота (вкладка Робот)",
                "4. SIMULATE — симуляция в 3D-окне",
                "",
                "Линия / Окружность / Прямоугольник — клик мышью | ? — справка",
            ]
            for i, t in enumerate(texts):
                tw = painter.fontMetrics().horizontalAdvance(t)
                painter.drawText(cx - tw // 2, cy - 70 + i * 20, t)
            painter.end()

    def _is_empty(self) -> bool:
        for key in ("lines", "circles", "points", "arcs", "polylines", "texts", "splines", "ellipses", "dimensions", "hatches", "inserts"):
            if self._entities.get(key):
                return False
        return True

    def set_entities(self, entities: Dict, layers: Dict, active_layer: str, blocks: Dict = None) -> None:
        self._entities = entities or {}
        self._layers = layers or {"0": {"visible": True}}
        self._active_layer = active_layer or "0"
        self._blocks = blocks or {}
        self._rebuild_scene()

    def set_selection(self, selected: List[Tuple[str, int]]) -> None:
        """Выделенные объекты: [(entity_type, index), ...]"""
        self._selected = list(selected) if selected else []

    def set_snap_enabled(self, enabled: bool) -> None:
        self._snap_enabled = bool(enabled)
        if not enabled and self._snap_marker:
            try:
                if self._snap_marker.scene():
                    self._scene.removeItem(self._snap_marker)
            except RuntimeError:
                pass
            self._snap_marker = None
            self._snap_marker_label = None

    def zoom_in(self):
        self._apply_zoom(1.2)

    def zoom_out(self):
        self._apply_zoom(1 / 1.2)

    def zoom_extents(self):
        items = self._scene.items()
        if not items:
            return
        rect = self._scene.itemsBoundingRect()
        if rect.isNull():
            return
        self.fitInView(rect, Qt.KeepAspectRatio)

    def zoom_to_origin(self):
        """Центрировать вид на начале координат (0,0)."""
        margin = 200
        rect = QRectF(-margin, -margin, margin * 2, margin * 2)
        self.fitInView(rect, Qt.KeepAspectRatio)

    def zoom_to_selection(self) -> bool:
        """Масштабировать вид к выделенным объектам. Возвращает True если было выделение."""
        if not self._selected:
            return False
        union = QRectF()
        for item in self._scene.items():
            data = item.data(Qt.UserRole)
            if data and data in self._selected:
                r = item.sceneBoundingRect()
                union = union.united(r)
        if union.isNull() or union.isEmpty():
            return False
        margin = 40
        union.adjust(-margin, -margin, margin, margin)
        self.fitInView(union, Qt.KeepAspectRatio)
        return True

    def toggle_pan(self):
        # Pan uses middle mouse button; this is a placeholder for UI toggle.
        pass

    def update_from_engine(self, frame_buffer):
        # Placeholder for future frame updates
        pass

    def _apply_zoom(self, factor: float):
        self._zoom *= factor
        self.scale(factor, factor)

    def _rebuild_scene(self):
        self._scene.clear()
        self._selection_box_item = None
        self._selection_box_start = None
        self._snap_marker = None
        self._snap_marker_label = None
        self._preview_item = None
        if hasattr(self, "_snap_text"):
            try:
                del self._snap_text
            except Exception:
                pass
        self._snap_points.clear()
        self._snap_buckets.clear()
        self._snap_endpoints.clear()
        self._snap_midpoints.clear()
        self._snap_intersections.clear()
        self._snap_segments.clear()
        self._snap_circles.clear()
        self._snap_arcs.clear()

        def layer_visible(layer: str) -> bool:
            return self._layers.get(layer, {}).get("visible", True)

        def is_selected(e_type: str, idx: int) -> bool:
            return (e_type, idx) in self._selected

        def pen_for(e_type: str, idx: int, entity: dict = None):
            p = QPen(QColor("#4FC3F7") if is_selected(e_type, idx) else QColor("#cccccc"))
            p.setWidthF(2.0 if is_selected(e_type, idx) else 0.8)
            lt = (entity or {}).get("linetype", "Continuous")
            style_map = {"Dashed": Qt.DashLine, "Dotted": Qt.DotLine, "DashDot": Qt.DashDotLine,
                        "DashDotDot": Qt.DashDotDotLine}
            p.setStyle(style_map.get(lt, Qt.SolidLine))
            return p

        # Lines
        for idx, line in enumerate(self._entities.get("lines", [])):
            if not layer_visible(line.get("layer", "0")):
                continue
            start = line.get("start", (0, 0, 0))
            end = line.get("end", (0, 0, 0))
            p1 = (start[0], -start[1])
            p2 = (end[0], -end[1])
            mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            item = QGraphicsLineItem(p1[0], p1[1], p2[0], p2[1])
            item.setPen(pen_for("lines", idx, line))
            item.setData(Qt.UserRole, ("lines", idx))
            item.setAcceptHoverEvents(True)
            self._scene.addItem(item)
            self._snap_points.extend([p1, p2, mid])
            self._bucket_snap_point(p1)
            self._bucket_snap_point(p2)
            self._bucket_snap_point(mid)
            self._snap_endpoints.extend([p1, p2])
            self._snap_midpoints.append(mid)
            self._snap_segments.append((p1, p2))

        # Circles
        for idx, circle in enumerate(self._entities.get("circles", [])):
            if not layer_visible(circle.get("layer", "0")):
                continue
            center = circle.get("center", (0, 0, 0))
            radius = float(circle.get("radius", 0))
            item = QGraphicsEllipseItem(center[0] - radius, -center[1] - radius, radius * 2, radius * 2)
            item.setPen(pen_for("circles", idx, circle))
            item.setData(Qt.UserRole, ("circles", idx))
            self._scene.addItem(item)
            center_pt = (center[0], -center[1])
            self._snap_points.append(center_pt)
            self._bucket_snap_point(center_pt)
            self._snap_circles.append((center_pt, radius))

        # Arcs
        for idx, arc in enumerate(self._entities.get("arcs", [])):
            if not layer_visible(arc.get("layer", "0")):
                continue
            center = arc.get("center", (0, 0, 0))
            radius = float(arc.get("radius", 0))
            start_angle = float(arc.get("start_angle", 0))
            end_angle = float(arc.get("end_angle", 0))
            rect = (center[0] - radius, -center[1] - radius, radius * 2, radius * 2)
            path = QPainterPath()
            path.arcMoveTo(*rect, -start_angle)
            span = -(end_angle - start_angle)
            path.arcTo(*rect, -start_angle, span)
            item = QGraphicsPathItem(path)
            item.setPen(pen_for("arcs", idx, arc))
            item.setData(Qt.UserRole, ("arcs", idx))
            self._scene.addItem(item)
            center_pt = (center[0], -center[1])
            self._snap_points.append(center_pt)
            self._bucket_snap_point(center_pt)
            self._snap_arcs.append((center_pt, radius, start_angle, end_angle))

        # Points
        for idx, point in enumerate(self._entities.get("points", [])):
            if not layer_visible(point.get("layer", "0")):
                continue
            loc = point.get("location", (0, 0, 0))
            r = 1.5
            item = QGraphicsEllipseItem(loc[0] - r, -loc[1] - r, r * 2, r * 2)
            item.setPen(pen_for("points", idx, point))
            item.setData(Qt.UserRole, ("points", idx))
            self._scene.addItem(item)
            sp = (loc[0], -loc[1])
            self._snap_points.append(sp)
            self._bucket_snap_point(sp)
            self._snap_endpoints.append(sp)

        # Polylines
        for idx, poly in enumerate(self._entities.get("polylines", [])):
            if not layer_visible(poly.get("layer", "0")):
                continue
            pts = poly.get("points", [])
            if len(pts) < 2:
                continue
            path = QPainterPath(QPointF(pts[0][0], -pts[0][1]))
            for p in pts[1:]:
                path.lineTo(QPointF(p[0], -p[1]))
            item = QGraphicsPathItem(path)
            item.setPen(pen_for("polylines", idx, poly))
            item.setData(Qt.UserRole, ("polylines", idx))
            self._scene.addItem(item)
            for idx, p in enumerate(pts):
                sp = (p[0], -p[1])
                self._snap_points.append(sp)
                self._bucket_snap_point(sp)
                self._snap_endpoints.append(sp)
                if idx > 0:
                    prev = (pts[idx - 1][0], -pts[idx - 1][1])
                    mid = ((prev[0] + sp[0]) / 2, (prev[1] + sp[1]) / 2)
                    self._snap_points.append(mid)
                    self._bucket_snap_point(mid)
                    self._snap_midpoints.append(mid)
                    self._snap_segments.append((prev, sp))

        # Splines
        for idx, spl in enumerate(self._entities.get("splines", [])):
            if not layer_visible(spl.get("layer", "0")):
                continue
            pts = spl.get("fit_points", [])
            if len(pts) < 2:
                continue
            path = QPainterPath(QPointF(pts[0][0], -pts[0][1]))
            for p in pts[1:]:
                path.lineTo(QPointF(p[0], -p[1]))
            item = QGraphicsPathItem(path)
            item.setPen(pen_for("splines", idx, spl))
            item.setData(Qt.UserRole, ("splines", idx))
            self._scene.addItem(item)
            for p in pts:
                sp = (p[0], -p[1])
                self._snap_points.append(sp)
                self._bucket_snap_point(sp)
                self._snap_endpoints.append(sp)

        # Ellipses
        for idx, ell in enumerate(self._entities.get("ellipses", [])):
            if not layer_visible(ell.get("layer", "0")):
                continue
            c = ell.get("center", (0, 0, 0))
            maj = ell.get("major_axis", (1, 0, 0))
            ratio = float(ell.get("ratio", 1.0))
            cx, cy = c[0], -c[1]
            mx, my = maj[0], -maj[1]
            maj_len = (mx * mx + my * my) ** 0.5
            if maj_len < 1e-9:
                continue
            min_len = maj_len * ratio
            ux, uy = mx / maj_len, my / maj_len
            vx, vy = -uy, ux  # perpendicular
            n = 64
            path = QPainterPath()
            for i in range(n + 1):
                t = 2 * math.pi * i / n
                x = cx + maj_len * ux * math.cos(t) + min_len * vx * math.sin(t)
                y = cy + maj_len * uy * math.cos(t) + min_len * vy * math.sin(t)
                if i == 0:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)
            path.closeSubpath()
            item = QGraphicsPathItem(path)
            item.setPen(pen_for("ellipses", idx, ell))
            item.setData(Qt.UserRole, ("ellipses", idx))
            self._scene.addItem(item)
            self._snap_points.append((c[0], -c[1]))
            self._bucket_snap_point((c[0], -c[1]))

        # Dimensions
        for idx, dim in enumerate(self._entities.get("dimensions", [])):
            if not layer_visible(dim.get("layer", "0")):
                continue
            dim_type = dim.get("dim_type", "linear")
            pen = pen_for("dimensions", idx, dim)
            val = dim.get("value", 0)
            if dim_type == "radius":
                c = dim.get("center", (0, 0, 0))
                r = dim.get("radius", 0)
                dim_pos = dim.get("dim_pos", (c[0] + r * 1.2, c[1], 0))
                cx, cy = c[0], -c[1]
                dx = dim_pos[0] - c[0]
                dy = -(dim_pos[1] - c[1])
                L = (dx*dx + dy*dy) ** 0.5
                if L < 1e-9:
                    dx, dy = r, 0
                else:
                    dx, dy = dx/L * r, dy/L * r
                line = self._scene.addLine(cx, cy, cx + dx, cy + dy, pen)
                line.setData(Qt.UserRole, ("dimensions", idx))
                txt = QGraphicsTextItem(f"R{val:.2f}")
                txt.setDefaultTextColor(QColor("#4FC3F7") if is_selected("dimensions", idx) else QColor("#cccccc"))
                txt.setFont(QFont("Arial", 10))
                txt.setPos(cx + dx * 0.5 - 15, cy + dy * 0.5 - 6)
                txt.setZValue(100)
                txt.setData(Qt.UserRole, ("dimensions", idx))
                self._scene.addItem(txt)
                self._snap_points.append((c[0], -c[1]))
                self._bucket_snap_point((c[0], -c[1]))
                continue
            if dim_type == "diameter":
                c = dim.get("center", (0, 0, 0))
                r = dim.get("radius", 0)
                dim_pos = dim.get("dim_pos", (c[0] + r * 1.2, c[1], 0))
                cx, cy = c[0], -c[1]
                dx = dim_pos[0] - c[0]
                dy = -(dim_pos[1] - c[1])
                L = (dx*dx + dy*dy) ** 0.5
                if L < 1e-9:
                    dx, dy = 1, 0
                else:
                    dx, dy = dx/L, dy/L
                x1, y1 = cx - dx*r, cy - dy*r
                x2, y2 = cx + dx*r, cy + dy*r
                line = self._scene.addLine(x1, y1, x2, y2, pen)
                line.setData(Qt.UserRole, ("dimensions", idx))
                txt = QGraphicsTextItem(f"Ø{val:.2f}")
                txt.setDefaultTextColor(QColor("#4FC3F7") if is_selected("dimensions", idx) else QColor("#cccccc"))
                txt.setFont(QFont("Arial", 10))
                txt.setPos((x1+x2)/2 - 15, (y1+y2)/2 - 6)
                txt.setZValue(100)
                txt.setData(Qt.UserRole, ("dimensions", idx))
                self._scene.addItem(txt)
                self._snap_points.append((c[0], -c[1]))
                self._bucket_snap_point((c[0], -c[1]))
                continue
            p1 = dim.get("p1", (0, 0, 0))
            p2 = dim.get("p2", (0, 0, 0))
            dim_pos = dim.get("dim_pos", ((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, 0))
            x1, y1 = p1[0], -p1[1]
            x2, y2 = p2[0], -p2[1]
            xm, ym = dim_pos[0], -dim_pos[1]
            dx, dy = x2 - x1, y2 - y1
            L = (dx*dx + dy*dy) ** 0.5
            if L < 1e-9:
                continue
            ux, uy = dx/L, dy/L
            nx, ny = -uy, ux
            off = (xm - x1) * nx + (ym - y1) * ny
            ext = 5.0
            ax, ay = x1 + ext * ux, y1 + ext * uy
            bx, by = x2 - ext * ux, y2 - ext * uy
            d1x, d1y = x1 + off * nx, y1 + off * ny
            d2x, d2y = x2 + off * nx, y2 + off * ny
            ext1 = self._scene.addLine(ax, ay, d1x, d1y, pen)
            ext2 = self._scene.addLine(bx, by, d2x, d2y, pen)
            dim_line = self._scene.addLine(d1x, d1y, d2x, d2y, pen)
            for it in (ext1, ext2, dim_line):
                it.setData(Qt.UserRole, ("dimensions", idx))
            txt = QGraphicsTextItem(f"{val:.2f}")
            txt.setDefaultTextColor(QColor("#4FC3F7") if is_selected("dimensions", idx) else QColor("#cccccc"))
            txt.setFont(QFont("Arial", 10))
            txt.setPos((d1x + d2x) / 2 - 15, (d1y + d2y) / 2 - 6)
            txt.setZValue(100)
            txt.setData(Qt.UserRole, ("dimensions", idx))
            self._scene.addItem(txt)
            self._snap_points.extend([(x1, y1), (x2, y2)])
            self._bucket_snap_point((x1, y1))
            self._bucket_snap_point((x2, y2))

        # Hatches
        for idx, hatch in enumerate(self._entities.get("hatches", [])):
            if not layer_visible(hatch.get("layer", "0")):
                continue
            col = QColor(hatch.get("color", "#555555"))
            path = QPainterPath()
            if hatch.get("type") == "polygon":
                pts = hatch.get("points", [])
                if len(pts) >= 3:
                    path.moveTo(pts[0][0], -pts[0][1])
                    for p in pts[1:]:
                        path.lineTo(p[0], -p[1])
                    path.closeSubpath()
            else:
                c = hatch.get("center", (0, 0, 0))
                r = hatch.get("radius", 0)
                path.addEllipse(c[0] - r, -c[1] - r, r * 2, r * 2)
            item = QGraphicsPathItem(path)
            item.setBrush(QBrush(col))
            item.setPen(QPen(Qt.NoPen))
            item.setZValue(-10)
            item.setData(Qt.UserRole, ("hatches", idx))
            self._scene.addItem(item)

        # Inserts (block references)
        def xform_pt(x: float, y: float, ins: dict):
            px, py = ins.get("position", (0, 0, 0))[0], ins.get("position", (0, 0, 0))[1]
            scale = ins.get("scale", 1.0)
            angle = math.radians(ins.get("angle", 0))
            c, s = math.cos(angle), math.sin(angle)
            xr, yr = x * c - y * s, x * s + y * c
            return (px + xr * scale, -(py + yr * scale))

        for idx, ins in enumerate(self._entities.get("inserts", [])):
            if not layer_visible(ins.get("layer", "0")):
                continue
            block = self._blocks.get(ins.get("block", ""))
            if not block:
                continue
            pen = pen_for("inserts", idx, ins)
            for ent in block.get("entities", []):
                key = ent.get("key", "")
                e = ent.get("entity", {})
                if key == "lines":
                    s, e2 = e.get("start", (0,0,0)), e.get("end", (0,0,0))
                    p1 = xform_pt(s[0], s[1], ins)
                    p2 = xform_pt(e2[0], e2[1], ins)
                    li = self._scene.addLine(p1[0], p1[1], p2[0], p2[1], pen)
                    li.setData(Qt.UserRole, ("inserts", idx))
                elif key == "circles":
                    c, r = e.get("center", (0,0,0)), e.get("radius", 0) * ins.get("scale", 1.0)
                    pc = xform_pt(c[0], c[1], ins)
                    ci = self._scene.addEllipse(pc[0]-r, pc[1]-r, r*2, r*2, pen)
                    ci.setData(Qt.UserRole, ("inserts", idx))
                elif key == "arcs":
                    c = e.get("center", (0,0,0))
                    r = e.get("radius", 0) * ins.get("scale", 1.0)
                    sa, ea = e.get("start_angle", 0), e.get("end_angle", 0)
                    pc = xform_pt(c[0], c[1], ins)
                    rect = (pc[0]-r, pc[1]-r, r*2, r*2)
                    path = QPainterPath()
                    path.arcMoveTo(*rect, -sa)
                    path.arcTo(*rect, -sa, -(ea-sa))
                    pi = self._scene.addPath(path, pen)
                    pi.setData(Qt.UserRole, ("inserts", idx))
                elif key == "polylines":
                    pts = e.get("points", [])
                    if len(pts) >= 2:
                        path = QPainterPath()
                        p0 = xform_pt(pts[0][0], pts[0][1], ins)
                        path.moveTo(p0[0], p0[1])
                        for p in pts[1:]:
                            pp = xform_pt(p[0], p[1], ins)
                            path.lineTo(pp[0], pp[1])
                        pi = self._scene.addPath(path, pen)
                        pi.setData(Qt.UserRole, ("inserts", idx))
            self._snap_points.append(xform_pt(0, 0, ins))
            self._bucket_snap_point(xform_pt(0, 0, ins))

        # Texts
        for idx, txt in enumerate(self._entities.get("texts", [])):
            if not layer_visible(txt.get("layer", "0")):
                continue
            pos = txt.get("position", (0, 0, 0))
            content = txt.get("text", "")
            height = float(txt.get("height", 10))
            item = QGraphicsTextItem(content)
            font = QFont()
            font.setPointSize(max(6, int(height)))
            item.setFont(font)
            item.setDefaultTextColor(QColor("#4FC3F7") if is_selected("texts", idx) else QColor("#cccccc"))
            item.setPos(QPointF(pos[0], -pos[1]))
            item.setData(Qt.UserRole, ("texts", idx))
            self._scene.addItem(item)
            sp = (pos[0], -pos[1])
            self._snap_points.append(sp)
            self._bucket_snap_point(sp)
            self._snap_endpoints.append(sp)

        self._add_intersection_snaps()
        items = self._scene.items()
        if items:
            self._scene.setSceneRect(self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50))
        else:
            self._scene.setSceneRect(-400, -400, 800, 800)
            self._draw_empty_grid()
        self._scene.update()

    def _draw_empty_grid(self) -> None:
        """Сетка осей при пустом холсте — чтобы видеть область рисования."""
        grid_pen = QPen(QColor("#404040"))
        grid_pen.setWidthF(0.5)
        for i in range(-400, 401, 50):
            if i == 0:
                continue
            self._scene.addLine(i, -400, i, 400, grid_pen)
            self._scene.addLine(-400, i, 400, i, grid_pen)
        axis_pen = QPen(QColor("#606060"))
        axis_pen.setWidthF(1.0)
        self._scene.addLine(-400, 0, 400, 0, axis_pen)
        self._scene.addLine(0, -400, 0, 400, axis_pen)

    def _add_intersection_snaps(self) -> None:
        max_seg_intersections = 500
        max_circle_intersections = 200
        # segment-segment
        if len(self._snap_segments) > max_seg_intersections:
            return
        if len(self._snap_segments) >= 2:
            for i in range(len(self._snap_segments)):
                for j in range(i + 1, len(self._snap_segments)):
                    if not self._bbox_overlap(self._snap_segments[i], self._snap_segments[j]):
                        continue
                    p = self._segment_intersection(self._snap_segments[i], self._snap_segments[j])
                    if p is not None:
                        self._snap_points.append(p)
                        self._snap_intersections.append(p)
                        self._bucket_snap_point(p)

        # segment-circle
        for seg in self._snap_segments:
            for center, radius in self._snap_circles:
                for p in self._segment_circle_intersections(seg, center, radius):
                    self._snap_points.append(p)
                    self._snap_intersections.append(p)
                    self._bucket_snap_point(p)

        # segment-arc (filter by arc angle)
        for seg in self._snap_segments:
            for center, radius, start_angle, end_angle in self._snap_arcs:
                for p in self._segment_circle_intersections(seg, center, radius):
                    if self._point_on_arc(p, center, start_angle, end_angle):
                        self._snap_points.append(p)
                        self._snap_intersections.append(p)
                        self._bucket_snap_point(p)

        if len(self._snap_circles) > max_circle_intersections:
            return

        # circle-circle
        for i in range(len(self._snap_circles)):
            for j in range(i + 1, len(self._snap_circles)):
                for p in self._circle_circle_intersections(self._snap_circles[i], self._snap_circles[j]):
                    self._snap_points.append(p)
                    self._snap_intersections.append(p)
                    self._bucket_snap_point(p)

        # arc-circle and arc-arc (filtered)
        for arc in self._snap_arcs:
            for circle in self._snap_circles:
                for p in self._circle_circle_intersections((arc[0], arc[1]), circle):
                    if self._point_on_arc(p, arc[0], arc[2], arc[3]):
                        self._snap_points.append(p)
                        self._snap_intersections.append(p)
                        self._bucket_snap_point(p)
        for i in range(len(self._snap_arcs)):
            for j in range(i + 1, len(self._snap_arcs)):
                arc1 = self._snap_arcs[i]
                arc2 = self._snap_arcs[j]
                for p in self._circle_circle_intersections((arc1[0], arc1[1]), (arc2[0], arc2[1])):
                    if self._point_on_arc(p, arc1[0], arc1[2], arc1[3]) and self._point_on_arc(p, arc2[0], arc2[2], arc2[3]):
                        self._snap_points.append(p)
                        self._snap_intersections.append(p)
                        self._bucket_snap_point(p)

    def _bbox_overlap(self, seg1, seg2) -> bool:
        (x1, y1), (x2, y2) = seg1
        (x3, y3), (x4, y4) = seg2
        min1x, max1x = (x1, x2) if x1 <= x2 else (x2, x1)
        min1y, max1y = (y1, y2) if y1 <= y2 else (y2, y1)
        min2x, max2x = (x3, x4) if x3 <= x4 else (x4, x3)
        min2y, max2y = (y3, y4) if y3 <= y4 else (y4, y3)
        return not (max1x < min2x or max2x < min1x or max1y < min2y or max2y < min1y)

    def _segment_intersection(self, seg1, seg2) -> Tuple[float, float] | None:
        (x1, y1), (x2, y2) = seg1
        (x3, y3), (x4, y4) = seg2
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-9:
            return None
        px = ((x1 * y2 - y1 * x2) * (x3 - x4) - (x1 - x2) * (x3 * y4 - y3 * x4)) / denom
        py = ((x1 * y2 - y1 * x2) * (y3 - y4) - (y1 - y2) * (x3 * y4 - y3 * x4)) / denom
        if (min(x1, x2) - 1e-6 <= px <= max(x1, x2) + 1e-6 and
                min(y1, y2) - 1e-6 <= py <= max(y1, y2) + 1e-6 and
                min(x3, x4) - 1e-6 <= px <= max(x3, x4) + 1e-6 and
                min(y3, y4) - 1e-6 <= py <= max(y3, y4) + 1e-6):
            return (px, py)
        return None

    def _segment_circle_intersections(self, seg, center, radius) -> List[Tuple[float, float]]:
        (x1, y1), (x2, y2) = seg
        cx, cy = center
        dx = x2 - x1
        dy = y2 - y1
        fx = x1 - cx
        fy = y1 - cy

        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - radius * radius

        disc = b * b - 4 * a * c
        if disc < 0 or abs(a) < 1e-9:
            return []
        disc = disc ** 0.5
        t1 = (-b - disc) / (2 * a)
        t2 = (-b + disc) / (2 * a)
        pts = []
        for t in (t1, t2):
            if 0.0 - 1e-6 <= t <= 1.0 + 1e-6:
                pts.append((x1 + t * dx, y1 + t * dy))
        return pts

    def _circle_circle_intersections(self, c1, c2) -> List[Tuple[float, float]]:
        (x0, y0), r0 = c1
        (x1, y1), r1 = c2
        dx = x1 - x0
        dy = y1 - y0
        d = (dx * dx + dy * dy) ** 0.5
        if d < 1e-9:
            return []
        if d > r0 + r1 or d < abs(r0 - r1):
            return []
        a = (r0 * r0 - r1 * r1 + d * d) / (2 * d)
        h_sq = r0 * r0 - a * a
        if h_sq < 0:
            return []
        h = h_sq ** 0.5
        xm = x0 + a * dx / d
        ym = y0 + a * dy / d
        rx = -dy * (h / d)
        ry = dx * (h / d)
        p1 = (xm + rx, ym + ry)
        p2 = (xm - rx, ym - ry)
        if h < 1e-9:
            return [p1]
        return [p1, p2]

    def _point_on_arc(self, p: Tuple[float, float], center: Tuple[float, float], start_angle: float, end_angle: float) -> bool:
        import math
        dx = p[0] - center[0]
        dy = p[1] - center[1]
        ang = math.degrees(math.atan2(dy, dx)) % 360.0
        s = start_angle % 360.0
        e = end_angle % 360.0
        if s <= e:
            return s - 1e-3 <= ang <= e + 1e-3
        return ang >= s - 1e-3 or ang <= e + 1e-3

    def _nearest_on_segment(self, px: float, py: float, seg: Tuple[Tuple[float, float], Tuple[float, float]]) -> Tuple[float, float]:
        """Ближайшая точка на отрезке к (px, py)."""
        (x1, y1), (x2, y2) = seg
        dx, dy = x2 - x1, y2 - y1
        L2 = dx * dx + dy * dy
        if L2 < 1e-12:
            return (x1, y1)
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / L2))
        return (x1 + t * dx, y1 + t * dy)

    def _nearest_on_circle(self, px: float, py: float, center: Tuple[float, float], radius: float) -> Tuple[float, float]:
        """Ближайшая точка на окружности к (px, py)."""
        cx, cy = center
        dx, dy = px - cx, py - cy
        d = (dx * dx + dy * dy) ** 0.5
        if d < 1e-9:
            return (cx + radius, cy)
        return (cx + radius * dx / d, cy + radius * dy / d)

    def _nearest_on_arc(self, px: float, py: float, center: Tuple[float, float], r: float, sa: float, ea: float) -> Tuple[float, float]:
        """Ближайшая точка на дуге (углы в градусах)."""
        cx, cy = center
        dx, dy = px - cx, py - cy
        d = (dx * dx + dy * dy) ** 0.5
        if d < 1e-9:
            ang = math.radians(sa)
            return (cx + r * math.cos(ang), cy + r * math.sin(ang))
        ang = math.degrees(math.atan2(dy, dx)) % 360.0
        s, e = sa % 360.0, ea % 360.0
        if s <= e:
            ang = max(s, min(e, ang))
        else:
            if s - 1e-3 <= ang <= 360 or 0 <= ang <= e + 1e-3:
                pass
            elif ang < s and ang > e:
                ang = e if abs(ang - e) < abs(ang - s) else s
        rad = math.radians(ang)
        return (cx + r * math.cos(rad), cy + r * math.sin(rad))

    def _find_snap_point(self, scene_pos: QPointF) -> Tuple[float, float] | None:
        sx, sy = scene_pos.x(), scene_pos.y()
        snap_radius = 12.0
        closest = None
        best_dist = snap_radius

        # Точки из buckets (E, M, I, C)
        for px, py in self._iter_nearby_points(sx, sy):
            dist = ((px - sx) ** 2 + (py - sy) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                closest = (px, py)

        # NEA: ближайшая точка на отрезках, окружностях, дугах
        if "N" in self._snap_types:
            for seg in self._snap_segments:
                np = self._nearest_on_segment(sx, sy, seg)
                dist = ((np[0] - sx) ** 2 + (np[1] - sy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    closest = np
            for center, radius in self._snap_circles:
                np = self._nearest_on_circle(sx, sy, center, radius)
                dist = ((np[0] - sx) ** 2 + (np[1] - sy) ** 2) ** 0.5
                if dist < best_dist:
                    best_dist = dist
                    closest = np
            for center, r, sa, ea in self._snap_arcs:
                np = self._nearest_on_arc(sx, sy, center, r, sa, ea)
                if self._point_on_arc(np, center, sa, ea):
                    dist = ((np[0] - sx) ** 2 + (np[1] - sy) ** 2) ** 0.5
                    if dist < best_dist:
                        best_dist = dist
                        closest = np

        # Привязка к сетке (fallback, если нет привязки к объекту)
        if closest is None and self._grid_enabled and self._grid_spacing > 0:
            gx = round(sx / self._grid_spacing) * self._grid_spacing
            gy = round(sy / self._grid_spacing) * self._grid_spacing
            dist = ((gx - sx) ** 2 + (gy - sy) ** 2) ** 0.5
            if dist < snap_radius:
                return ((gx, gy), "G")

        return (closest, None) if closest else (None, None)

    def _bucket_key(self, x: float, y: float) -> Tuple[int, int]:
        size = self._snap_bucket_size
        return (int(x // size), int(y // size))

    def _bucket_snap_point(self, p: Tuple[float, float]) -> None:
        key = self._bucket_key(p[0], p[1])
        self._snap_buckets.setdefault(key, []).append(p)

    def _iter_nearby_points(self, x: float, y: float):
        key = self._bucket_key(x, y)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                pts = self._snap_buckets.get((key[0] + dx, key[1] + dy), [])
                for p in pts:
                    yield p

    def mousePressEvent(self, event):
        mid = getattr(Qt, "MiddleButton", None) or Qt.MidButton
        if event.button() == mid:
            self._panning = True
            self._pan_start = QPointF(event.pos())
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton and not self._panning:
            scene_pos = self.mapToScene(event.pos())
            if self._point_pick_mode:
                x, y = scene_pos.x(), -scene_pos.y()
                self.pointPicked.emit(x, y)
                event.accept()
                return
            items = self._scene.items(scene_pos)
            for it in items:
                data = it.data(Qt.UserRole)
                if data:
                    e_type, idx = data
                    self.entityClicked.emit(e_type, idx)
                    event.accept()
                    return
            self._selection_box_start = scene_pos
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        mid = getattr(Qt, "MiddleButton", None) or Qt.MidButton
        if event.button() == mid:
            self._panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._selection_box_start is not None:
            scene_pos = self.mapToScene(event.pos())
            x1, y1 = self._selection_box_start.x(), self._selection_box_start.y()
            x2, y2 = scene_pos.x(), scene_pos.y()
            if abs(x2 - x1) > 2 and abs(y2 - y1) > 2:
                r = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
                is_window = x2 > x1
                if is_window:
                    items_in = self._scene.items(r, Qt.ContainsItemShape)
                else:
                    items_in = self._scene.items(r, Qt.IntersectsItemShape)
                selected = []
                seen = set()
                for it in items_in:
                    data = it.data(Qt.UserRole)
                    if data:
                        e_type, idx = data
                        key = (e_type, idx)
                        if key not in seen:
                            seen.add(key)
                            selected.append(key)
                add = event.modifiers() & Qt.ControlModifier
                self.selectionBoxFinished.emit(selected, bool(add))
            if self._selection_box_item:
                try:
                    self._scene.removeItem(self._selection_box_item)
                except RuntimeError:
                    pass
            self._selection_box_item = None
            self._selection_box_start = None
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning:
            pos = QPointF(event.pos())
            delta = pos - self._pan_start
            self._pan_start = pos
            self.translate(delta.x() * -1, delta.y() * -1)
            event.accept()
            return

        if self._selection_box_start is not None:
            scene_pos = self.mapToScene(event.pos())
            x1, y1 = self._selection_box_start.x(), self._selection_box_start.y()
            x2, y2 = scene_pos.x(), scene_pos.y()
            r = QRectF(min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            if not self._selection_box_item:
                self._selection_box_item = QGraphicsRectItem(r)
                pen = QPen(QColor("#4FC3F7"))
                pen.setStyle(Qt.DashLine)
                pen.setWidthF(2.0)
                self._selection_box_item.setPen(pen)
                self._selection_box_item.setBrush(QBrush(Qt.NoBrush))
                self._selection_box_item.setZValue(10000)
                self._scene.addItem(self._selection_box_item)
            else:
                self._selection_box_item.setRect(r)
            event.accept()
            return

        scene_pos = self.mapToScene(event.pos())
        snap_point = None
        snap_label = None
        if self._snap_enabled:
            snap_point, snap_label = self._find_snap_point(scene_pos)
            if snap_point and snap_label is None:
                snap_label = self._classify_snap(snap_point)

        if snap_point:
            self._show_snap_marker(snap_point, snap_label or "E")
            self.cursorMoved.emit(snap_point[0], -snap_point[1], True)
            if snap_label:
                self._show_snap_label(snap_label, snap_point)
        else:
            if self._snap_marker:
                try:
                    if self._is_scene_item_valid(self._snap_marker):
                        self._scene.removeItem(self._snap_marker)
                except RuntimeError:
                    pass
                self._snap_marker = None
                self._snap_marker_label = None
            self._hide_snap_label()
            self.cursorMoved.emit(scene_pos.x(), -scene_pos.y(), False)

        super().mouseMoveEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta().y()
        if delta > 0:
            self._apply_zoom(1.15)
        else:
            self._apply_zoom(1 / 1.15)

    def _classify_snap(self, p: Tuple[float, float]) -> str:
        if "C" in self._snap_types:
            for center, _ in self._snap_circles:
                if abs(p[0] - center[0]) < 1e-3 and abs(p[1] - center[1]) < 1e-3:
                    return "C"
            for center, _, _, _ in self._snap_arcs:
                if abs(p[0] - center[0]) < 1e-3 and abs(p[1] - center[1]) < 1e-3:
                    return "C"
        if "I" in self._snap_types:
            for ip in self._snap_intersections:
                if abs(p[0] - ip[0]) < 1e-3 and abs(p[1] - ip[1]) < 1e-3:
                    return "I"
        if "M" in self._snap_types:
            for mp in self._snap_midpoints:
                if abs(p[0] - mp[0]) < 1e-3 and abs(p[1] - mp[1]) < 1e-3:
                    return "M"
        if "E" in self._snap_types:
            for ep in self._snap_endpoints:
                if abs(p[0] - ep[0]) < 1e-3 and abs(p[1] - ep[1]) < 1e-3:
                    return "E"
        if "N" in self._snap_types:
            return "N"
        return "E"

    def _show_snap_label(self, label: str, pos: Tuple[float, float]) -> None:
        if not hasattr(self, "_snap_text"):
            self._snap_text = QGraphicsTextItem()
            self._snap_text.setDefaultTextColor(QColor("#FF0000"))
            font = QFont()
            font.setPointSize(10)
            font.setBold(True)
            self._snap_text.setFont(font)
            self._scene.addItem(self._snap_text)
        try:
            self._snap_text.setPlainText(label)
            self._snap_text.setPos(pos[0] + 6, pos[1] + 6)
        except RuntimeError:
            if hasattr(self, "_snap_text"):
                del self._snap_text

    def _hide_snap_label(self) -> None:
        if hasattr(self, "_snap_text"):
            try:
                if self._snap_text.scene():
                    self._scene.removeItem(self._snap_text)
            except RuntimeError:
                pass
            try:
                del self._snap_text
            except Exception:
                pass

    def _is_scene_item_valid(self, item) -> bool:
        """Проверка, что объект ещё в сцене (не удалён scene.clear)."""
        if item is None:
            return False
        try:
            return item.scene() is not None
        except RuntimeError:
            return False

    def _show_snap_marker(self, pos: Tuple[float, float], label: str) -> None:
        if not self._is_scene_item_valid(self._snap_marker):
            self._snap_marker = None
        if self._snap_marker is None:
            self._snap_marker = QGraphicsPathItem()
            self._snap_marker.setPen(QPen(QColor("#FF0000")))
            self._scene.addItem(self._snap_marker)
            self._snap_marker_label = None

        if self._snap_marker_label != label:
            self._snap_marker_label = label

        path = self._build_marker_path(label, pos)
        try:
            self._snap_marker.setPath(path)
        except RuntimeError:
            self._snap_marker = None

    def _build_marker_path(self, label: str, pos: Tuple[float, float]) -> QPainterPath:
        x, y = pos
        size = 4.0
        path = QPainterPath()
        if label == "E":
            # Cross
            path.moveTo(x - size, y)
            path.lineTo(x + size, y)
            path.moveTo(x, y - size)
            path.lineTo(x, y + size)
        elif label == "M":
            # Triangle
            path.moveTo(x, y - size)
            path.lineTo(x - size, y + size)
            path.lineTo(x + size, y + size)
            path.closeSubpath()
        elif label == "I":
            # X
            path.moveTo(x - size, y - size)
            path.lineTo(x + size, y + size)
            path.moveTo(x - size, y + size)
            path.lineTo(x + size, y - size)
        elif label == "C":
            # Circle
            path.addEllipse(x - size, y - size, size * 2, size * 2)
        elif label == "N":
            # Diamond (nearest)
            path.moveTo(x, y - size)
            path.lineTo(x + size, y)
            path.lineTo(x, y + size)
            path.lineTo(x - size, y)
            path.closeSubpath()
        elif label == "G":
            # Square (grid)
            path.addRect(x - size, y - size, size * 2, size * 2)
        else:
            path.addEllipse(x - size, y - size, size * 2, size * 2)
        return path
    def set_snap_types(self, types: List[str]) -> None:
        self._snap_types = set(types)
