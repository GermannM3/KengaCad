"""
WebSocket клиент для взаимодействия с движком Kenga
"""
import asyncio
import websockets
import json
import uuid
from typing import Dict, Any, Optional, Callable
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class KengaWebSocketClient:
    def __init__(self, uri: str = "ws://127.0.0.1:7777/ws"):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.response_handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {}
        self.request_callbacks: Dict[str, asyncio.Future] = {}
    
    async def connect(self):
        """Подключение к WebSocket серверу движка Kenga"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            logger.info(f"Подключено к движку Kenga: {self.uri}")
            
            # Запуск прослушивания сообщений
            asyncio.create_task(self._listen_for_messages())
            
            return True
        except Exception as e:
            logger.error(f"Ошибка подключения к {self.uri}: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """Отключение от WebSocket сервера"""
        self.connected = False
        if self.websocket:
            await self.websocket.close()
            logger.info("Отключено от движка Kenga")
    
    async def _listen_for_messages(self):
        """Прослушивание входящих сообщений"""
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    logger.error(f"Неверный JSON: {message}")
                except Exception as e:
                    logger.error(f"Ошибка обработки сообщения: {e}")
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Соединение закрыто")
            self.connected = False
        except Exception as e:
            logger.error(f"Ошибка прослушивания: {e}")
            self.connected = False
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Обработка входящего сообщения"""
        request_id = data.get('request_id')
        
        # Если это ответ на наш запрос
        if request_id and request_id in self.request_callbacks:
            future = self.request_callbacks[request_id]
            if not future.done():
                future.set_result(data)
            del self.request_callbacks[request_id]
        # Если это событие или команда от сервера
        else:
            # Проверим, есть ли обработчик для этого типа сообщения
            event_type = data.get('event') or data.get('cmd')
            if event_type in self.response_handlers:
                handler = self.response_handlers[event_type]
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
    
    async def send_command(self, cmd: str, data: Dict[str, Any] = None, timeout: float = 10.0) -> Dict[str, Any]:
        """Отправка команды в движок Kenga"""
        if not self.connected or not self.websocket:
            raise ConnectionError("Нет подключения к движку Kenga")
        
        request_id = str(uuid.uuid4())
        message = {
            "cmd": cmd,
            "request_id": request_id
        }
        
        if data:
            message["data"] = data
        
        # Создаем Future для ожидания ответа
        future = asyncio.Future()
        self.request_callbacks[request_id] = future
        
        try:
            await self.websocket.send(json.dumps(message))
            response = await asyncio.wait_for(future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            if not future.done():
                future.cancel()
            if request_id in self.request_callbacks:
                del self.request_callbacks[request_id]
            raise TimeoutError(f"Таймаут ожидания ответа на команду {cmd}")
    
    # Методы для различных команд API
    async def load_model(self, asset_id: str = None, path: str = None, entity_id: str = None, name: str = None):
        """Загрузка 3D модели"""
        data = {}
        if asset_id:
            data["asset_id"] = asset_id
        if path:
            data["path"] = path
        if entity_id:
            data["entity_id"] = entity_id
        if name:
            data["name"] = name
            
        return await self.send_command("load_model", data)
    
    async def unload_model(self, entity_id: str):
        """Выгрузка 3D модели"""
        data = {"entity_id": entity_id}
        return await self.send_command("unload_model", data)
    
    async def set_transform(self, entity_id: str, pos: tuple = None, rot_deg: tuple = None, scale: tuple = None):
        """Установка трансформации объекта"""
        data = {"entity_id": entity_id}
        
        if pos:
            data["pos"] = list(pos)
            data["use_pos"] = True
        if rot_deg:
            data["rot_deg"] = list(rot_deg)
            data["use_rot"] = True
        if scale:
            data["scale"] = list(scale)
            data["use_scale"] = True
            
        return await self.send_command("set_transform", data)
    
    async def set_camera(self, pos: tuple, target: tuple, fov_deg: float = 60.0, near: float = 0.1, far: float = 1000.0):
        """Установка камеры"""
        data = {
            "pos": list(pos),
            "target": list(target),
            "fov_deg": fov_deg,
            "near": near,
            "far": far
        }
        return await self.send_command("set_camera", data)
    
    async def set_trajectory(self, entity_id: str, points: list, color_rgba: tuple = None, width: float = 2.0):
        """Установка траектории"""
        data = {
            "entity_id": entity_id,
            "points": [list(point) for point in points],
            "width": width
        }
        if color_rgba:
            data["color_rgba"] = list(color_rgba)
        return await self.send_command("set_trajectory", data)
    
    async def add_trajectory_point(self, entity_id: str, point: tuple):
        """Добавление точки к траектории"""
        data = {
            "entity_id": entity_id,
            "point": list(point)
        }
        return await self.send_command("add_trajectory_point", data)
    
    async def clear_trajectory(self, entity_id: str):
        """Очистка траектории"""
        data = {"entity_id": entity_id}
        return await self.send_command("clear_trajectory", data)
    
    async def set_joint(self, joint_name: str = None, entity_id: str = None, angle_deg: float = 0.0, axis: tuple = None):
        """Установка угла сустава"""
        data = {"angle_deg": angle_deg}
        if joint_name:
            data["joint_name"] = joint_name
        if entity_id:
            data["entity_id"] = entity_id
        if axis:
            data["axis"] = list(axis)
        return await self.send_command("set_joint", data)
    
    async def get_joint(self, joint_name: str = None, entity_id: str = None):
        """Получение угла сустава"""
        data = {}
        if joint_name:
            data["joint_name"] = joint_name
        if entity_id:
            data["entity_id"] = entity_id
        return await self.send_command("get_joint", data)
    
    async def start_dispensing(self, entity_id: str, flow_rate: float = 1.0, radius: float = 0.02, color_rgba: tuple = None):
        """Начать нанесение материала"""
        data = {"entity_id": entity_id, "flow_rate": flow_rate, "radius": radius}
        if color_rgba:
            data["color_rgba"] = list(color_rgba)
        return await self.send_command("start_dispensing", data)
    
    async def stop_dispensing(self, entity_id: str):
        """Остановить нанесение материала"""
        data = {"entity_id": entity_id}
        return await self.send_command("stop_dispensing", data)
    
    async def simulate_step(self, step_count: int = 1, delta_time: float = 1.0/60.0):
        """Выполнить шаг симуляции"""
        data = {"step_count": step_count, "delta_time": delta_time}
        return await self.send_command("simulate_step", data)
    
    async def clear_scene(self, mode: str = None):
        """Очистка сцены"""
        data = {}
        if mode:
            data["mode"] = mode
        return await self.send_command("clear_scene", data)
    
    async def query_collisions(self, entity_id: str = None):
        """Запрос информации о коллизиях"""
        data = {}
        if entity_id:
            data["entity_id"] = entity_id
        return await self.send_command("query_collisions", data)

    async def check_reachability(self, pos: tuple, entity_id: str = None):
        """Проверка достижимости позиции (обратная кинематика). Требует поддержки движка."""
        data = {"pos": list(pos)}
        if entity_id:
            data["entity_id"] = entity_id
        return await self.send_command("check_reachability", data)
    
    def register_response_handler(self, cmd_or_event: str, handler: Callable[[Dict[str, Any]], None]):
        """Регистрация обработчика для ответов или событий"""
        self.response_handlers[cmd_or_event] = handler
    
    def unregister_response_handler(self, cmd_or_event: str):
        """Удаление обработчика"""
        if cmd_or_event in self.response_handlers:
            del self.response_handlers[cmd_or_event]


# Пример использования
async def example_usage():
    client = KengaWebSocketClient()
    
    if await client.connect():
        print("Подключено к движку Kenga")
        
        # Пример загрузки модели
        try:
            response = await client.load_model(path="assets/robot.gltf", entity_id="robot1", name="MyRobot")
            print(f"Загрузка модели: {response}")
        except Exception as e:
            print(f"Ошибка загрузки модели: {e}")
        
        # Пример установки трансформации
        try:
            response = await client.set_transform("robot1", pos=(0, 0, 0), rot_deg=(0, 0, 0))
            print(f"Установка трансформации: {response}")
        except Exception as e:
            print(f"Ошибка установки трансформации: {e}")
        
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(example_usage())