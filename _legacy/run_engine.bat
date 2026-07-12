@echo off
REM Скрипт для запуска движка Kenga с параметрами для KengaCAD

echo Запуск движка Kenga для KengaCAD...

REM Проверяем, установлен ли движок Kenga
where kenga >nul 2>&1
if errorlevel 1 (
    echo Движок Kenga не найден в PATH.
    echo Установите Kenga и убедитесь, что путь к нему добавлен в переменную PATH.
    pause
    exit /b 1
)

REM Запускаем движок Kenga с WebSocket API
echo Запуск движка Kenga с WebSocket API на порту 7777...
kenga run --project . --scene scene.json --ws-port 127.0.0.1:7777

pause