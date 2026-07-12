# KengaCAD — Расширенные возможности

## Обзор

KengaCAD — это полноценный CAD/CAM аналог AutoCAD и RoboCAD, предназначенный для:
- 2D/3D проектирования
- Настройки траекторий роботов нанесения мастики
- Виртуальной наладки (Virtual Commissioning)
- Генерации управляющих программ для промышленных роботов

---

## 🎨 2D-черчение (AutoCAD-совместимое)

### Команды рисования

| Команда | Синоним | Описание |
|---------|---------|----------|
| `LINE x1 y1 x2 y2` | `L` | Линия по точкам |
| `CIRCLE x y r` | `C` | Окружность (центр, радиус) |
| `ARC x y r start end` | `A` | Дуга |
| `POLYLINE x1 y1 x2 y2 ...` | `PL` | Полилиния |
| `RECTANGLE x1 y1 x2 y2` | `REC` | Прямоугольник |
| `ELLIPSE cx cy major major_minor [ratio]` | `EL` | Эллипс |
| `SPLINE x1 y1 x2 y2 ...` | `SPL` | Сплайн |
| `TEXT x y height text` | `T` | Текст |
| `HATCH` | `H` | Штриховка |
| `DIMLINEAR` | `DLI` | Линейный размер |
| `DIMRADIUS` | `DRA` | Размер радиуса |

### Команды редактирования

| Команда | Синоним | Описание |
|---------|---------|----------|
| `MOVE dx dy` | `M` | Перемещение |
| `COPY dx dy` | `CO` | Копирование |
| `ROTATE angle [cx cy]` | `RO` | Поворот |
| `SCALE factor [cx cy]` | `SC` | Масштабирование |
| `MIRROR x1 y1 x2 y2` | `MI` | Отражение |
| `OFFSET distance` | `O` | Смещение |
| `TRIM` | `TR` | Обрезка |
| `EXTEND` | `EX` | Удлинение |
| `FILLET radius` | `F` | Скругление |
| `CHAMFER d1 d2` | `CHA` | Фаска |
| `ARRAY R rows cols` | `AR` | Массив (rectangular/polar) |
| `MIRROR x1 y1 x2 y2` | `MI` | Зеркальное отражение |
| `STRETCH` | `S` | Растягивание |
| `EXPLODE` | `X` | Разобрать блок |

### Слои (Layers)

```
LAYER NEW name          # Создать слой
LAYER SET name          # Установить текущий слой
LAYER FREEZE name       # Заморозить слой
LAYER THAW name         # Разморозить слой
LAYER LOCK name         # Блокировать слой
LAYER UNLOCK name       # Разблокировать слой
LAYER DELETE name       # Удалить слой
LAYER COLOR name #RRGGBB # Изменить цвет слоя
```

### Горячие клавиши

| Клавиша | Действие |
|---------|----------|
| `F8` | Ортогональный режим (Ortho) |
| `F10` | Полярный режим (Polar) |
| `Ctrl+N` | Новый чертёж |
| `Ctrl+O` | Открыть |
| `Ctrl+S` | Сохранить |
| `Ctrl+Z` | Отменить (Undo) |
| `Ctrl+Y` | Повторить (Redo) |
| `Ctrl+0` | ZOOM_EXTENTS |
| `Delete` | Удалить выделенное |
| `Esc` | Отменить команду |

---

## 🤖 Робототехника (RoboCAD-совместимое)

### Поддерживаемые роботы

KengaCAD поддерживает следующие типы роботов:

#### 6-осевые сочленённые роботы
- **KUKA**: KR6 R900, KR16, KR210, KR500
- **ABB**: IRB 120, IRB 140, IRB 2600, IRB 6700
- **Fanuc**: LR Mate 200iD, M-10iA, M-20iA
- **Yaskawa/Motoman**: GP7, GP25, HP20
- **Universal Robots**: UR3, UR5, UR10, UR16

#### Другие типы
- **SCARA** (4 оси)
- **Декартовы** (3 оси)
- **Дельта** (параллельная кинематика)
- **Пользовательские** (DH-параметры)

### Команды управления роботом

```
# Загрузка робота
LOAD_DEMO_ROBOT                     # Демо-робот по умолчанию
LOAD_ROBOT path/to/robot.glb        # Своя модель
LOAD_ROBOT --config kuka_kr6r900    # Конфигурация из библиотеки

# Управление суставами
SET_JOINT joint_name angle          # Установить угол сустава
GET_JOINT joint_name                # Получить угол
ZERO_JOINTS                         # Все суставы в 0

# Проверка достижимости
REACHABILITY x y z                  # Проверка позиции
CHECK_SINGULARITY                   # Проверка сингулярностей
WORKSPACE_VISUALIZE                 # Визуализация рабочей зоны

# Траектории
TRAC_FROM_POLYLINE                  # Из полилинии в траекторию
EDIT_TRAC                           # Редактировать точки
TRAC_LENGTH                         # Длина траектории
TRAC_TIME                           # Время выполнения

# Симуляция
SIMULATE [steps]                    # Запуск симуляции
SIM_PAUSE                           # Пауза
SIM_STOP                            # Остановка
SIM_RESET                           # Сброс в начальное положение

# Диспенсинг (нанесение мастики)
START_DISPENSING [flow] [radius]    # Начать нанесение
STOP_DISPENSING                     # Остановить
CALIBRATE_DISPENSER                 # Калибровка
```

### Библиотека конфигураций роботов

```python
from cad.robot_kinematics import get_robot_config, list_available_robots

# Список доступных роботов
robots = list_available_robots()
# ['kuka_kr6r900', 'abb_irb120', 'fanuc_lrmate200id', 'ur_ur5', ...]

# Получить конфигурацию
config = get_robot_config("kuka_kr6r900")
print(config['name'])        # "KUKA KR6 R900 sixx"
print(config['reach_mm'])    # 903
print(config['payload_kg'])  # 6
print(config['dh_params'])   # DH-параметры
```

---

## 🛤️ Расширенное управление траекториями

### Типы интерполяции

```python
from cad.advanced_trajectory import AdvancedTrajectoryManager, TrajectoryPoint

manager = AdvancedTrajectoryManager()

# Создать траекторию с кубической интерполяцией
points = [
    TrajectoryPoint(0, 0, 0),
    TrajectoryPoint(100, 0, 50),
    TrajectoryPoint(200, 100, 50),
    TrajectoryPoint(300, 0, 0),
]

manager.create_trajectory("traj1", points, spline_type="cubic")
# spline_type: "linear", "cubic", "bspline", "chaikin"
```

### Сглаживание траекторий

```python
# Сгладить алгоритмом Chaikin
manager.smooth_trajectory("traj1", method="chaikin", iterations=3)

# Или использовать B-сплайн
manager.smooth_trajectory("traj1", method="bspline")
```

### Оптимизация скорости

```python
# Оптимизировать профиль скорости
manager.optimize_velocity(
    "traj1",
    max_velocity=200.0,         # мм/сек
    max_acceleration=100.0,     # мм/сек²
    corner_angle_threshold=30,  # градусов
    corner_velocity_factor=0.5, # снижение на углах
)
```

### Генерация специальных траекторий

```python
from cad.advanced_trajectory import generate_spiral, generate_zigzag

# Спираль (для круговых деталей)
spiral = generate_spiral(
    center=(0, 0, 0),
    radius=100,
    height=50,
    num_turns=2.0,
    num_points=100,
)

# Зигзаг (для покрытия площади)
zigzag = generate_zigzag(
    start=(0, 0, 0),
    size_x=200,
    size_y=150,
    step_over=10,
    num_points_per_line=20,
)
```

### Экспорт в G-код

```python
gcode = manager.export_to_gcode("traj1", num_points=100, feed_rate=150.0)
print(gcode)
```

---

## 📦 Импорт/Экспорт

### Поддерживаемые форматы

| Формат | Импорт | Экспорт | Примечание |
|--------|--------|---------|------------|
| **DXF** | ✅ | ✅ | Все версии R12-R2018 |
| **DWG** | ✅ | ✅ | Требуется ODA File Converter |
| **STEP** | ✅ | ✅ | .stp, .step (AP203, AP214, AP242) |
| **IGES** | ✅ | ❌ | .igs, .iges |
| **STL** | ✅ | ✅ | ASCII и бинарный |
| **JSON** | ✅ | ✅ | Траектории KengaCAD |
| **CSV** | ✅ | ✅ | RoboCAD-совместимый |
| **PDF** | ❌ | ✅ | 2D чертежи |
| **glTF/GLB** | ✅ | ❌ | 3D модели |
| **OBJ** | ✅ | ❌ | 3D модели |

### Примеры импорта

```python
from cad.import_export import CADImportExport
from cad.step_import import load_step, load_stl

importer = CADImportExport()

# Импорт DXF/DWG
entities = importer.import_dxf("drawing.dxf")

# Импорт STEP
step_mesh = load_step("part.step")

# Импорт STL
stl_mesh = load_stl("model.stl")

# Импорт траектории CSV
points = importer.import_csv_trajectory("trajectory.csv")
```

### Примеры экспорта

```python
# Экспорт DXF
importer.export_dxf(entities, "output.dxf")

# Экспорт STL
from cad.step_import import export_stl
export_stl(mesh, "output.stl", binary=True)

# Экспорт траектории
importer.export_json_trajectory(points, "trajectory.json")
importer.export_csv_trajectory(points, "trajectory.csv")
```

---

## 🏭 Post-процессоры для роботов

### Поддерживаемые контроллеры

| Производитель | Контроллер | Формат | Расширение |
|--------------|------------|--------|------------|
| **KUKA** | KRC4, KRC5 | KRL | .krl |
| **ABB** | IRC5, OmniCore | RAPID | .mod |
| **Fanuc** | R-30iB, R-30iB Plus | TP | .tp, .ls |
| **Yaskawa/Motoman** | DX200, YRC1000 | INFORM | .jbi |
| **Universal Robots** | CB3, e-Series | URScript | .script |
| **Kawasaki** | E-Series | AS | .as |
| **Nachi** | E2 Series | SL | .sl |

### Пример экспорта

```python
from cad.import_export import CADImportExport

exporter = CADImportExport()

# KUKA KRL
exporter.export_kuka_krl(
    points, 
    "program.krl",
    speed_mms=100.0,
    program_name="KengaCAD_Trajectory",
)

# ABB RAPID
exporter.export_abb_rapid(
    points,
    "module.mod",
    speed_mms=100.0,
    module_name="KengaCAD_Trajectory",
    tool_name="tool0",
)

# Fanuc TP
exporter.export_fanuc_tp(
    points,
    "program.tp",
    utool_num=1,
    uframe_num=0,
)

# Yaskawa INFORM
exporter.export_yaskawa_inform(
    points,
    "job.jbi",
    speed_mms=100.0,
)

# UR Script
exporter.export_ur_script(
    points,
    "program.script",
    speed_ms=0.1,
    accel=1.2,
)
```

---

## 🔧 Virtual Commissioning

### PLC-сигналы

```python
from cad.plc_signals import SignalTable

# Создать таблицу сигналов
signals = SignalTable()

# Добавить сигналы
signals.add_signal("Robot_Start", "output", False)
signals.add_signal("Robot_Ready", "input", False)
signals.add_signal("Cycle_Done", "input", False)
signals.add_signal("Emergency_Stop", "input", False)

# Установить значения
signals.set_value("Robot_Start", True)
```

### Производственные циклы

```python
from cad.virtual_commissioning import CycleModel, CycleStep, CycleSimulator

# Создать цикл
cycle = CycleModel("Цикл сварки")

# Добавить шаги
cycle.add_step(CycleStep(
    name="Подъезд к детали",
    duration_s=2.5,
    step_type="move",
    traj_start=0,
    traj_end=5,
    signals_before=[{"signal": "Grip_Close", "value": True}],
))

cycle.add_step(CycleStep(
    name="Сварка",
    duration_s=5.0,
    step_type="weld",
    traj_start=5,
    traj_end=20,
))

cycle.add_step(CycleStep(
    name="Возврат",
    duration_s=2.0,
    step_type="move",
    traj_start=20,
    traj_end=0,
    signals_after=[{"signal": "Grip_Open", "value": True}],
))

# Симуляция
simulator = CycleSimulator(cycle, signals)
simulator.set_callbacks(
    on_step=lambda step: print(f"Шаг {step}"),
    on_signal=lambda sig, val: print(f"{sig} = {val}"),
)

simulator.start()
# Запуск в QTimer для анимации
```

### Gantt-диаграмма

```python
# Получить данные для Gantt
gantt = cycle.gantt_data()
print(gantt.summary())
# Цикл: Цикл сварки
# Общее время: 9.50 сек
#   [0.00–2.50] Подъезд к детали (move, 2.50с)
#   [2.50–7.50] Сварка (weld, 5.00с)
#   [7.50–9.50] Возврат (move, 2.00с)
```

---

## 🎯 3D-визуализация

### Полноценное 3D-окно (pyvista)

```python
from ui.view3d_full import View3DFull

# В главном окне
view3d = View3DFull(parent)

# Загрузка модели
view3d.load_model("robot.glb")

# Траектория
view3d.set_trajectory_points([(0,0,0), (100,0,50), (200,100,50)])

# Симуляция
view3d.start_simulation(steps=60, speed=1.0)

# Визуализация коллизий
view3d.visualize_collisions([
    {"point": (50, 50, 50), "normal": (0, 0, 1)},
])

# Очистка
view3d.clear_scene()
```

### Виды камеры

- **Изометрия** (по умолчанию)
- **Сверху** (XY平面)
- **Спереди** (XZ平面)
- **Слева/Справа** (YZ平面)
- **Снизу**
- **Сзади**

---

## 🔍 Проверка коллизий

```python
from cad.collision import check_collisions_local, check_collisions_mesh

# Проверка коллизий между объектами
collisions = check_collisions_local(
    objects=[mesh1, mesh2, mesh3],
    robot_entity="robot1",
)

for col in collisions:
    print(f"Коллизия: {col['entity_a']} ↔ {col['entity_b']}")
    print(f"  Точка: {col['point']}")
    print(f"  Нормаль: {col['normal']}")
```

---

## 📐 Кинематика

### Прямая кинематика (FK)

```python
from cad.robot_kinematics import fk_6dof_full, get_robot_config

config = get_robot_config("kuka_kr6r900")
joints = [30, -45, 60, 0, 45, 0]  # углы в градусах

result = fk_6dof_full(joints, config['dh_params'])
print(f"TCP позиция: {result['tcp_pos']}")
print(f"TCP ориентация: {result['tcp_rpy']}")
```

### Обратная кинематика (IK)

```python
from cad.robot_kinematics import ik_6dof_numerical, ik_6dof_analytical

# Целевая позиция и ориентация
target_pos = (300, 0, 200)
target_rpy = (0, 45, 0)

# Численное решение
result = ik_6dof_numerical(
    target_pos,
    target_rpy,
    config['dh_params'],
    config['joint_limits'],
    initial_joints=[0, 0, 0, 0, 0, 0],
)

if result and result['converged']:
    print(f"Углы суставов: {result['joints_deg']}")
    print(f"Погрешность: {result['error_mm']} мм")
```

### Проверка сингулярностей

```python
from cad.robot_kinematics import check_singularity

sing = check_singularity(joints, config['dh_params'])
if sing['singular']:
    print(f"Сингулярность: {sing['type']}")
    print(f"  {sing['message']}")
```

---

## 🐍 Скрипты Python

KengaCAD поддерживает автоматизацию через Python:

```python
# Пример скрипта
from kengacad_app import KengaCADApp
from cad.advanced_trajectory import TrajectoryPoint

app = KengaCADApp()

# Загрузить робота
await app.load_robot("assets/robot.glb", "robot1")

# Создать траекторию
points = [
    TrajectoryPoint(0, 0, 100),
    TrajectoryPoint(100, 0, 100),
    TrajectoryPoint(100, 100, 100),
    TrajectoryPoint(0, 100, 100),
]

await app.setup_robot_trajectory("traj1", points)

# Симуляция
await app.run_simulation(steps=60)
```

---

## 📊 Системные требования

### Минимальные
- **ОС**: Windows 10 / Linux Ubuntu 20.04
- **Процессор**: Intel Core i5 / AMD Ryzen 5
- **ОЗУ**: 8 GB
- **GPU**: OpenGL 3.3+
- **Место на диске**: 500 MB

### Рекомендуемые
- **ОС**: Windows 11 / Linux Ubuntu 22.04
- **Процессор**: Intel Core i7 / AMD Ryzen 7
- **ОЗУ**: 16 GB
- **GPU**: NVIDIA GeForce GTX 1660 / AMD RX 5600
- **Место на диске**: 1 GB (SSD)

---

## 🚀 Быстрый старт

### 1. Установка

```bash
# Клонировать репозиторий
git clone https://github.com/your-org/KengaCAD.git
cd KengaCAD

# Установить зависимости
pip install -r requirements.txt

# Запустить
python main.py
```

### 2. Первый проект

1. **Нарисуйте полилинию**: `POLYLINE 0 0 100 50 200 100`
2. **Создайте траекторию**: Нажмите "Траектория из пути" или `TRAC_FROM_POLYLINE`
3. **Загрузите робота**: Нажмите "Загрузить робота" или `LOAD_DEMO_ROBOT`
4. **Запустите симуляцию**: Нажмите "Симуляция" или `SIMULATE`

### 3. Экспорт программы для робота

1. Выберите траекторию
2. `EXPORT_TRAC program.krl` (для KUKA)
3. Загрузите программу в контроллер робота

---

## 📚 Дополнительные ресурсы

- [ARCHITECTURE.md](ARCHITECTURE.md) — Архитектура проекта
- [API_DOCS.md](API_DOCS.md) — WebSocket API
- [COMMAND_REFERENCE.md](COMMAND_REFERENCE.md) — Справочник команд
- [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) — Руководство разработчика
- [FORMATS.md](FORMATS.md) — Форматы файлов

---

## 🤝 Вклад в проект

KengaCAD — проект с открытым исходным кодом. Приветствуются:
- Отчёты об ошибках
- Предложения по улучшению
- Pull requests
- Документация

---

## 📄 Лицензия

KengaCAD распространяется под лицензией MIT.
