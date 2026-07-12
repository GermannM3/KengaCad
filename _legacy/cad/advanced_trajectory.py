"""
Расширенное управление траекториями для KengaCAD.

Поддержка:
  - Линейная и сплайновая интерполяция
  - Сглаживание траекторий (B-сплайны, Chaikin, B-spline)
  - Адаптивная дискретизация
  - Оптимизация скорости и ускорения
  - Проверка ограничений робота
  - Генерация G-кода
"""
from typing import List, Tuple, Optional, Dict, Any, Union
import math

try:
    import numpy as np
    _HAS_NP = True
except ImportError:
    _HAS_NP = False

try:
    from scipy.interpolate import splprep, splev, CubicSpline
    _HAS_SCIPY = True
except ImportError:
    _HAS_SCIPY = False


class TrajectoryPoint:
    """Точка траектории с параметрами движения."""

    def __init__(
        self,
        x: float, y: float, z: float,
        rx: float = 0, ry: float = 0, rz: float = 0,
        velocity: float = 100.0,  # мм/сек
        acceleration: float = 50.0,  # мм/сек²
        blend_radius: float = 5.0,  # радиус сглаживания угла
        dwell_time: float = 0.0,  # задержка в секундах
        process_params: Dict = None,  # параметры процесса (диспенсинг и т.д.)
    ):
        self.x = x
        self.y = y
        self.z = z
        self.rx = rx
        self.ry = ry
        self.rz = rz
        self.velocity = velocity
        self.acceleration = acceleration
        self.blend_radius = blend_radius
        self.dwell_time = dwell_time
        self.process_params = process_params or {}

    @property
    def position(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    @property
    def orientation(self) -> Tuple[float, float, float]:
        return (self.rx, self.ry, self.rz)

    def to_dict(self) -> Dict:
        return {
            "x": self.x, "y": self.y, "z": self.z,
            "rx": self.rx, "ry": self.ry, "rz": self.rz,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "blend_radius": self.blend_radius,
            "dwell_time": self.dwell_time,
            "process_params": self.process_params,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TrajectoryPoint":
        return cls(
            x=data.get("x", 0), y=data.get("y", 0), z=data.get("z", 0),
            rx=data.get("rx", 0), ry=data.get("ry", 0), rz=data.get("rz", 0),
            velocity=data.get("velocity", 100),
            acceleration=data.get("acceleration", 50),
            blend_radius=data.get("blend_radius", 5),
            dwell_time=data.get("dwell_time", 0),
            process_params=data.get("process_params", {}),
        )

    def __repr__(self):
        return f"TrajectoryPoint({self.x}, {self.y}, {self.z})"


class TrajectorySpline:
    """Сплайн траектория для плавного движения."""

    def __init__(self, points: List[TrajectoryPoint], spline_type: str = "cubic"):
        """
        Args:
            points: опорные точки траектории
            spline_type: "linear", "cubic", "bspline", "chaikin"
        """
        self.points = points
        self.spline_type = spline_type
        self._parametric_spline = None
        self._cs_x = self._cs_y = self._cs_z = None

        if points:
            self._fit_spline()

    def _fit_spline(self):
        """Построение сплайна."""
        if not _HAS_NP or len(self.points) < 2:
            return

        pts = np.array([[p.x, p.y, p.z] for p in self.points])

        if self.spline_type == "linear":
            return  # Линейная интерполяция не требует сплайна

        if self.spline_type == "cubic" and _HAS_SCIPY:
            # Параметрический кубический сплайн
            t = np.linspace(0, 1, len(pts))
            self._cs_x = CubicSpline(t, pts[:, 0])
            self._cs_y = CubicSpline(t, pts[:, 1])
            self._cs_z = CubicSpline(t, pts[:, 2])
            self._parametric_spline = (t, pts)

        elif self.spline_type == "bspline" and _HAS_SCIPY:
            # B-сплайн
            tck, u = splprep([pts[:, 0], pts[:, 1], pts[:, 2]], s=0, k=min(3, len(pts)-1))
            self._parametric_spline = (tck, u)

        elif self.spline_type == "chaikin":
            # Сглаживание Chaikin
            self._chaikin_smooth()

    def _chaikin_smooth(self, iterations: int = 3):
        """Сглаживание алгоритмом Chaikin."""
        if not _HAS_NP:
            return

        pts = np.array([[p.x, p.y, p.z] for p in self.points])

        for _ in range(iterations):
            new_pts = []
            for i in range(len(pts) - 1):
                p0, p1 = pts[i], pts[i + 1]
                q = 0.75 * p0 + 0.25 * p1
                r = 0.25 * p0 + 0.75 * p1
                new_pts.extend([q, r])
            new_pts.append(pts[-1])
            pts = np.array(new_pts)

        # Обновить точки
        self.points = [
            TrajectoryPoint(p[0], p[1], p[2])
            for p in pts
        ]

    def evaluate(self, t: float) -> Optional[Tuple[float, float, float]]:
        """
        Вычислить точку на сплайне по параметру t (0-1).

        Returns:
            (x, y, z) или None
        """
        if not _HAS_NP:
            return None

        if self.spline_type == "linear":
            # Линейная интерполяция
            pts = np.array([[p.x, p.y, p.z] for p in self.points])
            n = len(pts) - 1
            if n < 1:
                return None
            idx = min(int(t * n), n - 1)
            local_t = (t * n) - idx
            p0, p1 = pts[idx], pts[idx + 1]
            return tuple(p0 + (p1 - p0) * local_t)

        if self._parametric_spline and _HAS_SCIPY:
            if self.spline_type in ("cubic",):
                t_arr, _ = self._parametric_spline
                return (
                    self._cs_x(t),
                    self._cs_y(t),
                    self._cs_z(t),
                )
            elif self.spline_type == "bspline":
                tck, u = self._parametric_spline
                return tuple(splev(t, tck))

        return None

    def evaluate_derivative(self, t: float) -> Optional[Tuple[float, float, float]]:
        """Производная (вектор скорости) в точке t."""
        if not _HAS_NP or not self._parametric_spline:
            return None

        if self.spline_type == "bspline" and _HAS_SCIPY:
            tck, u = self._parametric_spline
            return tuple(splev(t, tck, der=1))

        if self.spline_type == "cubic" and self._cs_x:
            return (
                self._cs_x(t, 1),
                self._cs_y(t, 1),
                self._cs_z(t, 1),
            )

        return None

    def discretize(self, num_points: int = 100) -> List[TrajectoryPoint]:
        """Дискретизация сплайна на заданное количество точек."""
        if not self.points:
            return []

        if self.spline_type == "linear":
            # Линейная интерполяция между исходными точками
            result = []
            for i in range(len(self.points) - 1):
                p0, p1 = self.points[i], self.points[i + 1]
                for j in range(num_points // (len(self.points) - 1)):
                    t = j / (num_points // (len(self.points) - 1))
                    result.append(TrajectoryPoint(
                        p0.x + (p1.x - p0.x) * t,
                        p0.y + (p1.y - p0.y) * t,
                        p0.z + (p1.z - p0.z) * t,
                    ))
            result.append(self.points[-1])
            return result

        # Дискретизация сплайна
        result = []
        for i in range(num_points):
            t = i / (num_points - 1)
            pt = self.evaluate(t)
            if pt:
                result.append(TrajectoryPoint(pt[0], pt[1], pt[2]))

        return result

    def get_length(self) -> float:
        """Длина траектории."""
        if not _HAS_NP or len(self.points) < 2:
            return 0

        total = 0
        for i in range(1, len(self.points)):
            p0, p1 = self.points[i - 1], self.points[i]
            dx = p1.x - p0.x
            dy = p1.y - p0.y
            dz = p1.z - p0.z
            total += math.sqrt(dx**2 + dy**2 + dz**2)

        return total


class AdvancedTrajectoryManager:
    """Расширенный менеджер траекторий."""

    def __init__(self):
        self.trajectories: Dict[str, TrajectorySpline] = {}
        self.metadata: Dict[str, Dict] = {}

    def create_trajectory(
        self,
        entity_id: str,
        points: Union[List[Tuple[float, float, float]], List[TrajectoryPoint]],
        spline_type: str = "cubic",
        metadata: Dict = None,
    ) -> bool:
        """Создать траекторию."""
        try:
            # Конвертация в TrajectoryPoint
            traj_points = []
            for p in points:
                if isinstance(p, TrajectoryPoint):
                    traj_points.append(p)
                elif isinstance(p, (list, tuple)) and len(p) >= 3:
                    traj_points.append(TrajectoryPoint(p[0], p[1], p[2]))

            if not traj_points:
                return False

            spline = TrajectorySpline(traj_points, spline_type)
            self.trajectories[entity_id] = spline
            self.metadata[entity_id] = metadata or {}
            return True
        except Exception as e:
            print(f"Ошибка создания траектории: {e}")
            return False

    def add_point(
        self,
        entity_id: str,
        point: Union[TrajectoryPoint, Tuple[float, float, float]],
        index: int = -1,
    ) -> bool:
        """Добавить точку в траекторию."""
        if entity_id not in self.trajectories:
            return False

        spline = self.trajectories[entity_id]

        if isinstance(point, TrajectoryPoint):
            pt = point
        else:
            pt = TrajectoryPoint(point[0], point[1], point[2])

        if index < 0:
            spline.points.append(pt)
        else:
            spline.points.insert(index, pt)

        # Перестроить сплайн
        spline._fit_spline()
        return True

    def remove_point(self, entity_id: str, index: int) -> bool:
        """Удалить точку из траектории."""
        if entity_id not in self.trajectories:
            return False

        spline = self.trajectories[entity_id]
        if index < 0 or index >= len(spline.points):
            return False

        spline.points.pop(index)
        spline._fit_spline()
        return True

    def get_trajectory(self, entity_id: str) -> Optional[TrajectorySpline]:
        """Получить траекторию."""
        return self.trajectories.get(entity_id)

    def discretize_trajectory(
        self,
        entity_id: str,
        num_points: int = 100,
    ) -> Optional[List[TrajectoryPoint]]:
        """Дискретизировать траекторию."""
        spline = self.trajectories.get(entity_id)
        if not spline:
            return None
        return spline.discretize(num_points)

    def get_trajectory_length(self, entity_id: str) -> float:
        """Получить длину траектории."""
        spline = self.trajectories.get(entity_id)
        if not spline:
            return 0
        return spline.get_length()

    def smooth_trajectory(
        self,
        entity_id: str,
        method: str = "chaikin",
        iterations: int = 3,
    ) -> bool:
        """Сгладить траекторию."""
        if entity_id not in self.trajectories:
            return False

        spline = self.trajectories[entity_id]

        if method == "chaikin":
            spline._chaikin_smooth(iterations)
        elif method == "bspline":
            spline.spline_type = "bspline"
            spline._fit_spline()
        elif method == "cubic":
            spline.spline_type = "cubic"
            spline._fit_spline()

        return True

    def interpolate_trajectory(
        self,
        entity_id: str,
        num_intermediate_points: int = 5,
    ) -> bool:
        """Добавить промежуточные точки линейной интерполяцией."""
        if entity_id not in self.trajectories:
            return False

        spline = self.trajectories[entity_id]
        if len(spline.points) < 2:
            return False

        new_points = []
        for i in range(len(spline.points) - 1):
            p0, p1 = spline.points[i], spline.points[i + 1]
            new_points.append(p0)
            for j in range(1, num_intermediate_points + 1):
                t = j / (num_intermediate_points + 1)
                new_points.append(TrajectoryPoint(
                    p0.x + (p1.x - p0.x) * t,
                    p0.y + (p1.y - p0.y) * t,
                    p0.z + (p1.z - p0.z) * t,
                ))

        new_points.append(spline.points[-1])
        spline.points = new_points
        spline._fit_spline()
        return True

    def optimize_velocity(
        self,
        entity_id: str,
        max_velocity: float = 200.0,
        max_acceleration: float = 100.0,
        corner_angle_threshold: float = 30.0,  # градусов
        corner_velocity_factor: float = 0.5,
    ) -> bool:
        """
        Оптимизировать профиль скорости с учётом ограничений.

        - Снижение скорости на углах
        - Ограничение ускорения
        """
        if entity_id not in self.trajectories:
            return False

        spline = self.trajectories[entity_id]
        if len(spline.points) < 3:
            return False

        for i in range(1, len(spline.points) - 1):
            p_prev = spline.points[i - 1]
            p_curr = spline.points[i]
            p_next = spline.points[i + 1]

            # Угол между сегментами
            v1 = np.array([p_curr.x - p_prev.x, p_curr.y - p_prev.y, p_curr.z - p_prev.z])
            v2 = np.array([p_next.x - p_curr.x, p_next.y - p_curr.y, p_next.z - p_curr.z])

            if np.linalg.norm(v1) < 0.01 or np.linalg.norm(v2) < 0.01:
                continue

            v1 = v1 / np.linalg.norm(v1)
            v2 = v2 / np.linalg.norm(v2)

            cos_angle = np.dot(v1, v2)
            angle = math.degrees(math.acos(max(-1, min(1, cos_angle))))

            # Снижение скорости на острых углах
            if angle > corner_angle_threshold:
                factor = corner_velocity_factor * (1 - (angle - corner_angle_threshold) / (180 - corner_angle_threshold))
                p_curr.velocity = max_velocity * factor
                p_curr.acceleration = max_acceleration * factor
            else:
                p_curr.velocity = max_velocity
                p_curr.acceleration = max_acceleration

        return True

    def export_to_gcode(
        self,
        entity_id: str,
        num_points: int = 100,
        feed_rate: float = 100.0,
    ) -> Optional[str]:
        """Экспорт в G-код."""
        points = self.discretize_trajectory(entity_id, num_points)
        if not points:
            return None

        lines = [
            "; KengaCAD G-code",
            f"; Points: {len(points)}",
            f"; Feed rate: {feed_rate} mm/min",
            "G21 ; mm",
            "G90 ; absolute",
            f"G1 F{feed_rate}",
        ]

        for i, pt in enumerate(points):
            if i == 0:
                lines.append(f"G0 X{pt.x:.3f} Y{pt.y:.3f} Z{pt.z:.3f}")
            else:
                lines.append(f"G1 X{pt.x:.3f} Y{pt.y:.3f} Z{pt.z:.3f}")

        lines.append("M30")
        return "\n".join(lines)

    def clear(self, entity_id: str = None):
        """Очистить траектории."""
        if entity_id:
            self.trajectories.pop(entity_id, None)
            self.metadata.pop(entity_id, None)
        else:
            self.trajectories.clear()
            self.metadata.clear()


# ============================================================================
#  Утилиты
# ============================================================================

def calculate_path_time(
    points: List[TrajectoryPoint],
    default_velocity: float = 100.0,
    default_acceleration: float = 50.0,
) -> float:
    """Расчёт времени прохождения пути."""
    if not _HAS_NP or len(points) < 2:
        return 0

    total_time = 0
    for i in range(1, len(points)):
        p0, p1 = points[i - 1], points[i]
        dist = math.sqrt(
            (p1.x - p0.x)**2 +
            (p1.y - p0.y)**2 +
            (p1.z - p0.z)**2
        )

        v = p1.velocity if p1.velocity > 0 else default_velocity
        a = p1.acceleration if p1.acceleration > 0 else default_acceleration

        # Время разгона/торможения
        t_accel = v / a
        d_accel = 0.5 * a * t_accel**2

        if dist >= 2 * d_accel:
            # Треугольный профиль скорости
            t_const = (dist - 2 * d_accel) / v
            total_time += 2 * t_accel + t_const
        else:
            # Треугольный профиль без постоянной скорости
            t_tri = math.sqrt(dist / a)
            total_time += 2 * t_tri

        total_time += p0.dwell_time

    return total_time


def generate_spiral(
    center: Tuple[float, float, float],
    radius: float,
    height: float,
    num_turns: float = 1.0,
    num_points: int = 50,
) -> List[TrajectoryPoint]:
    """Генерация спиральной траектории."""
    if not _HAS_NP:
        return []

    points = []
    cx, cy, cz = center

    for i in range(num_points):
        t = i / (num_points - 1)
        angle = 2 * math.pi * num_turns * t
        r = radius * t

        x = cx + r * math.cos(angle)
        y = cy + r * math.sin(angle)
        z = cz + height * t

        points.append(TrajectoryPoint(x, y, z))

    return points


def generate_zigzag(
    start: Tuple[float, float, float],
    size_x: float,
    size_y: float,
    step_over: float,
    num_points_per_line: int = 10,
) -> List[TrajectoryPoint]:
    """Генерация зигзагообразной траектории (для покрытия площади)."""
    if not _HAS_NP:
        return []

    points = []
    sx, sy, sz = start

    num_lines = max(1, int(size_y / step_over))
    direction = 1

    for i in range(num_lines):
        y = sy + i * step_over
        x_start = sx if direction > 0 else sx + size_x
        x_end = sx + size_x if direction > 0 else sx

        for j in range(num_points_per_line):
            t = j / (num_points_per_line - 1)
            x = x_start + (x_end - x_start) * t
            points.append(TrajectoryPoint(x, y, sz))

        direction = -direction

    return points
