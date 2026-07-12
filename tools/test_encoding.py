# -*- coding: utf-8 -*-
from pathlib import Path

samples = [
    'Jog: \ufffd\ufffd\ufffd \ufffd\ufffd\ufffd \ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd \ufffd 0.',
    '\ufffd \ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd \ufffd\ufffd\ufffd\ufffd\ufffd \ufffd',
]

path = Path(r"d:\KengaCAD\KengaCAD\MainWindow.xaml.cs")
text = path.read_text(encoding="utf-8")

# extract actual corrupted line
for line in text.splitlines():
    if 'Jog:' in line and 'AppendOutput' in line and 'deg' not in line:
        s = line.split('"')[1] if '"' in line else ''
        print('RAW:', repr(s))
        raw_bytes = s.encode('utf-8')
        print('UTF8 bytes:', raw_bytes)
        # try recover from cp1251 misread
        for enc in ('cp1251', 'cp866', 'latin1'):
            try:
                fixed = s.encode('cp1252', errors='replace').decode('utf-8')
                print('cp1252->utf8:', fixed)
            except Exception as e:
                print(enc, e)

# find line with mojibake only (no replacement char) 
for line in text.splitlines():
    if 'Workcell:' in line and 'AppendOutput' in line and '\ufffd' in line:
        import re
        m = re.search(r'"([^"]+)"', line)
        if m:
            s = m.group(1)
            print('Workcell line:', repr(s))
