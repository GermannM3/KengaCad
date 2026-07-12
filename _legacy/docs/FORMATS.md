# Поддерживаемые форматы KengaCAD

## Чертежи (CAD)

| Формат | Открыть | Сохранить |
|--------|---------|-----------|
| .kengacad | ✓ | ✓ |
| .dxf | ✓ | ✓ |
| .dwg | ✓ | ✓ (ODA) |
| .pdf | — | ✓ |

**DWG:** Сервис → Настройка DWG → указать ODAFileConverter.exe

## Траектории

| Формат | Импорт | Экспорт |
|--------|--------|---------|
| .json | ✓ | ✓ |
| .csv | ✓ | ✓ (RoboCAD) |

## Робот и 3D-модели

| Формат | Поддержка | Примечание |
|--------|-----------|------------|
| .gltf, .glb | ✓ | Загрузка напрямую |
| .obj | ✓ | Загрузка напрямую |
| .ipt | конвертация | Inventor Part. `kenga convert` или экспорт в Inventor |
| .iam | конвертация | Inventor Assembly. `kenga convert` или экспорт в Inventor |

**Inventor (.ipt / .iam):**

1. **Движок Kenga** — `kenga convert model.ipt -o model.glb` (требует Autodesk Forge API).
2. **Inventor** — Файл → Экспорт → glTF 3D.
3. **При `kenga import`** — автоконвертация при заданных `FORGE_CLIENT_ID` и `FORGE_CLIENT_SECRET`.
