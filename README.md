KengaCAD Professional

KengaCAD — программа для офлайн-программирования промышленных роботов. Рисуешь траекторию в 2D или 3D, задаёшь точки программы, смотришь симуляцию в ячейке, выгружаешь код под KUKA, ABB, Fanuc, UR, Yaskawa или G-code. Версия для Windows — основная, полнофункциональная. Для Linux и macOS есть переносимый пакет на PyQt (другой интерфейс, те же конфиги роботов и постпроцессоры).


Скачать готовую программу

Открой страницу Releases на GitHub:

https://github.com/GermannM3/KengaCad/releases

Там лежат файлы под каждую систему. Выбирай по названию:

KengaCAD_Professional_X.X.X_Setup.exe — установщик для Windows 10/11 (64 bit). Ставится как обычная программа, .NET отдельно ставить не нужно.

KengaCAD_Professional_X.X.X_win-x64.zip — Windows без установки. Распаковал папку, запустил KengaCAD.exe.

KengaCAD_Professional_X.X.X_linux-x64_portable.tar.gz — Linux. Архив с Python-клиентом, нужен Python 3 и пара минут на первую настройку (ниже).

KengaCAD_Professional_X.X.X_linux-x64.AppImage — Linux, один файл, если сборка AppImage прошла в релизе.

KengaCAD_Professional_X.X.X_macos_portable.tar.gz — macOS, тоже через Python.

Новые версии появляются, когда на репозитории ставят тег вида v2.1.0. GitHub Actions сам собирает все варианты и прикрепляет к Release.


Windows: установка за пять минут

1. Скачай Setup.exe с Releases.
2. Запусти. Если Windows ругается SmartScreen — это нормально для неподписанного exe: «Подробнее» → «Выполнить в любом случае», либо возьми ZIP и распакуй.
3. После установки в меню Пуск будет KengaCAD Professional.
4. При первом запуске откроется тёмное окно с лентой сверху, 2D-полем слева, 3D-robot справа, jog-пультом справа, журналом внизу.

Минимальные требования: Windows 10/11, 64 bit, 4 ГБ RAM, видеокарта с нормальной поддержкой 3D (любая современная встроенная или дискретная).


Windows: первые шаги в программе

Вкладка «Робот» — выбери модель в списке (KUKA, ABB и т.д.) или «Демо». Кнопка «Загрузить» подтягивает пресет.

Jog-пульт справа — ползунки осей или кнопки X/Y/Z двигают TCP. Внизу видны координаты.

Вкладка «Главная» — инструменты LINE, CIRCLE, POLYLINE. Кликаешь на 2D-поле, строишь контур.

Вкладка «Симуляция» — «Стол», «Конвейер», «+ Робот» для второго робота в ячейке, «Коллизии» для проверки.

Программа робота: на jog-пульте «Добавить текущую TCP» — появляется точка P001, P002… Кнопки +MoveL, +MoveJ собирают операции. «Старт» гоняет симуляцию.

Экспорт кода: вкладка «Файл» или лента — KRL, RAPID, TP, UR и т.д. Нужна хотя бы одна точка или траектория на чертеже.

Журнал Output внизу пишет, что произошло. Командная строка внизу принимает команды как в CAD: LINE, CIRCLE, ZOOM и ESC для отмены.

Файл → Сохранить — формат .kengacad. DXF тоже открывается и сохраняется.


Linux и macOS

Полноценный WPF-клиент только под Windows. На Linux и macOS в Releases лежит portable-архив с PyQt-версией из папки _legacy и актуальными config (robots.json, постпроцессоры).

Linux:

  tar xzf KengaCAD_Professional_2.1.0_linux-x64_portable.tar.gz
  cd распакованная_папка
  chmod +x install.sh run.sh
  ./install.sh
  ./run.sh

Нужны: Python 3.10+, pip, системные библиотеки Qt (на Ubuntu обычно python3-pyqt5 или pip поставит PyQt5 из requirements).

macOS:

  tar xzf KengaCAD_Professional_2.1.0_macos_portable.tar.gz
  chmod +x install.sh run.sh KengaCAD.command
  ./install.sh
  ./KengaCAD.command

AppImage на Linux можно собрать локально: bash installers/linux/build_appimage.sh (нужен Linux, не WSL без доработок).


Сборка из исходников (Windows, для разработчиков)

Нужны: .NET 8 SDK, Windows, для установщика — Inno Setup 6.

  git clone https://github.com/GermannM3/KengaCad.git
  cd KengaCad
  cd KengaCAD
  dotnet build -c Release
  dotnet run

Установщик и ZIP из корня репозитория:

  .\build_installer_professional.ps1

Все платформы сразу (Windows + portable Linux/macOS):

  .\build_all_installers.ps1

Подробнее для maintainer: docs/BUILD.md, docs/RELEASE_CHECKLIST.md.


Как выпустить новую версию на GitHub

1. Подними версию в KengaCAD/KengaCAD.csproj и installers/KengaCAD_Professional.iss.
2. Закоммить изменения в main.
3. Поставь тег и запушь:

  git tag v2.1.0
  git push origin v2.1.0

Workflow .github/workflows/release.yml соберёт Windows (Setup + ZIP), Linux portable (+ AppImage если получится), macOS portable и создаст Release с файлами.


Настройки и конфиги

После установки рядом с exe лежит папка config:

  robots.json — модели роботов и DH-параметры
  postprocessors.json — какие шаблоны постпроцессоров
  templates/*.sbn — шаблоны KRL, RAPID и др.
  settings.json — пути к FreeCAD (STEP) и ODA (DWG), если нужен импорт

STEP/IGES: без FreeCAD не конвертируются — укажи freecad_path в settings.json.
DWG: нужен ODA File Converter, путь в settings.json.


OPC UA и I/O

В левой панели блок «Сигналы I/O». Endpoint по умолчанию opc.tcp://localhost:4840. Кнопка OPC — подключение к PLC. В колонке NodeId пропиши адреса узлов. DO можно менять из программы и из таблицы.


Структура репозитория

KengaCAD/ — исходники C# WPF (основной продукт)
_legacy/ — PyQt-клиент для Linux/macOS
installers/ — Inno Setup, скрипты AppImage и DMG
scripts/ — вспомогательные скрипты сборки
docs/ — документация по сборке и подписи
tools/ — утилиты разработки (не нужны пользователю)
build_installer_professional.ps1 — сборка Windows-установщика
build_all_installers.ps1 — Windows + portable для Unix


Логи и проблемы

Если программа упала на Windows, смотри:

  %LocalAppData%\KengaCAD\crash_log.txt

Smart App Control блокирует неподписанный Setup — см. docs/WINDOWS_TRUST_AND_SIGNING.md и installers/sign_installer.ps1 для подписи.


Лицензия

Проприетарное ПО. Текст соглашения — LICENSE.txt и экран при установке.

KengaCAD Team, 2026.
