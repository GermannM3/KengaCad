"""
CAD import/export utilities for KengaCAD.
Поддержка форматов: DXF, DWG (через ODA), PDF, CSV (траектории).
Постпроцессоры роботов: KUKA KRL, ABB RAPID, Fanuc TP, Yaskawa INFORM, UR Script.
"""
from typing import List, Tuple, Dict, Optional, Any
import ezdxf
from ezdxf.math import Vec3
import json
import os
import csv
import math
from datetime import datetime

try:
    import jinja2
    _HAS_JINJA2 = True
except ImportError:
    _HAS_JINJA2 = False


def _read_cad_file(file_path: str):
    """Читает DXF или DWG. Для DWG требуется ODA File Converter."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".dwg":
        try:
            from ezdxf.addons import odafc
            return odafc.readfile(file_path)
        except ImportError:
            raise IOError("DWG: установите ODA File Converter и ezdxf[odafc]")
        except Exception as e:
            raise IOError(f"DWG: {e}")
    return ezdxf.readfile(file_path)


def _save_cad_file(doc, file_path: str) -> None:
    """Сохраняет в DXF или DWG."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".dwg":
        try:
            from ezdxf.addons import odafc
            odafc.export_dwg(doc, file_path, replace=True)
        except ImportError:
            raise IOError("DWG: установите ODA File Converter и ezdxf[odafc]")
        except Exception as e:
            raise IOError(f"DWG: {e}")
    else:
        doc.saveas(file_path)


def _euler_to_quaternion(rx: float, ry: float, rz: float):
    """Convert Euler angles (degrees) to quaternion [q1,q2,q3,q4] for ABB RAPID.

    Uses ZYX convention (Rz * Ry * Rx) which is standard for ABB robots.
    Returns (q1, q2, q3, q4) = (w, x, y, z).
    """
    rx_r = math.radians(rx)
    ry_r = math.radians(ry)
    rz_r = math.radians(rz)
    cx, sx = math.cos(rx_r / 2), math.sin(rx_r / 2)
    cy, sy = math.cos(ry_r / 2), math.sin(ry_r / 2)
    cz, sz = math.cos(rz_r / 2), math.sin(rz_r / 2)
    q1 = cx * cy * cz + sx * sy * sz
    q2 = sx * cy * cz - cx * sy * sz
    q3 = cx * sy * cz + sx * cy * sz
    q4 = cx * cy * sz - sx * sy * cz
    return (q1, q2, q3, q4)


def _prepare_trajectory_points(trajectory, config: dict = None):
    """Normalise trajectory points to list of dicts with x,y,z,rx,ry,rz (and quaternions).

    Accepts:
      - list of (x,y,z) tuples
      - list of (x,y,z,rx,ry,rz) tuples
      - list of dicts with 'x','y','z' (and optionally 'rx','ry','rz')
    """
    points = []
    for p in trajectory:
        if isinstance(p, dict):
            x = float(p.get("x", 0))
            y = float(p.get("y", 0))
            z = float(p.get("z", 0))
            rx = float(p.get("rx", 0))
            ry = float(p.get("ry", 0))
            rz = float(p.get("rz", 0))
        elif isinstance(p, (list, tuple)):
            x = float(p[0]) if len(p) > 0 else 0.0
            y = float(p[1]) if len(p) > 1 else 0.0
            z = float(p[2]) if len(p) > 2 else 0.0
            rx = float(p[3]) if len(p) > 3 else 0.0
            ry = float(p[4]) if len(p) > 4 else 0.0
            rz = float(p[5]) if len(p) > 5 else 0.0
        else:
            continue
        q1, q2, q3, q4 = _euler_to_quaternion(rx, ry, rz)
        points.append({
            "x": x, "y": y, "z": z,
            "rx": rx, "ry": ry, "rz": rz,
            "q1": q1, "q2": q2, "q3": q3, "q4": q4,
        })
    return points


def _get_templates_dir() -> str:
    """Return path to the templates directory."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "config", "templates")


def _render_template(template_name: str, context: dict) -> str:
    """Render a Jinja2 template by name.

    Falls back to a basic string-formatting approach if jinja2 is not installed.
    """
    templates_dir = _get_templates_dir()
    template_path = os.path.join(templates_dir, template_name)

    if _HAS_JINJA2:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        template = env.get_template(template_name)
        return template.render(**context)
    else:
        # Fallback: read template and do naive placeholder substitution
        if os.path.isfile(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                raw = f.read()
            # Simple variable replacement for {{ var }}
            for key, value in context.items():
                if not isinstance(value, (list, dict)):
                    raw = raw.replace("{{ " + key + " }}", str(value))
            return raw
        raise FileNotFoundError(f"Template not found: {template_path}")


class CADImportExport:
    def __init__(self):
        pass

    def import_dxf(self, file_path: str) -> Optional[Dict]:
        """Import DXF or DWG file into internal entities dict. Returns None on error."""
        try:
            doc = _read_cad_file(file_path)
            msp = doc.modelspace()

            entities_data = {
                "lines": [], "circles": [], "arcs": [], "points": [],
                "polylines": [], "splines": [], "ellipses": [], "texts": [],
                "dimensions": [], "hatches": [], "inserts": [],
            }

            for entity in msp:
                layer = getattr(entity.dxf, "layer", "0")
                dtype = entity.dxftype()

                if dtype == "LINE":
                    start = entity.dxf.start
                    end = entity.dxf.end
                    entities_data["lines"].append({
                        "start": (start.x, start.y, start.z),
                        "end": (end.x, end.y, end.z),
                        "layer": layer,
                    })
                elif dtype == "CIRCLE":
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    entities_data["circles"].append({
                        "center": (center.x, center.y, center.z),
                        "radius": radius,
                        "layer": layer,
                    })
                elif dtype == "ARC":
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    entities_data["arcs"].append({
                        "center": (center.x, center.y, center.z),
                        "radius": radius,
                        "start_angle": start_angle,
                        "end_angle": end_angle,
                        "layer": layer,
                    })
                elif dtype == "POINT":
                    point = entity.dxf.location
                    entities_data["points"].append({
                        "location": (point.x, point.y, point.z),
                        "layer": layer,
                    })
                elif dtype == "LWPOLYLINE":
                    points = [(v[0], v[1], 0) for v in entity.vertices]
                    entities_data["polylines"].append({
                        "points": points,
                        "layer": layer,
                    })
                elif dtype == "TEXT":
                    insert = entity.dxf.insert
                    height = getattr(entity.dxf, "height", 10)
                    entities_data["texts"].append({
                        "position": (insert.x, insert.y, insert.z),
                        "text": entity.dxf.text,
                        "height": height,
                        "layer": layer,
                    })
                elif dtype == "SPLINE":
                    fit_points = [(v.x, v.y, v.z) for v in entity.fit_points]
                    entities_data["splines"].append({
                        "fit_points": fit_points,
                        "layer": layer,
                    })
                elif dtype == "ELLIPSE":
                    center = entity.dxf.center
                    maj = entity.dxf.major_axis
                    ratio = getattr(entity.dxf, "ratio", 1.0)
                    entities_data["ellipses"].append({
                        "center": (center.x, center.y, center.z),
                        "major_axis": (maj.x, maj.y, maj.z),
                        "ratio": ratio,
                        "layer": layer,
                    })

            return entities_data
        except Exception as e:
            print(f"CAD import error: {e}")
            return None

    def export_dxf(self, entities_data: Dict, file_path: str, blocks: Dict = None) -> bool:
        """Export internal entities dict to DXF file."""
        blocks = blocks or {}
        try:
            doc = ezdxf.new("R2000", setup=True)
            msp = doc.modelspace()

            for bname, block in blocks.items():
                blk = doc.blocks.new(bname)
                for ent in block.get("entities", []):
                    key = ent.get("key", "")
                    e = ent.get("entity", {})
                    layer = e.get("layer", "0")
                    if key == "lines":
                        blk.add_line(start=Vec3(*e.get("start", (0,0,0))), end=Vec3(*e.get("end", (0,0,0))), dxfattribs={"layer": layer})
                    elif key == "circles":
                        blk.add_circle(center=Vec3(*e.get("center", (0,0,0))), radius=e.get("radius", 0), dxfattribs={"layer": layer})
                    elif key == "arcs":
                        blk.add_arc(center=Vec3(*e.get("center", (0,0,0))), radius=e.get("radius", 0),
                                    start_angle=e.get("start_angle", 0), end_angle=e.get("end_angle", 0), dxfattribs={"layer": layer})
                    elif key == "polylines":
                        pts = e.get("points", [])
                        if len(pts) >= 2:
                            blk.add_lwpolyline([(p[0], p[1]) for p in pts], dxfattribs={"layer": layer})

            for ins in entities_data.get("inserts", []):
                pos = ins.get("position", (0, 0, 0))
                bname = ins.get("block", "")
                if bname in blocks:
                    msp.add_blockref(bname, Vec3(*pos), dxfattribs={
                        "layer": ins.get("layer", "0"),
                        "xscale": ins.get("scale", 1.0),
                        "yscale": ins.get("scale", 1.0),
                        "rotation": ins.get("angle", 0),
                    })

            for line in entities_data.get("lines", []):
                start = line["start"]
                end = line["end"]
                layer = line.get("layer", "0")
                msp.add_line(start=Vec3(*start), end=Vec3(*end), dxfattribs={"layer": layer})

            for circle in entities_data.get("circles", []):
                center = circle["center"]
                radius = circle["radius"]
                layer = circle.get("layer", "0")
                msp.add_circle(center=Vec3(*center), radius=radius, dxfattribs={"layer": layer})

            for arc in entities_data.get("arcs", []):
                center = arc["center"]
                radius = arc["radius"]
                start_angle = arc["start_angle"]
                end_angle = arc["end_angle"]
                layer = arc.get("layer", "0")
                msp.add_arc(center=Vec3(*center), radius=radius,
                            start_angle=start_angle, end_angle=end_angle,
                            dxfattribs={"layer": layer})

            for point in entities_data.get("points", []):
                location = point["location"]
                layer = point.get("layer", "0")
                msp.add_point(location=Vec3(*location), dxfattribs={"layer": layer})

            for polyline in entities_data.get("polylines", []):
                points = polyline["points"]
                layer = polyline.get("layer", "0")
                msp.add_lwpolyline(points, dxfattribs={"layer": layer})

            for text in entities_data.get("texts", []):
                position = text.get("position", (0, 0, 0))
                content = text.get("text", "")
                height = float(text.get("height", 10))
                layer = text.get("layer", "0")
                msp.add_text(content, dxfattribs={"height": height, "insert": Vec3(*position), "layer": layer})

            for spline in entities_data.get("splines", []):
                fit_points = spline.get("fit_points", [])
                layer = spline.get("layer", "0")
                if len(fit_points) >= 2:
                    msp.add_spline(fit_points, dxfattribs={"layer": layer})

            for ellipse in entities_data.get("ellipses", []):
                center = ellipse.get("center", (0, 0, 0))
                major_axis = ellipse.get("major_axis", (1, 0, 0))
                ratio = ellipse.get("ratio", 1.0)
                layer = ellipse.get("layer", "0")
                msp.add_ellipse(center=Vec3(*center), major_axis=Vec3(*major_axis), ratio=ratio, dxfattribs={"layer": layer})

            for hatch in entities_data.get("hatches", []):
                layer = hatch.get("layer", "0")
                color = hatch.get("color", "#555555")
                try:
                    cint = int(color.lstrip("#")[:6], 16) if isinstance(color, str) and color.startswith("#") else 7
                    from ezdxf.gfxattribs import GfxAttribs
                    r = (cint >> 16) & 0xff
                    g = (cint >> 8) & 0xff
                    b = cint & 0xff
                    acad_color = 7
                    if r < 128 and g < 128 and b < 128:
                        acad_color = 0
                    elif r > 200:
                        acad_color = 1
                    elif g > 200:
                        acad_color = 3
                    else:
                        acad_color = 7
                except Exception:
                    acad_color = 7
                h = msp.add_hatch(color=acad_color, dxfattribs={"layer": layer})
                if hatch.get("type") == "polygon":
                    pts = [(p[0], p[1]) for p in hatch.get("points", [])]
                    if len(pts) >= 3:
                        h.paths.add_polyline_path(pts, is_closed=True)
                else:
                    c = hatch.get("center", (0, 0, 0))
                    rad = hatch.get("radius", 0)
                    edge = h.paths.add_edge_path()
                    edge.add_ellipse((c[0], c[1]), major_axis=(rad, 0), ratio=1.0)

            _save_cad_file(doc, file_path)
            print(f"CAD exported: {file_path}")
            return True
        except Exception as e:
            print(f"CAD export error: {e}")
            return False

    def import_json_trajectory(self, file_path: str) -> Optional[List[Tuple[float, float, float]]]:
        """Import trajectory from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if "trajectory" in data:
                points = data["trajectory"]
                validated_points = []
                for point in points:
                    if isinstance(point, (list, tuple)) and len(point) >= 3:
                        validated_points.append((float(point[0]), float(point[1]), float(point[2])))
                    elif isinstance(point, dict) and "x" in point and "y" in point and "z" in point:
                        validated_points.append((float(point["x"]), float(point["y"]), float(point["z"])))
                return validated_points
            print("Trajectory data not found in JSON")
            return None
        except Exception as e:
            print(f"JSON trajectory import error: {e}")
            return None

    def export_json_trajectory(self, points: List[Tuple[float, float, float]],
                               file_path: str, metadata: Dict = None) -> bool:
        """Export trajectory to JSON file."""
        try:
            data = {
                "trajectory": [{"x": p[0], "y": p[1], "z": p[2]} for p in points],
                "metadata": metadata or {},
                "created_by": "KengaCAD",
                "format_version": "1.0",
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Trajectory exported: {file_path}")
            return True
        except Exception as e:
            print(f"JSON trajectory export error: {e}")
            return False

    def import_csv_trajectory(self, file_path: str) -> Optional[List[Tuple[float, float, float]]]:
        """Import trajectory from CSV (RoboCAD: x,y,z или X,Y,Z)."""
        try:
            points = []
            with open(file_path, 'r', encoding='utf-8-sig', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)
                xi, yi, zi = 0, 1, 2
                if header and len(header) >= 3:
                    header_lower = [h.strip().lower() for h in header]
                    if 'x' in header_lower and 'y' in header_lower:
                        xi = header_lower.index('x')
                        yi = header_lower.index('y')
                        zi = header_lower.index('z') if 'z' in header_lower else 2
                else:
                    header = None
                for row in reader:
                    if len(row) >= 3:
                        try:
                            x = float(row[xi].strip())
                            y = float(row[yi].strip())
                            z = float(row[zi].strip()) if zi < len(row) else 0.0
                            points.append((x, y, z))
                        except (ValueError, IndexError):
                            continue
            return points if points else None
        except Exception as e:
            print(f"CSV trajectory import error: {e}")
            return None

    def export_csv_trajectory(self, points: List[Tuple[float, float, float]], file_path: str) -> bool:
        """Export trajectory to CSV (RoboCAD совместимый)."""
        try:
            with open(file_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["X", "Y", "Z"])
                for p in points:
                    writer.writerow([p[0], p[1], p[2] if len(p) > 2 else 0.0])
            print(f"CSV trajectory exported: {file_path}")
            return True
        except Exception as e:
            print(f"CSV trajectory export error: {e}")
            return False

    def _load_postprocessor_config(self, key: str) -> dict:
        """Загрузить настройки постпроцессора из config/postprocessors.json."""
        try:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            path = os.path.join(base, "config", "postprocessors.json")
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return data.get(key, {})
        except Exception:
            pass
        return {}

    def export_kuka_krl(self, points: List[Tuple[float, float, float]], file_path: str,
                       speed_mms: float = 100.0, program_name: str = None, config: dict = None) -> bool:
        """Export trajectory to KUKA KRL (LIN in Cartesian). Uses Jinja2 template."""
        try:
            cfg = config or self._load_postprocessor_config("kuka_krl")
            if "default_speed_mms" in cfg and speed_mms == 100.0:
                speed_mms = float(cfg["default_speed_mms"])
            prepared = _prepare_trajectory_points(points)
            context = {
                "program_name": program_name or cfg.get("program_name", "KengaCAD_Trajectory"),
                "comment": cfg.get("comment", "; Generated by KengaCAD"),
                "velocity_var": cfg.get("velocity_var", "$VEL.CP"),
                "motion_type": cfg.get("motion_type", "LIN"),
                "speed_mms": speed_mms,
                "points": prepared,
            }
            template_name = cfg.get("template", "kuka_krl.j2")
            output = _render_template(template_name, context)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"KUKA KRL exported: {file_path}")
            return True
        except Exception as e:
            print(f"KUKA KRL export error: {e}")
            return False

    def export_abb_rapid(self, points: List[Tuple[float, float, float]], file_path: str,
                        speed_mms: float = 100.0, module_name: str = None,
                        tool_name: str = None, config: dict = None) -> bool:
        """Export trajectory to ABB RAPID (MoveL). Uses Jinja2 template."""
        try:
            cfg = config or self._load_postprocessor_config("abb_rapid")
            if "default_speed_mms" in cfg and speed_mms == 100.0:
                speed_mms = float(cfg["default_speed_mms"])
            prepared = _prepare_trajectory_points(points)
            context = {
                "module_name": module_name or cfg.get("module_name", "KengaCAD_Trajectory"),
                "comment": cfg.get("comment", "! Generated by KengaCAD"),
                "proc_name": cfg.get("proc_name", "main"),
                "tool_name": tool_name or cfg.get("tool_name", "tool0"),
                "speed_mms": speed_mms,
                "points": prepared,
            }
            template_name = cfg.get("template", "abb_rapid.j2")
            output = _render_template(template_name, context)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"ABB RAPID exported: {file_path}")
            return True
        except Exception as e:
            print(f"ABB RAPID export error: {e}")
            return False

    def export_fanuc_tp(self, trajectory, file_path: str, config: dict = None) -> bool:
        """Export trajectory to Fanuc TP program format. Uses Jinja2 template."""
        try:
            cfg = config or self._load_postprocessor_config("fanuc_tp")
            speed_mms = float(cfg.get("default_speed_mms", 100))
            prepared = _prepare_trajectory_points(trajectory)
            context = {
                "program_name": cfg.get("program_name", "KengaCAD_TRAJ"),
                "comment": cfg.get("comment", "Generated by KengaCAD"),
                "utool_num": int(cfg.get("utool_num", 1)),
                "uframe_num": int(cfg.get("uframe_num", 0)),
                "motion_type": cfg.get("motion_type", "L"),
                "speed_mms": speed_mms,
                "points": prepared,
            }
            template_name = cfg.get("template", "fanuc_tp.j2")
            output = _render_template(template_name, context)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Fanuc TP exported: {file_path}")
            return True
        except Exception as e:
            print(f"Fanuc TP export error: {e}")
            return False

    def export_yaskawa_inform(self, trajectory, file_path: str, config: dict = None) -> bool:
        """Export trajectory to Yaskawa INFORM job format. Uses Jinja2 template."""
        try:
            cfg = config or self._load_postprocessor_config("yaskawa_inform")
            speed_mms = float(cfg.get("default_speed_mms", 100))
            prepared = _prepare_trajectory_points(trajectory)
            context = {
                "job_name": cfg.get("job_name", "KENGACAD_TRAJ"),
                "comment": cfg.get("comment", "Generated by KengaCAD"),
                "motion_type": cfg.get("motion_type", "MOVL"),
                "speed_mms": speed_mms,
                "date": datetime.now().strftime("%Y/%m/%d %H:%M"),
                "points": prepared,
            }
            template_name = cfg.get("template", "yaskawa_inform.j2")
            output = _render_template(template_name, context)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"Yaskawa INFORM exported: {file_path}")
            return True
        except Exception as e:
            print(f"Yaskawa INFORM export error: {e}")
            return False

    def export_ur_script(self, trajectory, file_path: str, config: dict = None) -> bool:
        """Export trajectory to Universal Robots URScript format. Uses Jinja2 template."""
        try:
            cfg = config or self._load_postprocessor_config("ur_script")
            speed_ms = float(cfg.get("default_speed_ms", 0.1))
            accel = float(cfg.get("default_accel", 1.2))
            prepared = _prepare_trajectory_points(trajectory)
            context = {
                "program_name": cfg.get("program_name", "KengaCAD_Trajectory"),
                "comment": cfg.get("comment", "# Generated by KengaCAD"),
                "tool_name": cfg.get("tool_name", "tool0"),
                "speed_ms": speed_ms,
                "accel": accel,
                "points": prepared,
            }
            template_name = cfg.get("template", "ur_script.j2")
            output = _render_template(template_name, context)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"UR Script exported: {file_path}")
            return True
        except Exception as e:
            print(f"UR Script export error: {e}")
            return False

    def import_robot_config(self, file_path: str) -> Optional[Dict]:
        """Import robot config from JSON file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if "joints" in config:
                return config
            print("Robot config missing 'joints'")
            return None
        except Exception as e:
            print(f"Robot config import error: {e}")
            return None

    def export_robot_config(self, joints_config: Dict, file_path: str) -> bool:
        """Export robot config to JSON file."""
        try:
            config = {
                "joints": joints_config,
                "created_by": "KengaCAD",
                "format_version": "1.0",
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            print(f"Robot config exported: {file_path}")
            return True
        except Exception as e:
            print(f"Robot config export error: {e}")
            return False

    def validate_file_path(self, file_path: str, extensions: List[str]) -> bool:
        """Validate file path extension."""
        if not file_path:
            return False
        _, ext = os.path.splitext(file_path.lower())
        return ext in extensions

    def get_supported_formats(self) -> Dict[str, str]:
        """Get supported formats."""
        return {
            "kengacad": "KengaCAD проект",
            "dxf": "AutoCAD DXF",
            "dwg": "AutoCAD DWG (требует ODA)",
            "pdf": "PDF",
            "json": "JSON (траектория)",
            "csv": "CSV (траектория, RoboCAD)",
            "krl": "KUKA KRL",
            "mod": "ABB RAPID",
            "ls": "Fanuc TP",
            "jbi": "Yaskawa INFORM",
            "script": "Universal Robots URScript",
        }


if __name__ == "__main__":
    importer = CADImportExport()
