"""
Финальный тест установщика KengaCAD
"""
import os
import sys
import subprocess
from pathlib import Path


def test_installer_components():
    """Тестирование всех компонентов установщика"""
    print("=== Финальный тест установщика KengaCAD ===\n")
    
    # Проверяем, что все установщики созданы
    print("1. Проверка наличия установщиков:")

    # Windows installer
    installer_path = Path("dist") / "KengaCAD_Installer.exe"
    if installer_path.exists():
        size = installer_path.stat().st_size / (1024*1024)  # в МБ
        print(f"   + Windows установщик: {installer_path} ({size:.2f} МБ)")
    else:
        print(f"   - Windows установщик: {installer_path} - НЕ НАЙДЕН")
        return False

    # Portable version
    portable_zip = Path(".") / "KengaCAD_Portable.zip"
    if portable_zip.exists():
        size = portable_zip.stat().st_size / (1024*1024)  # в МБ
        print(f"   + Portable версия: {portable_zip} ({size:.2f} МБ)")
    else:
        print(f"   - Portable версия: {portable_zip} - НЕ НАЙДЕНА")
        return False

    print("\n2. Проверка наличия скриптов сборки:")

    build_scripts = [
        "build_scripts/build_all_installers.py",
        "build_scripts/create_innosetup_installer.py",
        "build_scripts/create_deb_package.py",
        "build_scripts/create_rpm_package.py",
        "build_scripts/create_arch_package.py"
    ]

    for script in build_scripts:
        if Path(script).exists():
            print(f"   + {script}")
        else:
            print(f"   - {script} - НЕ НАЙДЕН")
            return False

    print("\n3. Проверка наличия файлов установщиков для Linux:")

    linux_installers = [
        "installers/deb_package/",
        "installers/rpm_package/kengacad.spec",
        "installers/arch_package/PKGBUILD"
    ]

    for installer in linux_installers:
        if Path(installer).exists():
            print(f"   + {installer}")
        else:
            print(f"   - {installer} - НЕ НАЙДЕН")
            return False

    print("\n4. Проверка наличия документации:")

    docs = [
        "README.md",
        "docs/INSTALL.md",
        "docs/INDEX.md",
        "COMMAND_REFERENCE.md",
        "API_DOCS.md",
    ]

    for doc in docs:
        if Path(doc).exists():
            print(f"   + {doc}")
        else:
            print(f"   - {doc} - НЕ НАЙДЕН")
            return False

    print("\n5. Проверка исполняемого файла приложения:")

    app_exe = Path("dist") / "KengaCAD.exe"
    if app_exe.exists():
        size = app_exe.stat().st_size / (1024*1024)  # в МБ
        print(f"   + Исполняемый файл приложения: {app_exe} ({size:.2f} МБ)")
    else:
        print(f"   - Исполняемый файл приложения: {app_exe} - НЕ НАЙДЕН")
        return False

    print("\n6. Проверка зависимостей Python:")

    try:
        import PyQt6
        print("   + PyQt6 установлен")
    except ImportError:
        print("   - PyQt6 НЕ УСТАНОВЛЕН")
        return False

    try:
        import websockets
        print("   + websockets установлен")
    except ImportError:
        print("   - websockets НЕ УСТАНОВЛЕН")
        return False

    try:
        import ezdxf
        print("   + ezdxf установлен")
    except ImportError:
        print("   - ezdxf НЕ УСТАНОВЛЕН")
        return False

    print("\n7. Проверка структуры проекта:")

    project_dirs = [
        "ui/",
        "engine/",
        "robot/",
        "cad/",
        "examples/",
        "config/",
        "assets/"
    ]

    for dir_path in project_dirs:
        if Path(dir_path).exists():
            print(f"   + {dir_path}")
        else:
            print(f"   - {dir_path} - НЕ НАЙДЕНА")
            return False
    
    print("\n=== Все компоненты установщика KengaCAD успешно созданы! ===")
    print("\nДоступные установщики:")
    print("- Windows Portable: KengaCAD_Portable.zip")
    print("- Windows Installer: dist\\KengaCAD_Installer.exe")
    print("- Linux DEB: installers\\deb_package\\ (структура)")
    print("- Linux RPM: installers\\rpm_package\\SPECS\\kengacad.spec")
    print("- Arch Linux: installers\\arch_package\\PKGBUILD")

    print("\nДля установки:")
    print("1. Скачайте подходящий установщик")
    print("2. Установите движок Kenga отдельно (https://github.com/GermannM3/GoEngineKenga)")
    print("3. Следуйте инструкциям в docs/INSTALL.md")

    return True


def main():
    success = test_installer_components()

    if success:
        print("\n+ Установщики KengaCAD готовы к использованию!")
    else:
        print("\n- Обнаружены проблемы с установщиками")
        sys.exit(1)


if __name__ == "__main__":
    main()