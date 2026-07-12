"""
Управление траекториями для KengaCAD
"""
from typing import List, Tuple, Dict, Optional
import asyncio
import math
from engine.websocket_client import KengaWebSocketClient


class TrajectoryManager:
    def __init__(self, client: KengaWebSocketClient):
        self.client = client
        self.trajectories: Dict[str, List[Tuple[float, float, float]]] = {}
        self.colors: Dict[str, Tuple[int, int, int, int]] = {}
        self.widths: Dict[str, float] = {}
    
    async def create_trajectory(self, entity_id: str, 
                               points: List[Tuple[float, float, float]] = None,
                               color_rgba: Tuple[int, int, int, int] = (255, 200, 80, 255),
                               width: float = 2.0) -> bool:
        """Создание новой траектории"""
        if points is None:
            points = []
        
        self.trajectories[entity_id] = points[:]
        self.colors[entity_id] = color_rgba
        self.widths[entity_id] = width
        
        if points:
            try:
                response = await self.client.set_trajectory(
                    entity_id=entity_id,
                    points=points,
                    color_rgba=color_rgba,
                    width=width
                )
                if response.get('ok'):
                    print(f"Траектория {entity_id} создана с {len(points)} точками")
                    return True
                else:
                    print(f"Ошибка создания траектории: {response.get('error', 'Неизвестная ошибка')}")
                    return False
            except Exception as e:
                print(f"Ошибка при создании траектории: {e}")
                return False
        else:
            print(f"Траектория {entity_id} создана (пустая)")
            return True
    
    async def add_point(self, entity_id: str, point: Tuple[float, float, float]) -> bool:
        """Добавление точки к траектории"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return False
        
        self.trajectories[entity_id].append(point)
        
        try:
            response = await self.client.add_trajectory_point(
                entity_id=entity_id,
                point=point
            )
            if response.get('ok'):
                print(f"Точка {point} добавлена к траектории {entity_id}")
                return True
            else:
                print(f"Ошибка добавления точки: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при добавлении точки: {e}")
            return False
    
    async def remove_point(self, entity_id: str, index: int) -> bool:
        """Удаление точки из траектории по индексу"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return False
        
        if index < 0 or index >= len(self.trajectories[entity_id]):
            print(f"Индекс {index} вне диапазона для траектории {entity_id}")
            return False
        
        # Удаляем точку из внутреннего списка
        removed_point = self.trajectories[entity_id].pop(index)
        
        # Пересоздаем траекторию с оставшимися точками
        try:
            response = await self.client.set_trajectory(
                entity_id=entity_id,
                points=self.trajectories[entity_id],
                color_rgba=self.colors[entity_id],
                width=self.widths[entity_id]
            )
            if response.get('ok'):
                print(f"Точка {removed_point} удалена из траектории {entity_id}")
                return True
            else:
                print(f"Ошибка удаления точки: {response.get('error', 'Неизвестная ошибка')}")
                # Восстанавливаем точку в случае ошибки
                self.trajectories[entity_id].insert(index, removed_point)
                return False
        except Exception as e:
            print(f"Ошибка при удалении точки: {e}")
            # Восстанавливаем точку в случае ошибки
            self.trajectories[entity_id].insert(index, removed_point)
            return False
    
    async def update_point(self, entity_id: str, index: int, new_point: Tuple[float, float, float]) -> bool:
        """Обновление точки в траектории по индексу"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return False
        
        if index < 0 or index >= len(self.trajectories[entity_id]):
            print(f"Индекс {index} вне диапазона для траектории {entity_id}")
            return False
        
        # Сохраняем старую точку на случай ошибки
        old_point = self.trajectories[entity_id][index]
        self.trajectories[entity_id][index] = new_point
        
        # Пересоздаем траекторию с обновленной точкой
        try:
            response = await self.client.set_trajectory(
                entity_id=entity_id,
                points=self.trajectories[entity_id],
                color_rgba=self.colors[entity_id],
                width=self.widths[entity_id]
            )
            if response.get('ok'):
                print(f"Точка {index} в траектории {entity_id} обновлена с {old_point} на {new_point}")
                return True
            else:
                print(f"Ошибка обновления точки: {response.get('error', 'Неизвестная ошибка')}")
                # Восстанавливаем старую точку в случае ошибки
                self.trajectories[entity_id][index] = old_point
                return False
        except Exception as e:
            print(f"Ошибка при обновлении точки: {e}")
            # Восстанавливаем старую точку в случае ошибки
            self.trajectories[entity_id][index] = old_point
            return False
    
    async def clear_trajectory(self, entity_id: str) -> bool:
        """Очистка траектории"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return False
        
        self.trajectories[entity_id] = []
        
        try:
            response = await self.client.clear_trajectory(entity_id=entity_id)
            if response.get('ok'):
                print(f"Траектория {entity_id} очищена")
                return True
            else:
                print(f"Ошибка очистки траектории: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при очистке траектории: {e}")
            return False
    
    async def get_trajectory(self, entity_id: str) -> Optional[List[Tuple[float, float, float]]]:
        """Получение точек траектории"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return None
        
        return self.trajectories[entity_id][:]
    
    def get_trajectory_info(self, entity_id: str) -> Optional[Dict]:
        """Получение информации о траектории"""
        if entity_id not in self.trajectories:
            return None
        
        return {
            "entity_id": entity_id,
            "point_count": len(self.trajectories[entity_id]),
            "color_rgba": self.colors[entity_id],
            "width": self.widths[entity_id],
            "points": self.trajectories[entity_id][:]
        }
    
    async def interpolate_trajectory(self, entity_id: str, start_index: int, end_index: int, 
                                   num_intermediate_points: int) -> bool:
        """Интерполяция между двумя точками траектории"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return False
        
        trajectory = self.trajectories[entity_id]
        if start_index < 0 or end_index >= len(trajectory) or start_index >= end_index:
            print(f"Неверные индексы для интерполяции: {start_index}, {end_index}")
            return False
        
        start_point = trajectory[start_index]
        end_point = trajectory[end_index]
        
        # Вычисляем промежуточные точки
        intermediate_points = []
        for i in range(1, num_intermediate_points + 1):
            t = i / (num_intermediate_points + 1)
            interpolated_point = (
                start_point[0] + t * (end_point[0] - start_point[0]),
                start_point[1] + t * (end_point[1] - start_point[1]),
                start_point[2] + t * (end_point[2] - start_point[2])
            )
            intermediate_points.append(interpolated_point)
        
        # Вставляем промежуточные точки в траекторию
        for i, point in enumerate(intermediate_points):
            insert_index = start_index + 1 + i
            trajectory.insert(insert_index, point)
        
        # Обновляем траекторию в движке
        try:
            response = await self.client.set_trajectory(
                entity_id=entity_id,
                points=trajectory,
                color_rgba=self.colors[entity_id],
                width=self.widths[entity_id]
            )
            if response.get('ok'):
                print(f"Интерполяция выполнена: добавлено {len(intermediate_points)} точек между {start_index} и {end_index}")
                return True
            else:
                print(f"Ошибка интерполяции: {response.get('error', 'Неизвестная ошибка')}")
                # Откатываем изменения
                for _ in range(len(intermediate_points)):
                    trajectory.pop(start_index + 1)
                return False
        except Exception as e:
            print(f"Ошибка при интерполяции: {e}")
            # Откатываем изменения
            for _ in range(len(intermediate_points)):
                trajectory.pop(start_index + 1)
            return False
    
    async def smooth_trajectory(self, entity_id: str, smoothing_factor: float = 0.3) -> bool:
        """Сглаживание траектории"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return False
        
        trajectory = self.trajectories[entity_id]
        if len(trajectory) < 3:
            print(f"Недостаточно точек для сглаживания: {len(trajectory)}")
            return False
        
        # Применяем алгоритм сглаживания (упрощенная версия)
        smoothed_trajectory = trajectory[:]  # Создаем копию
        
        for i in range(1, len(trajectory) - 1):
            prev_point = trajectory[i - 1]
            curr_point = trajectory[i]
            next_point = trajectory[i + 1]
            
            # Вычисляем сглаженную точку как комбинацию текущей и соседних
            smoothed_trajectory[i] = (
                curr_point[0] * (1 - smoothing_factor) + 
                (prev_point[0] + next_point[0]) * smoothing_factor / 2,
                
                curr_point[1] * (1 - smoothing_factor) + 
                (prev_point[1] + next_point[1]) * smoothing_factor / 2,
                
                curr_point[2] * (1 - smoothing_factor) + 
                (prev_point[2] + next_point[2]) * smoothing_factor / 2
            )
        
        # Обновляем траекторию в движке
        try:
            response = await self.client.set_trajectory(
                entity_id=entity_id,
                points=smoothed_trajectory,
                color_rgba=self.colors[entity_id],
                width=self.widths[entity_id]
            )
            if response.get('ok'):
                self.trajectories[entity_id] = smoothed_trajectory
                print(f"Траектория {entity_id} сглажена (фактор: {smoothing_factor})")
                return True
            else:
                print(f"Ошибка сглаживания: {response.get('error', 'Неизвестная ошибка')}")
                return False
        except Exception as e:
            print(f"Ошибка при сглаживании: {e}")
            return False
    
    async def calculate_length(self, entity_id: str) -> Optional[float]:
        """Расчет длины траектории"""
        if entity_id not in self.trajectories:
            print(f"Траектория {entity_id} не существует")
            return None
        
        trajectory = self.trajectories[entity_id]
        if len(trajectory) < 2:
            return 0.0
        
        total_length = 0.0
        for i in range(1, len(trajectory)):
            p1 = trajectory[i-1]
            p2 = trajectory[i]
            
            # Вычисляем расстояние между двумя точками
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            dz = p2[2] - p1[2]
            distance = math.sqrt(dx*dx + dy*dy + dz*dz)
            
            total_length += distance
        
        return total_length


class Waypoint:
    """Класс для представления точки траектории с дополнительными параметрами"""
    def __init__(self, position: Tuple[float, float, float], 
                 velocity: float = 1.0, 
                 acceleration: float = 1.0,
                 dwell_time: float = 0.0,
                 process_params: Dict = None):
        self.position = position
        self.velocity = velocity
        self.acceleration = acceleration
        self.dwell_time = dwell_time  # Время задержки в этой точке
        self.process_params = process_params or {}  # Параметры процесса (например, для диспенсинга)
    
    def to_dict(self) -> Dict:
        """Преобразование в словарь"""
        return {
            "position": self.position,
            "velocity": self.velocity,
            "acceleration": self.acceleration,
            "dwell_time": self.dwell_time,
            "process_params": self.process_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        """Создание из словаря"""
        return cls(
            position=data.get("position", (0, 0, 0)),
            velocity=data.get("velocity", 1.0),
            acceleration=data.get("acceleration", 1.0),
            dwell_time=data.get("dwell_time", 0.0),
            process_params=data.get("process_params", {})
        )


class AdvancedTrajectoryManager(TrajectoryManager):
    """Расширенный менеджер траекторий с поддержкой вейпоинтов"""
    
    def __init__(self, client: KengaWebSocketClient):
        super().__init__(client)
        self.waypoints: Dict[str, List[Waypoint]] = {}
    
    async def create_waypoint_trajectory(self, entity_id: str, 
                                       waypoints: List[Waypoint],
                                       color_rgba: Tuple[int, int, int, int] = (255, 200, 80, 255),
                                       width: float = 2.0) -> bool:
        """Создание траектории с вейпоинтами"""
        # Извлекаем только позиции для визуализации
        positions = [wp.position for wp in waypoints]
        
        success = await self.create_trajectory(entity_id, positions, color_rgba, width)
        if success:
            self.waypoints[entity_id] = waypoints[:]
        
        return success
    
    async def add_waypoint(self, entity_id: str, waypoint: Waypoint) -> bool:
        """Добавление вейпоинта к траектории"""
        if entity_id not in self.waypoints:
            self.waypoints[entity_id] = []
        
        self.waypoints[entity_id].append(waypoint)
        
        # Добавляем только позицию в визуальную траекторию
        return await self.add_point(entity_id, waypoint.position)
    
    def get_waypoints(self, entity_id: str) -> Optional[List[Waypoint]]:
        """Получение вейпоинтов траектории"""
        if entity_id not in self.waypoints:
            return None
        
        return self.waypoints[entity_id][:]