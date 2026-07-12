# Команды KengaCAD

Команды вводятся в командной строке. Синтаксис частично совместим с AutoCAD.

Выбор: клик по объекту. Ctrl+клик — добавить/убрать. Рамка: слева направо = внутри, справа налево = пересекающие.

## Файл
- `NEW`, `OPEN`, `SAVE` — см. меню Файл
- Поддержка: .kengacad, .dxf, .dwg (ODA), .pdf

## Рисование
- `LINE x1 y1 x2 y2` | `CIRCLE x y r` | `ARC x y r start end` | `POINT x y`
- `RECTANGLE x1 y1 x2 y2` | `POLYLINE x1 y1 x2 y2 [x3 y3 ...]` | `SPLINE` | `ELLIPSE` | `TEXT`

## Редактирование
- `MOVE dx dy` | `COPY dx dy` | `STRETCH dx dy` | `ROTATE angle [cx cy]` | `SCALE factor [cx cy]`
- `ERASE` (E) | `MIRROR x1 y1 x2 y2` | `OFFSET distance` | `ARRAY R rows cols` | `ARRAY P count angle [cx cy]`
- `TRIM x y` | `EXTEND x y` | `FILLET radius` | `CHAMFER d1 [d2]`
- `BREAK x1 y1 x2 y2` — разрыв линии | `JOIN` — соединить линии | `EXPLODE` — разобрать блок
- `BLOCK name` | `INSERT block x y [scale] [angle]` | `HATCH [color]` | `DIMLINEAR` | `LINETYPE`

## Робот
- `LOAD_DEMO_ROBOT` | `LOAD_ROBOT path` | `TRAJECTORY path` | `TRAC_FROM_POLYLINE` | `EXPORT_TRAC`
- `SET_JOINT name deg` | `SIMULATE [steps]` | `START_DISPENSING` | `STOP_DISPENSING`

## Горячие клавиши
- Ctrl+N — новый | Ctrl+S — сохранить | Ctrl+0 — показать всё | F8 — орто | F10 — полярный

Полный список: [COMMAND_REFERENCE.md](../COMMAND_REFERENCE.md)
