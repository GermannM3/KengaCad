"""
UI-панель PLC-сигналов и OPC UA подключения.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLabel, QLineEdit, QComboBox, QGroupBox, QHeaderView,
    QCheckBox, QDoubleSpinBox, QMessageBox, QFileDialog, QMenu, QAction,
    QInputDialog, QAbstractItemView,
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QFont

from cad.plc_signals import SignalTable, Signal
from cad.opcua_client import OpcUaConnection, OpcUaSimulator


class PLCPanel(QWidget):
    """Панель управления PLC-сигналами и OPC UA."""

    signalChanged = pyqtSignal(str, object)  # signal_name, new_value

    def __init__(self, parent=None):
        super().__init__(parent)
        self._signal_table = SignalTable.create_default()
        self._opcua: OpcUaConnection | OpcUaSimulator = OpcUaSimulator()
        self._node_map: dict = {}  # signal_name -> node_id
        self._setup_ui()
        self._refresh_table()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # --- OPC UA подключение ---
        opc_group = QGroupBox("OPC UA")
        opc_lay = QVBoxLayout(opc_group)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Endpoint:"))
        self._opc_endpoint = QLineEdit("opc.tcp://localhost:4840")
        self._opc_endpoint.setStyleSheet("background:#3c3f41; color:#e0e0e0; padding:2px;")
        row1.addWidget(self._opc_endpoint)
        self._btn_connect = QPushButton("Подключить")
        self._btn_connect.clicked.connect(self._toggle_connection)
        row1.addWidget(self._btn_connect)
        opc_lay.addLayout(row1)
        self._opc_status = QLabel("Отключено (симуляция)")
        self._opc_status.setStyleSheet("color:#888; font-size:10px;")
        opc_lay.addWidget(self._opc_status)
        layout.addWidget(opc_group)

        # --- Таблица сигналов ---
        sig_group = QGroupBox("Сигналы I/O")
        sig_lay = QVBoxLayout(sig_group)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Имя", "Тип", "Значение", "Описание", "OPC Node"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setStyleSheet("""
            QTableWidget { background:#2b2b2b; color:#e0e0e0; gridline-color:#444; }
            QTableWidget::item:selected { background:#3d5a80; }
            QHeaderView::section { background:#3c3f41; color:#ccc; padding:4px; border:1px solid #555; }
        """)
        self._table.cellChanged.connect(self._on_cell_changed)
        sig_lay.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Сигнал")
        btn_add.clicked.connect(self._add_signal)
        btn_row.addWidget(btn_add)
        btn_del = QPushButton("- Удалить")
        btn_del.clicked.connect(self._delete_signal)
        btn_row.addWidget(btn_del)
        btn_reset = QPushButton("Сброс")
        btn_reset.setToolTip("Вернуть стандартный набор сигналов")
        btn_reset.clicked.connect(self._reset_defaults)
        btn_row.addWidget(btn_reset)
        btn_save = QPushButton("Сохранить")
        btn_save.clicked.connect(self._save_signals)
        btn_row.addWidget(btn_save)
        btn_load = QPushButton("Загрузить")
        btn_load.clicked.connect(self._load_signals)
        btn_row.addWidget(btn_load)
        sig_lay.addLayout(btn_row)
        layout.addWidget(sig_group)

        # --- Привязка к траектории ---
        traj_group = QGroupBox("Привязка к траектории")
        traj_lay = QVBoxLayout(traj_group)
        traj_info = QLabel("Привяжите переключения сигналов к шагам траектории.\n"
                           "Используйте контекстное меню таблицы сигналов.")
        traj_info.setStyleSheet("color:#888; font-size:10px;")
        traj_info.setWordWrap(True)
        traj_lay.addWidget(traj_info)

        ev_row = QHBoxLayout()
        ev_row.addWidget(QLabel("Шаг:"))
        self._ev_step = QDoubleSpinBox()
        self._ev_step.setDecimals(0)
        self._ev_step.setRange(0, 9999)
        self._ev_step.setStyleSheet("background:#3c3f41; color:#e0e0e0;")
        ev_row.addWidget(self._ev_step)
        ev_row.addWidget(QLabel("Сигнал:"))
        self._ev_signal = QComboBox()
        self._ev_signal.setStyleSheet("background:#3c3f41; color:#e0e0e0;")
        ev_row.addWidget(self._ev_signal)
        ev_row.addWidget(QLabel("Значение:"))
        self._ev_value = QComboBox()
        self._ev_value.addItems(["True", "False", "0", "1"])
        self._ev_value.setEditable(True)
        self._ev_value.setStyleSheet("background:#3c3f41; color:#e0e0e0;")
        ev_row.addWidget(self._ev_value)
        btn_ev_add = QPushButton("Добавить")
        btn_ev_add.clicked.connect(self._add_trajectory_event)
        ev_row.addWidget(btn_ev_add)
        traj_lay.addLayout(ev_row)

        self._events_label = QLabel("Событий: 0")
        self._events_label.setStyleSheet("color:#8ab; font-size:10px;")
        traj_lay.addWidget(self._events_label)
        layout.addWidget(traj_group)

        layout.addStretch()

    @property
    def signal_table(self) -> SignalTable:
        return self._signal_table

    def _refresh_table(self):
        self._table.blockSignals(True)
        signals = self._signal_table.all_signals()
        self._table.setRowCount(len(signals))
        for row, sig in enumerate(signals):
            self._table.setItem(row, 0, QTableWidgetItem(sig.name))
            self._table.setItem(row, 1, QTableWidgetItem(sig.direction))
            val_text = "Вкл" if (sig.direction.startswith("D") and sig.value) else ("Выкл" if sig.direction.startswith("D") else str(sig.value))
            val_item = QTableWidgetItem(val_text)
            val_item.setForeground(QColor("#b0b0b0"))
            self._table.setItem(row, 2, val_item)
            self._table.setItem(row, 3, QTableWidgetItem(sig.description))
            node = self._node_map.get(sig.name, "")
            self._table.setItem(row, 4, QTableWidgetItem(node))
        self._table.blockSignals(False)
        # Обновить ComboBox событий
        self._ev_signal.clear()
        for sig in signals:
            self._ev_signal.addItem(sig.name)
        self._events_label.setText(
            f"Событий: {len(self._signal_table.trajectory_events)}")

    def _on_cell_changed(self, row, col):
        signals = self._signal_table.all_signals()
        if row >= len(signals):
            return
        sig = signals[row]
        if col == 2:  # значение
            text = self._table.item(row, 2).text().strip()
            if sig.dtype == "bool":
                sig.value = text.lower() in ("true", "1", "yes", "да", "вкл")
            elif sig.dtype == "int":
                try:
                    sig.value = int(text)
                except ValueError:
                    pass
            elif sig.dtype == "float":
                try:
                    sig.value = float(text)
                except ValueError:
                    pass
            self.signalChanged.emit(sig.name, sig.value)
            self._refresh_table()
        elif col == 4:  # OPC node
            node = self._table.item(row, 4).text().strip()
            if node:
                self._node_map[sig.name] = node
            else:
                self._node_map.pop(sig.name, None)

    def _add_signal(self):
        name, ok = QInputDialog.getText(self, "Новый сигнал", "Имя сигнала:")
        if not ok or not name.strip():
            return
        directions = ["DO", "DI", "AO", "AI"]
        direction, ok = QInputDialog.getItem(
            self, "Тип сигнала", "Направление:", directions, 0, False)
        if not ok:
            return
        dtype = "bool" if direction.startswith("D") else "float"
        self._signal_table.add_signal(Signal(name.strip(), direction, dtype))
        self._refresh_table()

    def _delete_signal(self):
        row = self._table.currentRow()
        signals = self._signal_table.all_signals()
        if 0 <= row < len(signals):
            self._signal_table.remove_signal(signals[row].name)
            self._refresh_table()

    def _reset_defaults(self):
        self._signal_table = SignalTable.create_default()
        self._node_map.clear()
        self._refresh_table()

    def _save_signals(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить сигналы", "", "JSON (*.json);;All (*)")
        if path:
            self._signal_table.save_json(path)

    def _load_signals(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить сигналы", "", "JSON (*.json);;All (*)")
        if path:
            st = SignalTable.load_json(path)
            if st:
                self._signal_table = st
                self._refresh_table()

    def _add_trajectory_event(self):
        step = int(self._ev_step.value())
        sig_name = self._ev_signal.currentText()
        val_text = self._ev_value.currentText().strip()
        if not sig_name:
            return
        sig = self._signal_table.get(sig_name)
        if sig and sig.dtype == "bool":
            value = val_text.lower() in ("true", "1", "yes")
        else:
            try:
                value = float(val_text)
            except ValueError:
                value = val_text
        self._signal_table.add_trajectory_event(step, sig_name, value)
        self._events_label.setText(
            f"Событий: {len(self._signal_table.trajectory_events)}")

    def _toggle_connection(self):
        if isinstance(self._opcua, OpcUaConnection) and self._opcua.connected:
            self._opcua.disconnect()
            self._opcua = OpcUaSimulator()
            self._btn_connect.setText("Подключить")
            self._opc_status.setText("Отключено (симуляция)")
            self._opc_status.setStyleSheet("color:#888; font-size:10px;")
            return

        endpoint = self._opc_endpoint.text().strip()
        if not endpoint:
            return
        conn = OpcUaConnection(endpoint)
        if not conn.available:
            self._opc_status.setText("Симуляция (подключение к PLC недоступно)")
            self._opc_status.setStyleSheet("color:#888; font-size:10px;")
            return
        self._opc_status.setText("Подключение...")
        self._opc_status.setStyleSheet("color:#cc8; font-size:10px;")
        if conn.connect():
            self._opcua = conn
            self._btn_connect.setText("Отключить")
            self._opc_status.setText(f"Подключено: {endpoint}")
            self._opc_status.setStyleSheet("color:#8c8; font-size:10px;")
            # Запустить поллинг если есть node_map
            if self._node_map:
                conn.start_polling(
                    self._node_map, 200,
                    on_value_changed=self._on_opcua_value)
        else:
            self._opc_status.setText("Ошибка подключения")
            self._opc_status.setStyleSheet("color:#c88; font-size:10px;")

    def _on_opcua_value(self, signal_name: str, value):
        self._signal_table.set_value(signal_name, value)
        # Обновление таблицы из другого потока — через сигнал
        try:
            self._refresh_table()
        except Exception:
            pass
