"""
Встроенный движок KengaCAD — без внешнего процесса и WebSocket.
Траектория хранится локально, симуляция — анимация маркера в 3D-превью.
"""
from typing import List, Tuple, Optional, Callable, Any


class LocalEngine:
    """Локальный движок: траектория, симуляция (через callback в UI)."""

    def __init__(self):
        self._trajectory_points: List[Tuple[float, float, float]] = []
        self._robot_loaded = False
        self.version = "local"

    def setup_trajectory(self, points: List[Tuple[float, float, float]], entity_id: str = "robot1_trajectory") -> bool:
        """Сохранить траекторию. Реальное отображение — в View3DPreview."""
        self._trajectory_points = list(points) if points else []
        return True

    def get_trajectory(self) -> List[Tuple[float, float, float]]:
        return list(self._trajectory_points)

    def run_simulation(self, steps: int, on_step: Optional[Callable[[int, Tuple[float, float, float]], None]] = None) -> bool:
        """
        Локальная симуляция: вызов on_step(i, point) для каждого шага.
        UI (View3DPreview) анимирует маркер вдоль траектории.
        """
        if not self._trajectory_points or len(self._trajectory_points) < 2:
            return False
        for i in range(min(steps, len(self._trajectory_points))):
            idx = min(i, len(self._trajectory_points) - 1)
            pt = self._trajectory_points[idx]
            if on_step:
                on_step(i, pt)
        return True

    def load_robot(self, path: str, entity_id: str = "robot1") -> bool:
        """Заглушка: робот считается загруженным для локального режима."""
        self._robot_loaded = True
        return True

    def is_ready(self) -> bool:
        return True
