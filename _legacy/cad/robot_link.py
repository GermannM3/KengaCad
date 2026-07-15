"""
Связь с контроллером робота в цехе (Astra Linux / Ред ОС / любой Linux).
Probe TCP + FTP upload — аналог KengaCAD.Core RobotLink.
"""
from __future__ import annotations

import ftplib
import socket
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Optional, Tuple
import json


@dataclass
class RobotLinkProfile:
    name: str = "Robot"
    brand: str = "KUKA"
    host: str = "192.168.1.10"
    port: int = 21
    username: str = "anonymous"
    password: str = ""
    remote_directory: str = "/"


PRESETS = [
    ("KUKA", 21, "/R1/Program", "FTP: программа .src на контроллер"),
    ("ABB", 21, "/", "FTP: .mod / HOME"),
    ("Fanuc", 21, "/", "FTP: .ls / MD:"),
    ("Yaskawa", 21, "/", "FTP INFORM"),
    ("UR", 29999, "/", "Dashboard Server (не FTP)"),
]


def probe(host: str, port: int, timeout_s: float = 3.0) -> Tuple[bool, str]:
    host = (host or "").strip()
    if not host:
        return False, "Не указан IP / hostname"
    try:
        with socket.create_connection((host, int(port)), timeout=timeout_s):
            return True, f"Открыт {host}:{port}"
    except Exception as ex:
        return False, f"{host}:{port} — {ex}"


def ftp_upload(profile: RobotLinkProfile, local_file: str) -> Tuple[bool, str]:
    path = Path(local_file)
    if not path.is_file():
        return False, "Локальный файл не найден"
    host = (profile.host or "").strip()
    if not host:
        return False, "Не указан Host"

    remote_dir = (profile.remote_directory or "/").rstrip("/") or "/"
    remote_name = path.name
    user = profile.username or "anonymous"
    passwd = profile.password or ""

    try:
        with ftplib.FTP() as ftp:
            ftp.connect(host, int(profile.port), timeout=15)
            ftp.login(user, passwd)
            ftp.set_pasv(True)
            if remote_dir not in ("", "/"):
                try:
                    ftp.cwd(remote_dir)
                except ftplib.error_perm:
                    # try create one level
                    for part in remote_dir.strip("/").split("/"):
                        try:
                            ftp.mkd(part)
                        except ftplib.error_perm:
                            pass
                        ftp.cwd(part)
            with path.open("rb") as f:
                ftp.storbinary(f"STOR {remote_name}", f)
            return True, f"FTP OK: {remote_dir}/{remote_name}"
    except Exception as ex:
        return False, f"FTP ошибка: {ex}"


def load_profiles(path: Path) -> List[RobotLinkProfile]:
    try:
        if not path.exists():
            return []
        data = json.loads(path.read_text(encoding="utf-8"))
        return [RobotLinkProfile(**item) for item in data]
    except Exception:
        return []


def save_profiles(profiles: List[RobotLinkProfile], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(p) for p in profiles], ensure_ascii=False, indent=2), encoding="utf-8")
