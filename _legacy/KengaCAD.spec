# -*- mode: python ; coding: utf-8 -*-
"""
KengaCAD PyInstaller Spec File
Сборка полноценного исполняемого файла KengaCAD
"""

block_cipher = None

# Список всех модулей для включения
hidden_imports = [
    'PyQt5',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PyQt5.QtPrintSupport',
    'pyqtribbon',
    'pyqtribbon.ribbonbar',
    'pyqtribbon.panel',
    'pyqtribbon.styles',
    'websockets',
    'ezdxf',
    'ezdxf.lldxf',
    'ezdxf.addons',
    'numpy',
    'numpy.linalg',
    'PIL',
    'PIL.Image',
]

# Данные для включения в сборку
datas = [
    ('config', 'config'),
    ('assets', 'assets'),
    ('scripts', 'scripts'),
    ('cad', 'cad'),
    ('ui', 'ui'),
    ('robot', 'robot'),
    ('engine', 'engine'),
]

a = Analysis(
    ['main.py'],
    pathex=['d:\\KengaCAD\\hooks'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=['d:\\KengaCAD\\hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'tkinter',
        'jupyter',
        'notebook',
        'IPython',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='KengaCAD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='KengaCAD',
)
