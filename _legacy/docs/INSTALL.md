# Установка KengaCAD

## Быстрый старт

1. **Движок Kenga** — скачайте с [GitHub Releases](https://github.com/GermannM3/GoEngineKenga/releases) или соберите из `GoEngineKenga`:
   ```bat
   python scripts/update_engine.py --build --version 0.2.0
   ```
2. **KengaCAD** — `python main.py` или запуск собранного exe из `dist/`.

## Windows

### Установщик

1. Скачайте `KengaCAD_Setup.exe` (один файл — приложение + движок)
2. Запустите — мастер установки с логотипом KengaCAD
3. После установки KengaCAD готов к работе (движок уже внутри)

### Портативная версия

1. Распакуйте `KengaCAD-Portable.zip`
2. Запустите `launch_kengacad.bat`
3. Движок — в `engine_bin/kenga.exe`

### DWG (AutoCAD)

Для работы с DWG нужен [ODA File Converter](https://www.opendesign.com/guestfiles/oda_file_converter).  
В KengaCAD: **Сервис → Настройка DWG** — укажите путь к `ODAFileConverter.exe`.

## Linux

- **Ubuntu/Debian**: `dpkg -i kengacad_*.deb`
- **Fedora/openSUSE**: `rpm -i kengacad_*.rpm`
- **Arch**: PKGBUILD в `installers/arch_package/`

## Требования

- **ОС**: Windows 10/11, Ubuntu 20.04+, Fedora 35+, Arch
- **ОЗУ**: 4 ГБ минимум, 8 ГБ рекомендуется
- **Python** (для разработки): 3.8+
- **Движок**: Go 1.22+ для сборки или готовый бинарник

## Сборка движка

```powershell
cd GoEngineKenga
$env:GOOS="windows"; $env:GOARCH="amd64"
go build -ldflags "-X goenginekenga/engine/version.Version=v0.2.0" -o dist/kenga.exe ./cmd/kenga
Copy-Item dist\kenga.exe ..\engine_bin\kenga.exe -Force
```

Или: `python scripts/update_engine.py --build --version 0.2.0`
