# Release Checklist (Factory-Ready)

## Preflight
1. `python build_scripts/preflight_check.py` returns OK.
1. `config/settings.json` has correct `app.name`, `app.product_name`, `app.version`.
1. `assets/logo.png` exists (and `assets/logo.ico` for Windows icon).

## Build
1. Windows: `python build_scripts/build_windows.py`
1. Linux: `python3 build_scripts/build_linux.py`

## Installers
1. Windows installer created (Inno Setup): `build_scripts/create_innosetup_installer.py` → `build_scripts/build_innosetup.bat`
1. MSI (WiX, optional): `build_scripts/create_msi_with_wix.py` → `build_scripts/build_msi_wix.bat`
1. Linux DEB: `build_scripts/build_deb.sh`
1. Linux RPM: `build_scripts/build_rpm.sh`
1. Linux Arch: `build_scripts/build_arch.sh`
1. AppImage: `build_scripts/build_appimage.sh`

## Release Packaging
1. `python build_scripts/package_release.py`
1. Artifacts in `release/<version>/` are correctly named.

## Factory Demo
1. Install on a clean Windows 10/11 machine.
1. Install on a clean Linux machine (Debian/Ubuntu or Fedora/RHEL).
1. Launch KengaCAD → engine auto-starts → no manual steps.
1. Create a simple `POINT/LINE/CIRCLE`, save DXF, reopen DXF.
1. Load robot model and run `SIMULATE`.

## Перед отправкой на тест (критично)
1. **Средняя кнопка мыши** — сдвиг вида (pan), не падает.
2. **Интерактивный режим** — Линия/Окружность/Прямоугольник: клик по точкам мышью.
3. **Резиновая линия** — при рисовании видна пунктирная линия до курсора.
4. **Оси и начало** — видны на холсте, кнопка «К началу координат» (вкладка Вид).
5. **Недавние файлы** — Файл → Недавние после открытия/сохранения.
6. **Привязка к сетке** — при отсутствии объектов курсор привязывается к узлам сетки.
7. **Правый клик** — контекстное меню на холсте (Отменить, Показать всё, Масштаб к выделению, Быстрый старт).
8. **Заголовок окна** — имя файла и * при несохранённых изменениях.
9. **Ctrl+A** — выделить все объекты.
10. **К выделению** — масштаб к выделенным объектам (вкладка Вид, ZOOM_SELECTION / ZS).
11. **Пустое состояние** — подсказка «4 шага» (Полилиния → TRAC_FROM_POLYLINE → LOAD_DEMO_ROBOT → SIMULATE).
12. **Панель 3D/Робот** — справа: «Загрузить демо-робота», «Траектория из полилинии», «Симуляция».
13. **Статус Connected/Disconnected** — зелёный/красный текст в статус-баре.