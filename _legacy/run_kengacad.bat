@echo off
REM Скрипт для запуска KengaCAD

echo Запуск KengaCAD...

REM Проверяем, установлен ли Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден. Установите Python 3.8 или выше.
    pause
    exit /b 1
)

REM Проверяем, установлены ли зависимости
echo Проверка зависимостей...
python -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo Установка зависимостей...
    pip install -r requirements.txt
)

REM Проверяем, существует ли исполняемый файл
if exist "dist\KengaCAD.exe" (
    echo Запуск KengaCAD из исполняемого файла...
    start "" "dist\KengaCAD.exe"
) else (
    echo Исполняемый файл не найден, запуск из исходников...
    python main.py
)

if errorlevel 1 (
    echo Ошибка запуска KengaCAD
    pause
    exit /b 1
)

echo KengaCAD успешно запущен!
pause