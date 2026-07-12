"""
Тестовый файл для проверки работоспособности KengaCAD
"""
import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def test_imports():
    """Тестирование импортов основных модулей"""
    print("Тестируем импорты...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        print("+ PyQt6 импортирован успешно")
    except ImportError:
        try:
            from PyQt5.QtWidgets import QApplication
            print("+ PyQt5 импортирован успешно (вместо PyQt6)")
        except ImportError as e:
            print(f"- Ошибка импорта PyQt6/PyQt5: {e}")
            return False

    try:
        import websockets
        print("+ websockets импортирован успешно")
    except ImportError as e:
        print(f"- Ошибка импорта websockets: {e}")
        return False

    try:
        import ezdxf
        print("+ ezdxf импортирован успешно")
    except ImportError as e:
        print(f"- Ошибка импорта ezdxf: {e}")
        return False

    try:
        from engine.websocket_client import KengaWebSocketClient
        print("+ KengaWebSocketClient импортирован успешно")
    except ImportError as e:
        print(f"- Ошибка импорта KengaWebSocketClient: {e}")
        return False

    try:
        from robot.model import RobotModel
        print("+ RobotModel импортирован успешно")
    except ImportError as e:
        print(f"- Ошибка импорта RobotModel: {e}")
        return False

    try:
        from cad.trajectory import TrajectoryManager
        print("+ TrajectoryManager импортирован успешно")
    except ImportError as e:
        print(f"- Ошибка импорта TrajectoryManager: {e}")
        return False

    try:
        from cad.import_export import CADImportExport
        print("+ CADImportExport импортирован успешно")
    except ImportError as e:
        print(f"- Ошибка импорта CADImportExport: {e}")
        return False

    print("+ Все основные модули импортированы успешно!")
    return True


def test_basic_functionality():
    """Тестирование базовой функциональности"""
    print("\nТестируем базовую функциональность...")
    
    # Тестирование CADImportExport
    try:
        from cad.import_export import CADImportExport
        importer = CADImportExport()
        formats = importer.get_supported_formats()
        print(f"+ Поддерживаемые форматы: {list(formats.keys())}")
    except Exception as e:
        print(f"- Ошибка при тестировании CADImportExport: {e}")
        return False

    # Тестирование Waypoint
    try:
        from cad.trajectory import Waypoint
        wp = Waypoint((1, 2, 3), velocity=2.0, dwell_time=0.5)
        wp_dict = wp.to_dict()
        print(f"+ Waypoint создан и преобразован в словарь: {wp_dict['position']}")
    except Exception as e:
        print(f"- Ошибка при тестировании Waypoint: {e}")
        return False

    print("+ Базовая функциональность работает!")
    return True


def test_collision():
    """Локальная проверка коллизий (cad.collision)."""
    print("\nТестируем проверку коллизий...")
    try:
        from cad.collision import check_collisions_local
        traj = [[0, 0, 0], [10, 10, 10], [50, 50, 50]]
        obstacles = [{"id": "box1", "type": "aabb", "min": [5, 5, 5], "max": [15, 15, 15]}]
        collisions = check_collisions_local(traj, obstacles)
        assert len(collisions) >= 1
        assert collisions[0]["object_b"] == "box1"
        assert "step" in collisions[0]
        empty = check_collisions_local(traj, [])
        assert len(empty) == 0
        print("+ check_collisions_local: OK")
        return True
    except Exception as e:
        print(f"- Ошибка проверки коллизий: {e}")
        return False


def test_kinematics():
    """FK и достижимость (cad.kinematics)."""
    print("\nТестируем кинематику...")
    try:
        from cad.kinematics import fk_6dof, check_reachability
        joints = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        link_lengths = [[0, 100], [200, 0], [150, 0], [0, 0], [0, 100], [0, 50]]
        x, y, z = fk_6dof(joints, link_lengths=link_lengths)
        assert isinstance(x, (int, float)) and isinstance(y, (int, float)) and isinstance(z, (int, float))
        ok = check_reachability((100, 0, 200), max_reach_mm=500)
        assert ok is True
        ok_far = check_reachability((2000, 0, 0), max_reach_mm=500)
        assert ok_far is False
        print("+ fk_6dof, check_reachability: OK")
        return True
    except Exception as e:
        print(f"- Ошибка кинематики: {e}")
        return False


def test_export_krl_rapid():
    """Экспорт KRL и RAPID в временные файлы."""
    print("\nТестируем экспорт KRL/RAPID...")
    try:
        import tempfile
        from cad.import_export import CADImportExport
        pts = [(0, 0, 0), (100, 0, 50), (100, 100, 50)]
        imp = CADImportExport()
        with tempfile.NamedTemporaryFile(suffix=".krl", delete=False) as f:
            path_krl = f.name
        with tempfile.NamedTemporaryFile(suffix=".mod", delete=False) as f:
            path_mod = f.name
        try:
            ok_krl = imp.export_kuka_krl(pts, path_krl, speed_mms=100.0)
            ok_rapid = imp.export_abb_rapid(pts, path_mod, speed_mms=100.0)
            assert ok_krl and ok_rapid
            assert os.path.isfile(path_krl) and os.path.isfile(path_mod)
            with open(path_krl, "r", encoding="utf-8") as f:
                content = f.read()
            assert "LIN" in content and "X 100" in content
            with open(path_mod, "r", encoding="utf-8") as f:
                content = f.read()
            assert "MoveL" in content
        finally:
            for p in (path_krl, path_mod):
                if os.path.isfile(p):
                    os.unlink(p)
        print("+ export_kuka_krl, export_abb_rapid: OK")
        return True
    except Exception as e:
        print(f"- Ошибка экспорта KRL/RAPID: {e}")
        return False


def main():
    print("=== Тестирование KengaCAD ===\n")

    success = True

    if not test_imports():
        success = False

    if not test_basic_functionality():
        success = False

    if not test_collision():
        success = False

    if not test_kinematics():
        success = False

    if not test_export_krl_rapid():
        success = False

    print(f"\n=== Результат тестирования: {'УСПЕШНО' if success else 'С ОШИБКАМИ'} ===")

    if success:
        print("KengaCAD готов к использованию!")
    else:
        print("Обнаружены проблемы. Проверьте зависимости и код.")

    return success


if __name__ == "__main__":
    main()