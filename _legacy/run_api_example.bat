@echo off
REM Скрипт для запуска примера Python API

echo Запуск примера Python API для KengaCAD...

REM Проверяем, установлен ли Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Python не найден. Установите Python 3.8 или выше.
    pause
    exit /b 1
)

REM Проверяем, установлены ли зависимости
python -c "import websockets" >nul 2>&1
if errorlevel 1 (
    echo Устанавливаю зависимости...
    pip install -r requirements.txt
)

REM Запускаем пример
echo Запуск примера Python API...
python examples/python_api_example.py

pause