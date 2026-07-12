@echo off
REM Скрипт для установки движка Kenga

echo Установка движка Kenga...

REM Проверяем, установлен ли Go
go version >nul 2>&1
if errorlevel 1 (
    echo Go не установлен. Установите Go 1.22+.
    pause
    exit /b 1
)

REM Проверяем, установлен ли Git
git version >nul 2>&1
if errorlevel 1 (
    echo Git не установлен. Установите Git.
    pause
    exit /b 1
)

REM Клонируем репозиторий
if not exist "GoEngineKenga" (
    echo Клонирование репозитория GoEngineKenga...
    git clone https://github.com/GermannM3/GoEngineKenga.git
) else (
    echo Репозиторий GoEngineKenga уже существует, обновляем...
    cd GoEngineKenga
    git pull
    cd ..
)

REM Переходим в директорию движка и собираем
cd GoEngineKenga
echo Сборка движка Kenga...
go build ./cmd/kenga

REM Возвращаемся в директорию KengaCAD
cd ..

echo Движок Kenga установлен и готов к использованию!
echo Для запуска используйте run_engine.bat

pause