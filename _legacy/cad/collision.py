"""
Проверка коллизий для KengaCAD.

• check_collisions_local()  — классическая AABB / сфера (траектория-точки vs примитивы)
• check_collisions_mesh()   — mesh-based: траекторная «труба» vs trimesh-объекты
• check_self_collision()    — коллизии между звеньями робота (не-соседними)
"""
from typing import List, Dict, Any, Optional, Tuple
import math

# ---------------------------------------------------------------------------
#  Проверка доступности trimesh.collision
# ---------------------------------------------------------------------------
_TRIMESH_COLLISION_AVAILABLE = False
try:
    import trimesh
    import trimesh.collision
    import numpy as np
    _TRIMESH_COLLISION_AVAILABLE = True
except ImportError:
    try:
        import numpy as np
    except ImportError:
        np = None  # type: ignore[assignment]


# ===================================================================
#  1. Классическая AABB / сфера (старый API — полная обратная совместимость)
# ===================================================================

def _point_in_aabb(p: list, min_xyz: list, max_xyz: list, margin: float = 0.0) -> bool:
    if margin:
        min_xyz = [a - margin for a in min_xyz]
        max_xyz = [a + margin for a in max_xyz]
    return (
        min_xyz[0] <= p[0] <= max_xyz[0]
        and min_xyz[1] <= p[1] <= max_xyz[1]
        and min_xyz[2] <= p[2] <= max_xyz[2]
    )


def _point_in_sphere(p: list, center: list, radius: float, margin: float = 0.0) -> bool:
    r = radius + margin
    dx = p[0] - center[0]
    dy = p[1] - center[1]
    dz = p[2] - center[2]
    return dx * dx + dy * dy + dz * dz <= r * r


def check_collisions_local(
    trajectory_points: List[List[float]],
    obstacles: List[Dict[str, Any]],
    margin: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Проверка коллизий траектории с препятствиями (AABB / сфера).

    trajectory_points: список [x, y, z] (или [x, y] с z=0).
    obstacles: список {"id": str, "type": "aabb"|"sphere",
        "min"/"max" для aabb, "center"/"radius" для sphere}.

    Возвращает список {"step": int, "point": [x,y,z], "object_a": "trajectory", "object_b": id}.
    """
    if not trajectory_points or not obstacles:
        return []
    collisions: List[Dict[str, Any]] = []
    for step, pt in enumerate(trajectory_points):
        x, y = float(pt[0]), float(pt[1])
        z = float(pt[2]) if len(pt) > 2 else 0.0
        p = [x, y, z]
        for obs in obstacles:
            oid = obs.get("id", "obstacle")
            if obs.get("type") == "aabb":
                min_xyz = obs.get("min", [0, 0, 0])
                max_xyz = obs.get("max", [0, 0, 0])
                if _point_in_aabb(p, min_xyz, max_xyz, margin):
                    collisions.append({
                        "step": step,
                        "point": p,
                        "object_a": "trajectory",
                        "object_b": oid,
                    })
            elif obs.get("type") == "sphere":
                center = obs.get("center", [0, 0, 0])
                radius = float(obs.get("radius", 0))
                if _point_in_sphere(p, center, radius, margin):
                    collisions.append({
                        "step": step,
                        "point": p,
                        "object_a": "trajectory",
                        "object_b": oid,
                    })
    return collisions


# ===================================================================
#  2. Mesh-based коллизии (trimesh.collision.CollisionManager)
# ===================================================================

def _build_trajectory_tube(
    trajectory_points: List,
    tube_radius: float = 5.0,
    segments: int = 8,
) -> "Optional[trimesh.Trimesh]":
    """
    Построить «трубу» (swept cylinder) вдоль траектории.

    Возвращает trimesh.Trimesh или None при ошибке.
    """
    if not _TRIMESH_COLLISION_AVAILABLE:
        return None
    if len(trajectory_points) < 2:
        return None

    try:
        pts = np.array(
            [[float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0]
             for p in trajectory_points],
            dtype=np.float64,
        )
        # Создаём Path3D → extrude в трубу
        # trimesh.creation.sweep_polygon — если доступен
        # Запасной вариант: набор цилиндров между точками
        meshes = []
        for i in range(len(pts) - 1):
            seg = trimesh.creation.cylinder(
                radius=tube_radius,
                segment=np.vstack([pts[i], pts[i + 1]]),
                sections=segments,
            )
            meshes.append(seg)
        if not meshes:
            return None
        combined = trimesh.util.concatenate(meshes)
        return combined
    except Exception as e:
        print(f"collision: ошибка построения trajectory tube: {e}")
        return None


def _mesh_aabb(mesh: "trimesh.Trimesh") -> Tuple[list, list]:
    """AABB для trimesh.Trimesh → (min_xyz, max_xyz)."""
    bounds = mesh.bounds  # [[min_x, min_y, min_z], [max_x, max_y, max_z]]
    return bounds[0].tolist(), bounds[1].tolist()


def _aabb_overlap(a_min: list, a_max: list, b_min: list, b_max: list) -> bool:
    """Пересечение двух AABB (быстрая проверка)."""
    return (
        a_min[0] <= b_max[0] and a_max[0] >= b_min[0]
        and a_min[1] <= b_max[1] and a_max[1] >= b_min[1]
        and a_min[2] <= b_max[2] and a_max[2] >= b_min[2]
    )


def check_collisions_mesh(
    meshes: List[Dict[str, Any]],
    trajectory_points: List,
    tube_radius: float = 5.0,
    margin: float = 0.0,
) -> List[Dict[str, Any]]:
    """
    Mesh-based проверка: траекторная «труба» vs список mesh-объектов.

    meshes:  [{"name": str, "mesh": trimesh.Trimesh}, ...]
    trajectory_points: список [x, y, z]
    tube_radius: радиус трубы вокруг траектории (мм)
    margin: дополнительный зазор (мм) — расширяет tube_radius

    Возвращает список:
        {"object": name, "in_collision": True, "method": "mesh"|"aabb_fallback"}
    """
    if not trajectory_points or not meshes:
        return []

    effective_radius = tube_radius + margin
    results: List[Dict[str, Any]] = []

    # --- Попытка использовать trimesh CollisionManager ---
    if _TRIMESH_COLLISION_AVAILABLE:
        tube = _build_trajectory_tube(trajectory_points, effective_radius)
        if tube is not None:
            try:
                manager = trimesh.collision.CollisionManager()
                manager.add_object("trajectory_tube", tube)
                for item in meshes:
                    name = item.get("name", "unknown")
                    mesh_obj = item.get("mesh")
                    if mesh_obj is None:
                        continue
                    is_collision, _contacts = manager.in_collision_single(
                        mesh_obj, return_names=True, return_data=False,
                    )
                    results.append({
                        "object": name,
                        "in_collision": is_collision,
                        "method": "mesh",
                    })
                return results
            except Exception as e:
                print(f"collision: trimesh CollisionManager ошибка, "
                      f"fallback на AABB: {e}")

    # --- Fallback: AABB-based проверка ---
    # Строим AABB «трубы» из точек траектории ± effective_radius
    if np is not None and trajectory_points:
        pts = np.array(
            [[float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0]
             for p in trajectory_points],
            dtype=np.float64,
        )
        traj_min = pts.min(axis=0) - effective_radius
        traj_max = pts.max(axis=0) + effective_radius
        traj_min_l = traj_min.tolist()
        traj_max_l = traj_max.tolist()
    else:
        # Без numpy — ручной min/max
        xs = [float(p[0]) for p in trajectory_points]
        ys = [float(p[1]) for p in trajectory_points]
        zs = [float(p[2]) if len(p) > 2 else 0.0 for p in trajectory_points]
        traj_min_l = [min(xs) - effective_radius, min(ys) - effective_radius,
                      min(zs) - effective_radius]
        traj_max_l = [max(xs) + effective_radius, max(ys) + effective_radius,
                      max(zs) + effective_radius]

    for item in meshes:
        name = item.get("name", "unknown")
        mesh_obj = item.get("mesh")
        if mesh_obj is None:
            continue
        try:
            m_min, m_max = _mesh_aabb(mesh_obj)
        except Exception:
            continue
        hit = _aabb_overlap(traj_min_l, traj_max_l, m_min, m_max)
        results.append({
            "object": name,
            "in_collision": hit,
            "method": "aabb_fallback",
        })

    return results


# ===================================================================
#  3. Self-collision (коллизии между звеньями робота)
# ===================================================================

def check_self_collision(
    link_meshes: List["trimesh.Trimesh"],
    skip_adjacent: int = 1,
) -> List[Tuple[int, int]]:
    """
    Проверка self-collision между звеньями робота.

    link_meshes: список trimesh.Trimesh — по одному на каждое звено.
    skip_adjacent: сколько соседних звеньев пропускать (по умолчанию 1 —
        соседние звенья всегда «касаются» и не считаются коллизией).

    Возвращает список пар (i, j) индексов звеньев, которые столкнулись.
    """
    if not _TRIMESH_COLLISION_AVAILABLE:
        # Fallback: AABB-проверка
        return _self_collision_aabb(link_meshes, skip_adjacent)

    collisions: List[Tuple[int, int]] = []
    n = len(link_meshes)
    if n < 2:
        return collisions

    try:
        manager = trimesh.collision.CollisionManager()
        for idx, mesh in enumerate(link_meshes):
            if mesh is not None:
                manager.add_object(str(idx), mesh)

        _, pairs = manager.in_collision_internal(return_names=True)
        for name_a, name_b in pairs:
            try:
                i, j = int(name_a), int(name_b)
            except (ValueError, TypeError):
                continue
            if abs(i - j) <= skip_adjacent:
                continue
            collisions.append((min(i, j), max(i, j)))
    except Exception as e:
        print(f"collision: self-collision trimesh ошибка, fallback AABB: {e}")
        return _self_collision_aabb(link_meshes, skip_adjacent)

    return sorted(set(collisions))


def _self_collision_aabb(
    link_meshes: List,
    skip_adjacent: int = 1,
) -> List[Tuple[int, int]]:
    """Fallback self-collision через AABB."""
    collisions: List[Tuple[int, int]] = []
    n = len(link_meshes)
    if n < 2 or np is None:
        return collisions

    bboxes = []
    for mesh in link_meshes:
        if mesh is None or not hasattr(mesh, "bounds"):
            bboxes.append(None)
        else:
            try:
                b = mesh.bounds
                bboxes.append((b[0].tolist(), b[1].tolist()))
            except Exception:
                bboxes.append(None)

    for i in range(n):
        if bboxes[i] is None:
            continue
        for j in range(i + 1, n):
            if bboxes[j] is None:
                continue
            if abs(i - j) <= skip_adjacent:
                continue
            a_min, a_max = bboxes[i]
            b_min, b_max = bboxes[j]
            if _aabb_overlap(a_min, a_max, b_min, b_max):
                collisions.append((i, j))

    return collisions
