#!/usr/bin/env python3
"""
Финальное тестирование производительности KengaCAD.

Тесты:
  - Время запуска приложения
  - Производительность кинематики
  - Производительность траекторий
  - Производительность GD&T вычислений
  - Потребление памяти
  - Время отрисовки

Запуск:
    python tests/benchmark_performance.py
"""
import os
import sys
import time
import tracemalloc
import statistics
from pathlib import Path
from datetime import datetime

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class BenchmarkResult:
    """Результат бенчмарка."""

    def __init__(self, name: str):
        self.name = name
        self.times = []
        self.memory_peak = 0
        self.memory_current = 0

    def add_time(self, time_ms: float):
        self.times.append(time_ms)

    @property
    def avg_time(self) -> float:
        return statistics.mean(self.times) if self.times else 0

    @property
    def min_time(self) -> float:
        return min(self.times) if self.times else 0

    @property
    def max_time(self) -> float:
        return max(self.times) if self.times else 0

    @property
    def std_dev(self) -> float:
        return statistics.stdev(self.times) if len(self.times) > 1 else 0

    def __str__(self):
        return (
            f"{self.name}:\n"
            f"  Среднее: {self.avg_time:.2f} мс\n"
            f"  Мин: {self.min_time:.2f} мс\n"
            f"  Макс: {self.max_time:.2f} мс\n"
            f"  Стд. отклонение: {self.std_dev:.2f} мс\n"
            f"  Пик памяти: {self.memory_peak / 1024 / 1024:.2f} МБ"
        )


def benchmark_function(func, *args, iterations: int = 10, track_memory: bool = True) -> BenchmarkResult:
    """Бенчмарк функции."""
    result = BenchmarkResult(func.__name__)

    for i in range(iterations):
        if track_memory:
            tracemalloc.start()

        start = time.perf_counter()
        func(*args)
        elapsed = (time.perf_counter() - start) * 1000  # мс

        if track_memory:
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            result.memory_peak = max(result.memory_peak, peak)
            result.memory_current = current

        result.add_time(elapsed)

    return result


# ============================================================================
# Бенчмарки кинематики
# ============================================================================

def benchmark_fk_6dof():
    """Прямая кинематика 6DOF."""
    from cad.robot_kinematics import fk_6dof_full, get_robot_config

    config = get_robot_config("kuka_kr6r900")
    joints = [30, -45, 60, 0, 45, 0]

    fk_6dof_full(joints, config['dh_params'])


def benchmark_ik_6dof():
    """Обратная кинематика 6DOF."""
    from cad.robot_kinematics import ik_6dof_numerical, get_robot_config

    config = get_robot_config("kuka_kr6r900")
    target = (300, 0, 200)

    ik_6dof_numerical(
        target,
        (0, 0, 0),
        config['dh_params'],
        config['joint_limits'],
        initial_joints=[0, 0, 0, 0, 0, 0],
        max_iter=50,
    )


def benchmark_workspace_check():
    """Проверка рабочей зоны."""
    from cad.robot_kinematics import check_workspace, get_robot_config

    config = get_robot_config("abb_irb120")

    for _ in range(10):
        check_workspace(
            (200, 200, 200),
            config['dh_params'],
            config['joint_limits'],
            config['reach_mm'],
        )


# ============================================================================
# Бенчмарки траекторий
# ============================================================================

def benchmark_trajectory_create():
    """Создание траектории."""
    from cad.advanced_trajectory import AdvancedTrajectoryManager, TrajectoryPoint

    manager = AdvancedTrajectoryManager()
    points = [TrajectoryPoint(i * 10, i * 5, i * 2) for i in range(20)]

    manager.create_trajectory("test", points, spline_type="cubic")


def benchmark_trajectory_smooth():
    """Сглаживание траектории."""
    from cad.advanced_trajectory import AdvancedTrajectoryManager, TrajectoryPoint

    manager = AdvancedTrajectoryManager()
    points = [TrajectoryPoint(i * 10, 0, 0) for i in range(50)]
    manager.create_trajectory("test", points, spline_type="linear")

    manager.smooth_trajectory("test", method="chaikin", iterations=2)


def benchmark_trajectory_discretize():
    """Дискретизация траектории."""
    from cad.advanced_trajectory import AdvancedTrajectoryManager, TrajectoryPoint

    manager = AdvancedTrajectoryManager()
    points = [
        TrajectoryPoint(0, 0, 0),
        TrajectoryPoint(100, 50, 25),
        TrajectoryPoint(200, 0, 50),
        TrajectoryPoint(300, 100, 25),
    ]
    manager.create_trajectory("test", points, spline_type="cubic")

    manager.discretize_trajectory("test", num_points=100)


# ============================================================================
# Бенчмарки GD&T
# ============================================================================

def benchmark_gdt_flatness():
    """Проверка плоскостности."""
    from cad.gdt import GDTCalculator

    points = [(x, y, 0) for x in range(20) for y in range(20)]

    GDTCalculator.check_flatness(points, tolerance=0.1)


def benchmark_gdt_circularity():
    """Проверка круглости."""
    from cad.gdt import GDTCalculator
    import math

    points = []
    for i in range(100):
        angle = math.radians(i * 3.6)
        x = 50 * math.cos(angle)
        y = 50 * math.sin(angle)
        points.append((x, y, 0))

    GDTCalculator.check_circularity(points, tolerance=1.0)


def benchmark_gdt_position():
    """Проверка позиционирования."""
    from cad.gdt import GDTCalculator

    for _ in range(50):
        GDTCalculator.check_position(
            (10.05, 20.03, 0),
            (10, 20, 0),
            tolerance=0.1,
            diameter_zone=True,
        )


# ============================================================================
# Бенчмарки импорта
# ============================================================================

def benchmark_step_import_check():
    """Проверка доступности STEP импорта."""
    from cad.step_import import can_import_step, get_backend_info

    can_import_step()
    get_backend_info()


# ============================================================================
# Главный бенчмарк
# ============================================================================

def run_all_benchmarks():
    """Запуск всех бенчмарков."""
    print("=" * 70)
    print(f" KengaCAD v2.0.0 - Бенчмарк производительности")
    print(f" Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    results = []

    # Кинематика
    print("Кинематика...")
    results.append(benchmark_function(benchmark_fk_6dof, iterations=100))
    results.append(benchmark_function(benchmark_ik_6dof, iterations=20))
    results.append(benchmark_function(benchmark_workspace_check, iterations=50))

    # Траектории
    print("Траектории...")
    results.append(benchmark_function(benchmark_trajectory_create, iterations=50))
    results.append(benchmark_function(benchmark_trajectory_smooth, iterations=20))
    results.append(benchmark_function(benchmark_trajectory_discretize, iterations=50))

    # GD&T
    print("GD&T...")
    results.append(benchmark_function(benchmark_gdt_flatness, iterations=50))
    results.append(benchmark_function(benchmark_gdt_circularity, iterations=30))
    results.append(benchmark_function(benchmark_gdt_position, iterations=100))

    # Импорт
    print("Импорт...")
    results.append(benchmark_function(benchmark_step_import_check, iterations=100))

    # Вывод результатов
    print("\n" + "=" * 70)
    print(" РЕЗУЛЬТАТЫ")
    print("=" * 70)

    for result in results:
        print()
        print(result)

    # Итог
    print("\n" + "=" * 70)
    total_avg = sum(r.avg_time for r in results)
    print(f" Общее среднее время всех операций: {total_avg:.2f} мс")
    print("=" * 70)

    # Сохранение результатов
    save_results(results)

    return results


def save_results(results: list):
    """Сохранение результатов в файл."""
    import json

    output = {
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "results": [
            {
                "name": r.name,
                "avg_ms": r.avg_time,
                "min_ms": r.min_time,
                "max_ms": r.max_time,
                "std_dev_ms": r.std_dev,
                "memory_peak_mb": r.memory_peak / 1024 / 1024,
            }
            for r in results
        ],
    }

    output_path = Path(__file__).parent.parent / "dist" / "benchmark_results.json"
    output_path.parent.mkdir(exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nРезультаты сохранены: {output_path}")


if __name__ == "__main__":
    run_all_benchmarks()
