"""
Упрощенный установщик для KengaCAD
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
import tempfile


def install_kengacad():
    """Установка KengaCAD"""
    print("Установка KengaCAD...")
    
    # Проверяем права администратора
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        if not is_admin:
            print("Для установки требуются права администратора.")
            print("Пожалуйста, запустите этот скрипт от имени администратора.")
            input("Нажмите Enter для выхода...")
            return False
    except:
        print("Не удалось проверить права администратора")
        # Продолжаем, если не можем проверить
    
    # Определяем путь установки
    program_files = os.environ.get("ProgramFiles", "C:\\Program Files")
    install_path = Path(program_files) / "KengaCAD"
    
    print(f"Установка в: {install_path}")
    
    # Проверяем, существует ли уже установка
    if install_path.exists():
        response = input(f"KengaCAD уже установлен в {install_path}. Перезаписать? (y/n): ")
        if response.lower() != 'y':
            print("Установка отменена.")
            return False
    
    try:
        # Создаем директорию установки
        install_path.mkdir(parents=True, exist_ok=True)
        
        # Копируем исполняемый файл
        exe_src = Path("dist") / "KengaCAD.exe"
        if not exe_src.exists():
            print(f"Исполняемый файл не найден: {exe_src}")
            print("Сначала создайте исполняемый файл с помощью PyInstaller:")
            print("  pyinstaller --onefile --windowed main.py")
            return False
        
        exe_dst = install_path / "KengaCAD.exe"
        shutil.copy2(exe_src, exe_dst)
        print(f"Скопирован исполняемый файл: {exe_dst}")
        
        # Копируем конфигурационные файлы
        config_src = Path("config")
        if config_src.exists():
            config_dst = install_path / "config"
            if config_dst.exists():
                shutil.rmtree(config_dst)
            shutil.copytree(config_src, config_dst)
            print(f"Скопированы конфигурационные файлы: {config_dst}")
        
        # Копируем ресурсы
        assets_src = Path("assets")
        if assets_src.exists():
            assets_dst = install_path / "assets"
            if assets_dst.exists():
                shutil.rmtree(assets_dst)
            shutil.copytree(assets_src, assets_dst)
            print(f"Скопированы ресурсы: {assets_dst}")
        
        # Создаем ярлык на рабочем столе
        desktop_path = Path.home() / "Desktop"
        shortcut_path = desktop_path / "KengaCAD.lnk"
        
        # В Windows для создания ярлыков нужна библиотека pywin32
        # Создадим bat файл как временное решение
        bat_path = desktop_path / "KengaCAD.bat"
        with open(bat_path, 'w') as f:
            f.write(f'@echo off\n"{exe_dst}"\npause')
        print(f"Создан ярлык запуска: {bat_path}")
        
        # Создаем ярлык в меню "Пуск"
        start_menu_path = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "KengaCAD"
        start_menu_path.mkdir(parents=True, exist_ok=True)
        
        start_bat_path = start_menu_path / "KengaCAD.bat"
        with open(start_bat_path, 'w') as f:
            f.write(f'@echo off\n"{exe_dst}"\npause')
        print(f"Создан ярлык в меню Пуск: {start_bat_path}")
        
        # Регистрируем в реестре для деинсталляции
        register_in_registry(install_path)
        
        print(f"\nKengaCAD успешно установлен в: {install_path}")
        print("Для запуска приложения:")
        print(f"  - Дважды щелкните по ярлыку на рабочем столе")
        print(f"  - Или запустите {exe_dst}")
        print("\nПомните, что для работы также требуется движок Kenga!")
        print("Скачайте его отдельно и убедитесь, что команда 'kenga' доступна в PATH.")
        
        return True
        
    except PermissionError:
        print(f"Ошибка: нет прав на запись в {install_path}")
        print("Запустите скрипт от имени администратора")
        return False
    except Exception as e:
        print(f"Ошибка при установке: {e}")
        return False


def register_in_registry(install_path):
    """Регистрация приложения в реестре Windows для деинсталляции"""
    try:
        import winreg
        
        # Создаем ключ в реестре для деинсталляции
        key_path = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KengaCAD"
        with winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "KengaCAD")
            winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, "1.0.0")
            winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "KengaCAD Development Team")
            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(install_path))
            winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(install_path / "KengaCAD.exe"))
            winreg.SetValueEx(key, "UninstallString", 0, winreg.REG_SZ, 
                             f'"{install_path}\\uninstall.bat"')
            winreg.SetValueEx(key, "URLInfoAbout", 0, winreg.REG_SZ, 
                             "https://github.com/GermannM3/KengaCAD")
        
        # Создаем скрипт деинсталляции
        uninstall_script = install_path / "uninstall.bat"
        with open(uninstall_script, 'w') as f:
            f.write(f'''@echo off
REM Скрипт деинсталляции KengaCAD
echo Удаление KengaCAD...

REM Удаляем приложение
rmdir /s /q "{install_path}"

REM Удаляем ярлыки
del "%USERPROFILE%\\Desktop\\KengaCAD.bat" 2>nul
rmdir /s /q "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\KengaCAD" 2>nul

REM Удаляем запись из реестра
reg delete "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KengaCAD" /f 2>nul

echo KengaCAD удален из системы.
pause
''')
        
        print("Приложение зарегистрировано в системе для деинсталляции")
        
    except ImportError:
        print("Модуль winreg не доступен, регистрация в реестре пропущена")
    except Exception as e:
        print(f"Ошибка при регистрации в реестре: {e}")


def main():
    print("Установщик KengaCAD")
    print("==================")
    print()
    
    success = install_kengacad()
    
    if success:
        print("\nУстановка завершена успешно!")
    else:
        print("\nУстановка завершена с ошибками!")
    
    input("\nНажмите Enter для выхода...")


if __name__ == "__main__":
    main()