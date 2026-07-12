# Клиент Hugging Face: вызов бесплатной модели через Inference API (токен из env).
from __future__ import annotations

import json
import re
from typing import List, Optional

import requests

from config import get_hf_token, HF_MODEL


INFERENCE_URL = "https://router.huggingface.co/v1/chat/completions"


def chat(messages: List[dict], token: Optional[str] = None, model: Optional[str] = None) -> str:
    """Один запрос к модели. Токен из env, если не передан."""
    t = (token or get_hf_token()).strip()
    if not t:
        raise ValueError(
            "Задайте переменную окружения HUGGINGFACE_TOKEN "
            "(токен: https://huggingface.co/settings/tokens)"
        )
    model = model or HF_MODEL
    resp = requests.post(
        INFERENCE_URL,
        headers={
            "Authorization": f"Bearer {t}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "messages": messages,
            "max_tokens": 256,
            "temperature": 0.3,
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Hugging Face API: {resp.status_code} — {resp.text[:500]}")
    data = resp.json()
    choice = data.get("choices")
    if not choice:
        raise RuntimeError(f"Нет ответа в теле: {data}")
    return (choice[0].get("message") or {}).get("content", "").strip()


# Формат ответа агента: одна строка на действие.
# CLICK <название кнопки>
# CMD <текст команды>
# DONE
ACTION_PATTERN = re.compile(r"^\s*(CLICK|CMD|DONE)\s*[:\s]*(.*)$", re.IGNORECASE)


def parse_actions(text: str) -> List[tuple]:
    """Из текста ответа модели извлекаем список (action, arg)."""
    out = []
    for line in text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = ACTION_PATTERN.match(line)
        if m:
            act, arg = m.group(1).upper(), (m.group(2) or "").strip()
            out.append((act, arg))
        elif line.upper() == "DONE":
            out.append(("DONE", ""))
    return out
