# Windows: Smart App Control, SmartScreen и подпись установщика

*(По материалам документации .NET deploy и Inno Setup через Context7: для установщика Microsoft Authenticode и timestamp — стандартный путь; встроенные механизмы ISSigTool/Inno относятся к другой модели подписи и не заменяют SmartScreen для обычных пользователей.)*

## Почему блокируют `KengaCAD_Professional_Setup.exe`

**Интеллектуальное управление приложениями (Smart App Control)** и **SmartScreen** опираются на репутацию файла. У сборки без **Authenticode-подписи** издателя Windows часто **не может установить автора** — и показывает именно то окно, которое вы видите.

Это **не доказательство**, что внутри установщика «мало файлов». Сжатый LZMA пакет **~50 МБ** нормален при **~170 МБ распакованного** self-contained .NET + WPF + SkiaSharp.

## Что реально нужно для доверия у пользователей

1. **Код-подпись (Authenticode)** сертификатом от доверенного УЦ (часто **EV** для лучшей репутации с первого дня).
2. Подписать **и** `Setup.exe`, **и** по возможности **`KengaCAD.exe`** (и при необходимости деинсталлятор — см. `SignedUninstaller` в Inno).

Подпись делается утилитой **signtool** из Windows SDK (или среды сборки Visual Studio).

Пример (подставьте свой PFX и пароль; timestamp обязателен для долгой жизни подписи):

```text
signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f "C:\path\cert.pfx" /p "PASSWORD" "KengaCAD_Professional_Setup.exe"
```

## Связка с Inno Setup

В **Inno Setup** можно вызывать подпись при компиляции через **`SignTool`** в `[Setup]` и настройку имени инструмента в IDE: *Tools → Configure Sign Tools*.

Типичная строка для зарегистрированного инструмента с именем `signtool`:

```text
signtool sign /fd SHA256 /td SHA256 /tr http://timestamp.digicert.com /f "C:\path\cert.pfx" /p "PASSWORD" $f
```

Переменная **`$f`** подставляется Inno — это путь к собираемому `Setup.exe`.

В репозитории шаблон параметров см. `installers/CodeSigning.example.ini` (без секретов).

## Проверка без подписи (только своя машина / тест)

- **Smart App Control:** *Параметры → Конфиденциальность и защита → Безопасность Windows → Управление приложениями и браузером → Интеллектуальное управление приложениями* — для теста можно переключить в **Режим оценки** или **Откл.** (политика организации может запретить).
- Либо ставить не установщиком, а из **портативного ZIP** (см. сборку: `KengaCAD_Professional_win-x64_self-contained.zip`) — распаковать и запустить `KengaCAD.exe`; предупреждение может остаться, но иногда проще обойти для локальной проверки.

## Проверка, что внутри «полная» программа

После `.\build_installer_professional.ps1` смотрите:

- `installers\Output\PUBLISH_MANIFEST.txt` — размер распакованного набора, число файлов, контрольные имена DLL.
- `installers\Output\KengaCAD_Professional_Setup.sha256` — хеш установщика.
- ZIP с полным содержимым `publish\` — размер порядка **150–200 МБ**; это тот же набор файлов, что попадает в `{app}` при установке.
