"""
Панель Joint status j1–j6: оси с ограничениями (min/max из конфига робота).
Пока без реальной кинематики — значения для отображения и ручной подстройки.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QDoubleSpinBox,
    QGroupBox, QScrollArea, QFrame,
)
from PyQt5.QtCore import Qt, pyqtSignal


DEFAULT_LIMITS = [[-180.0, 180.0]] * 6


class JointStatusPanel(QWidget):
    """Панель осей j1–j6 с ползунками и спинбоксами."""

    jointsChanged = pyqtSignal(list)  # [j1, j2, ..., j6] в градусах

    def __init__(self, parent=None):
        super().__init__(parent)
        self._limits = [list(L) for L in DEFAULT_LIMITS]
        self._spinboxes = []
        self._sliders = []
        self._block_signals = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        group = QGroupBox("Оси робота (j1–j6)")
        group.setStyleSheet("QGroupBox { color: #e0e0e0; font-weight: bold; }")
        group_layout = QVBoxLayout(group)
        for i in range(6):
            row = QHBoxLayout()
            row.addWidget(QLabel(f"j{i + 1}:"))
            smin, smax = self._limits[i][0], self._limits[i][1]
            spin = QDoubleSpinBox()
            spin.setRange(smin, smax)
            spin.setValue(0.0)
            spin.setDecimals(1)
            spin.setSuffix(" °")
            spin.setStyleSheet("background: #3c3f41; color: #e0e0e0; min-width: 70px;")
            spin.valueChanged.connect(self._on_joint_value_changed)
            self._spinboxes.append(spin)
            row.addWidget(spin)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(int(smin), int(smax))
            slider.setValue(0)
            slider.setStyleSheet("min-width: 80px;")
            slider.valueChanged.connect(self._on_slider_changed)
            self._sliders.append(slider)
            row.addWidget(slider)
            group_layout.addLayout(row)
        layout.addWidget(group)
        self.setStyleSheet("background: #2b2b2b; color: #e0e0e0;")

    def _on_slider_changed(self, value: int) -> None:
        if self._block_signals:
            return
        for i, s in enumerate(self._sliders):
            if s == self.sender():
                self._block_signals = True
                self._spinboxes[i].setValue(float(value))
                self._block_signals = False
                self._emit_joints()
                break

    def _on_joint_value_changed(self, value: float) -> None:
        if self._block_signals:
            return
        for i, sp in enumerate(self._spinboxes):
            if sp == self.sender():
                self._block_signals = True
                self._sliders[i].setValue(int(round(value)))
                self._block_signals = False
                self._emit_joints()
                break

    def _emit_joints(self) -> None:
        self.jointsChanged.emit([self._spinboxes[i].value() for i in range(6)])

    def set_limits(self, limits: list) -> None:
        """limits: список из 6 пар [min, max] в градусах."""
        if len(limits) < 6:
            limits = limits + DEFAULT_LIMITS[len(limits):]
        self._limits = [list(pair) for pair in limits[:6]]
        self._block_signals = True
        for i in range(6):
            smin, smax = self._limits[i][0], self._limits[i][1]
            self._spinboxes[i].setRange(smin, smax)
            self._sliders[i].setRange(int(smin), int(smax))
            v = max(smin, min(smax, self._spinboxes[i].value()))
            self._spinboxes[i].setValue(v)
            self._sliders[i].setValue(int(round(v)))
        self._block_signals = False

    def set_joints(self, values: list) -> None:
        """Установить значения осей (6 чисел в градусах)."""
        if len(values) < 6:
            return
        self._block_signals = True
        for i in range(6):
            v = float(values[i])
            smin, smax = self._limits[i][0], self._limits[i][1]
            v = max(smin, min(smax, v))
            self._spinboxes[i].setValue(v)
            self._sliders[i].setValue(int(round(v)))
        self._block_signals = False

    def get_joints(self) -> list:
        """Текущие значения j1–j6 в градусах."""
        return [self._spinboxes[i].value() for i in range(6)]
