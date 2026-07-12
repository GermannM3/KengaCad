# API Documentation for KengaCAD

## Overview

KengaCAD использует WebSocket API для взаимодействия с движком Kenga. Все команды передаются в формате JSON.

## Message Format

### Command Request
```json
{
  "cmd": "command_name",
  "request_id": "unique_request_id",
  "data": { ... }
}
```

### Response
```json
{
  "ok": true/false,
  "cmd": "command_name",
  "request_id": "unique_request_id",
  "error": "error_message_if_any",
  "data": { ... }
}
```

## Available Commands

### 1. load_model
Загружает 3D модель в сцену.

**Request:**
```json
{
  "cmd": "load_model",
  "data": {
    "asset_id": "UUID_of_asset",
    "path": "relative/path/to/model.gltf",
    "entity_id": "logical_entity_name",
    "name": "human_readable_name"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "cmd": "load_model",
  "request_id": "..."
}
```

### 2. unload_model
Выгружает 3D модель из сцены.

**Request:**
```json
{
  "cmd": "unload_model",
  "data": {
    "entity_id": "logical_entity_name"
  }
}
```

### 3. set_transform
Устанавливает трансформацию (позиция, вращение, масштаб) объекта.

**Request:**
```json
{
  "cmd": "set_transform",
  "data": {
    "entity_id": "entity_name",
    "pos": [x, y, z],
    "rot_deg": [rx, ry, rz],
    "scale": [sx, sy, sz],
    "use_pos": true,
    "use_rot": true,
    "use_scale": true
  }
}
```

### 4. set_camera
Устанавливает параметры камеры.

**Request:**
```json
{
  "cmd": "set_camera",
  "data": {
    "pos": [x, y, z],
    "target": [x, y, z],
    "fov_deg": 60.0,
    "near": 0.1,
    "far": 1000.0
  }
}
```

### 5. set_trajectory
Устанавливает траекторию с точками.

**Request:**
```json
{
  "cmd": "set_trajectory",
  "data": {
    "entity_id": "trajectory_name",
    "points": [[x1, y1, z1], [x2, y2, z2], ...],
    "color_rgba": [255, 200, 80, 255],
    "width": 2.0
  }
}
```

### 6. add_trajectory_point
Добавляет точку к существующей траектории.

**Request:**
```json
{
  "cmd": "add_trajectory_point",
  "data": {
    "entity_id": "trajectory_name",
    "point": [x, y, z]
  }
}
```

### 7. clear_trajectory
Очищает траекторию.

**Request:**
```json
{
  "cmd": "clear_trajectory",
  "data": {
    "entity_id": "trajectory_name"
  }
}
```

### 8. set_joint
Устанавливает угол сустава робота.

**Request:**
```json
{
  "cmd": "set_joint",
  "data": {
    "entity_id": "robot_entity",
    "joint_name": "joint_name",
    "angle_deg": 45.0,
    "axis": [0, 1, 0]
  }
}
```

### 9. get_joint
Получает текущий угол сустава робота.

**Request:**
```json
{
  "cmd": "get_joint",
  "data": {
    "entity_id": "robot_entity",
    "joint_name": "joint_name"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "cmd": "get_joint",
  "request_id": "...",
  "data": {
    "entity_id": "robot_entity",
    "joint_name": "joint_name",
    "angle_deg": 45.0,
    "axis": [0, 1, 0]
  }
}
```

### 10. start_dispensing
Начинает нанесение материала (мастики).

**Request:**
```json
{
  "cmd": "start_dispensing",
  "data": {
    "entity_id": "robot_entity",
    "flow_rate": 1.5,
    "radius": 0.02,
    "color_rgba": [255, 220, 120, 255]
  }
}
```

### 11. stop_dispensing
Останавливает нанесение материала.

**Request:**
```json
{
  "cmd": "stop_dispensing",
  "data": {
    "entity_id": "robot_entity"
  }
}
```

### 12. simulate_step
Выполняет шаг симуляции.

**Request:**
```json
{
  "cmd": "simulate_step",
  "data": {
    "step_count": 1,
    "delta_time": 0.01667
  }
}
```

### 13. clear_scene
Очищает сцену.

**Request:**
```json
{
  "cmd": "clear_scene",
  "data": {
    "mode": "play"
  }
}
```

### 14. query_collisions
Запрашивает информацию о коллизиях.

**Request:**
```json
{
  "cmd": "query_collisions",
  "data": {
    "entity_id": "optional_entity_filter"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "cmd": "query_collisions",
  "request_id": "...",
  "data": {
    "collisions": [
      {
        "entity_a": "entity1",
        "entity_b": "entity2",
        "point": [x, y, z],
        "normal": [nx, ny, nz]
      }
    ]
  }
}
```

### 15. check_reachability
Проверка достижимости позиции (обратная кинематика). Требует поддержки движка.

**Request:**
```json
{
  "cmd": "check_reachability",
  "data": {
    "pos": [x, y, z],
    "entity_id": "optional_robot_entity"
  }
}
```

**Response:**
```json
{
  "ok": true,
  "cmd": "check_reachability",
  "request_id": "...",
  "data": {
    "reachable": true,
    "joints": [j1, j2, j3, j4, j5, j6]
  }
}
```

## Python Client Example

```python
import asyncio
import websockets
import json
import uuid

class KengaWebSocketClient:
    def __init__(self, uri: str = "ws://127.0.0.1:7777/ws"):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.request_callbacks = {}

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    async def send_command(self, cmd: str, data: dict = None, timeout: float = 10.0):
        if not self.connected or not self.websocket:
            raise ConnectionError("Not connected to Kenga engine")

        request_id = str(uuid.uuid4())
        message = {
            "cmd": cmd,
            "request_id": request_id
        }

        if data:
            message["data"] = data

        await self.websocket.send(json.dumps(message))

        # Wait for response
        response = await self.websocket.recv()
        return json.loads(response)

# Usage example
async def example():
    client = KengaWebSocketClient()
    
    if await client.connect():
        # Load a robot model
        response = await client.send_command("load_model", {
            "path": "assets/robot.gltf",
            "entity_id": "my_robot",
            "name": "TestRobot"
        })
        print(f"Load model response: {response}")
        
        # Set a joint angle
        response = await client.send_command("set_joint", {
            "entity_id": "my_robot",
            "joint_name": "joint_1",
            "angle_deg": 45.0
        })
        print(f"Set joint response: {response}")

if __name__ == "__main__":
    asyncio.run(example())
```