KengaCAD Professional

Профессиональная CAD/CAM система для программирования промышленных роботов. Версия на C# / WPF для Windows.


Требования

Windows 10/11 (x64). Установщик содержит всё необходимое, отдельно ставить .NET не нужно.


Установка

1. Скачайте установщик KengaCAD_Professional_Setup.exe.
2. Запустите его и примите лицензионное соглашение.
3. Укажите папку установки и завершите установку.
4. Запуск: ярлык на рабочем столе или «Пуск» → «KengaCAD Professional».


Возможности

2D-черчение: линии, окружности, полилинии, прямоугольники; слои и привязки.
3D-сцена: вид камеры и модели робота (стандартный WPF Viewport3D).
Кинематика роботов: прямая кинематика (FK) по параметрам Денавита — Хартенберга для 6DOF.
Постпроцессоры — экспорт траекторий в форматы KUKA KRL (.krl), ABB RAPID (.mod), Fanuc TP (.ls), Yaskawa/Motoman INFORM (.jbi), Universal Robots URScript (.urp), G-code (.gcode).
Конфигурация: выбор робота из списка (config/robots.json), настройки постпроцессоров (config/postprocessors.json).


Сборка из исходников

Откройте папку KengaCAD в терминале. Выполните:

  dotnet restore
  dotnet build -c Release
  dotnet run

Или запустите build_csharp.bat.

Исполняемый файл: bin\Release\net8.0-windows\KengaCAD.exe или publish\KengaCAD.exe после публикации.


Создание установщика

Из корня репозитория (папка KengaCAD на уровень выше) запустите:

  build_installer_professional.bat   (cmd)
  .\build_installer_professional.ps1   (PowerShell)

Нужен установленный Inno Setup 6 (по умолчанию: C:\Program Files (x86)\Inno Setup 6\). Скрипт делает self-contained публикацию и собирает один EXE в installers\Output\KengaCAD_Professional_Setup.exe. Заказчику не нужно ставить .NET.


Лицензия

Проприетарное ПО. Использование регулируется лицензионным соглашением, отображаемым при установке.

KengaCAD Team, 2026.
