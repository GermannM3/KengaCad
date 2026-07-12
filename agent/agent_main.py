# -*- coding: utf-8 -*-
"""
Агент-роботист для KengaCAD: запускает приложение и выполняет задачи,
управляемый бесплатной нейросетью Hugging Face (без отдельного API-ключа).
Использование:
  set HUGGINGFACE_TOKEN=ваш_токен
  python agent_main.py
  python agent_main.py "нарисовать линию и запустить симуляцию"
"""
import os
import sys

# Загружаем .env из папки agent
def _load_dotenv():
    try:
        from dotenv import load_dotenv
        agent_dir = os.path.dirname(os.path.abspath(__file__))
        load_dotenv(os.path.join(agent_dir, ".env"))
    except ImportError:
        pass


def main():
    _load_dotenv()

    from kengacad_tools import (
        launch_kengacad,
        connect_kengacad,
        run_action,
        TOOL_DESCRIPTIONS,
        get_status,
    )
    from llm import ask_agent, build_system_prompt

    token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    if not token:
        print("Задайте HUGGINGFACE_TOKEN в .env или переменной окружения.")
        print("Пример: создайте agent/.env с строкой HUGGINGFACE_TOKEN=hf_...")
        sys.exit(1)

    # Запуск или подключение к KengaCAD
    ok, app_or_err = connect_kengacad(timeout=3)
    if not ok:
        ok, app_or_err = launch_kengacad(timeout=20)
    if not ok:
        print("Ошибка:", app_or_err)
        sys.exit(2)
    app = app_or_err
    print("KengaCAD подключён.")

    # Цель от пользователя
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
    else:
        goal = input("Задача для агента (например: нарисовать линию и запустить симуляцию): ").strip()
    if not goal:
        print("Задача не задана. Выход.")
        sys.exit(0)

    system_prompt = build_system_prompt(TOOL_DESCRIPTIONS)
    max_steps = 20
    last_status = ""

    for step in range(max_steps):
        user_msg = f"Задача: {goal}\n"
        if last_status:
            user_msg += f"Текущее состояние: {last_status}\n"
        user_msg += "Какое следующее действие? (одна строка)"

        action = ask_agent(system_prompt, user_msg)
        print(f"  [{step+1}] LLM: {action}")

        if not action or action.lower() == "done":
            print("Агент завершил работу.")
            break

        success, msg = run_action(app, action)
        print(f"       Результат: {msg}")
        last_status = msg
        if success and "status" in action.lower():
            last_status = msg

        # Краткая пауза, чтобы UI успел обновиться
        import time
        time.sleep(0.5)
    else:
        print("Достигнут лимит шагов.")

    print("Готово. Окно KengaCAD можно использовать вручную.")


if __name__ == "__main__":
    main()
