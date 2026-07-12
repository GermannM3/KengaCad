# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Сборка всех необходимых файлов и библиотек
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_dynamic_libs

# Собираем все подмодули PyQt6
hiddenimports = []
hiddenimports.extend(collect_submodules('PyQt6'))
hiddenimports.extend(collect_submodules('PyQt6.QtWidgets'))
hiddenimports.extend(collect_submodules('PyQt6.QtCore'))
hiddenimports.extend(collect_submodules('PyQt6.QtGui'))
hiddenimports.extend(collect_submodules('PyQt6.QtOpenGLWidgets'))

# Собираем подмодули других библиотек
hiddenimports.extend(collect_submodules('websockets'))
hiddenimports.extend(collect_submodules('ezdxf'))
hiddenimports.extend(collect_submodules('numpy'))

# Убираем дубликаты
hiddenimports = list(set(hiddenimports))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Включаем все файлы UI
        ('ui', 'ui'),
        # Включаем все файлы engine
        ('engine', 'engine'),
        # Включаем все файлы robot
        ('robot', 'robot'),
        # Включаем все файлы cad
        ('cad', 'cad'),
        # Включаем все файлы config
        ('config', 'config'),
        # Включаем все файлы examples
        ('examples', 'examples'),
        # Включаем все файлы assets
        ('assets', 'assets'),
        # Включаем файлы конфигурации
        ('requirements.txt', '.'),
        ('README.md', '.'),
    ] + collect_data_files('PyQt6') + collect_data_files('websockets') + collect_data_files('ezdxf'),
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Добавляем бинарные файлы, если есть
# a.binaries = a.binaries + Tree('./engine', prefix='engine', excludes=['*.py', '*.pyc', '*.pyo', '__pycache__', 'tests'])

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KengaCAD',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Используем оконный режим
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/logo.png' if Path('assets/logo.png').exists() else None,
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
