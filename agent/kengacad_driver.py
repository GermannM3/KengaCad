# Драйвер KengaCAD: запуск приложения и управление через UI (pywinauto).
from __future__ import annotations

import time
from typing import Optional

from pywinauto import Application

from config import KENGACAD_WINDOW_TITLE, get_kengacad_exe


# Соответствие русских названий кнопок ленты (как в UI)
RIBON_BUTTONS = {
    "линия": "Линия",
    "круг": "Круг",
    "дуга": "Дуга",
    "полилиния": "Полилиния",
    "прямоугольник": "Прямоугольник",
    "переместить": "Переместить",
    "копировать": "Копировать",
    "повернуть": "Повернуть",
    "масштаб": "Масштаб",
    "зеркало": "Зеркало",
    "обрезать": "Обрезать",
    "удлинить": "Удлинить",
    "скругление": "Скругление",
    "новый слой": "Новый слой",
    "показать всё": "Показать всё",
    "увеличить": "Увеличить",
    "уменьшить": "Уменьшить",
    "панорама": "Панорама",
    "сверху": "Сверху",
    "спереди": "Спереди",
    "слева": "Слева",
    "3d": "3D",
    "загрузить": "Загрузить",
    "демо": "Демо",
    "в ноль": "В ноль",
    "из полилинии": "Из полилинии",
    "сплайн": "Сплайн",
    "сгладить": "Сгладить",
    "спираль": "Спираль",
    "старт": "Старт",
    "пауза": "Пауза",
    "стоп": "Стоп",
    "сброс": "Сброс",
    "g-код": "G-код",
    "kuka krl": "KUKA KRL",
    "abb rapid": "ABB RAPID",
    "fanuc tp": "Fanuc TP",
    "yaskawa": "Yaskawa",
    "ur script": "UR Script",
    "step": "STEP",
    "iges": "IGES",
    "stl": "STL",
    "gltf": "glTF",
    "создать блок": "Создать блок",
    "вставить": "Вставить",
    "текст": "Текст",
    "размер": "Размер",
    "радиус": "Радиус",
    "изометрия": "Изометрия",
    "сброс вида": "Сброс",
}


class KengaCADDriver:
    def __init__(self, exe_path: Optional[str] = None, timeout: int = 30):
        self.exe_path = exe_path or get_kengacad_exe()
        self.timeout = timeout
        self._app: Optional[Application] = None
        self._window = None

    def start(self) -> bool:
        if not self.exe_path:
            raise FileNotFoundError(
                "KengaCAD.exe не найден. Соберите проект или укажите путь в config.KENGACAD_EXE_OVERRIDE"
            )
        self._app = Application(backend="uia").start(self.exe_path, timeout=self.timeout)
        time.sleep(2)
        return self.attach()

    def attach(self) -> bool:
        try:
            self._app = Application(backend="uia").connect(title_re=f".*{KENGACAD_WINDOW_TITLE}.*", timeout=10)
            self._window = self._app.window(title_re=f".*{KENGACAD_WINDOW_TITLE}.*")
            return True
        except Exception as e:
            if self._app is None:
                raise
            try:
                self._window = self._app.window(title_re=f".*{KENGACAD_WINDOW_TITLE}.*")
                return True
            except Exception:
                raise RuntimeError(f"Окно KengaCAD не найдено: {e}") from e

    def _ensure_window(self):
        if self._window is None and not self.attach():
            raise RuntimeError("Сначала запустите KengaCAD или вызовите start()")

    def click_tab(self, header: str) -> bool:
        """Переключить вкладку ленты по заголовку (Главная, Вид, Робот, Вставка)."""
        self._ensure_window()
        try:
            self._window.child_window(title=header.strip(), control_type="TabItem").click_input()
            time.sleep(0.3)
            return True
        except Exception as e:
            raise RuntimeError(f"Вкладка '{header}' не найдена: {e}") from e

    def click_ribbon_button(self, name: str) -> bool:
        """Клик по кнопке ленты по имени (русское, без учёта регистра)."""
        self._ensure_window()
        key = name.strip().lower()
        text = RIBON_BUTTONS.get(key) or name.strip()
        try:
            self._window.Button(name=text).click_input()
            return True
        except Exception:
            try:
                self._window.child_window(title=text, control_type="Button").click_input()
                return True
            except Exception as e:
                raise RuntimeError(f"Кнопка '{text}' не найдена: {e}") from e

    def type_command(self, cmd: str) -> bool:
        """Ввод текста в командную строку и Enter."""
        self._ensure_window()
        try:
            # WPF: x:Name="CommandLine" → AutomationId
            edit = self._window.child_window(auto_id="CommandLine", control_type="Edit")
            edit.set_focus()
            edit.set_edit_text("")
            edit.type_keys(cmd, with_spaces=True)
            edit.type_keys("{ENTER}")
            return True
        except Exception:
            try:
                edit = self._window.child_window(control_type="Edit", found_index=0)
                edit.set_focus()
                edit.set_edit_text("")
                edit.type_keys(cmd, with_spaces=True)
                edit.type_keys("{ENTER}")
                return True
            except Exception as e:
                raise RuntimeError(f"Не удалось ввести команду в строку: {e}") from e

    def get_status_text(self) -> str:
        """Текст строки состояния."""
        self._ensure_window()
        try:
            st = self._window.child_window(auto_id="StatusText", control_type="Text")
            return st.window_text() or ""
        except Exception:
            try:
                for c in self._window.descendants(control_type="Text"):
                    t = getattr(c, "window_text", lambda: "")()
                    if t and "Готов" in t or "точку" in t or "создан" in t:
                        return t
            except Exception:
                pass
            return ""

    def close(self):
        if self._app:
            try:
                self._window.close()
            except Exception:
                pass
            self._app = None
            self._window = None


def main():
    import sys
    driver = KengaCADDriver()
    if len(sys.argv) > 1:
        if sys.argv[1] == "start":
            driver.start()
            print("KengaCAD запущен.")
        elif sys.argv[1] == "click" and len(sys.argv) > 2:
            driver.attach()
            driver.click_ribbon_button(sys.argv[2])
            print("OK")
        elif sys.argv[1] == "cmd" and len(sys.argv) > 2:
            driver.attach()
            driver.type_command(sys.argv[2])
            print("OK")
        else:
            print("Использование: python kengacad_driver.py start | click <кнопка> | cmd <команда>")
    else:
        driver.start()
        print("KengaCAD запущен. Далее: click <кнопка> | cmd <команда>")

if __name__ == "__main__":
    main()
