@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion

echo ========================================
echo  KengaCAD - сборка релизного EXE
echo ========================================
echo.

cd /d "%~dp0.."

REM 1. Сборка движка
echo [1/4] Сборка движка GoEngineKenga...
cd GoEngineKenga
set GOOS=windows
set GOARCH=amd64
set CGO_ENABLED=0
go build -o dist/kenga.exe ./cmd/kenga 2>nul
if errorlevel 1 (
    echo Ошибка: Go не найден или ошибка сборки. Установите Go.
    exit /b 1
)
if not exist dist mkdir dist
copy /Y dist\kenga.exe dist\kenga-windows-amd64.exe >nul
if not exist ..\engine_bin mkdir ..\engine_bin
copy /Y dist\kenga-windows-amd64.exe ..\engine_bin\kenga.exe >nul
cd ..
echo      OK
echo.

REM 2. Создать venv с Python 3.11 или 3.12 (стабильнее с PyQt6)
echo [2/4] Подготовка окружения...
set PYVER=
for %%v in (3.11 3.12 3.10) do (
    py -%%v -c "exit(0)" 2>nul
    if !errorlevel! equ 0 (
        set PYVER=%%v
        goto :found_py
    )
)
:found_py
if "%PYVER%"=="" (
    echo Используем системный Python
    set PYTHON_EXE=python
) else (
    echo Используем Python %PYVER%
    set PYTHON_EXE=py -%PYVER%
    if exist .venv_release rmdir /s /q .venv_release
    %PYTHON_EXE% -m venv .venv_release
    call .venv_release\Scripts\activate.bat
)

REM 3. Установить зависимости (PyQt6 6.5.2 - стабильнее на Windows)
echo [3/4] Установка зависимостей...
pip install --quiet --upgrade pip
pip install --quiet PyQt6==6.5.2 pyqtribbon websockets ezdxf numpy
pip install --quiet PyInstaller
pip install --quiet pillow
echo      OK
echo.

REM 4. PyInstaller
echo [4/4] Сборка EXE...
set ICON_ARG=
if exist "assets\logo.ico" set ICON_ARG=--icon=assets/logo.ico

python -m PyInstaller --noconfirm ^
    --name=KengaCAD ^
    --windowed ^
    --onedir ^
    --exclude-module=PySide6 ^
    --exclude-module=PySide2 ^
    --exclude-module=PyQt5 ^
    --add-data="config;config" ^
    --add-data="ui;ui" ^
    --add-data="engine;engine" ^
    --add-data="robot;robot" ^
    --add-data="cad;cad" ^
    --add-data="assets;assets" ^
    --add-data="engine_bin;engine_bin" ^
    --hidden-import=PyQt6 ^
    --hidden-import=websockets ^
    --hidden-import=ezdxf ^
    --hidden-import=numpy ^
    %ICON_ARG% ^
    main.py

if not exist "dist\KengaCAD\KengaCAD.exe" (
    echo Ошибка сборки. Проверьте вывод выше.
    exit /b 1
)

REM Создать архив для отправки
echo.
echo Создание архива KengaCAD_Portable.zip...
if exist KengaCAD_Portable.zip del KengaCAD_Portable.zip
powershell -Command "Compress-Archive -Path 'dist\KengaCAD\*' -DestinationPath 'KengaCAD_Portable.zip' -Force"
if exist KengaCAD_Portable.zip (
    echo.
    echo ========================================
    echo  Готово!
    echo  EXE: dist\KengaCAD\KengaCAD.exe
    echo  Архив: KengaCAD_Portable.zip
    echo.
    echo  Отправьте роботисту KengaCAD_Portable.zip
    echo  Он распаковывает и запускает KengaCAD.exe
    echo ========================================
) else (
    echo EXE собран: dist\KengaCAD\KengaCAD.exe
)

rem Cleanup venv if we created it
if exist .venv_release (
    echo.
    echo Удаление временного venv...
    rmdir /s /q .venv_release 2>nul
)
