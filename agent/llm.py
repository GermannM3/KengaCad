# -*- coding: utf-8 -*-
"""
LLM через Hugging Face Inference API (бесплатный tier с токеном).
Модель управляет агентом: решает, какое действие выполнить в KengaCAD.
"""
import os
import re

def get_client():
    """Создать InferenceClient с токеном из окружения."""
    from huggingface_hub import InferenceClient
    token = os.environ.get("HUGGINGFACE_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "Задайте HUGGINGFACE_TOKEN в .env или в окружении. "
            "Токен: https://huggingface.co/settings/tokens"
        )
    return InferenceClient(api_key=token)


# Модель: бесплатная на HF Inference, без отдельного API-ключа
# Qwen2-0.5B — маленькая, быстрая, подходит для выбора действий
DEFAULT_MODEL = "Qwen/Qwen2-0.5B-Instruct"


def ask_agent(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL, max_tokens: int = 80) -> str:
    """
    Спросить LLM, какое действие выполнить. Возвращает одну строку действия
    (например "click Линия" или "command LINE" или "done").
    """
    client = get_client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    try:
        out = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.3,
        )
        text = (out.choices[0].message.content or "").strip()
        # Убираем кавычки и лишнее; оставляем одну строку
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        return "done"  # при ошибке не зацикливаться


def build_system_prompt(tool_descriptions: str) -> str:
    return (
        "Ты — агент-роботист. Управляешь программой KengaCAD: рисование, команды, симуляция. "
        "Отвечай только одной строкой — действием из списка. Без пояснений.\n"
        + tool_descriptions
    )
