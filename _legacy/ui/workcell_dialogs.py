"""
Диалоги для добавления параметрических объектов в рабочую ячейку (workcell).
Стол, конвейер, ограждение, а также редактирование свойств любого объекта.
Все диалоги выполнены в тёмной теме KengaCAD.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
    QLineEdit, QDoubleSpinBox, QSpinBox, QPushButton,
    QDialogButtonBox, QColorDialog, QComboBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

# ---------------------------------------------------------------------------
#  Общая тёмная тема для всех диалогов
# ---------------------------------------------------------------------------

_DARK_STYLE = """
QDialog {
    background: #2b2b2b; color: #e0e0e0;
}
QLabel {
    color: #cccccc; font-size: 13px;
}
QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {
    background: #3c3f41; color: #e0e0e0; border: 1px solid #555;
    padding: 4px; border-radius: 3px; font-size: 13px;
}
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {
    border: 1px solid #6a9fd8;
}
QPushButton {
    background: #3c3f41; color: #ccc; border: 1px solid #555;
    padding: 5px 16px; border-radius: 3px; font-size: 13px;
}
QPushButton:hover { background: #4a4e52; }
QPushButton:pressed { background: #555; }
QPushButton[default="true"], QPushButton:default {
    background: #37597a; border: 1px solid #6a9fd8;
}
QDialogButtonBox QPushButton { min-width: 80px; }
"""


def _make_double_spin(value: float = 0.0, min_val: float = -100000.0,
                      max_val: float = 100000.0, decimals: int = 1,
                      suffix: str = " мм") -> QDoubleSpinBox:
    """Утилита: создать настроенный QDoubleSpinBox."""
    sb = QDoubleSpinBox()
    sb.setRange(min_val, max_val)
    sb.setDecimals(decimals)
    sb.setValue(value)
    sb.setSuffix(suffix)
    sb.setSingleStep(10.0)
    return sb


# ===================================================================
#  AddBoxDialog — параметрический бокс (стол / оснастка)
# ===================================================================

class AddBoxDialog(QDialog):
    """
    Диалог для добавления параметрического бокса.
    Используется для столов, оснастки и прочих боксовых примитивов.
    """

    def __init__(self, parent=None, title: str = "Добавить бокс",
                 defaults: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(380)
        self.setStyleSheet(_DARK_STYLE)
        d = defaults or {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name_edit = QLineEdit(d.get("name", "Стол"))
        form.addRow("Имя:", self._name_edit)

        self._width = _make_double_spin(d.get("width", 800.0))
        form.addRow("Ширина (X):", self._width)

        self._length = _make_double_spin(d.get("length", 600.0))
        form.addRow("Длина (Y):", self._length)

        self._height = _make_double_spin(d.get("height", 50.0))
        form.addRow("Высота (Z):", self._height)

        self._pos_x = _make_double_spin(d.get("pos_x", 0.0))
        form.addRow("Позиция X:", self._pos_x)

        self._pos_y = _make_double_spin(d.get("pos_y", 0.0))
        form.addRow("Позиция Y:", self._pos_y)

        self._pos_z = _make_double_spin(d.get("pos_z", 0.0))
        form.addRow("Позиция Z:", self._pos_z)

        # Цвет
        self._color = d.get("color", "#5a4a3a")
        self._color_btn = QPushButton(self._color)
        self._color_btn.setStyleSheet(
            f"background: {self._color}; color: #fff; border: 1px solid #777;"
        )
        self._color_btn.clicked.connect(self._pick_color)
        form.addRow("Цвет:", self._color_btn)

        layout.addLayout(form)

        # OK / Cancel
        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def _pick_color(self):
        c = QColorDialog.getColor(QColor(self._color), self, "Выберите цвет")
        if c.isValid():
            self._color = c.name()
            self._color_btn.setText(self._color)
            self._color_btn.setStyleSheet(
                f"background: {self._color}; color: #fff; border: 1px solid #777;"
            )

    def get_params(self) -> dict:
        """Вернуть параметры бокса."""
        w = self._width.value()
        l = self._length.value()
        h = self._height.value()
        px = self._pos_x.value()
        py = self._pos_y.value()
        pz = self._pos_z.value()
        return {
            "name": self._name_edit.text().strip() or "Бокс",
            "width": w,
            "length": l,
            "height": h,
            "pos_x": px,
            "pos_y": py,
            "pos_z": pz,
            "color": self._color,
            "min_xyz": [px - w / 2, py - l / 2, pz],
            "max_xyz": [px + w / 2, py + l / 2, pz + h],
        }


# ===================================================================
#  AddConveyorDialog — конвейер
# ===================================================================

class AddConveyorDialog(QDialog):
    """Диалог для добавления конвейера."""

    def __init__(self, parent=None, defaults: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Добавить конвейер")
        self.setMinimumWidth(380)
        self.setStyleSheet(_DARK_STYLE)
        d = defaults or {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name_edit = QLineEdit(d.get("name", "Конвейер"))
        form.addRow("Имя:", self._name_edit)

        self._conv_length = _make_double_spin(d.get("length", 2000.0))
        form.addRow("Длина:", self._conv_length)

        self._conv_width = _make_double_spin(d.get("width", 400.0))
        form.addRow("Ширина:", self._conv_width)

        self._conv_height = _make_double_spin(d.get("height", 100.0))
        form.addRow("Высота:", self._conv_height)

        self._pos_x = _make_double_spin(d.get("pos_x", 0.0))
        form.addRow("Позиция X:", self._pos_x)

        self._pos_y = _make_double_spin(d.get("pos_y", 500.0))
        form.addRow("Позиция Y:", self._pos_y)

        self._pos_z = _make_double_spin(d.get("pos_z", 0.0))
        form.addRow("Позиция Z:", self._pos_z)

        self._direction = _make_double_spin(d.get("direction", 0.0),
                                            min_val=0.0, max_val=360.0,
                                            suffix="°")
        form.addRow("Направление:", self._direction)

        layout.addLayout(form)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def get_params(self) -> dict:
        ln = self._conv_length.value()
        w = self._conv_width.value()
        h = self._conv_height.value()
        px = self._pos_x.value()
        py = self._pos_y.value()
        pz = self._pos_z.value()
        return {
            "name": self._name_edit.text().strip() or "Конвейер",
            "length": ln,
            "width": w,
            "height": h,
            "pos_x": px,
            "pos_y": py,
            "pos_z": pz,
            "direction": self._direction.value(),
            "color": "#7a7a4a",
            "min_xyz": [px - ln / 2, py - w / 2, pz],
            "max_xyz": [px + ln / 2, py + w / 2, pz + h],
        }


# ===================================================================
#  AddFenceDialog — защитное ограждение
# ===================================================================

class AddFenceDialog(QDialog):
    """Диалог для добавления защитного ограждения."""

    def __init__(self, parent=None, defaults: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Добавить ограждение")
        self.setMinimumWidth(380)
        self.setStyleSheet(_DARK_STYLE)
        d = defaults or {}

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self._name_edit = QLineEdit(d.get("name", "Ограждение"))
        form.addRow("Имя:", self._name_edit)

        self._fence_length = _make_double_spin(d.get("length", 2000.0))
        form.addRow("Длина:", self._fence_length)

        self._fence_height = _make_double_spin(d.get("height", 1500.0))
        form.addRow("Высота:", self._fence_height)

        self._fence_thickness = _make_double_spin(d.get("thickness", 20.0))
        form.addRow("Толщина:", self._fence_thickness)

        self._pos_x = _make_double_spin(d.get("pos_x", 0.0))
        form.addRow("Позиция X:", self._pos_x)

        self._pos_y = _make_double_spin(d.get("pos_y", -800.0))
        form.addRow("Позиция Y:", self._pos_y)

        self._pos_z = _make_double_spin(d.get("pos_z", 0.0))
        form.addRow("Позиция Z:", self._pos_z)

        self._rotation = _make_double_spin(d.get("rotation", 0.0),
                                           min_val=0.0, max_val=360.0,
                                           suffix="°")
        form.addRow("Поворот:", self._rotation)

        layout.addLayout(form)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    def get_params(self) -> dict:
        ln = self._fence_length.value()
        h = self._fence_height.value()
        t = self._fence_thickness.value()
        px = self._pos_x.value()
        py = self._pos_y.value()
        pz = self._pos_z.value()
        return {
            "name": self._name_edit.text().strip() or "Ограждение",
            "length": ln,
            "height": h,
            "thickness": t,
            "pos_x": px,
            "pos_y": py,
            "pos_z": pz,
            "rotation": self._rotation.value(),
            "color": "#cc4444",
            "min_xyz": [px - ln / 2, py - t / 2, pz],
            "max_xyz": [px + ln / 2, py + t / 2, pz + h],
        }


# ===================================================================
#  ObjectPropertiesDialog — редактирование свойств существующего объекта
# ===================================================================

class ObjectPropertiesDialog(QDialog):
    """
    Универсальный диалог редактирования свойств объекта.
    Принимает dict свойств, показывает редактируемые поля, возвращает обновлённый dict.
    """

    # Ключи, которые не показываем / не даём редактировать
    _SKIP_KEYS = {"id", "aabb", "trimesh", "source_file", "children"}

    def __init__(self, parent=None, obj_data: dict | None = None):
        super().__init__(parent)
        self.setWindowTitle("Свойства объекта")
        self.setMinimumWidth(400)
        self.setStyleSheet(_DARK_STYLE)
        self._obj = dict(obj_data or {})
        self._editors: dict = {}

        layout = QVBoxLayout(self)

        # Заголовок
        title = QLabel(f"Объект: {self._obj.get('name', self._obj.get('id', '?'))}")
        title.setStyleSheet("font-size: 15px; font-weight: bold; color: #e0e0e0; margin-bottom: 6px;")
        layout.addWidget(title)

        form = QFormLayout()

        for key, val in self._obj.items():
            if key in self._SKIP_KEYS:
                continue
            label = self._pretty_label(key)
            if isinstance(val, (int, float)):
                sb = _make_double_spin(float(val))
                self._editors[key] = sb
                form.addRow(f"{label}:", sb)
            elif isinstance(val, str):
                le = QLineEdit(val)
                self._editors[key] = le
                form.addRow(f"{label}:", le)
            elif isinstance(val, dict):
                # Показываем как read-only
                le = QLineEdit(str(val))
                le.setReadOnly(True)
                le.setStyleSheet("background: #333; color: #888;")
                form.addRow(f"{label}:", le)
            # Пропускаем прочие типы

        layout.addLayout(form)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bbox.accepted.connect(self.accept)
        bbox.rejected.connect(self.reject)
        layout.addWidget(bbox)

    @staticmethod
    def _pretty_label(key: str) -> str:
        _MAP = {
            "name": "Имя",
            "type": "Тип",
            "width": "Ширина",
            "length": "Длина",
            "height": "Высота",
            "pos_x": "Позиция X",
            "pos_y": "Позиция Y",
            "pos_z": "Позиция Z",
            "color": "Цвет",
            "direction": "Направление",
            "rotation": "Поворот",
            "thickness": "Толщина",
        }
        return _MAP.get(key, key)

    def get_params(self) -> dict:
        """Вернуть обновлённые параметры."""
        result = dict(self._obj)
        for key, editor in self._editors.items():
            if isinstance(editor, QDoubleSpinBox):
                result[key] = editor.value()
            elif isinstance(editor, QLineEdit):
                result[key] = editor.text()
        return result
