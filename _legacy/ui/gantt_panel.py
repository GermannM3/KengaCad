"""
Gantt-диаграмма цикла и панель Virtual Commissioning.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QProgressBar, QTextEdit, QComboBox, QDoubleSpinBox,
)
from PyQt5.QtCore import Qt, QTimer, QRectF, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QFont, QPen, QBrush

from cad.virtual_commissioning import CycleModel, CycleSimulator, GanttData
from cad.plc_signals import SignalTable


# Цвета для типов шагов
_STEP_COLORS = {
    "move": QColor("#4a9eff"),
    "wait": QColor("#888888"),
    "weld": QColor("#ff6040"),
    "grip": QColor("#40c040"),
    "release": QColor("#c0c040"),
    "custom": QColor("#c080ff"),
}


class GanttWidget(QWidget):
    """Виджет отрисовки Gantt-диаграммы."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._gantt: GanttData | None = None
        self._current_step = -1
        self._elapsed = 0.0
        self.setMinimumHeight(80)
        self.setStyleSheet("background:#1e1e1e;")

    def set_gantt(self, gantt: GanttData):
        self._gantt = gantt
        self._current_step = -1
        self._elapsed = 0.0
        self.update()

    def set_progress(self, step: int, elapsed: float):
        self._current_step = step
        self._elapsed = elapsed
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self._gantt or not self._gantt.bars:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        w = self.width() - 20
        h = self.height()
        bar_h = max(20, h - 40)
        y0 = 20
        total = self._gantt.total_s
        if total <= 0:
            return

        # Фон
        painter.fillRect(10, y0, w, bar_h, QColor("#2b2b2b"))

        # Полоски шагов
        for bar in self._gantt.bars:
            x1 = 10 + int(bar["start_s"] / total * w)
            x2 = 10 + int(bar["end_s"] / total * w)
            bw = max(1, x2 - x1)
            color = _STEP_COLORS.get(bar["type"], QColor("#666"))
            if bar["index"] == self._current_step:
                color = color.lighter(140)
            painter.fillRect(x1, y0, bw, bar_h, color)
            # Граница
            painter.setPen(QPen(QColor("#555"), 1))
            painter.drawRect(x1, y0, bw, bar_h)
            # Текст
            if bw > 30:
                painter.setPen(QColor("#fff"))
                painter.setFont(QFont("", 7))
                painter.drawText(
                    QRectF(x1 + 2, y0 + 2, bw - 4, bar_h - 4),
                    Qt.AlignLeft | Qt.AlignTop,
                    bar["name"][:20])

        # Курсор текущей позиции
        if self._elapsed > 0 and total > 0:
            cx = 10 + int(self._elapsed / total * w)
            painter.setPen(QPen(QColor("#ff0"), 2))
            painter.drawLine(cx, y0 - 3, cx, y0 + bar_h + 3)

        # Метки времени
        painter.setPen(QColor("#888"))
        painter.setFont(QFont("", 8))
        painter.drawText(10, y0 + bar_h + 14, "0 с")
        painter.drawText(w - 30, y0 + bar_h + 14, f"{total:.1f} с")

        # Заголовок
        painter.setPen(QColor("#aaa"))
        painter.setFont(QFont("", 9))
        painter.drawText(10, 14, self._gantt.name)

        painter.end()


class VirtualCommissioningPanel(QWidget):
    """Панель Virtual Commissioning: Gantt + управление циклом."""

    simulationStep = pyqtSignal(int)  # текущий шаг цикла

    def __init__(self, parent=None):
        super().__init__(parent)
        self._cycle: CycleModel | None = None
        self._simulator: CycleSimulator | None = None
        self._signal_table: SignalTable | None = None
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Gantt-диаграмма
        gantt_group = QGroupBox("Gantt-диаграмма цикла")
        gantt_lay = QVBoxLayout(gantt_group)
        self._gantt_widget = GanttWidget()
        gantt_lay.addWidget(self._gantt_widget)
        layout.addWidget(gantt_group)

        # Управление
        ctrl_group = QGroupBox("Управление циклом")
        ctrl_lay = QVBoxLayout(ctrl_group)

        row1 = QHBoxLayout()
        self._btn_generate = QPushButton("Сгенерировать цикл")
        self._btn_generate.setToolTip("Создать цикл из текущей траектории")
        self._btn_generate.clicked.connect(self._generate_cycle)
        row1.addWidget(self._btn_generate)
        row1.addWidget(QLabel("Скорость (мм/с):"))
        self._speed_spin = QDoubleSpinBox()
        self._speed_spin.setRange(10, 5000)
        self._speed_spin.setValue(250)
        self._speed_spin.setStyleSheet("background:#3c3f41; color:#e0e0e0;")
        row1.addWidget(self._speed_spin)
        ctrl_lay.addLayout(row1)

        row2 = QHBoxLayout()
        self._btn_start = QPushButton("Старт")
        self._btn_start.clicked.connect(self._start_sim)
        row2.addWidget(self._btn_start)
        self._btn_stop = QPushButton("Стоп")
        self._btn_stop.clicked.connect(self._stop_sim)
        row2.addWidget(self._btn_stop)
        self._btn_reset = QPushButton("Сброс")
        self._btn_reset.clicked.connect(self._reset_sim)
        row2.addWidget(self._btn_reset)
        ctrl_lay.addLayout(row2)

        self._progress = QProgressBar()
        self._progress.setRange(0, 1000)
        self._progress.setValue(0)
        self._progress.setStyleSheet("""
            QProgressBar { background:#2b2b2b; border:1px solid #555; height:16px; }
            QProgressBar::chunk { background:#4a9eff; }
        """)
        ctrl_lay.addWidget(self._progress)

        self._status_label = QLabel("Цикл не создан")
        self._status_label.setStyleSheet("color:#888; font-size:10px;")
        ctrl_lay.addWidget(self._status_label)
        layout.addWidget(ctrl_group)

        # Лог
        log_group = QGroupBox("Лог цикла")
        log_lay = QVBoxLayout(log_group)
        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(120)
        self._log.setStyleSheet("background:#1e1e1e; color:#aaa; font-size:10px; font-family:Consolas;")
        log_lay.addWidget(self._log)
        layout.addWidget(log_group)

        layout.addStretch()

    def set_signal_table(self, st: SignalTable):
        self._signal_table = st

    def set_trajectory_points(self, points: list):
        """Сохранить точки траектории для генерации цикла."""
        self._traj_points = points

    def _generate_cycle(self):
        pts = getattr(self, "_traj_points", None)
        if not pts or len(pts) < 2:
            self._status_label.setText("Нет траектории для генерации цикла")
            return
        speed = self._speed_spin.value()
        st = self._signal_table or SignalTable.create_default()
        self._cycle = CycleModel.from_trajectory(pts, speed, st)
        gantt = self._cycle.gantt_data()
        self._gantt_widget.set_gantt(gantt)
        self._status_label.setText(
            f"Цикл: {len(self._cycle.steps)} шагов, "
            f"{self._cycle.total_time_s():.2f} сек")
        self._log.clear()
        self._log.append(gantt.summary())
        self._progress.setValue(0)

    def _start_sim(self):
        if not self._cycle or not self._cycle.steps:
            return
        st = self._signal_table or SignalTable.create_default()
        self._simulator = CycleSimulator(self._cycle, st)
        self._simulator.set_callbacks(
            on_step=self._on_step,
            on_signal=self._on_signal,
            on_finished=self._on_finished,
        )
        self._simulator.start()
        self._timer.start(50)  # 20 FPS
        self._status_label.setText("Симуляция запущена...")
        self._log.append("--- Старт симуляции ---")

    def _stop_sim(self):
        if self._simulator:
            self._simulator.stop()
        self._timer.stop()
        self._status_label.setText("Симуляция остановлена")

    def _reset_sim(self):
        self._timer.stop()
        if self._simulator:
            self._simulator.reset()
        self._gantt_widget.set_progress(-1, 0)
        self._progress.setValue(0)
        self._status_label.setText("Сброс")

    def _tick(self):
        if not self._simulator or not self._simulator.running:
            return
        self._simulator.tick(0.05)  # 50ms
        self._gantt_widget.set_progress(
            self._simulator.current_step,
            self._simulator.elapsed)
        self._progress.setValue(int(self._simulator.progress * 1000))

    def _on_step(self, step_idx: int):
        if self._cycle and 0 <= step_idx < len(self._cycle.steps):
            name = self._cycle.steps[step_idx].name
            self._log.append(f"  Шаг {step_idx + 1}: {name}")
            self.simulationStep.emit(step_idx)

    def _on_signal(self, name: str, value, when: str, step_idx: int):
        self._log.append(f"    [{when}] {name} = {value}")

    def _on_finished(self):
        self._timer.stop()
        self._status_label.setText(
            f"Цикл завершён: {self._simulator.elapsed:.2f} сек")
        self._log.append("--- Цикл завершён ---")
        self._progress.setValue(1000)
