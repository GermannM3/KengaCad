# Примеры команд для KengaCAD, вдохновленные RoboCAD

## Обзор

В этом файле представлены примеры команд, которые могут быть полезны для KengaCAD, основанные на функциональности RoboCAD и других CAD-систем для робототехники.

## Основные команды

### 1. Создание геометрии

#### LINE - создание линии
```
LINE
Specify first point: 0,0,0
Specify next point or [Undo]: 100,100,0
Specify next point or [Close,Undo]: 200,0,0
```

#### CIRCLE - создание окружности
```
CIRCLE
Specify center point for circle or [3P/2P/Ttr (tan tan radius)]: 0,0,0
Specify radius of circle or [Diameter]: 50
```

#### ARC - создание дуги
```
ARC
Specify start point of arc: 0,0,0
Specify second point of arc: 50,50,0
Specify end point of arc: 100,0,0
```

### 2. Команды для робототехники

#### CREATE_ROBOT - создание модели робота
```
CREATE_ROBOT
Select robot type [6DOF/7DOF/SCARA/DELTA]: 6DOF
Enter robot name: MyRobot1
Specify base position: 0,0,0
```

#### SET_JOINT - установка угла сустава
```
SET_JOINT
Select robot: MyRobot1
Select joint [J1/J2/J3/J4/J5/J6]: J1
Enter angle (degrees): 45.0
```

#### GET_JOINT - получение угла сустава
```
GET_JOINT
Select robot: MyRobot1
Select joint [J1/J2/J3/J4/J5/J6]: J1
Joint J1 angle: 45.0 degrees
```

#### MOVE_TO - перемещение в позицию
```
MOVE_TO
Select robot: MyRobot1
Specify target position: 100,200,300
Select motion type [P2P/Linear/Circular]: Linear
```

### 3. Команды для траекторий

#### CREATE_TRAJECTORY - создание траектории
```
CREATE_TRAJECTORY
Enter trajectory name: DispensePath1
Select robot: MyRobot1
```

#### ADD_POINT - добавление точки к траектории
```
ADD_POINT
Select trajectory: DispensePath1
Specify point coordinates: 50,50,10
Enter speed (mm/s): 50
Enter acceleration (mm/s²): 100
```

#### INSERT_POINT - вставка точки в траекторию
```
INSERT_POINT
Select trajectory: DispensePath1
Select position [Before/After/Specific]: After
Select reference point: Point_2
Specify new point coordinates: 75,75,10
```

#### EDIT_POINT - редактирование точки траектории
```
EDIT_POINT
Select trajectory: DispensePath1
Select point: Point_3
Current coordinates: 100,100,10
New coordinates: 100,120,10
```

#### DELETE_POINT - удаление точки из траектории
```
DELETE_POINT
Select trajectory: DispensePath1
Select point: Point_5
Point Point_5 deleted from trajectory DispensePath1
```

### 4. Команды симуляции

#### SIMULATE - запуск симуляции
```
SIMULATE
Select trajectory: DispensePath1
Select robot: MyRobot1
Set simulation speed [Slow/Medium/Fast/Custom]: Custom
Enter speed factor: 0.5
```

#### PAUSE_SIM - пауза симуляции
```
PAUSE_SIM
Simulation paused at 45% completion
```

#### RESUME_SIM - продолжение симуляции
```
RESUME_SIM
Resuming simulation...
```

#### STOP_SIM - остановка симуляции
```
STOP_SIM
Simulation stopped. Robot at position: 150,200,50
```

#### STEP_FORWARD - шаг вперед в симуляции
```
STEP_FORWARD
Advancing simulation by 1 step
Current position: Joint angles [0, 45, 90, 0, 45, 0]
```

### 5. Команды диспенсинга

#### START_DISPENSE - начало диспенсинга
```
START_DISPENSE
Select robot: MyRobot1
Set material [Adhesive/Sealant/Solder]: Sealant
Set flow rate (ml/min): 10.0
Set nozzle diameter (mm): 2.0
```

#### STOP_DISPENSE - остановка диспенсинга
```
STOP_DISPENSE
Dispensing stopped. Applied 45.2 ml of sealant.
```

#### CALIBRATE_DISP - калибровка диспенсера
```
CALIBRATE_DISP
Select robot: MyRobot1
Running calibration routine...
Calibration complete. Flow rate adjusted to 9.8 ml/min
```

### 6. Команды управления камерой

#### VIEW_ISO - изометрический вид
```
VIEW_ISO
Switching to isometric view
```

#### VIEW_TOP - вид сверху
```
VIEW_TOP
Switching to top view
```

#### VIEW_FRONT - вид спереди
```
VIEW_FRONT
Switching to front view
```

#### VIEW_LEFT - вид слева
```
VIEW_LEFT
Switching to left view
```

#### ZOOM_EXTENTS - показать все
```
ZOOM_EXTENTS
Zooming to show all objects
```

#### ZOOM_WINDOW - масштабирование окном
```
ZOOM_WINDOW
First corner: 0,0,0
Second corner: 500,500,500
```

### 7. Команды анализа

#### CHECK_COLLISION - проверка коллизий
```
CHECK_COLLISION
Select robot: MyRobot1
Select trajectory: DispensePath1
Checking for collisions...
No collisions detected
```

#### ANALYZE_PATH - анализ траектории
```
ANALYZE_PATH
Select trajectory: DispensePath1
Path length: 1250 mm
Estimated time: 25 seconds
Max velocity: 50 mm/s
Max acceleration: 100 mm/s²
```

#### REACHABILITY - проверка достижимости
```
REACHABILITY
Select robot: MyRobot1
Specify position: 500,500,500
Position is reachable: Yes
Recommended joint angles: [0, 30, 60, 0, 30, 0]
```

### 8. Команды управления процессом

#### START_PROCESS - начало процесса
```
START_PROCESS
Select process [Dispensing/Welding/Painting]: Dispensing
Select trajectory: DispensePath1
Process started successfully
```

#### MONITOR_PROCESS - мониторинг процесса
```
MONITOR_PROCESS
Process: Dispensing
Status: Running
Progress: 65%
Material used: 28.7 ml
Remaining time: 8 seconds
```

#### STOP_PROCESS - остановка процесса
```
STOP_PROCESS
Process stopped by user
Material used: 32.1 ml
```

### 9. Команды настройки

#### CONFIG_ROBOT - настройка робота
```
CONFIG_ROBOT
Select robot: MyRobot1
Current configuration:
- Base position: 0,0,0
- Joint limits: J1[-180,180], J2[-90,90], J3[-90,90], J4[-180,180], J5[-90,90], J6[-180,180]
- Max speed: 120 deg/s
- Max acceleration: 240 deg/s²
```

#### SET_WORKSPACE - установка рабочей зоны
```
SET_WORKSPACE
Select robot: MyRobot1
Define workspace boundary:
Min point: -500,-500,-100
Max point: 500,500,1000
Workspace set successfully
```

### 10. Команды отладки

#### SHOW_JOINTS - показать суставы
```
SHOW_JOINTS
Robot: MyRobot1
J1: 0.0° (Range: -180° to 180°)
J2: 45.0° (Range: -90° to 90°)
J3: 90.0° (Range: -90° to 90°)
J4: 0.0° (Range: -180° to 180°)
J5: 45.0° (Range: -90° to 90°)
J6: 0.0° (Range: -180° to 180°)
```

#### SHOW_COORDS - показать координаты
```
SHOW_COORDS
Current tool position:
Cartesian: X=150.0, Y=200.0, Z=50.0
Orientation: Rx=0.0°, Ry=0.0°, Rz=45.0°
```

## Сокращения команд

Для удобства можно использовать сокращения:

- `L` для `LINE`
- `C` для `CIRCLE`
- `A` для `ARC`
- `CR` для `CREATE_ROBOT`
- `SJ` для `SET_JOINT`
- `GJ` для `GET_JOINT`
- `MT` для `MOVE_TO`
- `CT` для `CREATE_TRAJECTORY`
- `AP` для `ADD_POINT`
- `SS` для `SIMULATE`
- `SD` для `START_DISPENSE`
- `VI` для `VIEW_ISO`
- `ZE` для `ZOOM_EXTENTS`

## Примеры сложных команд

### Создание комплексной траектории
```
CREATE_TRAJECTORY
Enter trajectory name: ComplexPath
Select robot: MyRobot1

ADD_POINT
Specify point coordinates: 0,0,100
Enter speed: 30

ADD_POINT
Specify point coordinates: 100,0,100
Enter speed: 30

ADD_POINT
Specify point coordinates: 100,100,100
Enter speed: 50

ADD_POINT
Specify point coordinates: 0,100,100
Enter speed: 30

CLOSE_TRAJECTORY
```

### Запуск комплексного процесса
```
START_DISPENSE
Set flow rate: 15.0
Set material: Adhesive

SIMULATE
Select trajectory: ComplexPath
Set speed: 0.7

MONITOR_PROCESS
```

Эти команды могут быть интегрированы в командную строку KengaCAD для обеспечения мощного и гибкого интерфейса управления роботами и траекториями.