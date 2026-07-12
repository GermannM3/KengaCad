# -*- coding: utf-8 -*-
"""Fix U+FFFD-corrupted Russian strings in MainWindow.xaml.cs (UTF-8 with BOM)."""
from pathlib import Path
import re

path = Path(r"d:\KengaCAD\KengaCAD\MainWindow.xaml.cs")
lines = path.read_text(encoding="utf-8").splitlines(keepends=True)

# --- full-line replacements (1-based line numbers from bad_lines audit) ---
LINE_FIX: dict[int, str] = {}

def set_line(n: int, content: str):
    LINE_FIX[n] = content.rstrip("\n") + "\n"

# Comments (top of file)
set_line(26, "        // Текущая команда")
set_line(32, "        // Список объектов")
set_line(35, "        // Настройки")
set_line(42, "        // Стек для Undo/Redo")
set_line(46, "        // Полилиния: накопление точек")
set_line(49, "        // Дуга: 3-точечная (начало, промежуточная, конец)")
set_line(52, "        // Симуляция траектории в 3D")
set_line(58, "        // Зум и панорама 2D")
set_line(64, "        // MOVE/COPY: базовая точка")
set_line(74, "        // 3D-навигация (орбита камеры)")
set_line(114, "        /// <summary>2D: Y вниз (Skia). 3D: Z вверх, для робота инвертируем Y оси CAD.</summary>")

# User-visible
set_line(161, '                AppendOutput("Готов к программированию робота.");')
set_line(548, '            AppendOutput("Jog: все оси установлены в 0.");')
set_line(594, '                StatusText.Text = "TCP-Jog: нет сходимости";')
set_line(660, '            AppendOutput($"Добавлена программная точка P{_programWaypoints.Count:000}.");')
set_line(670, '            AppendOutput("Программные точки очищены.");')
set_line(677, '                StatusText.Text = "Нет программных точек для выполнения.";')
set_line(688, '                StatusText.Text = "Нет программных точек.";')
set_line(699, '            StatusText.Text = $"Шаг программы: P{wp.Index:000}";')
set_line(711, '            AppendOutput($"Точка P{_selectedWaypointIndex + 1:000} перемещена вверх.");')
set_line(722, '            AppendOutput($"Точка P{_selectedWaypointIndex + 1:000} перемещена вниз.");')
set_line(734, '            AppendOutput($"Удалена точка P{removed:000}.");')
set_line(755, '            AppendOutput($"Программа сохранена: {dlg.FileName}");')
set_line(769, '                if (dto == null) throw new InvalidOperationException("Пустой файл программы.");')
set_line(792, '                AppendOutput($"Программа загружена: {dlg.FileName} ({_programWaypoints.Count} точек).");')
set_line(796, '                AppendOutput($"Ошибка загрузки программы: {ex.Message}");')
set_line(803, '            AppendOutput("Выполнение программы остановлено.");')
set_line(817, '                    AppendOutput($"Изменена точка P{_selectedWaypointIndex + 1:000}.");')
set_line(832, '                    AppendOutput($"Изменена операция O{_selectedOperationIndex + 1:000}.");')
set_line(863, '            AppendOutput($"Добавлена операция {type}.");')
set_line(893, '            AppendOutput("Команда отменена.");')
set_line(917, '                OrthoStatus.Text = "ВКЛ";')
set_line(922, '                OrthoStatus.Text = "ВЫКЛ";')
set_line(927, '                SnapStatus.Text = "ВКЛ";')
set_line(932, '                SnapStatus.Text = "ВЫКЛ";')
set_line(1124, '            if (selected.Count == 0) { StatusText.Text = "Выделите объекты для блока (хотя бы один)."; return; }')
set_line(1136, '            StatusText.Text = $"Блок «{block.Name}» создан ({selected.Count} объектов).";')
set_line(1142, '            if (_blocks.Count == 0) { StatusText.Text = "Нет сохранённых блоков. Сначала создайте блок."; return; }')
set_line(1145, '            StatusText.Text = $"INSERTBLOCK: укажите точку вставки блока «{_pendingBlockInsert.Name}»";')
set_line(1153, '                StatusText.Text = "Постройте полилинию или дугу для траектории.";')
set_line(1163, '                StatusText.Text = "Не найдена замкнутая полилиния.";')
set_line(1169, '            StatusText.Text = $"Траектория ({mode}): {poly.Points.Count} точек. Нажмите Старт для симуляции.";')
set_line(1176, '            string name = "Слой " + n;')
set_line(1181, '            StatusText.Text = "Новый слой: " + name;')
set_line(1189, '            StatusText.Text = "Сетка включена";')
set_line(1197, '                StatusText.Text = "Постройте полилинию или дугу, затем запустите симуляцию.";')
set_line(1199, '                StatusText.Text = $"Траектория из чертежа: {pts.Count} точек. Нажмите Старт для симуляции.";')
set_line(1376, '            StatusText.Text = "Удалено";')
set_line(1388, "            // Слои")
set_line(1396, "            // Цвета")
set_line(1413, "            // Тип линии")
set_line(1424, '            RobotPresetComboBox.Items.Add("— выберите модель —");')
set_line(1451, '                Title = "Загрузить 3D-модель робота"')
set_line(1475, '                    StatusText.Text = $"Модель загружена из файла: {fname}";')
set_line(1480, '                    StatusText.Text = $"Формат {ext} не поддерживается";')
set_line(1484, '                StatusText.Text = $"Ошибка загрузки: {ex.Message}";')
set_line(1498, '                LoadRobotPreset("Демо (6 осей)");')
set_line(1538, '                ? $"Робот: {_currentRobotDef.DisplayName} (reach {_currentRobotDef.MaxReachMm:F0} mm, {_currentRobotDef.PayloadKg:F0} kg)"')
set_line(1539, '                : $"Робот загружен: {name}";')
set_line(1749, "            // Рисование линий")
set_line(1759, "            // Рисование линий")
set_line(1788, "            // Горизонтальные линии")
set_line(1790, "            // Вертикальные линии")
set_line(2238, "            // Выделение объектов мышью")
set_line(2271, '                StatusText.Text = "Готово";')
set_line(2291, '            StatusText.Text = "Отменено действие";')
set_line(2400, '                StatusText.Text = "Повторено";')
set_line(2413, '                StatusText.Text = "Отменено";')
set_line(2438, '            StatusText.Text = "ZOOM: показать всё";')
set_line(2479, '                StatusText.Text = "Нет траектории. Добавьте точки, полилинию или программу.";')
set_line(2487, '                StatusText.Text = "Не удалось построить траекторию симуляции.";')
set_line(2501, '            StatusText.Text = "Симуляция: воспроизведение в 3D";')
set_line(2659, '            StatusText.Text = "Симуляция на паузе";')
set_line(2669, '            StatusText.Text = "Симуляция остановлена";')
set_line(2679, '            StatusText.Text = "3D симуляция сброшена";')
set_line(2695, '                    AppendOutput("Выполнение программы завершено.");')
set_line(2813, '            StatusText.Text = "Новый чертёж создан";')
set_line(2860, '                StatusText.Text = $"Открыто: {dlg.FileName} ({loaded.Count} объектов)";')
set_line(2865, '                StatusText.Text = $"Ошибка открытия: {ex.Message}";')
set_line(2889, '                StatusText.Text = $"Сохранено: {_currentDrawingPath}";')
set_line(2894, '                StatusText.Text = $"Ошибка сохранения: {ex.Message}";')
set_line(2902, "        // Навигация камеры 3D сцены")
set_line(2953, '            StatusText.Text = only3D ? "Режим только 3D включён" : "Режим только 3D выключен";')
set_line(2963, '            StatusText.Text = "База робота сброшена в 0,0,0";')
set_line(3091, '            AppendOutput("Точка добавлена на 3D сцене (double-click).");')
set_line(3102, '                StatusText.Text = $"База робота: X={cadX:F1} Y={cadY:F1}";')
set_line(3142, '            AppendOutput($"Workcell: добавлен {obj.Name}");')
set_line(3151, '            AppendOutput("Workcell очищен.");')
set_line(3200, '                StatusText.Text = "Коллизии: не обнаружены";')
set_line(3204, '            StatusText.Text = $"Коллизии: {hits.Count} точек";')
set_line(3207, '                AppendOutput($"  шаг {h.Step}: {h.ObjectA} ↔ {h.ObjectB} ({h.Point.X:F0},{h.Point.Y:F0},{h.Point.Z:F0})");')
set_line(3219, '                StatusText.Text = "Самоколлизия: не обнаружена";')
set_line(3223, '            StatusText.Text = $"Самоколлизия: {hits.Count} пар звеньев";')

# SetCurrentCommand switch block
set_line(1214, '                "LINE" => "LINE: укажите первую точку",')
set_line(1215, '                "CIRCLE" => "CIRCLE: укажите центр окружности",')
set_line(1216, '                "ARC" => "ARC: укажите начальную точку дуги",')
set_line(1217, '                "POLYLINE" => "POLYLINE: укажите первую точку",')
set_line(1218, '                "RECTANGLE" => "RECTANGLE: укажите первый угол",')
set_line(1219, '                "MOVE" => "MOVE: выберите объекты",')
set_line(1220, '                "COPY" => "COPY: выберите объекты",')
set_line(1221, '                "ROTATE" => "ROTATE: выберите объекты",')
set_line(1222, '                "SCALE" => "SCALE: выберите объекты",')
set_line(1223, '                "MIRROR" => "MIRROR: выберите объекты",')
set_line(1224, '                "TRIM" => "TRIM: выберите границу",')
set_line(1225, '                "EXTEND" => "EXTEND: выберите границу",')
set_line(1226, '                "FILLET" => "FILLET: выберите первую линию",')
set_line(1227, '                "LAYERNEW" => "Создание нового слоя",')
set_line(1228, '                "ZOOMIN" => "Увеличение масштаба",')
set_line(1229, '                "ZOOMOUT" => "Уменьшение масштаба",')
set_line(1230, '                "PAN" => "Панорама: перетаскивайте вид",')
set_line(1231, '                "VIEWTOP" => "Вид сверху",')
set_line(1232, '                "VIEWFRONT" => "Вид спереди",')
set_line(1233, '                "VIEWLEFT" => "Вид слева",')
set_line(1234, '                "VIEW3D" => "3D вид",')
set_line(1235, '                "LOADROBOT" => "Загрузить модель робота",')
set_line(1236, '                "LOADDEMOROBOT" => "Демо-робот",')
set_line(1237, '                "ZEROJOINTS" => "Сбросить в ноль",')
set_line(1238, '                "TRAJFROMPOLYLINE" => "Траектория из полилинии",')
set_line(1239, '                "TRAJSPLINE" => "Сплайн траектории",')
set_line(1240, '                "TRAJSMOOTH" => "Сглаженная траектория",')
set_line(1241, '                "TRAJSPIRAL" => "Спиральная траектория",')
set_line(1242, '                "SIMULATE" => "Старт симуляции",')
set_line(1243, '                "SIMPAUSE" => "Пауза",')
set_line(1244, '                "SIMSTOP" => "Стоп",')
set_line(1245, '                "SIMRESET" => "Сброс",')
set_line(1246, '                "IMPORTSTEP" => "Импорт STEP",')
set_line(1247, '                "IMPORTIGES" => "Импорт IGES",')
set_line(1248, '                "IMPORTSTL" => "Импорт STL",')
set_line(1249, '                "IMPORTGLTF" => "Импорт glTF",')
set_line(1250, '                "CREATEBLOCK" => "Создать блок из выделения",')
set_line(1251, '                "INSERTBLOCK" => "Вставить блок",')
set_line(1252, '                "TEXT" => "Разместить текст",')
set_line(1253, '                "DIMLINEAR" => "Линейный размер",')
set_line(1254, '                "DIMRADIUS" => "Радиальный размер",')
set_line(1255, '                _ => $"{cmd}: готово"')

# Export messages
for ln in (1312, 1322, 1332, 1342, 1352, 1362):
    set_line(ln, '            if (pts.Count == 0) { StatusText.Text = "Нет траектории. Добавьте точки или полилинию."; return; }')
set_line(1315, '            StatusText.Text = Postprocessors.ExportGCode(pts, dlg.FileName) ? "Экспорт G-code: " + dlg.FileName : "Ошибка экспорта.";')
set_line(1325, '            StatusText.Text = Postprocessors.ExportKukaKrl(pts, dlg.FileName) ? "Экспорт KUKA KRL: " + dlg.FileName : "Ошибка экспорта.";')
set_line(1335, '            StatusText.Text = Postprocessors.ExportAbbRapid(pts, dlg.FileName) ? "Экспорт ABB RAPID: " + dlg.FileName : "Ошибка экспорта.";')
set_line(1345, '            StatusText.Text = Postprocessors.ExportFanucTp(pts, dlg.FileName) ? "Экспорт Fanuc TP: " + dlg.FileName : "Ошибка экспорта.";')
set_line(1355, '            StatusText.Text = Postprocessors.ExportYaskawaInform(pts, dlg.FileName) ? "Экспорт Yaskawa INFORM: " + dlg.FileName : "Ошибка экспорта.";')
set_line(1365, '            StatusText.Text = Postprocessors.ExportUrScript(pts, dlg.FileName) ? "Экспорт UR Script: " + dlg.FileName : "Ошибка экспорта.";')

# Drawing interaction (mouse handlers) — batch by line
drawing_fixes = {
    1874: '                    StatusText.Text = cmd == "MOVE" ? "MOVE: укажите базовую точку" : "COPY: укажите базовую точку";',
    1879: '                if (selected.Count == 0) { StatusText.Text = "Выделите объекты (клик по объекту или рамкой)."; _editBaseSet = false; return; }',
    1888: '                    StatusText.Text = "Перемещение завершено";',
    1895: '                    StatusText.Text = "Копирование завершено";',
    1920: '                StatusText.Text = $"Полилиния: точек {_polylinePoints.Count}. Enter для замыкания или продолжайте.";',
    1929: '                    StatusText.Text = "ARC: укажите промежуточную точку дуги";',
    1931: '                    StatusText.Text = "ARC: укажите конечную точку дуги";',
    1939: '                        StatusText.Text = "Дуга создана";',
    1942: '                        StatusText.Text = "Не удалось построить дугу (точки на одной прямой)";',
    2009: '                StatusText.Text = "Прямоугольник";',
    2035: '                        StatusText.Text = "ROTATE: укажите центр поворота";',
    2044: '                    StatusText.Text = $"Поворот выполнен ({angle * 180 / Math.PI:F1}°)";',
    2056: '                        StatusText.Text = "SCALE: укажите базу масштаба";',
    2066: '                    StatusText.Text = $"Масштаб: x{factor:F2}";',
    2078: '                        StatusText.Text = "MIRROR: укажите первую точку оси";',
    2086: '                    StatusText.Text = "Зеркало выполнено";',
    2094: '                        StatusText.Text = _editRefEntity != null ? "TRIM: выберите объект для обрезки" : "TRIM: граница не найдена";',
    2104: '                            StatusText.Text = "Обрезка выполнена";',
    2106: '                        else StatusText.Text = "Обрезка не выполнена";',
    2116: '                        StatusText.Text = _editRefEntity != null ? "EXTEND: выберите линию для удлинения" : "EXTEND: граница не найдена";',
    2126: '                            StatusText.Text = "Удлинение выполнено";',
    2128: '                        else StatusText.Text = "Удлинение не выполнено";',
    2138: '                        StatusText.Text = _editRefEntity != null ? "FILLET: выберите вторую линию" : "FILLET: первая линия";',
    2144: '                        if (_editRefEntity2 == null) { StatusText.Text = "FILLET: выберите вторую линию"; return true; }',
    2145: '                        StatusText.Text = "FILLET: укажите радиус (число в командной строке)";',
    2158: '                            StatusText.Text = $"Скругление R={radius:F1}";',
    2160: '                        else StatusText.Text = "Скругление не выполнено";',
    2169: '                    var text = InputDialog.Prompt("Текст", "Введите текст:", "KengaCAD");',
    2174: '                        StatusText.Text = "Текст добавлен";',
    2182: '                    if (_dimPoints.Count == 1) StatusText.Text = "DIMLINEAR: вторая точка";',
    2183: '                    else if (_dimPoints.Count == 2) StatusText.Text = "DIMLINEAR: укажите положение размерной линии";',
    2190: '                        StatusText.Text = "Линейный размер добавлен";',
    2198: '                        if (_editRefEntity is CircleEntity) StatusText.Text = "DIMRADIUS: укажите положение";',
    2199: '                        else { _editRefEntity = null; StatusText.Text = "DIMRADIUS: выберите окружность"; }',
    2206: '                        StatusText.Text = "Радиальный размер добавлен";',
    2218: '                        StatusText.Text = $"Блок «{_pendingBlockInsert.Name}» вставлен";',
    2245: '                    StatusText.Text = entity.IsSelected ? "Объект выделен" : "Объект снят с выделения";',
    2321: '                    StatusText.Text = "LINE: укажите вторую точку";',
    2326: '                    StatusText.Text = "CIRCLE: укажите точку на окружности";',
    2331: '                    StatusText.Text = "POLYLINE: укажите следующую точку";',
    2336: '                    StatusText.Text = "RECTANGLE: укажите противоположный угол";',
    2342: '                    StatusText.Text = "MOVE: укажите точку назначения";',
    2348: '                    StatusText.Text = "COPY: укажите точку назначения";',
    2367: '                    OrthoStatus.Text = _orthoMode ? "ВКЛ" : "ВЫКЛ";',
    2371: '                    StatusText.Text = $"ORTHO: {(_orthoMode ? "ВКЛ" : "ВЫКЛ")}";',
    2375: '                    SnapStatus.Text = _snapEnabled ? "ВКЛ" : "ВЫКЛ";',
    2379: '                    StatusText.Text = $"SNAP: {(_snapEnabled ? "ВКЛ" : "ВЫКЛ")}";',
    2386: '                    StatusText.Text = $"Неизвестная команда: {cmd}";',
}
for k, v in drawing_fixes.items():
    set_line(k, v)

# Help dialog block — replace lines 2773-2800
HELP_START = 2773
HELP_END = 2800
HELP_REPLACEMENT = '''            var helpText = @"KengaCAD v2.1.0 - Справка

Основные команды:
  LINE (L)     - линия
  CIRCLE (C)   - окружность
  ARC (A)      - дуга
  RECTANGLE    - прямоугольник
  POLYLINE     - полилиния

Редактирование:
  MOVE (M)     - перемещение
  COPY (CO)    - копирование
  ROTATE (RO)  - поворот
  SCALE (SC)   - масштаб
  TRIM (TR)    - обрезка
  UNDO (U)     - отменить
  REDO (R)     - повторить

Навигация:
  ZOOM (Z)     - масштаб
  ZOOM (E)     - показать всё
  ORTHO (F8)   - ортогональный режим
  SNAP         - привязки

Нажмите ESC для отмены команды";

            MessageBox.Show(helpText, "KengaCAD - Справка",
                MessageBoxButton.OK, MessageBoxImage.Information);'''

set_line(2803, "        // Обработчики Ribbon")

# Apply line fixes
out = []
i = 0
while i < len(lines):
    line_no = i + 1
    if line_no == HELP_START:
        out.append(HELP_REPLACEMENT + "\n")
        i = HELP_END  # skip through old help block (1-based HELP_END inclusive)
        continue
    if line_no in LINE_FIX:
        fixed = LINE_FIX[line_no]
        out.append(fixed if fixed.endswith("\n") else fixed + "\n")
    elif "\ufffd" in lines[i]:
        out.append(lines[i])
        print(f"WARN unfixable line {line_no}")
    else:
        out.append(lines[i])
    i += 1

# Fix InputDialog line 1125 if corrupted
text = "".join(out)
text = text.replace('InputDialog.Prompt("Создать блок", "�мя блока:"', 'InputDialog.Prompt("Создать блок", "Имя блока:"')
text = text.replace('InputDialog.Prompt("Создать блок", "\ufffdмя блока:"', 'InputDialog.Prompt("Создать блок", "Имя блока:"')

path.write_text(text, encoding="utf-8-sig")
remaining = sum(1 for l in text.splitlines() if "\ufffd" in l)
print(f"Fixed {len(LINE_FIX)} lines. Remaining U+FFFD lines: {remaining}")
