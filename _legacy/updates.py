"""
Модуль проверки и установки обновлений KengaCAD.
Заложена структура для будущей интеграции с GitHub Releases, Tauri/Electric или собственным сервером.
Пока проверка не реализована — движок доставки ещё в подготовке.
"""
from pathlib import Path
from typing import Optional, Tuple
import json


def _load_settings() -> dict:
    """Загрузка настроек из config/settings.json."""
    try:
        base = Path(__file__).resolve().parent
        cfg = base / "config" / "settings.json"
        if cfg.exists():
            return json.loads(cfg.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def get_current_version() -> str:
    """Текущая версия приложения из config."""
    data = _load_settings()
    app = data.get("app") or {}
    return str(app.get("version", "1.0.0")).strip()


def get_updates_config() -> dict:
    """Настройки обновлений из config."""
    data = _load_settings()
    return data.get("updates") or {}


def is_update_check_enabled() -> bool:
    """Включена ли проверка обновлений."""
    cfg = get_updates_config()
    return cfg.get("enabled", False)


def get_update_check_url() -> Optional[str]:
    """URL для проверки версии (GitHub API, свой сервер и т.п.)."""
    cfg = get_updates_config()
    url = cfg.get("check_url", "").strip()
    return url if url else None


def should_check_on_startup() -> bool:
    """Проверять ли при запуске."""
    cfg = get_updates_config()
    return cfg.get("check_on_startup", False)


def check_for_updates() -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Проверка наличия новой версии.
    Возвращает: (найдено_обновление, новая_версия, url_скачивания).
    Пока всегда (False, None, None) — сервер доставки не настроен.
    """
    url = get_update_check_url()
    if not url or not is_update_check_enabled():
        return False, None, None

    # TODO: при подключении сервера:
    # - запрос к url (GitHub Releases API, свой JSON и т.п.)
    # - сравнение версий (semver)
    # - возврат (True, "1.1.0", "https://...") при наличии новой версии
    try:
        # import urllib.request
        # with urllib.request.urlopen(url, timeout=5) as r:
        #     data = json.loads(r.read().decode())
        # latest = data.get("tag_name", "").lstrip("v")
        # if _version_greater(latest, get_current_version()):
        #     return True, latest, data.get("assets", [{}])[0].get("browser_download_url")
        pass
    except Exception:
        pass

    return False, None, None


def _version_greater(new: str, current: str) -> bool:
    """Сравнение версий (упрощённый semver)."""
    def parse(v: str) -> list:
        return [int(x) for x in v.split(".")[:3] if x.isdigit()]
    try:
        n = parse(new)
        c = parse(current)
        return n > c
    except (ValueError, IndexError):
        return False
