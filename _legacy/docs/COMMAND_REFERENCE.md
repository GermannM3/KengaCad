# Команды KengaCAD

## Обзор

Команды вводятся в командной строке в нижней части экрана. Синтаксис частично совместим с AutoCAD.

Выбор объектов: щёлкните по объекту для выделения (синяя подсветка). Ctrl+клик — добавить/убрать из выбора. Перетащите мышью (при пустом клике) — выбор рамкой: слева направо = только целиком внутри, справа налево = пересекающие. Ctrl+рамка — добавить к выбору.

## Реализованные команды

### Файл
- `NEW` — новый чертёж (Ctrl+N)
- `OPEN` — открыть KengaCAD (.kengacad) или DXF
- `SAVE` — сохранить (Ctrl+S). Поддерживаются: .kengacad, .dxf, .dwg (ODA), .pdf
- `SAVE AS` — сохранить как (диалог)

### Рисование
- `LINE x1 y1 x2 y2 [z1 z2]` — линия
- `CIRCLE x y [z] r` — окружность
- `ARC x y r start_angle end_angle` — дуга
- `POINT x y [z]` — точка
- `RECTANGLE x1 y1 x2 y2 [z]` — прямоугольник
- `POLYLINE x1 y1 x2 y2 [x3 y3 ...]` — полилиния (пары или тройки координат)
- `SPLINE x1 y1 x2 y2 [x3 y3 ...]` — сплайн по опорным точкам
- `ELLIPSE cx cy majorX majorY [ratio]` — эллипс (ratio — отношение осей, по умолчанию 1)
- `TEXT x y [z] height text` — текст

### Редактирование
- `MOVE dx dy` — перемещение выбранных объектов
- `COPY dx dy` — копирование выбранных объектов
- `STRETCH dx dy` — растягивание выбранных объектов
- `EXPLODE` — разобрать блок (INSERT) на отдельные объекты
- `BREAK x1 y1 x2 y2` — разрыв линии между точками (выберите 1 линию)
- `JOIN` — соединить коллинеарные линии в полилинию (выберите 2+ линии)
- `ROTATE angle [cx cy]` — поворот выбранных объектов
- `SCALE factor [cx cy]` — масштабирование выбранных объектов
- `ERASE` / `E` — удаление выбранных объектов
- `MIRROR x1 y1 x2 y2` — отражение по оси (x1,y1)–(x2,y2)
- `OFFSET distance` — смещение линий, полилиний, окружностей, дуг
- `ARRAY R rows cols [rowDist colDist]` — прямоугольный массив
- `ARRAY P count angle [cx cy]` — полярный массив
- `TRIM x y` — обрезка выбранной линии в точке (x,y)
- `EXTEND x y` — удлинение выбранной линии до точки (x,y)
- `FILLET radius` — скругление двух выбранных линий
- `CHAMFER distance` или `CHAMFER d1 d2` — срез угла двух линий
- `DIMLINEAR x1 y1 x2 y2 [xm ym]` — линейный размер
- `DIMRADIUS` / `DRA` — размер радиуса (выберите круг)
- `DIMDIAMETER` / `DDI` — размер диаметра (выберите круг)
- `LINETYPE [Continuous|Dashed|Dotted|DashDot|DashDotDot]` — тип линии для новых объектов
- `HATCH [color]` — штриховка выбранной замкнутой полилинии или круга (color — например #555555)
- `BLOCK name [base_x base_y]` — создать блок из выбранных объектов
- `INSERT block_name x y [scale] [angle]` — вставить блок
- `DISTANCE` — расстояние между двумя выбранными точками или линиями
- `AREA` — площадь выбранных кругов и замкнутых полилиний
- `MULTIPLE [cmd]` — повтор команды
- `PEDIT W width` — ширина полилинии | `PEDIT J` — соединить полилинии
- `LAYER NEW name` | `SET name` | `FREEZE name` | `THAW name` | `LOCK name` | `UNLOCK name` | `DELETE name`
- `XREF ATTACH path` — прикрепить файл как блок
- `UNDO` / `U` — отмена
- `REDO` / `R` — повтор

### Вид
- `GRID [шаг]` — сетка (вкл/выкл или шаг)
- `ZOOM_EXTENTS` / `ZE` — показать всё (Ctrl+0)
- `VIEW_TOP` / `VT` — вид сверху
- `VIEW_FRONT` / `VF` — вид спереди
- `VIEW_LEFT` / `VL` — вид слева
- Масштаб: колёсико мыши
- Сдвиг: средняя кнопка мыши

### Робот и траектории
- `LOAD_DEMO_ROBOT` — загрузить встроенную модель робота
- `LOAD_ROBOT <path>` — загрузить модель (glTF/GLB)
- `TRAJECTORY <path>` — траектория из JSON или CSV (RoboCAD-совместимый)
- `TRAC_FROM_POLYLINE` — траектория из последней полилинии
- `EDIT_TRAC` — редактировать траекторию (таблица X,Y,Z)
- `EXPORT_TRAC [path]` — экспорт в JSON, CSV, KUKA KRL (.krl), ABB RAPID (.mod)
- `SET_JOINT <name> <deg>` — угол сустава
- `SIMULATE [steps]` — симуляция
- `CHECK_COLLISION [entity_id]` — проверка коллизий
- `REACHABILITY x y z` — проверка достижимости позиции (обратная кинематика)

### Диспенсинг
- `START_DISPENSING [flow] [radius]` — начать нанесение
- `STOP_DISPENSING` — остановить
- `CALIBRATE_DISPENSER` — подсказка по калибровке

### Сцена
- `CLEAR_SCENE` — очистить сцену

### Системные
- `STATUS` — статус
- `HELP` — справка

## Примеры

### Прямоугольник и траектория
```
RECTANGLE 0 0 100 50
TRAC_FROM_POLYLINE
EXPORT_TRAC path.json
```

### Траектория из полилинии
```
POLYLINE 0 0 100 50 200 100 300 80
TRAC_FROM_POLYLINE
EDIT_TRAC
TRAC_LENGTH
```

### Экспорт для контроллеров
```
TRAC_FROM_POLYLINE
EXPORT_TRAC path.krl
EXPORT_TRAC path.mod
```

### Проверка достижимости
```
LOAD_DEMO_ROBOT
REACHABILITY 100 0 50
CHECK_COLLISION
```

### Блок
```
LINE 0 0 10 0
LINE 10 0 10 10
LINE 10 10 0 10
LINE 0 10 0 0
(выбрать все)
BLOCK MySymbol
INSERT MySymbol 50 50 2 45
```

### Загрузка робота и траектории
```
LOAD_DEMO_ROBOT
LOAD_ROBOT path/to/robot.glb
TRAJECTORY path/to/trajectory.json
```

### Симуляция
```
SIMULATE 60
```

## Синонимы (AutoCAD-совместимые)

- `L` — LINE | `C` — CIRCLE | `A` — ARC | `PL` — POLYLINE | `REC` — RECTANGLE
- `M` — MOVE | `CO` — COPY | `E` — ERASE | `RO` — ROTATE | `SC` — SCALE
- `MI` — MIRROR | `O` — OFFSET | `TR` — TRIM | `EX` — EXTEND | `F` — FILLET
- `CHA` — CHAMFER | `BR` — BREAK | `J` — JOIN | `X` — EXPLODE
- `D` / `DLI` — DIMLINEAR | `DRA` — DIMRADIUS | `DDI` — DIMDIAMETER
- `PE` — PEDIT | `LA` — LAYER

## Интерактивный ввод (AutoCAD-like)

- `LINE` или `L` без аргументов — указать точки мышью
- `CIRCLE` или `C` без аргументов — центр мышью, затем радиус
- `ARC` или `A` без аргументов — центр, начало, конец дуги
- Enter — завершить LINE (цепочку линий)
- Esc — отменить текущую команду

## Сокращения и горячие клавиши

- `ZE` — ZOOM_EXTENTS (Ctrl+0)
- `U` — UNDO
- `R` — REDO
- Delete — ERASE (удаление выбранных)
- F8 — орто
- F10 — полярный режим
- `VT` — VIEW_TOP
- `VF` — VIEW_FRONT
- `VL` — VIEW_LEFT
- Ctrl+N — новый чертёж
- F8 — ортогональный режим
- F10 — полярный режим

## Автодополнение

Командная строка поддерживает автодополнение по Tab и историю (стрелки вверх/вниз).