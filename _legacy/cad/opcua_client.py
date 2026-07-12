"""
OPC UA клиент для KengaCAD.

Позволяет подключаться к OPC UA серверу PLC (Siemens S7, Beckhoff, и др.)
и синхронизировать виртуальные сигналы с реальными сигналами контроллера.

Требует: opcua (python-opcua) или asyncua — опционально.
При отсутствии библиотеки работает в режиме симуляции.
"""

from typing import Optional, Dict, Any, List, Callable
import threading
import time

try:
    from opcua import Client as OpcClient, ua
    _HAS_OPCUA = True
except ImportError:
    try:
        from asyncua.sync import Client as OpcClient
        from asyncua import ua
        _HAS_OPCUA = True
    except ImportError:
        _HAS_OPCUA = False


class OpcUaConnection:
    """OPC UA клиент — подключение к PLC."""

    def __init__(self, endpoint: str = "opc.tcp://localhost:4840"):
        self.endpoint = endpoint
        self._client = None
        self._connected = False
        self._node_cache: Dict[str, Any] = {}
        self._subscriptions: Dict[str, Any] = {}
        self._poll_thread: Optional[threading.Thread] = None
        self._poll_running = False
        self._on_value_changed: Optional[Callable] = None

    @property
    def available(self) -> bool:
        """Установлена ли библиотека OPC UA."""
        return _HAS_OPCUA

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        """Подключиться к серверу."""
        if not _HAS_OPCUA:
            return False
        try:
            self._client = OpcClient(self.endpoint)
            self._client.connect()
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            self._client = None
            return False

    def disconnect(self) -> None:
        """Отключиться от сервера."""
        self._poll_running = False
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=3)
        if self._client:
            try:
                self._client.disconnect()
            except Exception:
                pass
        self._client = None
        self._connected = False
        self._node_cache.clear()

    def read_node(self, node_id: str) -> Any:
        """Прочитать значение OPC UA узла."""
        if not self._connected or not self._client:
            return None
        try:
            node = self._client.get_node(node_id)
            return node.get_value()
        except Exception:
            return None

    def write_node(self, node_id: str, value: Any, dtype=None) -> bool:
        """Записать значение в OPC UA узел."""
        if not self._connected or not self._client:
            return False
        try:
            node = self._client.get_node(node_id)
            if dtype is not None and _HAS_OPCUA:
                dv = ua.DataValue(ua.Variant(value, dtype))
                node.set_value(dv)
            else:
                node.set_value(value)
            return True
        except Exception:
            return False

    def browse_children(self, node_id: str = "i=85") -> List[Dict[str, str]]:
        """Просмотреть дочерние узлы (Objects folder = i=85)."""
        if not self._connected or not self._client:
            return []
        try:
            node = self._client.get_node(node_id)
            children = node.get_children()
            result = []
            for ch in children:
                try:
                    result.append({
                        "node_id": ch.nodeid.to_string(),
                        "name": ch.get_browse_name().Name,
                    })
                except Exception:
                    pass
            return result
        except Exception:
            return []

    def start_polling(self, node_map: Dict[str, str],
                      interval_ms: int = 200,
                      on_value_changed: Optional[Callable] = None) -> None:
        """Запустить поллинг узлов.

        Args:
            node_map: {signal_name: node_id, ...}
            interval_ms: интервал опроса
            on_value_changed: callback(signal_name, new_value)
        """
        self._poll_running = False
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=2)
        self._on_value_changed = on_value_changed
        self._poll_running = True
        self._poll_thread = threading.Thread(
            target=self._poll_loop,
            args=(dict(node_map), interval_ms / 1000.0),
            daemon=True,
        )
        self._poll_thread.start()

    def stop_polling(self) -> None:
        self._poll_running = False

    def _poll_loop(self, node_map: Dict[str, str], interval: float) -> None:
        cache: Dict[str, Any] = {}
        while self._poll_running and self._connected:
            for sig_name, node_id in node_map.items():
                val = self.read_node(node_id)
                if val is not None and val != cache.get(sig_name):
                    cache[sig_name] = val
                    if self._on_value_changed:
                        try:
                            self._on_value_changed(sig_name, val)
                        except Exception:
                            pass
            time.sleep(interval)


class OpcUaSimulator:
    """Локальная симуляция OPC UA для тестирования без реального PLC."""

    def __init__(self):
        self._values: Dict[str, Any] = {}
        self._connected = True

    @property
    def available(self) -> bool:
        return True

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> bool:
        self._connected = True
        return True

    def disconnect(self) -> None:
        self._connected = False

    def read_node(self, node_id: str) -> Any:
        return self._values.get(node_id)

    def write_node(self, node_id: str, value: Any, dtype=None) -> bool:
        self._values[node_id] = value
        return True

    def browse_children(self, node_id: str = "i=85") -> List[Dict[str, str]]:
        return [{"node_id": k, "name": k.split(".")[-1]}
                for k in self._values.keys()]

    def start_polling(self, *a, **kw) -> None:
        pass

    def stop_polling(self) -> None:
        pass

    def set_simulated(self, node_id: str, value: Any) -> None:
        """Установить значение для симуляции."""
        self._values[node_id] = value
