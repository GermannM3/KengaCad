"""
Кинематика 6DOF-манипулятора.
  - FK (Денавит-Хартенберг) — позиция + ориентация + координаты звеньев
  - IK (численный, Левенберг-Марквардт) — целевая поза -> углы суставов
  - Проверка достижимости
Без тяжёлых внешних зависимостей (только numpy).
"""
from typing import List, Tuple, Optional, Dict, Any
import math

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

# ---------------------------------------------------------------------------
#  Низкоуровневые 4x4 матрицы (row-major, 16 элементов)
# ---------------------------------------------------------------------------

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

def _dh_link(theta: float, d: float, a: float, alpha: float) -> list:
    """Матрица перехода DH (стандартная конвенция). theta/alpha в радианах."""
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
    """Извлечь 3x3 подматрицу вращения (row-major, 9 элементов)."""
    return [T[0], T[1], T[2],
            T[4], T[5], T[6],
            T[8], T[9], T[10]]

def _rot3_to_rpy(R: list) -> Tuple[float, float, float]:
    """Матрица 3x3 -> Roll-Pitch-Yaw (rx, ry, rz) в градусах (XYZ Euler)."""
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

def _rpy_to_rot3(rx_deg: float, ry_deg: float, rz_deg: float) -> list:
    """RPY (XYZ Euler, в градусах) -> матрица 3x3 (row-major). R = Rz * Ry * Rx."""
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    return [
        cz*cy,              cz*sy*sx - sz*cx,   cz*sy*cx + sz*sx,
        sz*cy,              sz*sy*sx + cz*cx,   sz*sy*cx - cz*sx,
        -sy,                cy*sx,              cy*cx,
    ]

def _rpy_to_mat4(rx_deg: float, ry_deg: float, rz_deg: float,
                 x: float, y: float, z: float) -> list:
    """RPY + позиция -> полная 4x4 матрица."""
    rx = math.radians(rx_deg)
    ry = math.radians(ry_deg)
    rz = math.radians(rz_deg)
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # R = Rz * Ry * Rx
    return [
        cz*cy,              cz*sy*sx - sz*cx,   cz*sy*cx + sz*sx,  x,
        sz*cy,              sz*sy*sx + cz*cx,   sz*sy*cx - cz*sx,  y,
        -sy,                cy*sx,              cy*cx,             z,
        0,                  0,                  0,                 1,
    ]

# ---------------------------------------------------------------------------
#  DH-параметры по умолчанию
# ---------------------------------------------------------------------------

# Каждый элемент: (a_mm, d_mm, alpha_rad, theta_offset_rad)
DEFAULT_DH: List[Tuple[float, float, float, float]] = [
    (75,   330,   math.pi / 2,  0),
    (300,  0,     0,            0),
    (75,   0,     math.pi / 2,  0),
    (0,    320,  -math.pi / 2,  0),
    (0,    0,     math.pi / 2,  0),
    (0,    80,    0,            0),
]

# ---------------------------------------------------------------------------
#  FK — прямая кинематика
# ---------------------------------------------------------------------------

def fk_full(
    joints_deg: List[float],
    dh_params: Optional[List[Tuple[float, float, float, float]]] = None,
) -> Dict[str, Any]:
    """
    FK с полной информацией: позиция TCP, ориентация RPY, промежуточные позиции звеньев.
    Возвращает:
      {
        "tcp_pos": (x, y, z),
        "tcp_rpy": (rx, ry, rz),
        "T":       <4x4 list>,
        "link_positions": [(x0,y0,z0), (x1,y1,z1), ..., (x6,y6,z6)],
      }
    link_positions[0] = база, link_positions[6] = TCP
    """
    if dh_params is None:
        dh_params = DEFAULT_DH
    while len(dh_params) < 6:
        dh_params = list(dh_params) + [DEFAULT_DH[len(dh_params)]]
    T = _mat4_eye()
    positions = [_mat4_pos(T)]
    for i in range(6):
        a, d, alpha, th_off = dh_params[i]
        theta = math.radians(float(joints_deg[i])) + th_off
        Ti = _dh_link(theta, d, a, alpha)
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


def fk_6dof(
    joints_deg: List[float],
    dh_params: Optional[List[Tuple[float, float, float, float]]] = None,
    link_lengths: Optional[List[Tuple[float, float]]] = None,
) -> Tuple[float, float, float]:
    """
    Обратная совместимость. Возвращает (x, y, z) TCP.
    Если заданы link_lengths, они подставляются как (a, d) в DH.
    """
    if dh_params is None:
        dh_params = list(DEFAULT_DH)
    else:
        dh_params = list(dh_params)
    if link_lengths is not None:
        while len(link_lengths) < 6:
            link_lengths = list(link_lengths) + [(0.0, 0.0)]
        for i in range(min(6, len(link_lengths))):
            a_orig, d_orig, alpha, th_off = dh_params[i] if i < len(dh_params) else (0, 0, 0, 0)
            a_new, d_new = link_lengths[i]
            if a_new != 0:
                a_orig = a_new
            if d_new != 0:
                d_orig = d_new
            if i < len(dh_params):
                dh_params[i] = (a_orig, d_orig, alpha, th_off)
    result = fk_full(joints_deg, dh_params)
    return result["tcp_pos"]


# ---------------------------------------------------------------------------
#  IK — обратная кинематика (численный метод Левенберга-Марквардта)
# ---------------------------------------------------------------------------

def _pose_error(T_current: list, T_target: list) -> list:
    """
    Вектор ошибки позы (6 элементов): [dx, dy, dz, erx, ery, erz].
    Позиционная ошибка — разность координат (мм).
    Ориентационная — разность RPY (рад), масштабированная.
    """
    px, py, pz = T_current[3], T_current[7], T_current[11]
    tx, ty, tz = T_target[3], T_target[7], T_target[11]
    dp = [tx - px, ty - py, tz - pz]

    Rc = _mat4_rot3(T_current)
    Rt = _mat4_rot3(T_target)
    # Re = Rt * Rc^T
    # Rc^T:
    RcT = [Rc[0], Rc[3], Rc[6],
           Rc[1], Rc[4], Rc[7],
           Rc[2], Rc[5], Rc[8]]
    # Re = Rt * RcT (3x3 mul)
    Re = [0.0] * 9
    for i in range(3):
        for j in range(3):
            Re[i*3+j] = sum(Rt[i*3+k]*RcT[k*3+j] for k in range(3))
    # Извлечь angle*axis из Re (Rodrigues)
    trace = Re[0] + Re[4] + Re[8]
    angle = math.acos(max(-1.0, min(1.0, (trace - 1.0) / 2.0)))
    if abs(angle) < 1e-10:
        eo = [0.0, 0.0, 0.0]
    elif abs(angle - math.pi) < 1e-6:
        eo = [math.pi, 0.0, 0.0]
    else:
        k = angle / (2.0 * math.sin(angle))
        eo = [k * (Re[7] - Re[5]),
              k * (Re[2] - Re[6]),
              k * (Re[3] - Re[1])]
    return dp + eo


def _numerical_jacobian(
    joints_deg: List[float],
    dh_params: List[Tuple[float, float, float, float]],
    delta_deg: float = 0.01,
) -> list:
    """
    Числовой якобиан 6x6 (row-major, 36 элементов).
    Каждый столбец — производная 6D ошибки по одному суставу.
    """
    T0 = fk_full(joints_deg, dh_params)["T"]
    zero_err = [0.0] * 6  # используем как "нулевую цель" = T0
    J = [0.0] * 36  # 6x6 row-major
    for j in range(6):
        joints_plus = list(joints_deg)
        joints_plus[j] += delta_deg
        Tp = fk_full(joints_plus, dh_params)["T"]
        err = _pose_error(T0, Tp)
        for i in range(6):
            J[i * 6 + j] = err[i] / delta_deg
    return J


def ik_6dof(
    target_xyz: Tuple[float, float, float],
    target_rpy_deg: Tuple[float, float, float] = (0, 0, 0),
    dh_params: Optional[List[Tuple[float, float, float, float]]] = None,
    joint_limits: Optional[List[Tuple[float, float]]] = None,
    initial_joints_deg: Optional[List[float]] = None,
    max_iter: int = 200,
    pos_tol: float = 0.5,
    orient_tol: float = 0.02,
    position_only: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Обратная кинематика (Левенберг-Марквардт).

    Args:
        target_xyz: целевая позиция TCP (мм)
        target_rpy_deg: целевая ориентация (Roll-Pitch-Yaw, градусы)
        dh_params: DH-параметры робота
        joint_limits: [(min, max)] для каждого сустава (градусы)
        initial_joints_deg: начальное приближение
        max_iter: макс. итераций
        pos_tol: допуск по позиции (мм)
        orient_tol: допуск по ориентации (рад)
        position_only: если True, только позиция (игнорируем ориентацию)

    Returns:
        {"joints_deg": [...], "tcp_pos": (...), "tcp_rpy": (...), "iterations": N, "converged": bool}
        или None при неудаче.
    """
    if not _HAS_NP:
        return None  # numpy нужен для IK

    if dh_params is None:
        dh_params = DEFAULT_DH
    if joint_limits is None:
        joint_limits = [(-180, 180)] * 6
    while len(joint_limits) < 6:
        joint_limits.append((-180, 180))
    if initial_joints_deg is None:
        initial_joints_deg = [0.0] * 6

    T_target = _rpy_to_mat4(
        target_rpy_deg[0], target_rpy_deg[1], target_rpy_deg[2],
        target_xyz[0], target_xyz[1], target_xyz[2],
    )

    q = np.array(initial_joints_deg, dtype=float)
    lam = 1.0  # параметр демпфирования ЛМ
    n_dims = 3 if position_only else 6

    for iteration in range(max_iter):
        fk_res = fk_full(q.tolist(), dh_params)
        T_cur = fk_res["T"]
        err = _pose_error(T_cur, T_target)

        if position_only:
            err = err[:3]

        err_np = np.array(err)
        pos_err = np.linalg.norm(err_np[:3]) if len(err_np) >= 3 else np.linalg.norm(err_np)
        orient_err = np.linalg.norm(err_np[3:]) if not position_only and len(err_np) > 3 else 0.0

        if pos_err < pos_tol and (position_only or orient_err < orient_tol):
            return {
                "joints_deg": q.tolist(),
                "tcp_pos": fk_res["tcp_pos"],
                "tcp_rpy": fk_res["tcp_rpy"],
                "iterations": iteration,
                "converged": True,
            }

        # Якобиан
        J_flat = _numerical_jacobian(q.tolist(), dh_params)
        J_full = np.array(J_flat).reshape(6, 6)
        if position_only:
            J = J_full[:3, :]
        else:
            J = J_full

        # ЛМ шаг: dq = (J^T J + lambda*I)^-1 * J^T * err
        JtJ = J.T @ J
        Jte = J.T @ err_np
        try:
            dq = np.linalg.solve(JtJ + lam * np.eye(6), Jte)
        except np.linalg.LinAlgError:
            lam *= 10
            continue

        q_new = q + dq

        # Ограничения суставов
        for i in range(6):
            lo, hi = joint_limits[i]
            q_new[i] = max(lo, min(hi, q_new[i]))

        # Проверяем, стало ли лучше
        fk_new = fk_full(q_new.tolist(), dh_params)
        err_new = _pose_error(fk_new["T"], T_target)
        if position_only:
            err_new = err_new[:3]
        if np.linalg.norm(err_new) < np.linalg.norm(err_np):
            q = q_new
            lam = max(lam * 0.5, 1e-6)
        else:
            lam = min(lam * 5, 1e6)

    # Не сошлось, возвращаем лучшее что нашли
    fk_res = fk_full(q.tolist(), dh_params)
    return {
        "joints_deg": q.tolist(),
        "tcp_pos": fk_res["tcp_pos"],
        "tcp_rpy": fk_res["tcp_rpy"],
        "iterations": max_iter,
        "converged": False,
    }


# ---------------------------------------------------------------------------
#  Проверка достижимости
# ---------------------------------------------------------------------------

def check_reachability(
    point_xyz: Tuple[float, float, float],
    max_reach_mm: float = 1500.0,
    base_xyz: Tuple[float, float, float] = (0, 0, 0),
) -> bool:
    """Точка в сфере радиуса max_reach_mm от базы."""
    x, y, z = point_xyz
    bx, by, bz = base_xyz
    d = math.sqrt((x - bx) ** 2 + (y - by) ** 2 + (z - bz) ** 2)
    return d <= max_reach_mm


def check_reachability_ik(
    point_xyz: Tuple[float, float, float],
    dh_params: Optional[List[Tuple[float, float, float, float]]] = None,
    joint_limits: Optional[List[Tuple[float, float]]] = None,
) -> bool:
    """Достижимость через IK — точнее, чем сфера."""
    result = ik_6dof(point_xyz, position_only=True,
                     dh_params=dh_params, joint_limits=joint_limits)
    return result is not None and result["converged"]
