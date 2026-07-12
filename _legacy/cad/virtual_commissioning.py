"""
Virtual Commissioning движок для KengaCAD.

Содержит:
  - CycleModel — модель цикла (шаги с таймингами и сигналами)
  - CycleSimulator — проигрыватель цикла с синхронизацией I/O
  - GanttData — данные для Gantt-диаграммы
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
import time
import math

from cad.plc_signals import SignalTable


class CycleStep:
    """Один шаг производственного цикла."""

    def __init__(self, name: str, duration_s: float = 1.0,
                 step_type: str = "move",
                 traj_start: int = 0, traj_end: int = 0,
                 signals_before: Optional[List[Dict[str, Any]]] = None,
                 signals_after: Optional[List[Dict[str, Any]]] = None):
        """
        Args:
            name: название шага (напр. "Подъезд к детали")
            duration_s: расчётная длительность (сек)
            step_type: move | wait | weld | grip | release | custom
            traj_start: индекс начальной точки траектории
            traj_end: индекс конечной точки траектории
            signals_before: сигналы, переключаемые ДО шага [{signal, value}, ...]
            signals_after: сигналы, переключаемые ПОСЛЕ шага
        """
        self.name = name
        self.duration_s = duration_s
        self.step_type = step_type
        self.traj_start = traj_start
        self.traj_end = traj_end
        self.signals_before = signals_before or []
        self.signals_after = signals_after or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "duration_s": self.duration_s,
            "step_type": self.step_type,
            "traj_start": self.traj_start,
            "traj_end": self.traj_end,
            "signals_before": self.signals_before,
            "signals_after": self.signals_after,
        }

    @staticmethod
    def from_dict(d: dict) -> "CycleStep":
        return CycleStep(
            name=d["name"],
            duration_s=d.get("duration_s", 1.0),
            step_type=d.get("step_type", "move"),
            traj_start=d.get("traj_start", 0),
            traj_end=d.get("traj_end", 0),
            signals_before=d.get("signals_before"),
            signals_after=d.get("signals_after"),
        )


class CycleModel:
    """Модель производственного цикла."""

    def __init__(self, name: str = "Цикл 1"):
        self.name = name
        self.steps: List[CycleStep] = []

    def add_step(self, step: CycleStep) -> None:
        self.steps.append(step)

    def remove_step(self, index: int) -> None:
        if 0 <= index < len(self.steps):
            self.steps.pop(index)

    def total_time_s(self) -> float:
        return sum(s.duration_s for s in self.steps)

    def gantt_data(self) -> "GanttData":
        """Построить данные для Gantt-диаграммы."""
        bars = []
        t = 0.0
        for i, step in enumerate(self.steps):
            bars.append({
                "index": i,
                "name": step.name,
                "type": step.step_type,
                "start_s": t,
                "end_s": t + step.duration_s,
                "duration_s": step.duration_s,
                "signals_before": step.signals_before,
                "signals_after": step.signals_after,
            })
            t += step.duration_s
        return GanttData(self.name, bars, t)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }

    @staticmethod
    def from_dict(d: dict) -> "CycleModel":
        cm = CycleModel(d.get("name", "Цикл"))
        for sd in d.get("steps", []):
            cm.add_step(CycleStep.from_dict(sd))
        return cm

    @staticmethod
    def from_trajectory(
        points: List[Tuple[float, float, float]],
        speed_mm_s: float = 250.0,
        signal_table: Optional[SignalTable] = None,
    ) -> "CycleModel":
        """Автоматическое создание модели цикла из траектории.

        Разбивает траекторию на сегменты "move", считает время по длине/скорости,
        вставляет переключения сигналов из signal_table.trajectory_events.
        """
        cm = CycleModel("Авто-цикл")
        if not points or len(points) < 2:
            return cm

        # Home → первая точка
        p0 = points[0]
        dist_home = math.sqrt(p0[0]**2 + p0[1]**2 + p0[2]**2) if len(p0) >= 3 else 0
        if dist_home > 1:
            cm.add_step(CycleStep(
                "Подъезд к старту", max(0.5, dist_home / speed_mm_s),
                "move", 0, 0))

        # Основные перемещения
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i + 1]
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = (p2[2] - p1[2]) if len(p1) > 2 and len(p2) > 2 else 0
            dist = math.sqrt(dx**2 + dy**2 + dz**2)
            t = max(0.05, dist / speed_mm_s)

            # Проверяем, есть ли сигнальные события на этом шаге
            sig_before = []
            sig_after = []
            if signal_table:
                events = signal_table.get_events_at_step(i)
                for ev in events:
                    sig_before.append({
                        "signal": ev["signal"],
                        "value": ev["value"],
                    })

            cm.add_step(CycleStep(
                f"Перемещение {i+1}→{i+2}", t, "move",
                i, i + 1, sig_before, sig_after))

        # Возврат домой
        pn = points[-1]
        dist_ret = math.sqrt(pn[0]**2 + pn[1]**2 + pn[2]**2) if len(pn) >= 3 else 0
        if dist_ret > 1:
            cm.add_step(CycleStep(
                "Возврат в Home", max(0.5, dist_ret / speed_mm_s),
                "move", len(points) - 1, len(points) - 1))

        return cm


class GanttData:
    """Данные Gantt-диаграммы для отрисовки."""

    def __init__(self, name: str, bars: List[Dict[str, Any]], total_s: float):
        self.name = name
        self.bars = bars
        self.total_s = total_s

    def summary(self) -> str:
        lines = [f"Цикл: {self.name}",
                 f"Общее время: {self.total_s:.2f} сек"]
        for b in self.bars:
            lines.append(
                f"  [{b['start_s']:.2f}–{b['end_s']:.2f}] "
                f"{b['name']} ({b['type']}, {b['duration_s']:.2f}с)")
        return "\n".join(lines)


class CycleSimulator:
    """Проигрыватель цикла с синхронизацией сигналов."""

    def __init__(self, cycle: CycleModel, signal_table: SignalTable):
        self.cycle = cycle
        self.signal_table = signal_table
        self._current_step = -1
        self._running = False
        self._elapsed = 0.0
        self._step_elapsed = 0.0
        self._on_step_changed: Optional[Callable] = None
        self._on_signal_fired: Optional[Callable] = None
        self._on_finished: Optional[Callable] = None

    @property
    def current_step(self) -> int:
        return self._current_step

    @property
    def running(self) -> bool:
        return self._running

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def progress(self) -> float:
        total = self.cycle.total_time_s()
        return min(1.0, self._elapsed / total) if total > 0 else 0.0

    def set_callbacks(self, on_step=None, on_signal=None, on_finished=None):
        self._on_step_changed = on_step
        self._on_signal_fired = on_signal
        self._on_finished = on_finished

    def reset(self) -> None:
        self._current_step = -1
        self._running = False
        self._elapsed = 0.0
        self._step_elapsed = 0.0

    def start(self) -> None:
        if not self.cycle.steps:
            return
        self._running = True
        self._current_step = 0
        self._elapsed = 0.0
        self._step_elapsed = 0.0
        self._fire_signals_before(0)
        if self._on_step_changed:
            self._on_step_changed(0)

    def stop(self) -> None:
        self._running = False

    def tick(self, dt_s: float) -> None:
        """Продвинуть симуляцию на dt_s секунд. Вызывается из QTimer."""
        if not self._running or self._current_step < 0:
            return
        if self._current_step >= len(self.cycle.steps):
            self._running = False
            if self._on_finished:
                self._on_finished()
            return

        self._elapsed += dt_s
        self._step_elapsed += dt_s

        step = self.cycle.steps[self._current_step]
        if self._step_elapsed >= step.duration_s:
            # Шаг завершён
            self._fire_signals_after(self._current_step)
            self._current_step += 1
            self._step_elapsed = 0.0

            if self._current_step >= len(self.cycle.steps):
                self._running = False
                if self._on_finished:
                    self._on_finished()
            else:
                self._fire_signals_before(self._current_step)
                if self._on_step_changed:
                    self._on_step_changed(self._current_step)

    def _fire_signals_before(self, step_idx: int) -> None:
        step = self.cycle.steps[step_idx]
        for evt in step.signals_before:
            name = evt.get("signal", "")
            val = evt.get("value")
            self.signal_table.set_value(name, val)
            if self._on_signal_fired:
                self._on_signal_fired(name, val, "before", step_idx)

    def _fire_signals_after(self, step_idx: int) -> None:
        step = self.cycle.steps[step_idx]
        for evt in step.signals_after:
            name = evt.get("signal", "")
            val = evt.get("value")
            self.signal_table.set_value(name, val)
            if self._on_signal_fired:
                self._on_signal_fired(name, val, "after", step_idx)
