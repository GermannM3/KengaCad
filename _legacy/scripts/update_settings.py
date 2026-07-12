# One-time script to add show_3d_window and robot.library to settings.json
import json
from pathlib import Path

p = Path(__file__).parent.parent / "config" / "settings.json"
with open(p, "r", encoding="utf-8") as f:
    s = json.load(f)
s.setdefault("engine", {})["show_3d_window"] = True
s.setdefault("robot", {})["library"] = [
    {"id": "demo", "name": "Demo", "path": "assets/robot.glb", "description": "Built-in 6DOF"},
    {"id": "custom", "name": "Custom", "path": "", "description": "Load glTF/GLB/OBJ"},
]
with open(p, "w", encoding="utf-8") as f:
    json.dump(s, f, ensure_ascii=False)
print("OK")
