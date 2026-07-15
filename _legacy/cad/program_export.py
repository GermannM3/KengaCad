"""
Экспорт программы с Move + IO (впрыск) для заливки на контроллер с Linux-ноутбука.
"""
from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def _ch_num(channel: str) -> int:
    m = re.search(r"\d+", channel or "")
    return int(m.group(0)) if m else 1


def _quat(rx: float, ry: float, rz: float):
    rx_r, ry_r, rz_r = map(math.radians, (rx, ry, rz))
    cx, sx = math.cos(rx_r / 2), math.sin(rx_r / 2)
    cy, sy = math.cos(ry_r / 2), math.sin(ry_r / 2)
    cz, sz = math.cos(rz_r / 2), math.sin(rz_r / 2)
    return (
        cx * cy * cz + sx * sy * sz,
        sx * cy * cz - cx * sy * sz,
        cx * sy * cz + sx * cy * sz,
        cx * cy * sz - sx * sy * cz,
    )


def export_program(
    brand: str,
    waypoints: List[Dict[str, Any]],
    operations: List[Dict[str, Any]],
    file_path: str,
    default_speed: float = 100.0,
) -> bool:
    """
    waypoints: [{index,x,y,z,rx,ry,rz,speed?}, ...]
    operations: [{type: MoveL|MoveJ|Wait|IO, waypoint_index, speed?, wait_ms?, io_channel?, io_value?}, ...]
    """
    if not waypoints:
        return False
    if not operations:
        operations = [
            {
                "type": "MoveL",
                "waypoint_index": int(w.get("index", i + 1)),
                "speed": float(w.get("speed", default_speed)),
            }
            for i, w in enumerate(waypoints)
        ]

    brand_l = (brand or "kuka").lower()
    if brand_l in ("abb", "rapid"):
        text = _abb(waypoints, operations, default_speed)
    elif brand_l in ("fanuc", "tp"):
        text = _fanuc(waypoints, operations, default_speed)
    elif brand_l == "ur":
        text = _ur(waypoints, operations, default_speed)
    else:
        text = _kuka(waypoints, operations, default_speed)

    Path(file_path).write_text(text, encoding="utf-8")
    return True


def _find_wp(waypoints, index: int) -> Optional[Dict[str, Any]]:
    for w in waypoints:
        if int(w.get("index", -1)) == index:
            return w
    if 1 <= index <= len(waypoints):
        return waypoints[index - 1]
    return None


def _kuka(wps, ops, def_speed) -> str:
    lines = [
        "DEF KengaCAD_Cell()",
        "  ; Offline — KengaCAD Linux (Astra/Ред ОС)",
        "  ; DO: впрыск/захват — сверьте $OUT с ячейкой",
        "  $TOOL = TOOL_DATA[1]",
        "  $BASE = BASE_DATA[0]",
        "",
    ]
    for op in ops:
        t = str(op.get("type", "MoveL")).upper()
        if t == "IO":
            ch = _ch_num(str(op.get("io_channel", "DO3")))
            val = "TRUE" if op.get("io_value") else "FALSE"
            lines.append(f"  ; IO {op.get('io_channel')}={1 if op.get('io_value') else 0}")
            lines.append(f"  $OUT[{ch}] = {val}")
        elif t == "WAIT":
            ms = float(op.get("wait_ms", 500))
            lines.append(f"  WAIT SEC {max(0.01, ms / 1000.0):.3f}")
        else:
            wp = _find_wp(wps, int(op.get("waypoint_index", 1)))
            if not wp:
                continue
            vel = max(0.01, float(op.get("speed", def_speed)) / 1000.0)
            cmd = "PTP" if t == "MOVEJ" else "LIN"
            lines.append(f"  $VEL.CP = {vel:.3f}")
            lines.append(
                f"  {cmd} {{X {float(wp['x']):.3f}, Y {float(wp['y']):.3f}, Z {float(wp['z']):.3f}, "
                f"A {float(wp.get('rz', 0)):.3f}, B {float(wp.get('ry', 0)):.3f}, C {float(wp.get('rx', 0)):.3f}}}"
                + (" C_DIS" if cmd == "LIN" else "")
            )
    lines.append("END")
    return "\n".join(lines) + "\n"


def _abb(wps, ops, def_speed) -> str:
    lines = [
        "MODULE KengaCAD_Cell",
        "  ! Offline — KengaCAD Linux",
        "  PERS tooldata tool0 := [TRUE,[[0,0,0],[1,0,0,0]],[0.001,[0,0,0.001],[1,0,0,0],0,0,0]];",
        "  PROC main()",
        "    ConfL \\Off;",
    ]
    for op in ops:
        t = str(op.get("type", "MoveL")).upper()
        if t == "IO":
            ch = _ch_num(str(op.get("io_channel", "DO3")))
            lines.append(f"    SetDO do{ch}, {1 if op.get('io_value') else 0};")
        elif t == "WAIT":
            ms = float(op.get("wait_ms", 500))
            lines.append(f"    WaitTime {max(0.01, ms / 1000.0):.3f};")
        else:
            wp = _find_wp(wps, int(op.get("waypoint_index", 1)))
            if not wp:
                continue
            v = int(round(float(op.get("speed", def_speed))))
            q1, q2, q3, q4 = _quat(float(wp.get("rx", 0)), float(wp.get("ry", 0)), float(wp.get("rz", 0)))
            move = "MoveJ" if t == "MOVEJ" else "MoveL"
            lines.append(
                f"    {move} [[{float(wp['x']):.3f},{float(wp['y']):.3f},{float(wp['z']):.3f}],"
                f"[{q1:.6f},{q2:.6f},{q3:.6f},{q4:.6f}],[0,0,0,0],[9E9,9E9,9E9,9E9,9E9,9E9]], "
                f"v{v}, fine, tool0;"
            )
    lines += ["  ENDPROC", "ENDMODULE"]
    return "\n".join(lines) + "\n"


def _fanuc(wps, ops, def_speed) -> str:
    points = []
    lines = [
        "/PROG  KENGACAD_CELL",
        "/ATTR",
        'COMMENT     = "KengaCAD Linux cell";',
        "/MN",
        "   1:  UTOOL_NUM=1 ;",
        "   2:  UFRAME_NUM=0 ;",
    ]
    line = 3
    pnum = 1
    for op in ops:
        t = str(op.get("type", "MoveL")).upper()
        if t == "IO":
            ch = _ch_num(str(op.get("io_channel", "DO3")))
            lines.append(f"   {line}:  DO[{ch}]={'ON' if op.get('io_value') else 'OFF'} ;")
            line += 1
        elif t == "WAIT":
            ms = float(op.get("wait_ms", 500))
            lines.append(f"   {line}:  WAIT  {max(0.01, ms / 1000.0):.2f} sec ;")
            line += 1
        else:
            wp = _find_wp(wps, int(op.get("waypoint_index", 1)))
            if not wp:
                continue
            points.append(wp)
            spd = float(op.get("speed", def_speed))
            motion = "J" if t == "MOVEJ" else "L"
            lines.append(f"   {line}:{motion} P[{pnum}] {spd:.0f}mm/sec FINE    ;")
            line += 1
            pnum += 1
    lines.append("/POS")
    for i, wp in enumerate(points):
        lines.append(f"P[{i + 1}]{{")
        lines.append("  GP1:")
        lines.append("  UF : 0, UT : 1,")
        lines.append(
            f"  X = {float(wp['x']):.3f}  mm, Y = {float(wp['y']):.3f}  mm, Z = {float(wp['z']):.3f}  mm,"
        )
        lines.append(
            f"  W = {float(wp.get('rx', 0)):.3f}  deg, P = {float(wp.get('ry', 0)):.3f}  deg, "
            f"R = {float(wp.get('rz', 0)):.3f}  deg"
        )
        lines.append("};")
    lines.append("/END")
    return "\n".join(lines) + "\n"


def _ur(wps, ops, def_speed) -> str:
    lines = ["def kengacad_cell():", "  # KengaCAD Linux"]
    for op in ops:
        t = str(op.get("type", "MoveL")).upper()
        if t == "IO":
            ch = max(0, _ch_num(str(op.get("io_channel", "DO3"))) - 1)
            lines.append(f"  set_digital_out({ch}, {'True' if op.get('io_value') else 'False'})")
        elif t == "WAIT":
            ms = float(op.get("wait_ms", 500))
            lines.append(f"  sleep({max(0.01, ms / 1000.0):.3f})")
        else:
            wp = _find_wp(wps, int(op.get("waypoint_index", 1)))
            if not wp:
                continue
            s = max(0.01, float(op.get("speed", def_speed)) / 1000.0)
            lines.append(
                f"  movel(p[{float(wp['x'])/1000:.5f}, {float(wp['y'])/1000:.5f}, {float(wp['z'])/1000:.5f}, "
                f"{math.radians(float(wp.get('rx', 0))):.4f}, {math.radians(float(wp.get('ry', 0))):.4f}, "
                f"{math.radians(float(wp.get('rz', 0))):.4f}], a=1.2, v={s:.3f})"
            )
    lines.append("end")
    return "\n".join(lines) + "\n"
