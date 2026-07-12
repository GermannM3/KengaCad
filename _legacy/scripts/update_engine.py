"""
Скрипт обновления движка Kenga для KengaCAD.
Варианты:
  1. Обновить код и собрать: python scripts/update_engine.py --pull --build
  2. Собрать из GoEngineKenga: python scripts/update_engine.py --build
  3. Загрузка из GitHub Release: python scripts/update_engine.py --version 0.2.0
"""
import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

REPO = "GermannM3/GoEngineKenga"
ROOT = Path(__file__).resolve().parent.parent
ENGINE_BIN = ROOT / "engine_bin"
GO_ENGINE = ROOT / "GoEngineKenga"


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def _exe_name() -> str:
    return "kenga.exe" if _is_windows() else "kenga"


def _artifact_name(version: str) -> str:
    goos = "windows" if _is_windows() else "linux" if platform.system() == "Linux" else "darwin"
    goarch = "amd64"
    return f"GoEngineKenga-{version}-{goos}-{goarch}"


def pull_latest() -> bool:
    """Обновить GoEngineKenga из git (git pull)."""
    if not (GO_ENGINE / ".git").exists():
        print(f"[WARN] GoEngineKenga не является git-репозиторием")
        return True
    print("[INFO] git pull в GoEngineKenga...")
    r = subprocess.run(["git", "pull", "--rebase"], cwd=GO_ENGINE, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"[ERROR] git pull: {r.stderr or r.stdout}")
        return False
    print(r.stdout or r.stderr or "+ Репозиторий обновлён")
    return True


def build_local(version: str = "0.2.0") -> bool:
    """Собрать движок из GoEngineKenga."""
    if not GO_ENGINE.exists():
        print(f"[ERROR] Папка GoEngineKenga не найдена: {GO_ENGINE}")
        return False
    dist = GO_ENGINE / "dist"
    dist.mkdir(exist_ok=True)
    env = os.environ.copy()
    env["GOOS"] = "windows" if _is_windows() else "linux" if platform.system() == "Linux" else "darwin"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    ldflags = f"-s -w -X goenginekenga/engine/version.Version=v{version}"
    cmd = ["go", "build", "-ldflags", ldflags, "-o", str(dist / _exe_name()), "./cmd/kenga"]
    print(f"[INFO] Сборка: {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=GO_ENGINE, env=env)
    if r.returncode != 0:
        return False
    src = dist / _exe_name()
    if not src.exists():
        print(f"[ERROR] Бинарник не создан: {src}")
        return False
    ENGINE_BIN.mkdir(parents=True, exist_ok=True)
    dst = ENGINE_BIN / _exe_name()
    try:
        shutil.copy2(src, dst)
    except PermissionError:
        alt = ROOT / "kenga_new.exe"
        shutil.copy2(src, alt)
        print(f"[WARN] {dst} занят. Скопирован в {alt}")
        print(f"       Закройте KengaCAD и переименуйте: move {alt} {dst}")
        return True
    print(f"+ Движок обновлён: {dst}")
    return True


def download_release(version: str) -> bool:
    """Скачать движок из GitHub Release."""
    v = version.lstrip("v")
    artifact = _artifact_name(v)
    url = f"https://github.com/{REPO}/releases/download/v{v}/{artifact}.zip"
    print(f"[INFO] Загрузка: {url}")
    tmp = ROOT / "tmp_engine_download"
    tmp.mkdir(exist_ok=True)
    zip_path = tmp / f"{artifact}.zip"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "KengaCAD-update"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            zip_path.write_bytes(resp.read())
    except Exception as e:
        print(f"[ERROR] Не удалось скачать: {e}")
        return False
    exe_name = _exe_name()
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            if name.endswith(exe_name) or (exe_name == "kenga" and name.endswith("/kenga")):
                ENGINE_BIN.mkdir(parents=True, exist_ok=True)
                dst = ENGINE_BIN / exe_name
                with z.open(name) as src, open(dst, "wb") as out:
                    out.write(src.read())
                print(f"+ Движок обновлён: {dst}")
                break
        else:
            print(f"[ERROR] Файл {exe_name} не найден в архиве")
            return False
    zip_path.unlink(missing_ok=True)
    if tmp.exists() and not any(tmp.iterdir()):
        tmp.rmdir()
    return True


def main():
    ap = argparse.ArgumentParser(description="Обновление движка Kenga для KengaCAD")
    ap.add_argument("--pull", action="store_true", help="Обновить GoEngineKenga (git pull) перед сборкой")
    ap.add_argument("--build", action="store_true", help="Собрать из GoEngineKenga (требуется Go)")
    ap.add_argument("--version", default="0.2.0", help="Версия для загрузки (например 0.2.0)")
    args = ap.parse_args()
    if args.build:
        if args.pull and not pull_latest():
            sys.exit(1)
        ok = build_local(args.version)
    elif args.pull:
        ok = pull_latest()
    else:
        ok = download_release(args.version)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
