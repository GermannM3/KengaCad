"""
3D-сцена с загрузкой модели робота (GLB/glTF) и траектории — через PyVista.
Fallback: загрузка GLB через trimesh с конвертацией в PyVista (Context7).
Если pyvistaqt недоступен, показывается заглушка.
"""
from pathlib import Path
from typing import Optional, List, Tuple
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt5.QtCore import Qt

from cad.kinematics import fk_full

_plotter = None


def _flatten_meshes(obj, out: list):
    """Рекурсивно собрать все меши из MultiBlock в список."""
    try:
        import pyvista as pv
    except ImportError:
        return
    if hasattr(obj, "n_blocks"):
        for i in range(obj.n_blocks):
            _flatten_meshes(obj[i], out)
    elif isinstance(obj, (pv.PolyData, pv.UnstructuredGrid, pv.StructuredGrid)):
        out.append(obj)


def _trimesh_to_pyvista(tm):
    """Конвертировать trimesh в PyVista PolyData (Context7: vertices, faces)."""
    try:
        import pyvista as pv
        import numpy as np
    except ImportError:
        return None
    if not hasattr(tm, "vertices") or not hasattr(tm, "faces"):
        return None
    verts = np.asarray(tm.vertices, dtype=np.float64)
    faces_np = np.asarray(tm.faces, dtype=np.int64)
    if faces_np.size == 0:
        return pv.PolyData(verts)
    n_faces = len(faces_np)
    cells = np.hstack([np.full((n_faces, 1), 3), faces_np]).flatten()
    return pv.PolyData(verts, cells)


def _load_glb_trimesh(path: str) -> list:
    """Загрузить GLB/glTF через trimesh, вернуть список PyVista PolyData."""
    try:
        import trimesh
        import numpy as np
    except ImportError:
        return []
    path = Path(path)
    if not path.exists():
        return []
    out = []
    try:
        obj = trimesh.load(str(path))
        if obj is None:
            return out
        if isinstance(obj, trimesh.Scene):
            for geom in obj.geometry.values():
                pv_m = _trimesh_to_pyvista(geom)
                if pv_m is not None:
                    out.append(pv_m)
            return out
        pv_m = _trimesh_to_pyvista(obj)
        if pv_m is not None:
            out.append(pv_m)
    except Exception:
        pass
    return out


def _load_glb_meshes(path: str) -> list:
    """Загрузить GLB/glTF: сначала PyVista, при неудаче — trimesh (Context7)."""
    try:
        import pyvista as pv
    except ImportError:
        return _load_glb_trimesh(path)
    path = Path(path)
    if not path.exists():
        return []
    meshes = []
    try:
        data = pv.read(str(path))
        _flatten_meshes(data, meshes)
    except Exception:
        pass
    if not meshes:
        meshes = _load_glb_trimesh(path)
    return meshes


class View3DScene(QWidget):
    """
    Виджет 3D-сцены: робот (GLB) + траектория.
    Требует pyvista и pyvistaqt. Без них — заглушка с подсказкой.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 150)
        self.setStyleSheet("background-color: #1e1e1e; border: 1px solid #444;")
        self._plotter = None
        self._frame = None
        self._traj_actor = None
        self._robot_bbox = None  # (min_xyz, max_xyz) после загрузки робота
        self._workcell_boxes = []  # [{"id", "min", "max", "color"}, ...] для столов/оснастки
        self._wireframe_actors = []  # actors for FK wireframe robot rendering
        self._setup()

    def _setup(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        _import_err = None
        try:
            import pyvista as pv
            from pyvistaqt import QtInteractor
        except Exception as _exc:
            _import_err = str(_exc)
            import traceback as _tb
            _import_err += "\n\n" + _tb.format_exc()
        if _import_err is not None:
            self._placeholder = QLabel(
                "3D-сцена недоступна\n\n"
                f"Ошибка: {_import_err[:600]}"
            )
            self._placeholder.setAlignment(Qt.AlignCenter)
            self._placeholder.setStyleSheet("color: #c66; padding: 16px; font-size: 10px;")
            self._placeholder.setWordWrap(True)
            layout.addWidget(self._placeholder)
            return
        self._frame = QFrame()
        self._frame.setStyleSheet("background: #1e1e1e;")
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        self._plotter = QtInteractor(self._frame)
        self._plotter.set_background("#1e1e1e")
        frame_layout.addWidget(self._plotter.interactor)
        layout.addWidget(self._frame)
        self._plotter.view_isometric()
        self._plotter.add_axes()

    def load_mesh(self, path: str) -> bool:
        """Загрузить модель робота (GLB/glTF)."""
        if self._plotter is None:
            return False
        path = Path(path)
        if not path.exists():
            return False
        meshes = _load_glb_meshes(str(path))
        if not meshes:
            return False
        try:
            self._plotter.clear()
            self._plotter.add_axes()
            all_bounds = []
            for mesh in meshes:
                self._plotter.add_mesh(mesh, color="#4a9eff", smooth_shading=True)
                b = mesh.bounds
                if b is not None and len(b) >= 6:
                    all_bounds.append((b[0], b[2], b[4]))
                    all_bounds.append((b[1], b[3], b[5]))
            if all_bounds:
                import numpy as np
                arr = np.array(all_bounds)
                self._robot_bbox = (arr.min(axis=0).tolist(), arr.max(axis=0).tolist())
            else:
                self._robot_bbox = None
            self._redraw_workcell_boxes()
            self._plotter.reset_camera()
            self._plotter.view_isometric()
        except Exception:
            self._robot_bbox = None
            return False
        return True

    def _redraw_workcell_boxes(self) -> None:
        """Отрисовать все столы/оснастку из _workcell_boxes."""
        if self._plotter is None:
            return
        try:
            import pyvista as pv
        except ImportError:
            return
        for box in self._workcell_boxes:
            min_xyz = box.get("min", [0, 0, 0])
            max_xyz = box.get("max", [1, 1, 1])
            cx = (min_xyz[0] + max_xyz[0]) / 2
            cy = (min_xyz[1] + max_xyz[1]) / 2
            cz = (min_xyz[2] + max_xyz[2]) / 2
            sx = max(1e-3, max_xyz[0] - min_xyz[0])
            sy = max(1e-3, max_xyz[1] - min_xyz[1])
            sz = max(1e-3, max_xyz[2] - min_xyz[2])
            solid = pv.Box(bounds=(min_xyz[0], max_xyz[0], min_xyz[1], max_xyz[1], min_xyz[2], max_xyz[2]))
            self._plotter.add_mesh(solid, color=box.get("color", "#6b6b6b"), smooth_shading=True)
        return

    def add_trimesh_object(self, id_: str, tm_mesh, color: str = "#8bc34a", name: str = "") -> bool:
        """Добавить trimesh.Trimesh объект в 3D-сцену (STEP/IGES импорт).

        Возвращает True при успешном добавлении.
        """
        if self._plotter is None:
            return False
        pv_mesh = _trimesh_to_pyvista(tm_mesh)
        if pv_mesh is None:
            return False
        try:
            self._plotter.add_mesh(pv_mesh, color=color, smooth_shading=True)
            # Сохраняем bounding box для collision-проверок
            b = pv_mesh.bounds
            if b is not None and len(b) >= 6:
                self._workcell_boxes.append({
                    "id": id_,
                    "min": [b[0], b[2], b[4]],
                    "max": [b[1], b[3], b[5]],
                    "color": color,
                })
            self._plotter.reset_camera()
            return True
        except Exception:
            return False

    def add_workcell_box(self, id_: str, min_xyz: list, max_xyz: list, color: str = "#6b6b6b") -> None:
        """Добавить бокс в рабочую ячейку (стол, оснастка, ограждение)."""
        self._workcell_boxes.append({"id": id_, "min": list(min_xyz), "max": list(max_xyz), "color": color})
        if self._plotter is not None:
            try:
                import pyvista as pv
                solid = pv.Box(bounds=(min_xyz[0], max_xyz[0], min_xyz[1], max_xyz[1], min_xyz[2], max_xyz[2]))
                self._plotter.add_mesh(solid, color=color, smooth_shading=True)
            except Exception:
                pass

    def set_trajectory(self, points: list) -> None:
        """Нарисовать траекторию линией (список (x,y,z))."""
        if self._plotter is None or not points:
            return
        try:
            import pyvista as pv
            import numpy as np
        except ImportError:
            return
        if len(points) < 2:
            return
        pts = np.array([[float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0] for p in points])
        poly = pv.lines_from_points(pts)
        if self._traj_actor is not None:
            try:
                self._plotter.remove_actor(self._traj_actor)
            except Exception:
                pass
        self._traj_actor = self._plotter.add_mesh(poly, color="#ffc850", line_width=3, render_lines_as_tubes=True)
        self._plotter.reset_camera()

    def get_robot_bbox(self) -> Optional[tuple]:
        """Возвращает (min_xyz, max_xyz) робота после load_mesh или None."""
        return self._robot_bbox

    # ------------------------------------------------------------------
    #  Wireframe robot rendering based on FK link positions
    # ------------------------------------------------------------------

    def draw_robot_wireframe(
        self,
        link_positions: List[Tuple[float, float, float]],
        joint_radii: Optional[List[float]] = None,
    ) -> None:
        """
        Draw the robot as coloured cylinders + joint spheres from FK positions.

        Args:
            link_positions: 7 positions [(x,y,z), ...] — base through TCP.
            joint_radii: optional per-joint sphere radii (len == len(link_positions)).
                         If *None*, a default radius is computed from link lengths.
        """
        if self._plotter is None:
            return
        try:
            import pyvista as pv
            import numpy as np
        except ImportError:
            return

        # --- clear previous wireframe ---------------------------------
        for actor in self._wireframe_actors:
            try:
                self._plotter.remove_actor(actor)
            except Exception:
                pass
        self._wireframe_actors = []

        if not link_positions or len(link_positions) < 2:
            return

        pts = [np.array(p, dtype=float) for p in link_positions]

        # Compute a sensible default radius from the average link length
        link_lens = [float(np.linalg.norm(pts[i + 1] - pts[i]))
                     for i in range(len(pts) - 1)]
        avg_len = max(np.mean(link_lens), 1.0)
        default_cyl_radius = avg_len * 0.06
        default_sphere_radius = avg_len * 0.10

        if joint_radii is None:
            joint_radii = [default_sphere_radius] * len(pts)

        # Colours: base=gray, then alternating blue/orange, TCP=red
        n_links = len(pts) - 1
        cyl_colors: list = []
        for i in range(n_links):
            if i == 0:
                cyl_colors.append("#888888")        # base link — gray
            elif i == n_links - 1:
                cyl_colors.append("#e04040")        # last link to TCP — red
            elif i % 2 == 1:
                cyl_colors.append("#4a9eff")        # blue
            else:
                cyl_colors.append("#ff9f40")        # orange

        sphere_colors: list = []
        for i in range(len(pts)):
            if i == 0:
                sphere_colors.append("#888888")     # base joint — gray
            elif i == len(pts) - 1:
                sphere_colors.append("#e04040")     # TCP — red
            elif i % 2 == 1:
                sphere_colors.append("#4a9eff")     # blue
            else:
                sphere_colors.append("#ff9f40")     # orange

        # --- draw cylinders between consecutive positions -------------
        for i in range(n_links):
            seg_len = link_lens[i]
            if seg_len < 1e-6:
                continue  # skip zero-length segments
            center = (pts[i] + pts[i + 1]) / 2.0
            direction = pts[i + 1] - pts[i]
            cyl = pv.Cylinder(
                center=center.tolist(),
                direction=direction.tolist(),
                radius=default_cyl_radius,
                height=seg_len,
                resolution=20,
                capping=True,
            )
            actor = self._plotter.add_mesh(
                cyl, color=cyl_colors[i], smooth_shading=True,
            )
            self._wireframe_actors.append(actor)

        # --- draw spheres at each joint / TCP -------------------------
        for i, pt in enumerate(pts):
            radius = joint_radii[i] if i < len(joint_radii) else default_sphere_radius
            sphere = pv.Sphere(radius=radius, center=pt.tolist())
            actor = self._plotter.add_mesh(
                sphere, color=sphere_colors[i], smooth_shading=True,
            )
            self._wireframe_actors.append(actor)

    def update_robot_pose(
        self,
        joints_deg: List[float],
        dh_params=None,
    ) -> Optional[Tuple[float, float, float]]:
        """
        Compute FK and redraw the wireframe robot in the 3-D scene.

        Args:
            joints_deg: 6 joint angles in degrees.
            dh_params: optional DH parameter table (defaults to DEFAULT_DH).

        Returns:
            TCP position (x, y, z) or *None* when pyvista is unavailable.
        """
        if self._plotter is None:
            return None
        try:
            import pyvista as pv  # noqa: F401 — guard for availability
        except ImportError:
            return None

        fk_result = fk_full(joints_deg, dh_params)
        link_positions = fk_result["link_positions"]
        self.draw_robot_wireframe(link_positions)

        self._plotter.reset_camera()
        return fk_result["tcp_pos"]

    # ------------------------------------------------------------------

    def clear(self) -> None:
        """Очистить сцену."""
        self._robot_bbox = None
        self._workcell_boxes = []
        # Remove wireframe actors
        for actor in self._wireframe_actors:
            try:
                self._plotter.remove_actor(actor)
            except Exception:
                pass
        self._wireframe_actors = []
        if self._plotter is not None:
            try:
                self._plotter.clear()
                self._plotter.add_axes()
                self._traj_actor = None
            except Exception:
                pass
