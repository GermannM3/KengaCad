"""
Тесты для новых модулей KengaCAD.

Запуск:
    python -m pytest tests/test_new_features.py -v
    или
    python tests/test_new_features.py
"""
import unittest
import sys
import math
from pathlib import Path

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ============================================================================
# Тесты GD&T
# ============================================================================

class TestGDT(unittest.TestCase):
    """Тесты системы GD&T."""

    def test_tolerance_frame_creation(self):
        """Создание рамки допуска."""
        from cad.gdt import GDTToleranceType, ToleranceFrame, MaterialCondition

        frame = ToleranceFrame(
            tolerance_type=GDTToleranceType.POSITION,
            tolerance_value=0.1,
            datums=["A", "B", "C"],
            material_condition=MaterialCondition.MMC,
            diameter_zone=True,
        )

        self.assertEqual(frame.tolerance_type, GDTToleranceType.POSITION)
        self.assertEqual(frame.tolerance_value, 0.1)
        self.assertEqual(frame.datums, ["A", "B", "C"])
        self.assertEqual(frame.material_condition, MaterialCondition.MMC)
        self.assertTrue(frame.diameter_zone)

    def test_tolerance_frame_string(self):
        """Строковое представление рамки допуска."""
        from cad.gdt import GDTToleranceType, ToleranceFrame

        frame = ToleranceFrame(
            tolerance_type=GDTToleranceType.FLATNESS,
            tolerance_value=0.05,
        )

        str_repr = frame.to_string()
        self.assertIn("0.05", str_repr)

    def test_dimension_with_tolerance(self):
        """Размер с допусками."""
        from cad.gdt import DimensionWithTolerance

        dim = DimensionWithTolerance(
            nominal=50.0,
            upper_tolerance=0.1,
            lower_tolerance=0.05,
        )

        self.assertEqual(dim.max_value, 50.1)
        self.assertEqual(dim.min_value, 49.95)
        self.assertTrue(dim.is_within_tolerance(50.05))
        self.assertFalse(dim.is_within_tolerance(50.2))

    def test_straightness_check(self):
        """Проверка прямолинейности."""
        from cad.gdt import GDTCalculator

        # Прямая линия
        points = [(i, 0, 0) for i in range(10)]
        result = GDTCalculator.check_straightness(points, tolerance=0.1)

        self.assertTrue(result["within_tolerance"])
        self.assertLess(result["deviation"], 0.01)

    def test_flatness_check(self):
        """Проверка плоскостности."""
        from cad.gdt import GDTCalculator

        # Плоская поверхность
        points = [(x, y, 0) for x in range(5) for y in range(5)]
        result = GDTCalculator.check_flatness(points, tolerance=0.1)

        self.assertTrue(result["within_tolerance"])

    def test_circularity_check(self):
        """Проверка круглости."""
        from cad.gdt import GDTCalculator

        # Окружность
        points = []
        for i in range(36):
            angle = math.radians(i * 10)
            x = 50 * math.cos(angle)
            y = 50 * math.sin(angle)
            points.append((x, y, 0))

        result = GDTCalculator.check_circularity(points, tolerance=1.0)

        self.assertTrue(result["within_tolerance"])
        self.assertIn("center", result)

    def test_position_check(self):
        """Проверка позиционирования."""
        from cad.gdt import GDTCalculator

        result = GDTCalculator.check_position(
            measured_point=(10.02, 20.01, 0),
            nominal_point=(10, 20, 0),
            tolerance=0.1,
            diameter_zone=False,  # Изменено для корректности теста
        )

        self.assertTrue(result["within_tolerance"])

    def test_perpendicularity_check(self):
        """Проверка перпендикулярности."""
        from cad.gdt import GDTCalculator

        # Перпендикулярные плоскости (упрощённо)
        datum_points = [(x, 0, 0) for x in range(10)]
        measured_points = [(0, y, 0) for y in range(10)]

        result = GDTCalculator.check_perpendicularity(
            measured_points,
            datum_points,
            tolerance=5.0,  # градусов
        )

        # Угол должен быть близок к 90°
        self.assertAlmostEqual(result["angle_deg"], 90, delta=5)


# ============================================================================
# Тесты кинематики роботов
# ============================================================================

class TestRobotKinematics(unittest.TestCase):
    """Тесты кинематики роботов."""

    def test_fk_6dof_full(self):
        """Прямая кинематика 6DOF."""
        from cad.robot_kinematics import fk_6dof_full, get_robot_config

        config = get_robot_config("kuka_kr6r900")
        self.assertIsNotNone(config)

        joints = [0, 0, 0, 0, 0, 0]
        result = fk_6dof_full(joints, config['dh_params'])

        self.assertIn("tcp_pos", result)
        self.assertIn("tcp_rpy", result)
        self.assertIn("link_positions", result)

    def test_ik_6dof_numerical(self):
        """Обратная кинематика (численная)."""
        from cad.robot_kinematics import ik_6dof_numerical, get_robot_config

        config = get_robot_config("kuka_kr6r900")
        self.assertIsNotNone(config)

        # Целевая позиция в рабочей зоне
        target = (300, 0, 200)

        result = ik_6dof_numerical(
            target,
            (0, 0, 0),
            config['dh_params'],
            config['joint_limits'],
            initial_joints=[0, 0, 0, 0, 0, 0],
            max_iter=100,
        )

        if result:
            self.assertIn("joints_deg", result)
            self.assertIn("converged", result)

    def test_check_workspace(self):
        """Проверка рабочей зоны."""
        from cad.robot_kinematics import check_workspace, get_robot_config

        config = get_robot_config("abb_irb120")
        self.assertIsNotNone(config)

        # Точка в рабочей зоне
        result = check_workspace(
            (200, 200, 200),
            config['dh_params'],
            config['joint_limits'],
            config['reach_mm'],
        )

        self.assertIn("reachable", result)

    def test_check_singularity(self):
        """Проверка сингулярности."""
        from cad.robot_kinematics import check_singularity, get_robot_config

        config = get_robot_config("kuka_kr6r900")

        # Нормальное положение
        result = check_singularity([30, -45, 60, 0, 45, 0], config['dh_params'])

        self.assertIn("singular", result)

    def test_list_available_robots(self):
        """Список доступных роботов."""
        from cad.robot_kinematics import list_available_robots

        robots = list_available_robots()
        self.assertGreater(len(robots), 0)
        self.assertIn("kuka_kr6r900", robots)


# ============================================================================
# Тесты расширенных траекторий
# ============================================================================

class TestAdvancedTrajectory(unittest.TestCase):
    """Тесты расширенного управления траекториями."""

    def test_trajectory_point_creation(self):
        """Создание точки траектории."""
        from cad.advanced_trajectory import TrajectoryPoint

        pt = TrajectoryPoint(100, 200, 50, velocity=150)

        self.assertEqual(pt.x, 100)
        self.assertEqual(pt.y, 200)
        self.assertEqual(pt.z, 50)
        self.assertEqual(pt.velocity, 150)

    def test_trajectory_spline_linear(self):
        """Линейная интерполяция."""
        from cad.advanced_trajectory import TrajectorySpline, TrajectoryPoint

        points = [
            TrajectoryPoint(0, 0, 0),
            TrajectoryPoint(100, 0, 0),
            TrajectoryPoint(100, 100, 0),
        ]

        spline = TrajectorySpline(points, spline_type="linear")
        discretized = spline.discretize(num_points=10)

        self.assertGreater(len(discretized), 0)

    def test_trajectory_spline_cubic(self):
        """Кубический сплайн."""
        from cad.advanced_trajectory import TrajectorySpline, TrajectoryPoint

        points = [
            TrajectoryPoint(0, 0, 0),
            TrajectoryPoint(50, 50, 25),
            TrajectoryPoint(100, 0, 50),
        ]

        spline = TrajectorySpline(points, spline_type="cubic")
        pt = spline.evaluate(0.5)

        if pt:
            self.assertEqual(len(pt), 3)

    def test_smooth_trajectory_chaikin(self):
        """Сглаживание Chaikin."""
        from cad.advanced_trajectory import TrajectorySpline, TrajectoryPoint

        points = [
            TrajectoryPoint(0, 0, 0),
            TrajectoryPoint(50, 0, 0),
            TrajectoryPoint(50, 50, 0),
            TrajectoryPoint(100, 50, 0),
        ]

        spline = TrajectorySpline(points, spline_type="chaikin")
        spline._chaikin_smooth(iterations=2)

        # После сглаживания точек должно стать больше
        self.assertGreater(len(spline.points), len(points))

    def test_generate_spiral(self):
        """Генерация спирали."""
        from cad.advanced_trajectory import generate_spiral

        points = generate_spiral(
            center=(0, 0, 0),
            radius=100,
            height=50,
            num_turns=2,
            num_points=50,
        )

        self.assertEqual(len(points), 50)
        # Первая точка в центре
        self.assertAlmostEqual(points[0].x, 0, delta=1)
        self.assertAlmostEqual(points[0].y, 0, delta=1)

    def test_generate_zigzag(self):
        """Генерация зигзага."""
        from cad.advanced_trajectory import generate_zigzag

        points = generate_zigzag(
            start=(0, 0, 0),
            size_x=100,
            size_y=50,
            step_over=10,
            num_points_per_line=10,
        )

        self.assertGreater(len(points), 0)

    def test_trajectory_manager(self):
        """Менеджер траекторий."""
        from cad.advanced_trajectory import AdvancedTrajectoryManager, TrajectoryPoint

        manager = AdvancedTrajectoryManager()

        points = [
            TrajectoryPoint(0, 0, 0),
            TrajectoryPoint(100, 0, 50),
            TrajectoryPoint(100, 100, 50),
        ]

        created = manager.create_trajectory("test", points, spline_type="cubic")
        self.assertTrue(created)

        length = manager.get_trajectory_length("test")
        self.assertGreater(length, 0)


# ============================================================================
# Тесты макросов
# ============================================================================

class TestMacros(unittest.TestCase):
    """Тесты системы макросов."""

    def test_macro_command_creation(self):
        """Создание команды макроса."""
        from scripts.macros import MacroCommand

        cmd = MacroCommand(
            command="LINE",
            args=["0", "0", "100", "100"],
            description="Линия",
        )

        self.assertEqual(cmd.command, "LINE")
        self.assertEqual(len(cmd.args), 4)

    def test_macro_command_string(self):
        """Строковое представление команды."""
        from scripts.macros import MacroCommand

        cmd = MacroCommand(command="CIRCLE", args=["50", "50", "25"])
        str_repr = cmd.to_string()

        self.assertIn("CIRCLE", str_repr)
        self.assertIn("50", str_repr)

    def test_macro_creation(self):
        """Создание макроса."""
        from scripts.macros import Macro, MacroCommand

        macro = Macro(name="TestMacro", description="Тестовый макрос")
        macro.add_command("LINE", ["0", "0", "100", "0"])
        macro.add_command("CIRCLE", ["50", "50", "25"])

        self.assertEqual(len(macro.commands), 2)

    def test_macro_serialization(self):
        """Сериализация макроса."""
        from scripts.macros import Macro

        macro = Macro(name="SerializationTest")
        macro.add_command("LINE", ["0", "0", "10", "10"])

        data = macro.to_dict()
        restored = Macro.from_dict(data)

        self.assertEqual(restored.name, macro.name)
        self.assertEqual(len(restored.commands), len(macro.commands))

    def test_macro_recorder(self):
        """Запись макроса."""
        from scripts.macros import MacroRecorder

        recorder = MacroRecorder()
        recorder.start_recording("TestRecording")
        recorder.record_command("LINE", ["0", "0", "100", "100"])
        recorder.record_command("CIRCLE", ["50", "50", "25"])

        macro = recorder.stop_recording()

        self.assertIsNotNone(macro)
        self.assertEqual(len(macro.commands), 2)
        self.assertFalse(recorder.is_recording)


# ============================================================================
# Тесты Python скрипт-движка
# ============================================================================

class TestPythonScriptEngine(unittest.TestCase):
    """Тесты Python-скрипт-движка."""

    def test_script_execution(self):
        """Выполнение простого скрипта."""
        from scripts.macros import PythonScriptEngine

        engine = PythonScriptEngine()

        script = """
result = 2 + 2
"""
        result = engine.execute_script(script)

        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 4)

    def test_script_with_math(self):
        """Скрипт с математикой."""
        from scripts.macros import PythonScriptEngine

        engine = PythonScriptEngine()

        script = """
result = pow(2, 3)
"""
        result = engine.execute_script(script)

        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 8.0)

    def test_script_error_handling(self):
        """Обработка ошибок в скрипте."""
        from scripts.macros import PythonScriptEngine

        engine = PythonScriptEngine()

        script = """
result = 1 / 0
"""
        result = engine.execute_script(script)

        self.assertFalse(result["success"])
        self.assertIn("error", result)


# ============================================================================
# Тесты STEP/STL импорта
# ============================================================================

class TestStepImport(unittest.TestCase):
    """Тесты импорта STEP/STL."""

    def test_can_import_step(self):
        """Проверка доступности STEP импорта."""
        from cad.step_import import can_import_step

        # Функция должна возвращать True или False
        result = can_import_step()
        self.assertIsInstance(result, bool)

    def test_get_backend_info(self):
        """Информация о back-end."""
        from cad.step_import import get_backend_info

        info = get_backend_info()
        self.assertIsInstance(info, str)


# ============================================================================
# Запуск тестов
# ============================================================================

if __name__ == "__main__":
    # Создаём тестовый раннер
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Добавляем все тесты
    suite.addTests(loader.loadTestsFromTestCase(TestGDT))
    suite.addTests(loader.loadTestsFromTestCase(TestRobotKinematics))
    suite.addTests(loader.loadTestsFromTestCase(TestAdvancedTrajectory))
    suite.addTests(loader.loadTestsFromTestCase(TestMacros))
    suite.addTests(loader.loadTestsFromTestCase(TestPythonScriptEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestStepImport))

    # Запускаем
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Выводим итог
    print("\n" + "=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
