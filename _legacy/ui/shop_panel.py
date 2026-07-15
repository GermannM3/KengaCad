"""
Панель «Цех» для Linux (Astra Linux / Ред ОС): IP → Проверить → Экспорт+ → FTP.
"""
from __future__ import annotations

from pathlib import Path

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QGroupBox, QFileDialog, QMessageBox, QListWidget, QListWidgetItem,
)

from cad.robot_link import PRESETS, RobotLinkProfile, probe, ftp_upload, load_profiles, save_profiles
from cad.program_export import export_program


class ShopFloorPanel(QWidget):
    """Заводской сценарий с ноутбука на отечественном Linux."""

    statusMessage = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_export: str | None = None
        self._ops: list[dict] = []
        self._profiles_path = Path.home() / ".kengacad" / "robot_links.json"
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        info = QLabel(
            "Для Astra / Ред ОС и кузовного цеха:\n"
            "ноутбук в одной LAN с шкафом робота → IP → Проверить →\n"
            "точки траектории → Впрыск → Экспорт+ → Залить FTP."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color:#9aaa9a; font-size:11px;")
        root.addWidget(info)

        box = QGroupBox("Связь с контроллером")
        lay = QVBoxLayout(box)

        row_b = QHBoxLayout()
        row_b.addWidget(QLabel("Бренд:"))
        self.brand = QComboBox()
        for name, port, rdir, hint in PRESETS:
            self.brand.addItem(name, (port, rdir, hint))
        self.brand.currentIndexChanged.connect(self._on_brand)
        row_b.addWidget(self.brand)
        lay.addLayout(row_b)

        self.hint = QLabel("")
        self.hint.setStyleSheet("color:#777; font-size:10px;")
        self.hint.setWordWrap(True)
        lay.addWidget(self.hint)

        row_h = QHBoxLayout()
        self.host = QLineEdit("192.168.1.10")
        self.port = QLineEdit("21")
        self.port.setMaximumWidth(64)
        row_h.addWidget(QLabel("IP:"))
        row_h.addWidget(self.host)
        row_h.addWidget(QLabel("Порт:"))
        row_h.addWidget(self.port)
        lay.addLayout(row_h)

        row_u = QHBoxLayout()
        self.user = QLineEdit("anonymous")
        self.password = QLineEdit("")
        self.password.setEchoMode(QLineEdit.Password)
        row_u.addWidget(QLabel("Логин:"))
        row_u.addWidget(self.user)
        row_u.addWidget(QLabel("Пароль:"))
        row_u.addWidget(self.password)
        lay.addLayout(row_u)

        row_d = QHBoxLayout()
        self.remote = QLineEdit("/R1/Program")
        row_d.addWidget(QLabel("Каталог:"))
        row_d.addWidget(self.remote)
        lay.addLayout(row_d)

        row_btn = QHBoxLayout()
        self.btn_probe = QPushButton("Проверить")
        self.btn_probe.clicked.connect(self._probe)
        self.btn_save = QPushButton("Сохранить профиль")
        self.btn_save.clicked.connect(self._save_profile)
        row_btn.addWidget(self.btn_probe)
        row_btn.addWidget(self.btn_save)
        lay.addLayout(row_btn)

        root.addWidget(box)

        spray = QGroupBox("Впрыск в программу (DO3)")
        s_lay = QVBoxLayout(spray)
        s_row = QHBoxLayout()
        btn_on = QPushButton("Впрыск ВКЛ")
        btn_on.setStyleSheet("background:#1565C0; color:white;")
        btn_on.clicked.connect(lambda: self._add_io(True))
        btn_off = QPushButton("Впрыск ВЫКЛ")
        btn_off.clicked.connect(lambda: self._add_io(False))
        btn_clear = QPushButton("Очистить IO")
        btn_clear.clicked.connect(self._clear_ops)
        s_row.addWidget(btn_on)
        s_row.addWidget(btn_off)
        s_row.addWidget(btn_clear)
        s_lay.addLayout(s_row)
        self.ops_list = QListWidget()
        self.ops_list.setMaximumHeight(90)
        s_lay.addWidget(self.ops_list)
        root.addWidget(spray)

        exp = QGroupBox("Экспорт и заливка")
        e_lay = QVBoxLayout(exp)
        e_row = QHBoxLayout()
        self.btn_export = QPushButton("Экспорт+")
        self.btn_export.setToolTip("Программа с Move по траектории + сигналы впрыска")
        self.btn_export.clicked.connect(self._export)
        self.btn_ftp = QPushButton("Залить FTP")
        self.btn_ftp.setStyleSheet("background:#2E7D32; color:white;")
        self.btn_ftp.clicked.connect(self._upload)
        e_row.addWidget(self.btn_export)
        e_row.addWidget(self.btn_ftp)
        e_lay.addLayout(e_row)
        root.addWidget(exp)

        self.status = QLabel("Статус: не проверено")
        self.status.setWordWrap(True)
        self.status.setStyleSheet("color:#8A9099; font-size:11px;")
        root.addWidget(self.status)
        root.addStretch(1)

        self._on_brand(0)

    def _main(self):
        w = self.window()
        return w

    def _set_status(self, text: str):
        self.status.setText(text)
        self.statusMessage.emit(text)

    def _on_brand(self, _idx: int):
        data = self.brand.currentData()
        if not data:
            return
        port, rdir, hint = data
        self.port.setText(str(port))
        self.remote.setText(rdir)
        self.hint.setText(hint)

    def _profile(self) -> RobotLinkProfile:
        return RobotLinkProfile(
            name=self.brand.currentText(),
            brand=self.brand.currentText(),
            host=self.host.text().strip(),
            port=int(self.port.text() or "21"),
            username=self.user.text(),
            password=self.password.text(),
            remote_directory=self.remote.text().strip() or "/",
        )

    def _probe(self):
        p = self._profile()
        self._set_status(f"Проверка {p.host}:{p.port}…")
        ok, msg = probe(p.host, p.port)
        self._set_status(msg)
        QMessageBox.information(self, "Цех" if ok else "Нет связи", msg)

    def _save_profile(self):
        p = self._profile()
        items = load_profiles(self._profiles_path)
        items = [x for x in items if not (x.host == p.host and x.port == p.port)]
        items.insert(0, p)
        save_profiles(items, self._profiles_path)
        self._set_status(f"Профиль сохранён: {p.brand} {p.host}:{p.port}")

    def _add_io(self, value: bool):
        label = "Впрыск ВКЛ" if value else "Впрыск ВЫКЛ"
        self._ops.append({
            "type": "IO",
            "waypoint_index": 1,
            "io_channel": "DO3",
            "io_value": value,
        })
        self.ops_list.addItem(QListWidgetItem(f"{label} → DO3={'1' if value else '0'}"))
        self._set_status(f"{label} добавлен в программу экспорта")

    def _clear_ops(self):
        self._ops.clear()
        self.ops_list.clear()
        self._set_status("Сигналы IO очищены")

    def _trajectory_as_waypoints(self) -> list[dict]:
        main = self._main()
        pts = getattr(main, "_last_trajectory_points", None) or []
        # Also try drawing entities polylines if empty
        if not pts and hasattr(main, "cad_entities"):
            for pl in main.cad_entities.get("polylines", []):
                for p in pl.get("points", []):
                    if len(p) >= 2:
                        pts.append((float(p[0]), float(p[1]), float(p[2]) if len(p) > 2 else 0.0))
        wps = []
        for i, p in enumerate(pts):
            if isinstance(p, dict):
                wps.append({
                    "index": i + 1,
                    "x": float(p.get("x", 0)),
                    "y": float(p.get("y", 0)),
                    "z": float(p.get("z", 0)),
                    "rx": float(p.get("rx", 0)),
                    "ry": float(p.get("ry", 0)),
                    "rz": float(p.get("rz", 0)),
                    "speed": float(p.get("speed", 120)),
                })
            else:
                x = float(p[0]) if len(p) > 0 else 0.0
                y = float(p[1]) if len(p) > 1 else 0.0
                z = float(p[2]) if len(p) > 2 else 0.0
                wps.append({"index": i + 1, "x": x, "y": y, "z": z, "rx": 0, "ry": 0, "rz": 0, "speed": 120})
        return wps

    def _build_ops(self, waypoints: list[dict]) -> list[dict]:
        """MoveL для каждой точки; IO-события впрыска вставляются равномерно: ON в начале шва, OFF в конце если заданы."""
        ops: list[dict] = []
        io_ops = [o for o in self._ops if o.get("type") == "IO"]
        on_ops = [o for o in io_ops if o.get("io_value")]
        off_ops = [o for o in io_ops if not o.get("io_value")]

        if on_ops and waypoints:
            ops.append({**on_ops[0], "waypoint_index": 1})

        for w in waypoints:
            ops.append({
                "type": "MoveL",
                "waypoint_index": int(w["index"]),
                "speed": float(w.get("speed", 120)),
            })

        if off_ops and waypoints:
            ops.append({**off_ops[-1], "waypoint_index": int(waypoints[-1]["index"])})
        elif on_ops and not off_ops and waypoints:
            # если только ВКЛ — автоматически ВЫКЛ в конце
            ops.append({
                "type": "IO",
                "waypoint_index": int(waypoints[-1]["index"]),
                "io_channel": "DO3",
                "io_value": False,
            })
        return ops

    def _export(self):
        wps = self._trajectory_as_waypoints()
        if not wps:
            QMessageBox.warning(
                self, "Экспорт",
                "Нет траектории.\nНарисуйте полилинию или задайте точки программы,\nзатем снова Экспорт+."
            )
            return
        brand = self.brand.currentText()
        filters = {
            "KUKA": "KUKA KRL (*.src *.krl);;All (*.*)",
            "ABB": "ABB RAPID (*.mod);;All (*.*)",
            "Fanuc": "Fanuc TP (*.ls);;All (*.*)",
            "UR": "UR Script (*.script);;All (*.*)",
            "Yaskawa": "Yaskawa (*.jbi);;All (*.*)",
        }
        ext = {"KUKA": "src", "ABB": "mod", "Fanuc": "ls", "UR": "script", "Yaskawa": "jbi"}.get(brand, "src")
        path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт программы для цеха",
            f"KengaCAD_Cell.{ext}",
            filters.get(brand, "All (*.*)"),
        )
        if not path:
            return
        ops = self._build_ops(wps)
        ok = export_program(brand, wps, ops, path)
        if ok:
            self._last_export = path
            self._set_status(f"Экспорт готов: {path} — можно Залить FTP")
            QMessageBox.information(self, "Экспорт", f"Сохранено:\n{path}")
        else:
            QMessageBox.warning(self, "Экспорт", "Не удалось сохранить файл")

    def _upload(self):
        if not self._last_export or not Path(self._last_export).is_file():
            QMessageBox.information(self, "FTP", "Сначала нажмите «Экспорт+».")
            return
        p = self._profile()
        if not p.host:
            QMessageBox.warning(self, "FTP", "Укажите IP контроллера.")
            return
        if p.brand == "UR":
            QMessageBox.information(
                self, "UR",
                "Для UR заливка по FTP часто не используется.\n"
                "Экспортируйте .script и загрузите через teach pendant / Dashboard."
            )
            return
        self._set_status(f"FTP → {p.host}…")
        ok, msg = ftp_upload(p, self._last_export)
        self._set_status(msg)
        QMessageBox.information(self, "Залито" if ok else "Ошибка FTP", msg)
