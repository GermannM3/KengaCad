# Аудит соответствия KengaCAD и AutoCAD

## Цель

Сравнение базовых команд и рабочих процессов KengaCAD с AutoCAD для выявления совпадений и расхождений.

---

## 1. Соответствие команд

### Файл — полное соответствие

| AutoCAD | KengaCAD | Примечание |
|---------|----------|------------|
| NEW | NEW | Ctrl+N |
| OPEN | OPEN | .kengacad, .dxf, .dwg |
| SAVE | SAVE | Ctrl+S |
| SAVEAS | SAVEAS | сохранить как |

### Рисование — базовое соответствие

| AutoCAD | KengaCAD | Совпадение |
|---------|----------|------------|
| LINE (L) | LINE x1 y1 x2 y2 | синтаксис через координаты вместо интерактивного ввода |
| CIRCLE (C) | CIRCLE x y r | центр + радиус |
| ARC | ARC x y r start end | параметры |
| POINT | POINT x y | точка |
| RECTANGLE (REC) | RECTANGLE x1 y1 x2 y2 | прямоугольник |
| PLINE/POLYLINE | POLYLINE x1 y1 x2 y2 [...] | полилиния |
| SPLINE | SPLINE x1 y1 x2 y2 [...] | сплайн |
| ELLIPSE | ELLIPSE cx cy majX majY [ratio] | эллипс |
| TEXT | TEXT x y height text | текст |

Различия: В AutoCAD большинство команд интерактивные (указание точек мышью). В KengaCAD — координаты в командной строке. Режим указания точки мышью в KengaCAD реализован через курсор и привязки.

### Редактирование — соответствие

| AutoCAD | KengaCAD | Совпадение |
|---------|----------|------------|
| MOVE (M) | MOVE dx dy | да |
| COPY (CO) | COPY dx dy | да |
| ERASE (E) | ERASE / E | да |
| ROTATE (RO) | ROTATE angle [cx cy] | да |
| SCALE (SC) | SCALE factor [cx cy] | да |
| MIRROR (MI) | MIRROR x1 y1 x2 y2 | да |
| OFFSET (O) | OFFSET distance | да |
| TRIM (TR) | TRIM x y | да |
| EXTEND (EX) | EXTEND x y | да |
| FILLET (F) | FILLET radius | да |
| CHAMFER (CHA) | CHAMFER d1 [d2] | да |
| BREAK (BR) | BREAK x1 y1 x2 y2 | да |
| JOIN (J) | JOIN | да |
| EXPLODE (X) | EXPLODE | да |
| ARRAY | ARRAY R/P | прямоугольный и полярный |
| STRETCH | STRETCH dx dy | да |

### Блоки и размеры

| AutoCAD | KengaCAD | Совпадение |
|---------|----------|------------|
| BLOCK | BLOCK name [base_x base_y] | да |
| INSERT | INSERT name x y [scale] [angle] | да |
| HATCH | HATCH [color] | да |
| DIMLINEAR | DIMLINEAR x1 y1 x2 y2 [xm ym] | да |

### Вид

| AutoCAD | KengaCAD | Совпадение |
|---------|----------|------------|
| ZOOM Extents | ZOOM_EXTENTS / ZE | Ctrl+0 |
| PAN | средняя кнопка мыши | да |
| ZOOM | колёсико мыши | да |
| GRID | GRID [шаг] | да |
| ORTHO (F8) | орто (F8) | да |
| POLAR (F10) | полярный (F10) | да |
| SNAP | привязки (E,M,I,C,N) | да |

### Специфика KengaCAD (нет в AutoCAD)

- LOAD_DEMO_ROBOT, LOAD_ROBOT — загрузка модели робота
- TRAC_FROM_POLYLINE — траектория из полилинии
- TRAJECTORY, EXPORT_TRAC — работа с траекториями
- SET_JOINT, SIMULATE — управление роботом
- START_DISPENSING, STOP_DISPENSING — диспенсинг

---

## 2. Расхождения и рекомендации

### 2.1 Интерактивный ввод

AutoCAD: команды чаще всего интерактивные ("Specify first point:", "Specify next point:").

KengaCAD: координаты задаются в командной строке. Добавлен режим интерактивного ввода для LINE, CIRCLE, ARC.

### 2.2 Сокращения команд

AutoCAD: L (LINE), C (CIRCLE), M (MOVE), CO (COPY), E (ERASE), RO (ROTATE) и т.д.

KengaCAD: L, C, A, M, CO, E, PL, REC, DRA, DDI, PE, LA и др. Добавлены синонимы.

### 2.3 Ранее отсутствующие — добавлены

- GRID — сетка (вкл/выкл, шаг)
- DIMRADIUS, DIMDIAMETER — размеры радиуса/диаметра
- MULTIPLE — повтор команды
- PEDIT — редактирование полилинии (W width, J join)
- LAYER — управление слоями (NEW, SET, FREEZE, THAW, LOCK, UNLOCK, DELETE)
- XREF ATTACH — внешние ссылки (прикрепить файл как блок)
- 3D-команды (EXTRUDE, REVOLVE) — KengaCAD ориентирован на 2D + робот

### 2.4 Выбор объектов

Совпадение: клик, Ctrl+клик, рамка слева направо / справа налево, crossing vs window.

---

## 3. Итоговая оценка

| Категория | Совпадение | Примечание |
|-----------|------------|------------|
| Файл (NEW, OPEN, SAVE) | 100% | полное |
| Рисование (LINE, CIRCLE и т.д.) | ~90% | синтаксис через координаты |
| Редактирование | ~95% | основные команды есть |
| Блоки, размеры, штриховка | ~80% | базовая поддержка |
| Вид (ZOOM, PAN) | ~85% | без GRID |
| Слои | ~90% | LAYER NEW/SET/FREEZE/LOCK |
| Горячие клавиши | ~70% | Ctrl+N/S, F8, F10, Delete |

Общий вывод: KengaCAD покрывает основную часть базовых команд AutoCAD. Для профиля CAD для траекторий роботов уровень соответствия достаточный.

---

## 4. Приоритеты доработки

1. Высокий: NEW, OPEN, SAVE из командной строки — сделано.
2. Высокий: загрузка робота и черчение из коробки после установки.
3. Средний: синонимы команд (L, C, M, CO, E, RO, SC и т.д.) — сделано.
4. Средний: интерактивный режим LINE/CIRCLE/ARC/POINT/RECTANGLE (точки мышью) — сделано.
5. Низкий: GRID, DIMRADIUS/DIMDIAMETER, PEDIT, LAYER, XREF — сделано.
6. Низкий: оси и начало координат на холсте, кнопка «К началу координат» — сделано.
7. Низкий: недавние файлы в меню Файл — сделано.
8. Низкий: глобальный excepthook — диалог ошибки закрывается, приложение не зависает — сделано.
