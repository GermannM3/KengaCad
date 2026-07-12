"""
Пример Python клиента для управления движком Kenga через WebSocket API
"""
import asyncio
import websockets
import json
import uuid


class KengaExampleClient:
    def __init__(self, uri="ws://127.0.0.1:7777/ws"):
        self.uri = uri
        self.websocket = None
        self.connected = False
    
    async def connect(self):
        """Подключение к движку Kenga"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print(f"Подключено к движку Kenga: {self.uri}")
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от движка Kenga"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("Отключено от движка Kenga")
    
    async def send_command(self, cmd, data=None):
        """Отправка команды в движок"""
        if not self.connected:
            print("Нет подключения к движку")
            return None
        
        request_id = str(uuid.uuid4())
        message = {
            "cmd": cmd,
            "request_id": request_id
        }
        
        if data:
            message["data"] = data
        
        await self.websocket.send(json.dumps(message))
        
        # Ждем ответ
        response = await self.websocket.recv()
        return json.loads(response)
    
    # Примеры использования команд
    async def example_load_model(self):
        """Пример загрузки модели"""
        print("\n--- Пример: Загрузка модели ---")
        response = await self.send_command("load_model", {
            "path": "assets/robot.gltf",
            "entity_id": "my_robot",
            "name": "TestRobot"
        })
        print(f"Ответ: {response}")
    
    async def example_set_joint(self):
        """Пример установки угла сустава"""
        print("\n--- Пример: Установка угла сустава ---")
        response = await self.send_command("set_joint", {
            "entity_id": "my_robot",
            "joint_name": "joint_1",
            "angle_deg": 45.0,
            "axis": [0, 1, 0]
        })
        print(f"Ответ: {response}")
    
    async def example_get_joint(self):
        """Пример получения угла сустава"""
        print("\n--- Пример: Получение угла сустава ---")
        response = await self.send_command("get_joint", {
            "entity_id": "my_robot",
            "joint_name": "joint_1"
        })
        print(f"Ответ: {response}")
    
    async def example_simulate_step(self):
        """Пример шага симуляции"""
        print("\n--- Пример: Шаг симуляции ---")
        response = await self.send_command("simulate_step", {
            "step_count": 1,
            "delta_time": 1.0/60.0
        })
        print(f"Ответ: {response}")


async def main():
    # Создаем клиент
    client = KengaExampleClient()
    
    # Подключаемся к движку
    if await client.connect():
        # Выполняем примеры команд
        await client.example_load_model()
        await client.example_set_joint()
        await client.example_get_joint()
        await client.example_simulate_step()
        
        # Отключаемся
        await client.disconnect()
    else:
        print("Не удалось подключиться к движку Kenga")


if __name__ == "__main__":
    asyncio.run(main())