import re
from pathlib import Path

path = Path(r"d:\KengaCAD\KengaCAD\MainWindow.xaml.cs")
text = path.read_text(encoding="utf-8", errors="replace")
lines = text.splitlines()
bad = []
for i, line in enumerate(lines, 1):
    if "\ufffd" in line:
        bad.append((i, line.strip()))
    elif re.search(r"[\u0400-\u04ff].*[\x80-\xff]", line) is None and re.search(r"[\u0080-\u00ff]{4,}", line):
        if '"' in line or "AppendOutput" in line or "StatusText" in line:
            bad.append((i, line.strip()))

print(f"Found {len(bad)} suspicious lines")
for i, line in bad[:120]:
    print(f"{i}: {line[:140]}")
