"""
Командная строка для KengaCAD (аналог AutoCAD командной строки)
"""
from PyQt5.QtWidgets import QLineEdit, QCompleter
from PyQt5.QtCore import Qt, QStringListModel
from PyQt5.QtGui import QPalette


class CommandLine(QLineEdit):
    def __init__(self):
        super().__init__()
        self.setObjectName("CommandLine")
        self.setPlaceholderText("LINE, CIRCLE, RECTANGLE — клик мышью или координаты | Ctrl+0 — всё | HELP") 
        
        # Установка стиля для командной строки
        self.setStyleSheet("""
            QLineEdit#CommandLine {
                border: 1px solid #555555;
                border-radius: 3px;
                padding: 6px 8px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                background-color: #3c3f41;
                color: #cccccc;
            }
        """)
        
        # Настройка автодополнения
        self._setup_completer()
    
    def _setup_completer(self):
        """Настройка автодополнения команд"""
        # Список команд для автодополнения
        commands = [
            "LINE", "CIRCLE", "ARC", "POINT", "POLYLINE", "TEXT", "SPLINE", "ELLIPSE",
            "ZOOM_EXTENTS", "ZE", "VIEW_ORIGIN", "ZO", "ZOOM_SELECTION", "ZS", "UNDO", "U",
            "LOAD_DEMO_ROBOT", "TRAJECTORY", "TRAC_FROM_POLYLINE", "EXPORT_TRAC", "RECTANGLE", "LOAD_ROBOT", "SET_JOINT", "SIMULATE",
            "START_DISPENSING", "STOP_DISPENSING", "CLEAR_SCENE", "CHECK_COLLISION", "EDIT_TRAC", "REACHABILITY",
            "STATUS", "HELP",
            "MOVE", "COPY", "ROTATE", "SCALE", "ERASE", "E",
            "MIRROR", "OFFSET", "ARRAY", "TRIM", "EXTEND", "FILLET", "CHAMFER",
            "STRETCH", "EXPLODE", "BREAK", "JOIN",
            "DIM", "DIMLINEAR", "DIMRADIUS", "DIMDIAMETER", "LINETYPE", "HATCH", "BLOCK", "INSERT", "DISTANCE", "AREA",
            "NEW", "OPEN", "SAVE", "SAVEAS", "IMPORT", "EXPORT",
            "GRID", "MULTIPLE", "PEDIT", "LAYER", "XREF",
            "L", "C", "A", "M", "CO", "E", "PL", "REC",
            "DIM", "TEXT", "HATCH", "BLOCK", "INSERT",
            "MEASURE", "DISTANCE", "AREA", "VOLUME",
            "SETTINGS", "OPTIONS", "CONFIG", "PREFERENCES",
            "HELP", "ABOUT", "QUIT", "EXIT"
        ]
        
        # Создание модели для автодополнения
        model = QStringListModel(commands)
        
        # Создание completer
        completer = QCompleter(model)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        
        # Установка completer для поля ввода
        self.setCompleter(completer)