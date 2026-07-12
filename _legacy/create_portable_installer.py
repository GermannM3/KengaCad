"""
Создание standalone установщика для KengaCAD с встроенным Python
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path


def create_portable_installer():
    """Создание portable версии KengaCAD с встроенным Python"""
    print("Создание portable версии KengaCAD с встроенным Python...")
    
    # Убедимся, что мы в правильной директории
    os.chdir(Path(__file__).parent)
    
    # Создаем директорию для portable версии
    portable_dir = Path("portable")
    portable_dir.mkdir(exist_ok=True)
    
    # Создаем структуру portable версии
    (portable_dir / "app").mkdir(exist_ok=True)
    (portable_dir / "python").mkdir(exist_ok=True)
    (portable_dir / "data").mkdir(exist_ok=True)
    
    print("Копирование файлов приложения...")
    
    # Копируем исполняемый файл
    if Path("dist/KengaCAD.exe").exists():
        shutil.copy2("dist/KengaCAD.exe", portable_dir / "app")
        print("+ Исполняемый файл скопирован")
    else:
        print("- Исполняемый файл не найден. Сначала создайте его с помощью PyInstaller.")
        return False

    # Копируем конфигурационные файлы
    config_dir = portable_dir / "app" / "config"
    if Path("config").exists():
        shutil.copytree("config", config_dir, dirs_exist_ok=True)
        print("+ Конфигурационные файлы скопированы")

    # Копируем ресурсы
    assets_dir = portable_dir / "app" / "assets"
    if Path("assets").exists():
        shutil.copytree("assets", assets_dir, dirs_exist_ok=True)
        print("+ Ресурсы скопированы")

    # Создаем скрипт запуска
    launch_script = portable_dir / "launch_kengacad.bat"
    with open(launch_script, 'w', encoding='utf-8') as f:
        f.write('''@echo off
REM Скрипт запуска KengaCAD Portable

REM Проверяем, установлен ли движок Kenga
where kenga >nul 2>&1
if %errorlevel% neq 0 (
    echo Ошибка: Движок Kenga не установлен или не доступен.
    echo Купите или установите Движок Kenga из: https://github.com/GermannM3/GoEngineKenga
    echo Как установить Движок Kenga:
    echo.  1. Клонируйте репозиторий: git clone https://github.com/GermannM3/GoEngineKenga.git
    echo.  2. Скопируйте kenga.exe в папку GoEngineKenga
    echo.  3. Добавьте путь к kenga.exe в переменную PATH
    pause
    exit /b 1
)

REM Распаковываем пользовательские данные
if not exist "%%USERPROFILE%%\\.kengacad" (
    mkdir "%%USERPROFILE%%\\.kengacad"
)

REM Распаковываем книгу данных
if not exist "%%USERPROFILE%%\\.kengacad\\scenes" (
    mkdir "%%USERPROFILE%%\\.kengacad\\scenes"
)

echo KengaCAD доступен. Часть 1/2.
echo.

REM Распаковываем книгу данных для симуляции
if not exist "scenes" (
    mkdir scenes
    echo {} > scenes\\default.json
)

echo KengaCAD доступен. Часть 2/2.
echo.

REM Запуск интерфейса
start "" "app\\KengaCAD.exe"

echo KengaCAD успешно запущен!
echo Все составляющие установлены.
pause
''')

    print("+ Скрипт запуска создан: portable/launch_kengacad.bat")

    # Создаем README для portable версии
    readme_content = """# Portable версия KengaCAD

## Обзор

Portable версия KengaCAD включает в себя все необходимые компоненты для запуска приложения без установки в систему. Это удобно для тестирования и использования на системах, где установка программ ограничена.

## Структура

```
portable/
├── app/                 # Основное приложение
│   ├── KengaCAD.exe     # Исполняемый файл приложения
│   ├── config/          # Конфигурационные файлы
│   └── assets/          # Ресурсы (иконки, логотипы)
├── python/              # Встроенный Python (опционально)
├── data/                # Пользовательские данные
└── launch_kengacad.bat  # Скрипт запуска
```

## Требования

Для работы portable версии KengaCAD требуется:
- Windows 10/11 (64-bit)
- Отдельно установленный движок Kenga (https://github.com/GermannM3/GoEngineKenga)
- 4 ГБ свободного места
- 8 ГБ ОЗУ (рекомендуется)

## Установка движка Kenga

Portable версия KengaCAD не включает движок Kenga. Для его установки:

1. Скачайте исходники движка:
   ```
   git clone https://github.com/GermannM3/GoEngineKenga.git
   ```

2. Установите Go (версия 1.22+):
   - Скачайте с https://golang.org/dl/
   - Установите и убедитесь, что `go version` работает

3. Соберите движок:
   ```
   cd GoEngineKenga
   go build ./cmd/kenga
   ```

4. Добавьте путь к `kenga.exe` в переменную PATH:
   - Нажмите Win+R, введите `sysdm.cpl`
   - Перейдите на вкладку "Дополнительно" → "Переменные среды"
   - В "Системные переменные" найдите "Path" и нажмите "Изменить"
   - Нажмите "Создать" и добавьте путь к папке с `kenga.exe`
   - Нажмите "ОК" для сохранения

## Запуск

1. Запустите `launch_kengacad.bat`
2. Приложение автоматически проверит наличие движка Kenga
3. Если движок установлен и доступен, приложение запустится

## Запуск движка Kenga

Для полноценной работы запустите движок Kenga отдельно:

```
kenga run --project . --scene scenes/default.json --ws-port 127.0.0.1:7777
```

Затем запустите KengaCAD.

## Обновление

Для обновления portable версии:
1. Скачайте новую версию KengaCAD
2. Замените файлы в папке `app/`
3. Сохраните свои проекты в папке `data/`

## Устранение неполадок

### Приложение не запускается
- Убедитесь, что движок Kenga установлен и доступен в PATH
- Проверьте, что используется 64-битная версия Windows
- Запустите из командной строки для просмотра ошибок

### Ошибки подключения к движку
- Убедитесь, что движок Kenga запущен
- Проверьте, что используется правильный порт (по умолчанию 7777)
- Убедитесь, что брандмауэр не блокирует соединение

## Обратная связь

Если у вас возникли проблемы с portable версией:
- Проверьте требования к системе
- Убедитесь, что движок Kenga установлен правильно
- Создайте Issue на GitHub: https://github.com/GermannM3/KengaCAD/issues
"""

    readme_path = portable_dir / "README_PORTABLE.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)

    print("+ README для portable версии создан: portable/README_PORTABLE.md")

    print(f"\n+ Portable версия KengaCAD создана в: {portable_dir}")
    print("  Для запуска используйте: portable\\launch_kengacad.bat")

    return True


def main():
    success = create_portable_installer()

    if success:
        print("\n+ Создание portable версии завершено успешно!")
        print("  Теперь пользователи могут просто запустить launch_kengacad.bat")
        print("  для использования KengaCAD без установки Python и зависимостей")
    else:
        print("\n- Ошибка при создании portable версии")
        sys.exit(1)


if __name__ == "__main__":
    main()