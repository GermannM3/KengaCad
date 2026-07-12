# Сборка KengaCAD Professional

## Требования

- Windows 10/11 (x64)
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0)
- Для установщика: [Inno Setup 6](https://jrsoftware.org/isdl.php) (стандартный путь: `C:\Program Files (x86)\Inno Setup 6\`)

## Сборка приложения

```bash
cd KengaCAD
dotnet restore
dotnet build -c Release
```

Запуск: `dotnet run` или `bin\Release\net8.0-windows\KengaCAD.exe`.

## Публикация (self-contained)

```bash
cd KengaCAD
dotnet publish -c Release -o publish -r win-x64 --self-contained true -p:PublishSingleFile=false
```

Папка `publish/` будет содержать все нужные файлы; можно копировать на другой ПК без установки .NET.

## Установщик

Из **корня** репозитория (не из папки KengaCAD):

**PowerShell (рекомендуется):**
```powershell
.\build_installer_professional.ps1
```

**Cmd:**
```cmd
build_installer_professional.bat
```

Скрипт:
1. Удаляет старую папку `KengaCAD\publish\` (иначе можно получить неполный набор DLL и «мгновенную» установку без рантайма).
2. Публикует приложение в `KengaCAD\publish\` (win-x64, self-contained).
3. Проверяет наличие `KengaCAD.exe` и `clrjit.dll`, выводит размер и число файлов.
4. Копирует config и assets в publish.
5. Запускает Inno Setup и собирает `installers\Output\KengaCAD_Professional_Setup.exe`.

Ожидаемо: **~170 МБ** в `publish\`, **~50 МБ** у `KengaCAD_Professional_Setup.exe` (сжатие). Дополнительно: **ZIP** `KengaCAD_Professional_win-x64_self-contained.zip` (~70–90 МБ) — полный состав для проверки без установщика; **PUBLISH_MANIFEST.txt**, **\*.sha256**.

Долгая установка не означает «качаем зависимости» — они уже внутри архива. Блокировка Windows у неподписанного setup: `docs/WINDOWS_TRUST_AND_SIGNING.md`, `installers/sign_installer.ps1`.

Если Inno Setup не установлен, выполнится только шаг 1–2; установщик можно собрать позже, установив Inno и запустив скрипт снова.

## Лог падения

При сбое приложение пишет лог в:
`%LocalAppData%\KengaCAD\crash_log.txt`

По нему можно увидеть полный текст исключения и стек вызовов.
