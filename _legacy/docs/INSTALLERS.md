# Установщики KengaCAD

## Windows

| Тип | Файл | Описание |
|-----|------|----------|
| Inno Setup | KengaCAD_Setup.exe | Установка в Program Files, ярлыки |
| Portable | KengaCAD_Portable.zip | Без установки, распаковать и запустить |
| MSI | .msi | WiX-установщик |

## Linux

| Тип | Команда |
|-----|---------|
| DEB | `dpkg -i kengacad_*.deb` |
| RPM | `rpm -i kengacad_*.rpm` |
| Arch | PKGBUILD в `installers/arch_package/` |
| AppImage | `build_scripts/build_appimage.sh` |

## Сборка

См. [BUILD.md](BUILD.md), `build_scripts/BUILD_INSTRUCTIONS.md`, `build_scripts/release_pipeline.py`
