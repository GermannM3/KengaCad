# Релизы

## Checklist

1. Preflight: `python build_scripts/preflight_check.py`
2. config/settings.json: version, name
3. assets/logo.png, logo.ico
4. Сборка: `build_windows.py` / `build_linux.py`
5. Установщики: Inno Setup, MSI, DEB, RPM
6. `python build_scripts/package_release.py`

## Файлы

- `RELEASE_CHECKLIST.md` — полный checklist
- `RELEASE_ROADMAP.md` — roadmap
- `RELEASE_README.md` — readme для релиза
