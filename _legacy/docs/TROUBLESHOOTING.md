# Решение проблем

## DLL load failed (QtWidgets)

- Переустановите PyQt: `scripts\fix-pyqt6-dll.ps1`
- Установите [VC++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- Python должен быть 64-bit

## Нет подключения к движку

- Запустите KengaCAD — движок стартует автоматически из `engine_bin/`
- Или: `update_engine.bat` — обновить движок
- Порт 7777 должен быть свободен

## DWG не открывается

- Сервис → Настройка DWG → указать ODAFileConverter.exe

## Обновление движка

```bat
python scripts/update_engine.py --build --version 0.2.0
```
