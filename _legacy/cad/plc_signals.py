"""
Модель PLC-сигналов для KengaCAD.

Виртуальные дискретные и аналоговые сигналы (I/O),
используемые при оффлайн-программировании и virtual commissioning.
Сигналы можно привязать к шагам траектории, использовать
в шаблонах постпроцессоров и синхронизировать с OPC UA сервером.
"""

from typing import Dict, List, Optional, Any, Callable
import time
import json
from pathlib import Path


class Signal:
    """Один PLC-сигнал (DI/DO/AI/AO)."""

    def __init__(self, name: str, direction: str = "DO",
                 dtype: str = "bool", value: Any = False,
                 description: str = ""):
        """
        Args:
            name: имя сигнала (напр. DO_Gripper)
            direction: DI | DO | AI | AO
            dtype: bool | int | float
            value: начальное значение
            description: описание
        """
        self.name = name
        self.direction = direction  # DI, DO, AI, AO
        self.dtype = dtype
        self._value = value
        self.description = description
        self._listeners: List[Callable] = []

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, v):
        old = self._value
        if self.dtype == "bool":
            self._value = bool(v)
        elif self.dtype == "int":
            self._value = int(v)
        elif self.dtype == "float":
            self._value = float(v)
        else:
            self._value = v
        if self._value != old:
            for cb in self._listeners:
                try:
                    cb(self.name, self._value, old)
                except Exception:
                    pass

    def on_change(self, callback: Callable):
        """Подписаться на изменение сигнала."""
        self._listeners.append(callback)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "direction": self.direction,
            "dtype": self.dtype,
            "value": self._value,
            "description": self.description,
        }

    @staticmethod
    def from_dict(d: dict) -> "Signal":
        return Signal(
            name=d["name"],
            direction=d.get("direction", "DO"),
            dtype=d.get("dtype", "bool"),
            value=d.get("value", False),
            description=d.get("description", ""),
        )


class SignalTable:
    """Таблица PLC-сигналов для рабочей ячейки."""

    def __init__(self):
        self._signals: Dict[str, Signal] = {}
        self._trajectory_events: List[Dict[str, Any]] = []

    def add_signal(self, sig: Signal) -> None:
        self._signals[sig.name] = sig

    def remove_signal(self, name: str) -> None:
        self._signals.pop(name, None)

    def get(self, name: str) -> Optional[Signal]:
        return self._signals.get(name)

    def set_value(self, name: str, value: Any) -> bool:
        sig = self._signals.get(name)
        if sig is None:
            return False
        sig.value = value
        return True

    def get_value(self, name: str) -> Any:
        sig = self._signals.get(name)
        return sig.value if sig else None

    def all_signals(self) -> List[Signal]:
        return list(self._signals.values())

    def digital_outputs(self) -> List[Signal]:
        return [s for s in self._signals.values() if s.direction == "DO"]

    def digital_inputs(self) -> List[Signal]:
        return [s for s in self._signals.values() if s.direction == "DI"]

    def analog_outputs(self) -> List[Signal]:
        return [s for s in self._signals.values() if s.direction == "AO"]

    def analog_inputs(self) -> List[Signal]:
        return [s for s in self._signals.values() if s.direction == "AI"]

    # --- Привязка сигналов к шагам траектории ---

    def add_trajectory_event(self, step_index: int, signal_name: str,
                             value: Any, wait_ms: int = 0) -> None:
        """Привязать переключение сигнала к шагу траектории.

        Args:
            step_index: индекс точки траектории (0-based)
            signal_name: имя сигнала
            value: новое значение
            wait_ms: задержка перед переключением (мс)
        """
        self._trajectory_events.append({
            "step": step_index,
            "signal": signal_name,
            "value": value,
            "wait_ms": wait_ms,
        })

    def get_events_at_step(self, step_index: int) -> List[Dict[str, Any]]:
        return [e for e in self._trajectory_events if e["step"] == step_index]

    def clear_trajectory_events(self) -> None:
        self._trajectory_events.clear()

    @property
    def trajectory_events(self) -> List[Dict[str, Any]]:
        return list(self._trajectory_events)

    # --- Сериализация ---

    def to_dict(self) -> dict:
        return {
            "signals": [s.to_dict() for s in self._signals.values()],
            "trajectory_events": self._trajectory_events,
        }

    @staticmethod
    def from_dict(d: dict) -> "SignalTable":
        st = SignalTable()
        for sd in d.get("signals", []):
            st.add_signal(Signal.from_dict(sd))
        st._trajectory_events = d.get("trajectory_events", [])
        return st

    def save_json(self, path: str) -> bool:
        try:
            Path(path).write_text(
                json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8")
            return True
        except Exception:
            return False

    @staticmethod
    def load_json(path: str) -> Optional["SignalTable"]:
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            return SignalTable.from_dict(data)
        except Exception:
            return None

    # --- Стандартный набор сигналов для типовой ячейки ---

    @staticmethod
    def create_default() -> "SignalTable":
        """Создать типовую таблицу сигналов для сварочной/сборочной ячейки."""
        st = SignalTable()
        st.add_signal(Signal("DO_Gripper", "DO", "bool", False, "Захват/зажим"))
        st.add_signal(Signal("DO_Weld_Start", "DO", "bool", False, "Старт сварки"))
        st.add_signal(Signal("DO_Weld_Stop", "DO", "bool", False, "Стоп сварки"))
        st.add_signal(Signal("DO_Air_Blow", "DO", "bool", False, "Продув воздухом"))
        st.add_signal(Signal("DI_Part_Present", "DI", "bool", False, "Датчик наличия детали"))
        st.add_signal(Signal("DI_Clamp_Closed", "DI", "bool", False, "Зажим закрыт"))
        st.add_signal(Signal("DI_Safety_OK", "DI", "bool", True, "Безопасность ОК"))
        st.add_signal(Signal("AO_WeldCurrent", "AO", "float", 0.0, "Ток сварки (А)"))
        st.add_signal(Signal("AO_WeldVoltage", "AO", "float", 0.0, "Напряжение сварки (В)"))
        st.add_signal(Signal("AO_Speed_Override", "AO", "float", 100.0, "Скорость (%)"))
        st.add_signal(Signal("AI_Temperature", "AI", "float", 25.0, "Температура (°C)"))
        st.add_signal(Signal("AI_Force", "AI", "float", 0.0, "Усилие (Н)"))
        return st
