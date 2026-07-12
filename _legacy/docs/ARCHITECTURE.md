# Архитектура KengaCAD

## Обзор

KengaCAD — CAD-приложение с модульной архитектурой. Model-View-ViewModel (MVVM) + взаимодействие с движком Kenga через WebSocket.

## Структура проекта

```
KengaCAD/
├── main.py                 # Точка входа
├── kengacad_app.py         # Основной класс приложения
├── updates.py              # Проверка обновлений (заготовка)
├── config/                 # Настройки
├── ui/                     # Интерфейс (main_window, ribbon, command_line, drawing_area)
├── engine/                 # WebSocket клиент к движку
├── robot/                  # Модель робота
├── cad/                    # Траектории, import_export, dwg_setup
├── build_scripts/          # Сборка, установщики
├── installers/             # DEB, RPM, Inno Setup
├── docs/                   # Документация
└── scripts/                # update_engine, build-engine
```

## Слои

| Слой | Файлы | Ответственность |
|------|-------|-----------------|
| UI | ui/ | Ribbon, командная строка, область рисования |
| Application | main.py, kengacad_app.py | Жизненный цикл, оркестрация |
| Domain | robot/, cad/ | Модель робота, траектории, импорт/экспорт |
| Infrastructure | engine/, config/ | WebSocket, настройки |

## Обновления

Структура в `updates.py` и `config.settings.updates` — для будущей интеграции с GitHub Releases / Tauri.

См. также [BUILD.md](BUILD.md), [docs/INDEX.md](INDEX.md).
