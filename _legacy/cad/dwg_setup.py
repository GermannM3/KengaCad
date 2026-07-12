"""
Настройка DWG — мастер для подключения ODA File Converter.
Пользователь один раз указывает путь к ODAFileConverter.exe — дальше всё работает.
"""
import os
import sys
from pathlib import Path
from typing import Optional

ODA_URL = "https://www.opendesign.com/guestfiles/oda_file_converter"
DEFAULT_WIN_PATH = r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"


def get_odafc_path_from_config() -> Optional[str]:
    """Путь к ODA из настроек KengaCAD."""
    try:
        base = Path(__file__).resolve().parent.parent
        cfg = base / "config" / "settings.json"
        if cfg.exists():
            import json
            data = json.loads(cfg.read_text(encoding="utf-8"))
            path = (data.get("cad") or {}).get("odafc_path")
            if path and os.path.isfile(path):
                return path
    except Exception:
        pass
    return None


def save_odafc_path(path: str) -> bool:
    """Сохранить путь ODA в настройки."""
    try:
        base = Path(__file__).resolve().parent.parent
        cfg = base / "config" / "settings.json"
        data = {}
        if cfg.exists():
            import json
            data = json.loads(cfg.read_text(encoding="utf-8"))
        if "cad" not in data:
            data["cad"] = {}
        data["cad"]["odafc_path"] = path
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text(encoding="utf-8", text=json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False


def apply_odafc_path(path: str) -> None:
    """Применить путь для ezdxf odafc."""
    try:
        import ezdxf
        ezdxf.options.set("odafc-addon", "win_exec_path", path)
        ezdxf.options.write_home_config()
    except Exception:
        pass


def is_odafc_available() -> bool:
    """Проверка: ODA File Converter доступен."""
    path = get_odafc_path_from_config()
    if path and os.path.isfile(path):
        apply_odafc_path(path)
        try:
            from ezdxf.addons import odafc
            return True
        except Exception:
            pass
    if sys.platform == "win32" and os.path.isfile(DEFAULT_WIN_PATH):
        return True
    try:
        from ezdxf.addons import odafc
        return True
    except Exception:
        return False


def open_oda_download_page() -> None:
    """Открыть страницу загрузки ODA в браузере."""
    import webbrowser
    webbrowser.open(ODA_URL)
