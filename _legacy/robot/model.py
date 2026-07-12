"""
Модель робота для KengaCAD
"""
from typing import Dict, List, Tuple, Optional
import asyncio
from engine.websocket_client import KengaWebSocketClient


class RobotModel:
    def __init__(self, client: KengaWebSocketClient, entity_id: str, joints_config: Dict[str, dict] = None):
        self.client = client
        self.entity_id = entity_id
        self.joints_config = joints_config or {}
        self.current_angles = {}
        self.trajectory_points = []
        
        # Инициализируем углы суставов
        for joint_name in self.joints_config.keys():
            self.current_angles[joint_name] = 0.0
    
    async def load_model(self, model_path: str) -> bool:
        """Загрузка 3D модели робота в сцену"""
        try:
            response = await self.client.load_model(path=model_path, entity_id=self.entity_id)
            if response.get('ok'):
                print(f"Модель робота {self.entity_id} успешно загружена")
                return True
            else:
                print(f"Ошибка загрузки модели: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при загрузке модели: {e}")
            return False
    
    async def set_joint_angle(self, joint_name: str, angle_deg: float) -> bool:
        """Установка угла сустава"""
        if joint_name not in self.joints_config:
            print(f"Сустав {joint_name} не существует в конфигурации робота")
            return False
        
        try:
            response = await self.client.set_joint(
                entity_id=self.entity_id,
                joint_name=joint_name,
                angle_deg=angle_deg
            )
            if response.get('ok'):
                self.current_angles[joint_name] = angle_deg
                print(f"Угол сустава {joint_name} установлен в {angle_deg}°")
                return True
            else:
                print(f"Ошибка установки угла сустава: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при установке угла сустава: {e}")
            return False
    
    async def get_joint_angle(self, joint_name: str) -> Optional[float]:
        """Получение текущего угла сустава"""
        if joint_name not in self.joints_config:
            print(f"Сустав {joint_name} не существует в конфигурации робота")
            return None
        
        try:
            response = await self.client.get_joint(
                entity_id=self.entity_id,
                joint_name=joint_name
            )
            if response.get('ok'):
                angle = response.get('data', {}).get('angle_deg')
                self.current_angles[joint_name] = angle
                return angle
            else:
                print(f"Ошибка получения угла сустава: {response.get('error', 'Неизвестная ошибка')}")
                return None
        except Exception as e:
            print(f"Ошибка при получении угла сустава: {e}")
            return None
    
    async def set_all_joints(self, angles: Dict[str, float]) -> bool:
        """Установка углов всех суставов"""
        success = True
        for joint_name, angle in angles.items():
            if not await self.set_joint_angle(joint_name, angle):
                success = False
        return success
    
    async def get_all_joints(self) -> Dict[str, float]:
        """Получение углов всех суставов"""
        angles = {}
        for joint_name in self.joints_config.keys():
            angle = await self.get_joint_angle(joint_name)
            if angle is not None:
                angles[joint_name] = angle
        return angles
    
    async def add_trajectory_point(self, point: Tuple[float, float, float]) -> bool:
        """Добавление точки к траектории робота"""
        try:
            response = await self.client.add_trajectory_point(
                entity_id=f"{self.entity_id}_trajectory",
                point=point
            )
            if response.get('ok'):
                self.trajectory_points.append(point)
                print(f"Точка {point} добавлена к траектории")
                return True
            else:
                print(f"Ошибка добавления точки к траектории: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при добавлении точки к траектории: {e}")
            return False
    
    async def set_trajectory(self, points: List[Tuple[float, float, float]], 
                           color_rgba: Tuple[int, int, int, int] = (255, 200, 80, 255), 
                           width: float = 2.0) -> bool:
        """Установка всей траектории"""
        try:
            response = await self.client.set_trajectory(
                entity_id=f"{self.entity_id}_trajectory",
                points=points,
                color_rgba=color_rgba,
                width=width
            )
            if response.get('ok'):
                self.trajectory_points = points.copy()
                print(f"Траектория из {len(points)} точек установлена")
                return True
            else:
                print(f"Ошибка установки траектории: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при установке траектории: {e}")
            return False
    
    async def clear_trajectory(self) -> bool:
        """Очистка траектории"""
        try:
            response = await self.client.clear_trajectory(entity_id=f"{self.entity_id}_trajectory")
            if response.get('ok'):
                self.trajectory_points = []
                print("Траектория очищена")
                return True
            else:
                print(f"Ошибка очистки траектории: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при очистке траектории: {e}")
            return False
    
    async def start_dispensing(self, flow_rate: float = 1.0, radius: float = 0.02, 
                              color_rgba: Tuple[int, int, int, int] = (255, 220, 120, 255)) -> bool:
        """Начать нанесение материала (мастики)"""
        try:
            response = await self.client.start_dispensing(
                entity_id=self.entity_id,
                flow_rate=flow_rate,
                radius=radius,
                color_rgba=color_rgba
            )
            if response.get('ok'):
                print("Начато нанесение материала")
                return True
            else:
                print(f"Ошибка начала нанесения: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при начале нанесения материала: {e}")
            return False
    
    async def stop_dispensing(self) -> bool:
        """Остановить нанесение материала"""
        try:
            response = await self.client.stop_dispensing(entity_id=self.entity_id)
            if response.get('ok'):
                print("Нанесение материала остановлено")
                return True
            else:
                print(f"Ошибка остановки нанесения: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при остановке нанесения материала: {e}")
            return False
    
    async def move_to_position(self, position: Tuple[float, float, float], 
                             duration: float = 1.0) -> bool:
        """Перемещение робота в позицию (упрощенная симуляция)"""
        # В реальной реализации это включало бы кинематический расчет
        # и последовательное изменение углов суставов
        
        # Для простоты просто обновим позицию в сцене
        try:
            response = await self.client.set_transform(
                entity_id=self.entity_id,
                pos=position
            )
            if response.get('ok'):
                print(f"Робот перемещен в позицию {position}")
                return True
            else:
                print(f"Ошибка перемещения: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при перемещении робота: {e}")
            return False
    
    def get_info(self) -> Dict:
        """Получение информации о роботе"""
        return {
            "entity_id": self.entity_id,
            "joint_count": len(self.joints_config),
            "current_angles": self.current_angles.copy(),
            "trajectory_points_count": len(self.trajectory_points),
            "joints_config": self.joints_config
        }


# Пример конфигурации 6-осевого робота
DEFAULT_6_AXIS_ROBOT_CONFIG = {
    "joint_1": {"type": "revolute", "axis": [0, 0, 1], "limits": [-180, 180]},
    "joint_2": {"type": "revolute", "axis": [0, 1, 0], "limits": [-90, 90]},
    "joint_3": {"type": "revolute", "axis": [0, 1, 0], "limits": [-90, 90]},
    "joint_4": {"type": "revolute", "axis": [0, 0, 1], "limits": [-180, 180]},
    "joint_5": {"type": "revolute", "axis": [0, 1, 0], "limits": [-90, 90]},
    "joint_6": {"type": "revolute", "axis": [0, 0, 1], "limits": [-180, 180]},
}