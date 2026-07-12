@echo off
chcp 65001 >nul
echo Обновление движка Kenga для KengaCAD
echo.
echo Закройте KengaCAD перед обновлением.
pause

python scripts\update_engine.py --pull --build
if %ERRORLEVEL% neq 0 (
    echo.
    echo Попытка сборки без pull...
    python scripts\update_engine.py --build
)
if %ERRORLEVEL% neq 0 (
    echo.
    echo Попытка загрузить из GitHub Release...
    python scripts\update_engine.py --version 0.2.0
)

if exist engine_bin\kenga_new.exe (
    echo.
    echo Файл engine_bin\kenga.exe занят. Скопирован в kenga_new.exe
    echo Закройте KengaCAD и выполните:
    echo   move engine_bin\kenga_new.exe engine_bin\kenga.exe
)
pause
