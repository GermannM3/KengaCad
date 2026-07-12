# Агент-роботист: цель от пользователя → модель Hugging Face → действия в KengaCAD.
from __future__ import annotations

import sys
import time
from typing import Optional, List, Tuple

from config import get_hf_token, get_kengacad_exe
from hf_client import chat, parse_actions
from kengacad_driver import KengaCADDriver


TOOLS_DESC = """
Доступные действия в KengaCAD (выводи ровно одну строку на действие):
- CLICK <кнопка> — нажать кнопку ленты. Примеры: Линия, Круг, Полилиния, Старт, Сброс.
- CMD <текст> — ввести команду в командную строку и Enter. Примеры: LINE, CIRCLE, POLYLINE.
- DONE — задача выполнена, завершить.

Кнопки (русские): Линия, Круг, Полилиния, Прямоугольник, Старт, Пауза, Стоп, Сброс, Показать всё.
"""

SYSTEM_PROMPT = """Ты — агент-оператор KengaCAD. Выводи только строки: CLICK <кнопка> или CMD <команда> или DONE. Одна строка — одно действие."""


def build_prompt(goal: str, status: str = "") -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT + "\n" + TOOLS_DESC},
        {"role": "user", "content": f"Цель: {goal}. " + (f"Статус: {status}." if status else "") + "\nВыведи действия по одному на строку."},
    ]


def get_fallback_actions(goal: str) -> List[Tuple[str, str]]:
    """Сценарий по умолчанию, если API недоступен."""
    g = goal.lower()
    if "полилин" in g or "polyline" in g or "траектор" in g or "антиграви" in g or "кузов" in g or "порог" in g:
        return [
            ("CLICK", "Полилиния"),
            ("CMD", "POLYLINE"),
            ("DONE", ""),
        ]
    if "симуля" in g or "simulation" in g or "старт" in g or "start" in g:
        return [("TAB", "Робот"), ("CLICK", "Старт"), ("DONE", "")]
    return [("CLICK", "Полилиния"), ("CMD", "POLYLINE"), ("DONE", "")]


def run_agent(
    goal: str,
    driver: Optional[KengaCADDriver] = None,
    max_steps: int = 20,
    dry_run: bool = False,
) -> bool:
    token = get_hf_token()
    use_llm = bool(token)

    own_driver = driver is None
    if own_driver:
        exe = get_kengacad_exe()
        if not exe:
            print("Ошибка: KengaCAD.exe не найден. Соберите проект.")
            return False
        driver = KengaCADDriver(exe_path=exe)
        try:
            driver.attach()
            print("Подключились к уже открытому KengaCAD.")
        except Exception:
            try:
                driver.start()
                print("Запущен KengaCAD.")
            except Exception as e:
                print(f"Не удалось запустить KengaCAD: {e}")
                return False
        time.sleep(1.5)

    try:
        step = 0
        while step < max_steps:
            step += 1
            status = driver.get_status_text() if not dry_run else ""
            actions = []

            if use_llm:
                try:
                    messages = build_prompt(goal, status)
                    reply = chat(messages, token=token)
                    actions = parse_actions(reply)
                except Exception as e:
                    print(f"Модель недоступна ({e}), выполняю сценарий по умолчанию.")
                    use_llm = False
                    actions = get_fallback_actions(goal)
            else:
                if step == 1:
                    actions = get_fallback_actions(goal)

            if not actions and use_llm:
                first = (reply or "").split("\n")[0].strip()
                if first.upper().startswith("CLICK"):
                    actions = [("CLICK", first[5:].strip())]
                elif first.upper().startswith("CMD"):
                    actions = [("CMD", first[3:].strip())]
                elif first.upper() == "DONE":
                    actions = [("DONE", "")]

            for act, arg in actions:
                if act == "DONE":
                    print("Готово.")
                    return True
                if dry_run:
                    print(f"  [dry-run] {act}: {arg}")
                    continue
                try:
                    if act == "CLICK":
                        driver.click_ribbon_button(arg)
                        print(f"  CLICK: {arg}")
                    elif act == "CMD":
                        driver.type_command(arg)
                        print(f"  CMD: {arg}")
                    elif act == "TAB":
                        driver.click_tab(arg)
                        print(f"  TAB: {arg}")
                except Exception as e:
                    print(f"  Ошибка {act} {arg}: {e}")
                time.sleep(1.5)

        print("Достигнут лимит шагов.")
        return False
    finally:
        if own_driver and driver:
            pass


def main():
    goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Нарисовать полилинию и запустить симуляцию."
    dry = "--dry-run" in sys.argv
    if dry:
        sys.argv = [a for a in sys.argv if a != "--dry-run"]
        goal = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else goal
    print("Цель:", goal)
    ok = run_agent(goal, max_steps=15, dry_run=dry)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
