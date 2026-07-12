# Конфигурация агента. Токен НЕ хранить в коде — только в переменной окружения или .env.
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass

# Путь к KengaCAD: либо установленный exe, либо сборка из репозитория
REPO_ROOT = Path(__file__).resolve().parent.parent
KENGACAD_EXE_BUILD = REPO_ROOT / "KengaCAD" / "bin" / "Release" / "net8.0-windows" / "win-x64" / "KengaCAD.exe"
KENGACAD_EXE_PUBLISH = REPO_ROOT / "KengaCAD" / "publish" / "KengaCAD.exe"
KENGACAD_WINDOW_TITLE = "KengaCAD Professional"

def get_kengacad_exe():
    for p in (KENGACAD_EXE_PUBLISH, KENGACAD_EXE_BUILD):
        if p.exists():
            return str(p)
    return None

# Токен Hugging Face — только из окружения (не коммитить в репозиторий)
def get_hf_token():
    return os.environ.get("HUGGINGFACE_TOKEN", "").strip()

# Модель (router.huggingface.co). Включите провайдера в https://huggingface.co/settings/inference
HF_MODEL = "HuggingFaceH4/zephyr-7b-beta"
