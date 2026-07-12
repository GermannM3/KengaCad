<p align="center">
  <img src="KengaCAD/assets/logo.png" alt="KengaCAD Professional" width="160"/>
</p>

<h1 align="center">KengaCAD Professional</h1>

<p align="center">
  Офлайн-программирование промышленных роботов: 2D/3D-траектории, симуляция ячейки, экспорт KRL, RAPID, TP, UR, Yaskawa, G-code.
</p>

<p align="center">
  <a href="https://github.com/GermannM3/KengaCad/releases/latest">Скачать релиз</a>
  ·
  <a href="#windows-установка">Windows</a>
  ·
  <a href="#linux-и-macos">Linux / macOS</a>
  ·
  <a href="#android">Android</a>
</p>

---

## О программе

KengaCAD — программа для офлайн-программирования промышленных роботов. Рисуешь траекторию в 2D или 3D, задаёшь точки программы, смотришь симуляцию в ячейке, выгружаешь код под KUKA, ABB, Fanuc, UR, Yaskawa или G-code.

- **Windows (WPF)** — основная, полнофункциональная версия
- **Linux / macOS** — portable на PyQt (`_legacy`, те же конфиги и постпроцессоры)
- **Android (MAUI)** — jog, TCP, точки программы, экспорт KRL / RAPID / G-code

---

## Скачать

Страница релизов: **https://github.com/GermannM3/KengaCad/releases**

| Файл | Платформа | Описание |
|------|-----------|----------|
| `KengaCAD_Professional_X.X.X_Setup.exe` | Windows | Установщик, .NET ставить не нужно |
| `KengaCAD_Professional_X.X.X_win-x64.zip` | Windows | Portable: распаковал → `KengaCAD.exe` |
| `KengaCAD_Professional_X.X.X_linux-x64_portable.tar.gz` | Linux | PyQt-клиент, нужен Python 3 |
| `KengaCAD_Professional_X.X.X_linux-x64.AppImage` | Linux | Один файл (если собрался в CI) |
| `KengaCAD_Professional_X.X.X_macos_portable.tar.gz` | macOS | PyQt-клиент |
| `KengaCAD_Professional_X.X.X_android.apk` | Android | Упрощённый jog + экспорт, не полный CAD |

Новая версия появляется при теге `v2.2.0` и выше — GitHub Actions собирает все артефакты и прикрепляет к Release.

---

## Windows: установка

<a id="windows-установка"></a>

1. Скачай `Setup.exe` с Releases.
2. Запусти. SmartScreen на неподписанном exe — «Подробнее» → «Выполнить в любом случае», или возьми ZIP.
3. В меню Пуск появится **KengaCAD Professional**.
4. При первом запуске: лента сверху, 2D слева, 3D-робот справа, jog-пульт, журнал внизу.

**Минимум:** Windows 10/11 x64, 4 ГБ RAM, любая современная видеокарта с 3D.

---

## Windows: первые шаги

| Действие | Где |
|----------|-----|
| Выбор робота (KUKA, ABB, «Демо»…) | Вкладка **Робот** → «Загрузить» |
| Движение TCP | Jog-пульт справа, ползунки или X/Y/Z |
| Чертёж LINE, CIRCLE, POLYLINE | Вкладка **Главная**, клики на 2D-поле |
| Стол, конвейер, второй робот | Вкладка **Симуляция** |
| Точки P001, P002… | Jog → «Добавить текущую TCP» |
| MoveL / MoveJ, симуляция | Кнопки на jog-пульте → «Старт» |
| Экспорт KRL, RAPID, TP, UR… | **Файл** или лента |
| Сохранение проекта | `.kengacad`; DXF открывается и сохраняется |

Командная строка внизу: `LINE`, `CIRCLE`, `ZOOM`, `ESC` — отмена. Журнал **Output** пишет, что произошло.

---

## Linux и macOS

<a id="linux-и-macos"></a>

Полноценный WPF-клиент только под Windows. На Linux и macOS в Releases — portable с PyQt из `_legacy` и актуальными `config/`.

**Linux:**

```bash
tar xzf KengaCAD_Professional_2.2.0_linux-x64_portable.tar.gz
cd распакованная_папка
chmod +x install.sh run.sh
./install.sh
./run.sh
```

Нужны Python 3.10+, pip, Qt (Ubuntu: `python3-pyqt5` или PyQt5 из requirements).

**macOS:**

```bash
tar xzf KengaCAD_Professional_2.2.0_macos_portable.tar.gz
chmod +x install.sh run.sh KengaCAD.command
./install.sh
./KengaCAD.command
```

AppImage локально: `bash installers/linux/build_appimage.sh` (нужен Linux, не WSL без доработок).

---

## Android

<a id="android"></a>

APK в Releases: jog по осям, TCP, точки программы, экспорт KRL / RAPID / G-code через «Поделиться». Полный CAD и 3D-симуляция — только в desktop-версии.

---

## Сборка из исходников

Для разработчиков на Windows.

**Нужно:** .NET 8 SDK, .NET 9 + MAUI workload (Android), Inno Setup 6 (для установщика).

```powershell
git clone https://github.com/GermannM3/KengaCad.git
cd KengaCad
dotnet build KengaCAD.slnx -c Release
cd KengaCAD
dotnet run
```

**Android APK:**

```powershell
.\scripts\sync_mobile_config.ps1
dotnet publish KengaCAD.Mobile\KengaCAD.Mobile.csproj -f net9.0-android -c Release -p:AndroidPackageFormat=apk
```

**Установщик и ZIP:**

```powershell
.\build_installer_professional.ps1
```

**Все платформы:**

```powershell
.\build_all_installers.ps1
```

Подробнее: `docs/BUILD.md`, `docs/RELEASE_CHECKLIST.md`.

---

## Новый релиз на GitHub

1. Версия в `KengaCAD/KengaCAD.csproj`, `KengaCAD.Mobile/KengaCAD.Mobile.csproj`, `installers/KengaCAD_Professional.iss`.
2. Коммит в `main`.
3. Тег и push:

```bash
git tag v2.2.0
git push origin v2.2.0
```

Workflow `.github/workflows/release.yml` соберёт Setup, ZIP, Linux, macOS, AppImage и Android APK.

---

## Настройки и конфиги

Рядом с exe — папка `config/`:

| Файл | Назначение |
|------|------------|
| `robots.json` | Модели роботов, DH-параметры |
| `postprocessors.json` | Шаблоны постпроцессоров |
| `templates/*.sbn` | KRL, RAPID и др. |
| `settings.json` | Пути FreeCAD (STEP) и ODA (DWG) |

- **STEP/IGES** — без FreeCAD не конвертируются; укажи `freecad_path` в `settings.json`
- **DWG** — нужен ODA File Converter, путь в `settings.json`

---

## OPC UA и I/O

В левой панели — блок **Сигналы I/O**.

- Endpoint по умолчанию: `opc.tcp://localhost:4840`
- Кнопка **OPC** — подключение к PLC
- Колонка **NodeId** — адреса узлов
- DO меняются из программы и из таблицы

---

## Структура репозитория

```
KengaCAD/              WPF desktop (Windows)
KengaCAD.Core/         Роботы, постпроцессоры (Scriban 7.x)
KengaCAD.Mobile/       MAUI Android
_legacy/               PyQt для Linux/macOS
installers/            Inno Setup, AppImage
scripts/               Скрипты сборки
docs/                  BUILD, подпись, релизы
build_installer_professional.ps1
build_all_installers.ps1
```

---

## Логи и проблемы

**Crash log (Windows):**

```
%LocalAppData%\KengaCAD\crash_log.txt
```

**Smart App Control** блокирует неподписанный Setup — см. [docs/WINDOWS_TRUST_AND_SIGNING.md](docs/WINDOWS_TRUST_AND_SIGNING.md). Подпись в CI: secrets `KENGACAD_CODESIGN_PFX_BASE64` + `KENGACAD_CODESIGN_PASS`; локально: `scripts/setup_codesign_cert.ps1`.

---

## Лицензия

Проприетарное ПО. Текст — `LICENSE.txt` и экран установки.

KengaCAD Team, 2026.
