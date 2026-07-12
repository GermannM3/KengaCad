"""
Сборка релизного EXE KengaCAD для отправки роботисту.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run(cmd: list, cwd=None):
    r = subprocess.run(cmd, cwd=cwd or ROOT, shell=False)
    if r.returncode != 0:
        sys.exit(r.returncode)


def main():
    print("=" * 50)
    print(" KengaCAD - сборка релизного EXE")
    print("=" * 50)

    # 1. Сборка движка
    print("\n[1/4] Сборка движка...")
    engine_dir = ROOT / "GoEngineKenga"
    env = os.environ.copy()
    env["GOOS"] = "windows"
    env["GOARCH"] = "amd64"
    env["CGO_ENABLED"] = "0"
    run(["go", "build", "-o", "dist/kenga.exe", "./cmd/kenga"], cwd=engine_dir)
    (engine_dir / "dist").mkdir(exist_ok=True)
    shutil.copy(engine_dir / "dist/kenga.exe", engine_dir / "dist/kenga-windows-amd64.exe")
    (ROOT / "engine_bin").mkdir(exist_ok=True)
    dst = ROOT / "engine_bin" / "kenga.exe"
    try:
        shutil.copy(engine_dir / "dist/kenga-windows-amd64.exe", dst)
    except PermissionError:
        print("      (kenga.exe занят - используем существующий)")
    print("      OK")

    # 2. Venv с Python 3.11/3.12 (стабильнее с PyQt6)
    print("\n[2/4] Окружение...")
    venv_dir = ROOT / ".venv_release"
    use_venv = False
    for ver in ["3.11", "3.12", "3.10"]:
        try:
            r = subprocess.run(["py", f"-{ver}", "-c", "exit(0)"], capture_output=True, shell=True)
            if r.returncode == 0:
                print(f"      Python {ver}")
                if venv_dir.exists():
                    shutil.rmtree(venv_dir)
                subprocess.run(["py", f"-{ver}", "-m", "venv", str(venv_dir)], check=True, cwd=ROOT)
                use_venv = True
                break
        except Exception:
            pass
    if not use_venv:
        print("      Системный Python")

    if venv_dir.exists():
        pip_exe = str(venv_dir / "Scripts" / "pip.exe")
        python_exe = str(venv_dir / "Scripts" / "python.exe")
    else:
        pip_exe = sys.executable.replace("python.exe", "pip.exe")
        if not os.path.exists(pip_exe):
            pip_exe = sys.executable.replace("python.exe", "Scripts\\pip.exe")
        python_exe = sys.executable

    # 3. Зависимости
    print("\n[3/4] Установка зависимостей...")
    subprocess.run([python_exe, "-m", "pip", "install", "-q", "PyQt5", "pyqtribbon", "websockets", "ezdxf", "numpy"], cwd=ROOT, check=False)
    subprocess.run([python_exe, "-m", "pip", "install", "-q", "PyInstaller", "pillow"], cwd=ROOT, check=True)
    print("      OK")

    # 4. PyInstaller
    print("\n[4/4] Сборка EXE...")
    import pyqtribbon
    pqt_dir = Path(pyqtribbon.__file__).parent
    pqt_styles = str(pqt_dir / "styles")
    pqt_icons = str(pqt_dir / "icons")
    cmd = [
        str(python_exe), "-m", "PyInstaller", "--noconfirm",
        "--name=KengaCAD", "--windowed", "--onedir",
        "--additional-hooks-dir=hooks",
        "--exclude-module=PySide6", "--exclude-module=PySide2", "--exclude-module=PyQt6",
        "--add-data=config;config", "--add-data=ui;ui", "--add-data=engine;engine",
        "--add-data=robot;robot", "--add-data=cad;cad", "--add-data=assets;assets",
        "--add-data=engine_bin;engine_bin",
        f"--add-data={pqt_styles};pyqtribbon/styles",
        f"--add-data={pqt_icons};pyqtribbon/icons",
        "--hidden-import=PyQt5", "--hidden-import=websockets", "--hidden-import=ezdxf",
        "--hidden-import=numpy",
    ]
    if (ROOT / "assets" / "logo.ico").exists():
        cmd.append("--icon=assets/logo.ico")
    cmd.append("main.py")

    run(cmd)

    out_exe = ROOT / "dist" / "KengaCAD" / "KengaCAD.exe"
    if not out_exe.exists():
        print("Ошибка: EXE не создан")
        sys.exit(1)

    # 5. Архив
    print("\nСоздание архива...")
    zip_path = ROOT / "KengaCAD_Portable.zip"
    if zip_path.exists():
        zip_path.unlink()
    import zipfile
    # README для роботиста
    readme = ROOT / "dist" / "KengaCAD" / "README_для_роботиста.txt"
    readme.write_text(
        "KengaCAD — программа для настройки траекторий роботов\n\n"
        "КАК ЗАПУСТИТЬ:\n"
        "1. Распакуйте архив в любую папку (правый клик по ZIP → «Извлечь всё»)\n"
        "2. Дважды щёлкните KengaCAD.exe\n"
        "3. Готово. Рисуйте линии, точки, окружности — кнопками или командной строкой.\n\n"
        "ТРЕБОВАНИЯ: Windows 10/11 (64-bit)\n\n"
        "Если не запускается — установите VC++ Redistributable:\n"
        "https://aka.ms/vs/17/release/vc_redist.x64.exe",
        encoding="utf-8"
    )
    dist_dir = ROOT / "dist" / "KengaCAD"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in dist_dir.rglob("*"):
            if f.is_file():
                arcname = "KengaCAD/" + f.relative_to(dist_dir).as_posix()
                zf.write(f, arcname)

    if venv_dir.exists():
        print("Удаление venv...")
        shutil.rmtree(venv_dir, ignore_errors=True)

    print("\n" + "=" * 50)
    print(" Готово!")
    print(f" EXE:    {out_exe}")
    print(f" Архив:  {zip_path}")
    print()
    print(" Отправьте роботисту KengaCAD_Portable.zip")
    print(" Он распаковывает и запускает KengaCAD.exe")
    print("=" * 50)


if __name__ == "__main__":
    main()
