"""
Панель ввода TCP-позиции и ориентации (X, Y, Z, RX, RY, RZ)
с интеграцией обратной кинематики (IK).
"""
from PyQt5.QtWidgets import (
    QWidget, QGridLayout, QLabel, QDoubleSpinBox, QGroupBox, QVBoxLayout,
)
from PyQt5.QtCore import Qt, pyqtSignal


class TCPPositionPanel(QWidget):
    """Компактная панель TCP: 6 полей (X Y Z RX RY RZ) + статус IK."""

    tcpChanged = pyqtSignal(list)  # [x, y, z, rx, ry, rz]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._spinboxes: list[QDoubleSpinBox] = []
        self._block_signals = False
        self._setup_ui()

    # ------------------------------------------------------------------
    #  UI
    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(2)

        group = QGroupBox("TCP позиция / ориентация")
        group.setStyleSheet("QGroupBox { color: #e0e0e0; font-weight: bold; }")
        grid = QGridLayout(group)
        grid.setContentsMargins(4, 8, 4, 4)
        grid.setHorizontalSpacing(4)
        grid.setVerticalSpacing(2)

        labels = ("X:", "Y:", "Z:", "RX:", "RY:", "RZ:")
        ranges = [
            (-5000.0, 5000.0),   # X  мм
            (-5000.0, 5000.0),   # Y  мм
            (-5000.0, 5000.0),   # Z  мм
            (-360.0, 360.0),     # RX градусы
            (-360.0, 360.0),     # RY градусы
            (-360.0, 360.0),     # RZ градусы
        ]
        suffixes = (" мм", " мм", " мм", " °", " °", " °")

        for i, (lbl_text, (vmin, vmax), suffix) in enumerate(
            zip(labels, ranges, suffixes)
        ):
            row, col_offset = divmod(i, 3)  # 2 строки × 3 колонки
            col = col_offset * 2

            lbl = QLabel(lbl_text)
            lbl.setStyleSheet("color: #e0e0e0; font-size: 11px;")
            lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(lbl, row, col)

            spin = QDoubleSpinBox()
            spin.setRange(vmin, vmax)
            spin.setValue(0.0)
            spin.setDecimals(1)
            spin.setSuffix(suffix)
            spin.setSingleStep(1.0 if vmax > 1000 else 0.5)
            spin.setStyleSheet(
                "background: #3c3f41; color: #e0e0e0; min-width: 70px; font-size: 11px;"
            )
            spin.valueChanged.connect(self._on_value_changed)
            self._spinboxes.append(spin)
            grid.addWidget(spin, row, col + 1)

        outer.addWidget(group)

        # статус IK
        self._ik_label = QLabel("IK: —")
        self._ik_label.setStyleSheet("color: #8ab; font-size: 10px; padding-left: 4px;")
        outer.addWidget(self._ik_label)

        self.setStyleSheet("background: #2b2b2b; color: #e0e0e0;")

    # ------------------------------------------------------------------
    #  Внутренние слоты
    # ------------------------------------------------------------------
    def _on_value_changed(self, _value: float) -> None:
        if self._block_signals:
            return
        self.tcpChanged.emit(self.get_tcp())

    # ------------------------------------------------------------------
    #  Публичный API
    # ------------------------------------------------------------------
    def set_tcp(self, x: float, y: float, z: float,
                rx: float, ry: float, rz: float) -> None:
        """Установить значения программно БЕЗ эмиссии сигнала."""
        values = (x, y, z, rx, ry, rz)
        self._block_signals = True
        for i, v in enumerate(values):
            self._spinboxes[i].setValue(float(v))
        self._block_signals = False

    def get_tcp(self) -> list:
        """Вернуть [x, y, z, rx, ry, rz]."""
        return [sp.value() for sp in self._spinboxes]

    def set_ik_status(self, converged: bool) -> None:
        """Обновить метку статуса IK."""
        if converged:
            self._ik_label.setText("IK: converged")
            self._ik_label.setStyleSheet("color: #6c5; font-size: 10px; padding-left: 4px;")
        else:
            self._ik_label.setText("IK: no solution")
            self._ik_label.setStyleSheet("color: #e55; font-size: 10px; padding-left: 4px;")
