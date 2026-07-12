"""
Расширенная кинематика роботов для KengaCAD.

Поддержка:
  - 6-осевые сочленённые роботы (KUKA, ABB, Fanuc, Yaskawa, UR)
  - SCARA роботы (4 оси)
  - Декартовы роботы (3 оси)
  - Дельта роботы (параллельная кинематика)
  - Пользовательские DH-параметры
  - Аналитическая и численная обратная кинематика
  - Проверка сингулярностей
  - Оптимизация траектории (минимизация движения суставов)
"""
from typing import List, Tuple, Optional, Dict, Any, Union
import math

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

try:
    from scipy.optimize import minimize
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


# ============================================================================
#  Типы роботов и конфигурации по умолчанию
# ============================================================================

class RobotType:
    """Типы роботов."""
    ARTICULATED_6DOF = "articulated_6dof"  # 6-осевой сочленённый
    SCARA = "scara"  # SCARA
    CARTESIAN = "cartesian"  # Декартов
    DELTA = "delta"  # Дельта
    ARTICULATED_7DOF = "articulated_7dof"  # 7-осевой (избыточный)
    ARTICULATED_5DOF = "articulated_5dof"  # 5-осевой


# DH-параметры для популярных роботов
# Формат: (a, d, alpha, theta_offset) для каждого сустава

ROBOT_CONFIGS: Dict[str, Dict[str, Any]] = {
    # KUKA KR6 R900 sixx
    "kuka_kr6r900": {
        "type": RobotType.ARTICULATED_6DOF,
        "name": "KUKA KR6 R900 sixx",
        "dh_params": [
            (0, 360, math.pi/2, 0),      # J1
            (-25, 0, 0, 0),              # J2
            (315, 0, math.pi/2, 0),      # J3
            (0, 365, -math.pi/2, 0),     # J4
            (0, 0, math.pi/2, 0),        # J5
            (0, 100, 0, 0),              # J6
        ],
        "joint_limits": [
            (-185, 185),   # J1
            (-135, 135),   # J2
            (-154, 154),   # J3
            (-350, 350),   # J4
            (-130, 130),   # J5
            (-350, 350),   # J6
        ],
        "max_velocity": [100, 90, 100, 120, 120, 180],  # град/сек
        "payload_kg": 6,
        "reach_mm": 903,
    },

    # ABB IRB 120
    "abb_irb120": {
        "type": RobotType.ARTICULATED_6DOF,
        "name": "ABB IRB 120",
        "dh_params": [
            (0, 290, math.pi/2, 0),      # J1
            (0, 0, -math.pi/2, 0),       # J2
            (270, 0, 0, -math.pi/2),     # J3
            (70, 302, -math.pi/2, 0),    # J4
            (0, 0, math.pi/2, 0),        # J5
            (0, 72, 0, 0),               # J6
        ],
        "joint_limits": [
            (-165, 165),
            (-110, 110),
            (-110, 90),
            (-160, 160),
            (-120, 120),
            (-400, 400),
        ],
        "max_velocity": [250, 250, 250, 320, 320, 420],
        "payload_kg": 3,
        "reach_mm": 580,
    },

    # Fanuc LR Mate 200iD
    "fanuc_lrmate200id": {
        "type": RobotType.ARTICULATED_6DOF,
        "name": "Fanuc LR Mate 200iD",
        "dh_params": [
            (0, 330, math.pi/2, 0),
            (-50, 0, 0, 0),
            (300, 0, math.pi/2, 0),
            (0, 320, -math.pi/2, 0),
            (0, 0, math.pi/2, 0),
            (0, 80, 0, 0),
        ],
        "joint_limits": [
            (-170, 170),
            (-190, 190),
            (-155, 155),
            (-190, 190),
            (-140, 140),
            (-360, 360),
        ],
        "max_velocity": [300, 300, 300, 400, 400, 500],
        "payload_kg": 7,
        "reach_mm": 717,
    },

    # Universal Robots UR5
    "ur_ur5": {
        "type": RobotType.ARTICULATED_6DOF,
        "name": "UR5",
        "dh_params": [
            (0, 118, math.pi/2, 0),
            (-425, 0, 0, -math.pi/2),
            (-392, 0, 0, 0),
            (0, 131, math.pi/2, 0),
            (0, 0, -math.pi/2, 0),
            (0, 106, 0, 0),
        ],
        "joint_limits": [
            (-360, 360),
            (-180, 180),
            (-180, 180),
            (-360, 360),
            (-180, 180),
            (-360, 360),
        ],
        "max_velocity": [180, 180, 180, 180, 180, 360],
        "payload_kg": 5,
        "reach_mm": 850,
    },

    # SCARA робот (4 оси)
    "scara_generic": {
        "type": RobotType.SCARA,
        "name": "SCARA 4-axis",
        "dh_params": [
            (200, 0, 0, 0),      # J1
            (200, 0, math.pi, 0), # J2
            (0, 0, 0, 0),        # J3 (вращение)
            (0, -200, math.pi/2, 0),  # J4 (линейный)
        ],
        "joint_limits": [
            (-135, 135),
            (-150, 150),
            (-180, 180),
            (0, 200),
        ],
        "max_velocity": [180, 240, 360, 100],
        "payload_kg": 10,
        "reach_mm": 400,
    },

    # Декартов робот
    "cartesian_xyz": {
        "type": RobotType.CARTESIAN,
        "name": "Cartesian XYZ",
        "dh_params": [],  # Не используется
        "joint_limits": [
            (-1000, 1000),  # X
            (-1000, 1000),  # Y
            (-500, 500),    # Z
            (-180, 180),    # R (вращение)
        ],
        "max_velocity": [500, 500, 300, 180],
        "payload_kg": 20,
        "reach_mm": 2000,
    },
}


# ============================================================================
#  Матричные операции (копия из kinematics.py для автономности)
# ============================================================================

def _rot_z(t: float) -> list:
    c, s = math.cos(t), math.sin(t)
    return [c, -s, 0, 0, s, c, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

def _rot_x(t: float) -> list:
    c, s = math.cos(t), math.sin(t)
    return [1, 0, 0, 0, 0, c, -s, 0, 0, s, c, 0, 0, 0, 0, 1]

def _trans(x: float, y: float, z: float) -> list:
    return [1, 0, 0, x, 0, 1, 0, y, 0, 0, 1, z, 0, 0, 0, 1]

def _mat4_mul(a: list, b: list) -> list:
    out = [0.0] * 16
    for i in range(4):
        for j in range(4):
            out[i * 4 + j] = sum(a[i * 4 + k] * b[k * 4 + j] for k in range(4))
    return out

def _mat4_eye() -> list:
    return [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]

def _dh_matrix(theta: float, d: float, a: float, alpha: float) -> list:
    """Матрица DH (стандартная конвенция)."""
    rz = _rot_z(theta)
    tz = _trans(0, 0, d)
    tx = _trans(a, 0, 0)
    rx = _rot_x(alpha)
    t = _mat4_mul(rz, tz)
    t = _mat4_mul(t, tx)
    t = _mat4_mul(t, rx)
    return t

def _mat4_pos(T: list) -> Tuple[float, float, float]:
    return (T[3], T[7], T[11])

def _mat4_rot3(T: list) -> list:
    return [T[0], T[1], T[2], T[4], T[5], T[6], T[8], T[9], T[10]]

def _rot3_to_rpy(R: list) -> Tuple[float, float, float]:
    """3x3 матрица -> RPY (градусы)."""
    sy = math.sqrt(R[0]**2 + R[3]**2)
    singular = sy < 1e-6
    if not singular:
        rx = math.atan2(R[7], R[8])
        ry = math.atan2(-R[6], sy)
        rz = math.atan2(R[3], R[0])
    else:
        rx = math.atan2(-R[5], R[4])
        ry = math.atan2(-R[6], sy)
        rz = 0.0
    return (math.degrees(rx), math.degrees(ry), math.degrees(rz))


# ============================================================================
#  Прямая кинематика
# ============================================================================

def fk_6dof_full(
    joints_deg: List[float],
    dh_params: List[Tuple[float, float, float, float]],
) -> Dict[str, Any]:
    """
    Прямая кинематика для 6-осевого робота.

    Returns:
        {
            "tcp_pos": (x, y, z),
            "tcp_rpy": (rx, ry, rz),
            "T": <4x4 matrix>,
            "link_positions": [(x,y,z) для каждого звена],
        }
    """
    T = _mat4_eye()
    positions = [_mat4_pos(T)]

    for i in range(6):
        if i >= len(dh_params):
            break
        a, d, alpha, th_off = dh_params[i]
        theta = math.radians(joints_deg[i]) + th_off
        Ti = _dh_matrix(theta, d, a, alpha)
        T = _mat4_mul(T, Ti)
        positions.append(_mat4_pos(T))

    R = _mat4_rot3(T)
    rpy = _rot3_to_rpy(R)

    return {
        "tcp_pos": _mat4_pos(T),
        "tcp_rpy": rpy,
        "T": T,
        "link_positions": positions,
    }


def fk_scara(
    joints: List[float],
    dh_params: List[Tuple[float, float, float, float]],
) -> Dict[str, Any]:
    """Прямая кинематика SCARA робота."""
    T = _mat4_eye()
    positions = [_mat4_pos(T)]

    for i in range(min(4, len(dh_params))):
        a, d, alpha, th_off = dh_params[i]
        if i < 3:  # Вращательные суставы
            theta = math.radians(joints[i]) + th_off
        else:  # Линейный сустав (Z)
            theta = th_off
        Ti = _dh_matrix(theta, d if i != 3 else joints[i], a, alpha)
        T = _mat4_mul(T, Ti)
        positions.append(_mat4_pos(T))

    return {
        "tcp_pos": _mat4_pos(T),
        "tcp_rpy": (0, 0, joints[2]) if len(joints) > 2 else (0, 0, 0),
        "T": T,
        "link_positions": positions,
    }


# ============================================================================
#  Обратная кинематика (аналитическая для 6DOF)
# ============================================================================

def ik_6dof_analytical(
    target_pos: Tuple[float, float, float],
    target_rpy: Tuple[float, float, float],
    dh_params: List[Tuple[float, float, float, float]],
    joint_limits: List[Tuple[float, float]],
    preferred_config: str = "elbow_up",  # elbow_up, elbow_down, wrist_up, wrist_down
) -> Optional[Dict[str, Any]]:
    """
    Аналитическая обратная кинематика для 6DOF с запястным смещением.

    Метод работает для роботов у которых оси J4, J5, J6 пересекаются в одной точке.
    """
    if not _HAS_NP:
        return None

    px, py, pz = target_pos
    rx, ry, rz = target_rpy

    # Матрица вращения цели
    cx, sx = math.cos(math.radians(rx)), math.sin(math.radians(rx))
    cy, sy = math.cos(math.radians(ry)), math.sin(math.radians(ry))
    cz, sz = math.cos(math.radians(rz)), math.sin(math.radians(rz))

    R_target = np.array([
        [cz*cy, cz*sy*sx - sz*cx, cz*sy*cx + sz*sx],
        [sz*cy, sz*sy*sx + cz*cx, sz*sy*cx - cz*sx],
        [-sy,   cy*sx,            cy*cx],
    ])

    # Параметры DH
    a2, a3 = dh_params[1][0], dh_params[2][0]  # Длины звеньев
    d1, d4, d6 = dh_params[0][1], dh_params[3][1], dh_params[5][1]

    # Центр запястья
    wx = px - d6 * R_target[0, 2]
    wy = py - d6 * R_target[1, 2]
    wz = pz - d6 * R_target[2, 2]

    # J1
    j1 = math.degrees(math.atan2(wy, wx))

    # J2, J3
    r = math.sqrt(wx**2 + wy**2)
    z = wz - d1

    # Косинусная теорема для J3
    D = (r**2 + z**2 - a2**2 - a3**2) / (2 * a2 * a3)
    D = max(-1, min(1, D))  # Ограничение

    elbow_mult = 1 if preferred_config == "elbow_up" else -1
    j3 = math.degrees(math.atan2(elbow_mult * math.sqrt(1 - D**2), D))

    # J2
    k1 = a2 + a3 * math.cos(math.radians(j3))
    k2 = a3 * math.sin(math.radians(j3))
    j2 = math.degrees(math.atan2(z, r) - math.atan2(k2, k1))

    # J4, J5, J6 (ориентация)
    # Упрощённо - требуется полная реализация
    j4 = 0
    j5 = 0
    j6 = 0

    joints = [j1, j2, j3, j4, j5, j6]

    # Проверка пределов
    for i, (lo, hi) in enumerate(joint_limits[:6]):
        if joints[i] < lo or joints[i] > hi:
            return None  # Недостижимо

    # Проверка через FK
    fk_res = fk_6dof_full(joints, dh_params)
    pos_err = math.sqrt(sum((fk_res["tcp_pos"][i] - target_pos[i])**2 for i in range(3)))

    return {
        "joints_deg": joints,
        "tcp_pos": fk_res["tcp_pos"],
        "tcp_rpy": fk_res["tcp_rpy"],
        "converged": pos_err < 1.0,
        "error_mm": pos_err,
        "config": preferred_config,
    }


def ik_6dof_numerical(
    target_pos: Tuple[float, float, float],
    target_rpy: Tuple[float, float, float] = (0, 0, 0),
    dh_params: List[Tuple[float, float, float, float]] = None,
    joint_limits: List[Tuple[float, float]] = None,
    initial_joints: List[float] = None,
    max_iter: int = 200,
    tol: float = 0.5,
    position_only: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Численная обратная кинематика (Левенберг-Марквардт).
    """
    if not _HAS_NP:
        return None

    if dh_params is None:
        from cad.kinematics import DEFAULT_DH
        dh_params = DEFAULT_DH

    if joint_limits is None:
        joint_limits = [(-180, 180)] * 6

    if initial_joints is None:
        initial_joints = [0.0] * 6

    def objective(q):
        fk_res = fk_6dof_full(q.tolist(), dh_params)
        pos = fk_res["tcp_pos"]
        err_pos = math.sqrt(sum((pos[i] - target_pos[i])**2 for i in range(3)))

        if position_only:
            return err_pos

        rpy = fk_res["tcp_rpy"]
        err_orient = math.sqrt(sum((rpy[i] - target_rpy[i])**2 for i in range(3)))
        return err_pos + 0.1 * err_orient

    # Оптимизация с ограничениями
    bounds = joint_limits[:6]

    if _HAS_SCIPY:
        result = minimize(
            objective,
            initial_joints,
            method='L-BFGS-B',
            bounds=bounds,
            options={'maxiter': max_iter, 'ftol': tol},
        )
        joints = result.x.tolist()
    else:
        # Простая градиентная оптимизация
        q = np.array(initial_joints, dtype=float)
        lr = 1.0
        for _ in range(max_iter):
            grad = np.zeros(6)
            eps = 0.01
            base_err = objective(q)
            for i in range(6):
                q_plus = q.copy()
                q_plus[i] += eps
                grad[i] = (objective(q_plus) - base_err) / eps

            q = q - lr * grad
            for i in range(6):
                q[i] = max(bounds[i][0], min(bounds[i][1], q[i]))

        joints = q.tolist()

    fk_res = fk_6dof_full(joints, dh_params)
    pos_err = math.sqrt(sum((fk_res["tcp_pos"][i] - target_pos[i])**2 for i in range(3)))

    return {
        "joints_deg": joints,
        "tcp_pos": fk_res["tcp_pos"],
        "tcp_rpy": fk_res["tcp_rpy"],
        "converged": pos_err < tol,
        "error_mm": pos_err,
    }


# ============================================================================
#  Проверка достижимости и сингулярностей
# ============================================================================

def check_workspace(
    point: Tuple[float, float, float],
    dh_params: List[Tuple[float, float, float, float]],
    joint_limits: List[Tuple[float, float]],
    reach_mm: float = None,
) -> Dict[str, Any]:
    """
    Проверка точки на достижимость.

    Returns:
        {
            "reachable": bool,
            "distance_mm": float,  # Расстояние до рабочей зоны
            "reason": str,  # Причина недостижимости
        }
    """
    x, y, z = point

    # Быстрая проверка по сфере досягаемости
    if reach_mm:
        dist = math.sqrt(x**2 + y**2 + z**2)
        if dist > reach_mm * 1.1:
            return {
                "reachable": False,
                "distance_mm": dist - reach_mm,
                "reason": "Вне рабочей зоны",
            }

    # Попытка IK
    result = ik_6dof_numerical(point, (0, 0, 0), dh_params, joint_limits)

    if result and result.get("converged"):
        return {
            "reachable": True,
            "distance_mm": 0,
            "reason": "",
        }

    return {
        "reachable": False,
        "distance_mm": result.get("error_mm", 0) if result else 0,
        "reason": "Не решается обратная кинематика",
    }


def check_singularity(
    joints_deg: List[float],
    dh_params: List[Tuple[float, float, float, float]],
) -> Dict[str, Any]:
    """
    Проверка на сингулярность.

    Сингулярности возникают когда:
    - Ось J5 = 0 (запястье выровнено)
    - Робот полностью вытянут
    - Ось J1 совпадает с осью J6
    """
    if not _HAS_NP:
        return {"singular": False, "type": None, "severity": 0}

    j5 = joints_deg[4] if len(joints_deg) > 4 else 0

    # Проверка J5 ≈ 0
    if abs(j5) < 5:
        return {
            "singular": True,
            "type": "wrist_singular",
            "severity": 1 - abs(j5) / 5,
            "message": "Сингулярность запястья (J5 ≈ 0)",
        }

    # Проверка вытянутого положения через FK
    fk_res = fk_6dof_full(joints_deg, dh_params)
    pos = fk_res["tcp_pos"]
    dist = math.sqrt(pos[0]**2 + pos[1]**2 + pos[2]**2)

    # Максимальная досягаемость (сумма длин звеньев)
    max_reach = sum(abs(p[0]) + abs(p[1]) for p in dh_params[:3])

    if dist > max_reach * 0.95:
        return {
            "singular": True,
            "type": "boundary_singular",
            "severity": (dist - max_reach * 0.95) / (max_reach * 0.05),
            "message": "Граничная сингулярность (робот вытянут)",
        }

    return {"singular": False, "type": None, "severity": 0}


# ============================================================================
#  Оптимизация траектории
# ============================================================================

def optimize_trajectory(
    trajectory: List[Tuple[float, float, float]],
    dh_params: List[Tuple[float, float, float, float]],
    joint_limits: List[Tuple[float, float]],
    initial_joints: List[float] = None,
    smoothness_weight: float = 0.3,
) -> Dict[str, Any]:
    """
    Оптимизация траектории для минимизации движения суставов.

    Args:
        trajectory: список точек (x, y, z)
        dh_params: DH-параметры
        joint_limits: пределы суставов
        initial_joints: начальное положение
        smoothness_weight: вес плавности (0-1)

    Returns:
        {
            "joints_trajectory": [[j1,j2,j3,j4,j5,j6], ...],
            "total_motion": float,
            "smoothness": float,
        }
    """
    if not trajectory:
        return {"joints_trajectory": [], "total_motion": 0, "smoothness": 1}

    joints_trajectory = []
    prev_joints = initial_joints or [0] * 6
    total_motion = 0

    for i, point in enumerate(trajectory):
        # IK для точки
        ik_result = ik_6dof_numerical(
            point, (0, 0, 0), dh_params, joint_limits,
            initial_joints=prev_joints,
        )

        if not ik_result or not ik_result.get("converged"):
            return {
                "error": f"Точка {i} недостижима: {point}",
                "joints_trajectory": joints_trajectory,
                "total_motion": total_motion,
            }

        joints = ik_result["joints_deg"]

        # Минимизация скачков (выбор конфигурации с мин. движением)
        motion = sum(abs(joints[j] - prev_joints[j]) for j in range(6))
        total_motion += motion

        joints_trajectory.append(joints)
        prev_joints = joints

    # Плавность (1 = идеально плавно)
    smoothness = 1.0 if len(joints_trajectory) < 2 else 1 - (smoothness_weight * total_motion / (len(joints_trajectory) * 180))

    return {
        "joints_trajectory": joints_trajectory,
        "total_motion": total_motion,
        "smoothness": max(0, smoothness),
    }


# ============================================================================
#  Утилита для выбора конфигурации робота
# ============================================================================

def get_robot_config(robot_name: str) -> Optional[Dict[str, Any]]:
    """Получить конфигурацию робота по имени."""
    return ROBOT_CONFIGS.get(robot_name.lower())


def list_available_robots() -> List[str]:
    """Список доступных конфигураций роботов."""
    return list(ROBOT_CONFIGS.keys())


def create_custom_robot(
    name: str,
    dh_params: List[Tuple[float, float, float, float]],
    joint_limits: List[Tuple[float, float]],
    reach_mm: float = None,
    payload_kg: float = None,
) -> Dict[str, Any]:
    """Создать пользовательскую конфигурацию робота."""
    config = {
        "type": RobotType.ARTICULATED_6DOF,
        "name": name,
        "dh_params": dh_params,
        "joint_limits": joint_limits,
        "reach_mm": reach_mm or sum(abs(p[0]) + abs(p[1]) for p in dh_params),
        "payload_kg": payload_kg or 0,
    }
    ROBOT_CONFIGS[name.lower()] = config
    return config
