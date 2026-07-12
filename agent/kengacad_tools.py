# -*- coding: utf-8 -*-
"""
Инструменты для управления KengaCAD Professional через UI (pywinauto).
Агент запускает приложение и выполняет действия как роботист: рисование, команды, симуляция.
"""
import os
import sys
import time
from pathlib import Path

try:
    from pywinauto import Application
    from pywinauto.findwindows import ElementNotFoundError
except ImportError:
    Application = None
    ElementNotFoundError = Exception

# Заголовок главного окна KengaCAD
KENGACAD_TITLE = "KengaCAD Professional"
def _default_paths():
    root = Path(__file__).resolve().parent.parent
    return [
        os.path.expandvars(r"%ProgramFiles%\KengaCAD Professional\KengaCAD.exe"),
        os.path.expandvars(r"%LocalAppData%\Programs\KengaCAD Professional\KengaCAD.exe"),
        str(root / "KengaCAD" / "bin" / "Release" / "net8.0-windows" / "win-x64" / "KengaCAD.exe"),
        str(root / "KengaCAD" / "publish" / "KengaCAD.exe"),
    ]


def _find_exe():
    exe = os.environ.get("KENGACAD_EXE", "").strip()
    if exe and os.path.isfile(exe):
        return exe
    for p in _default_paths():
        if os.path.isfile(p):
            return p
    return None


def launch_kengacad(timeout=15):
    """Запустить KengaCAD. Возвращает (True, app) или (False, error_message)."""
    if Application is None:
        return False, "pywinauto не установлен: pip install pywinauto"
    exe = _find_exe()
    if not exe:
        return False, "KengaCAD не найден. Задайте KENGACAD_EXE в .env или установите приложение."
    try:
        app = Application(backend="uia").start(exe, timeout=timeout)
        time.sleep(2)
        return True, app
    except Exception as e:
        return False, str(e)


def connect_kengacad(timeout=5):
    """Подключиться к уже запущенному KengaCAD. Возвращает (True, app) или (False, error_message)."""
    if Application is None:
        return False, "pywinauto не установлен"
    try:
        app = Application(backend="uia").connect(title_re=".*KengaCAD.*", timeout=timeout)
        return True, app
    except ElementNotFoundError:
        return False, "Окно KengaCAD не найдено. Запустите приложение."
    except Exception as e:
        return False, str(e)


def _get_window(app):
    if hasattr(app, "window"):
        return app.window(title_re=".*KengaCAD.*")
    for w in app.windows():
        if "KengaCAD" in (w.window_text() or ""):
            return w
    return app.top_window()


def click_ribbon_button(app, button_content):
    """
    Нажать кнопку на ленте по тексту (Content).
    button_content: "Линия", "Круг", "Прямоугольник", "Полилиния", "Старт", "Сброс" и т.д.
    """
    try:
        win = _get_window(app)
        # WPF: кнопки в TabControl, текст кнопки = Content
        btn = win.child_window(title=button_content, control_type="Button")
        btn.click_input()
        return True, "Нажато: " + button_content
    except Exception as e:
        return False, str(e)


def type_command(app, text):
    """Ввести текст в командную строку KengaCAD и нажать Enter."""
    try:
        win = _get_window(app)
        # Командная строка — обычно единственное поле ввода внизу или по имени
        for ctrl in win.descendants(control_type="Edit"):
            ctrl.set_focus()
            ctrl.set_edit_text("")
            ctrl.type_keys(text, with_spaces=True)
            ctrl.type_keys("{ENTER}")
            return True, "Выполнено: " + text
        return False, "Командная строка не найдена"
    except Exception as e:
        return False, str(e)


def get_status(app):
    """Прочитать текст из строки состояния (StatusBar)."""
    try:
        win = _get_window(app)
        for ctrl in win.descendants():
            if "StatusBar" in ctrl.class_name() or ctrl.element_info.control_type == "StatusBar":
                return True, (ctrl.window_text() or "")[:200]
            # Первый Text в статусной строке
            if ctrl.control_type() == "Text" and ctrl.window_text():
                return True, ctrl.window_text()[:200]
        return False, "Строка состояния не найдена"
    except Exception as e:
        return False, str(e)


def run_simulation(app):
    """Перейти на вкладку Робот и нажать Старт симуляции."""
    try:
        win = _get_window(app)
        # Сначала переключиться на вкладку "Робот"
        tab = win.child_window(title="Робот", control_type="TabItem")
        tab.click_input()
        time.sleep(0.3)
        btn = win.child_window(title="Старт", control_type="Button")
        btn.click_input()
        return True, "Симуляция запущена"
    except Exception as e:
        return False, str(e)


def reset_simulation(app):
    """Нажать Сброс в панели Робот."""
    try:
        win = _get_window(app)
        tab = win.child_window(title="Робот", control_type="TabItem")
        tab.click_input()
        time.sleep(0.2)
        btn = win.child_window(title="Сброс", control_type="Button")
        btn.click_input()
        return True, "Сброс симуляции"
    except Exception as e:
        return False, str(e)


# Список доступных действий для LLM
TOOL_DESCRIPTIONS = """
Доступные действия (ответь одним словом или короткой фразой из списка):
- launch — запустить KengaCAD
- click Линия — инструмент линия
- click Круг — инструмент круг
- click Прямоугольник — инструмент прямоугольник
- click Полилиния — инструмент полилиния
- click Старт — запуск симуляции (вкладка Робот)
- click Сброс — сброс 3D траектории
- command <текст> — ввести в командную строку (например: command LINE)
- status — прочитать строку состояния
- done — задача выполнена, выйти
"""


def run_action(app, action_str):
    """
    Выполнить одну команду агента.
    action_str: "click Линия", "command LINE", "status", "done"
    Возвращает (success, message).
    """
    action_str = (action_str or "").strip().lower()
    if not action_str or action_str == "done":
        return True, "Готово."

    if action_str == "status":
        return get_status(app)

    if action_str.startswith("command "):
        text = action_str[8:].strip()
        return type_command(app, text)

    if action_str.startswith("click "):
        name = action_str[6:].strip()
        # Нормализуем для отображения с большой буквы
        if name in ("линия", "line"): name = "Линия"
        elif name in ("круг", "circle"): name = "Круг"
        elif name in ("прямоугольник", "rectangle", "rec"): name = "Прямоугольник"
        elif name in ("полилиния", "polyline", "pl"): name = "Полилиния"
        elif name in ("старт", "start", "simulate"): name = "Старт"
        elif name in ("сброс", "reset"): name = "Сброс"
        return click_ribbon_button(app, name)

    return False, "Неизвестная команда: " + action_str
