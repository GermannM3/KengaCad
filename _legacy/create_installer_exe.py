"""
Создание установщика KengaCAD с помощью PyInstaller
"""
import os
import sys
import subprocess
from pathlib import Path


def create_installer():
    """Создание исполняемого установщика"""
    print("Создание установщика KengaCAD...")
    
    # Проверяем, установлен ли PyInstaller
    try:
        import PyInstaller
        print("PyInstaller установлен")
    except ImportError:
        print("Установка PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Создаем установщик
    installer_spec = '''
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['simple_installer.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('dist/KengaCAD.exe', '.'),
        ('config', 'config'),
        ('assets', 'assets'),
        ('ui', 'ui'),
        ('engine', 'engine'),
        ('robot', 'robot'),
        ('cad', 'cad'),
        ('examples', 'examples'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='KengaCAD_Installer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Используем консоль для отображения процесса установки
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
'''
    
    # Записываем spec файл
    with open("KengaCAD_Installer.spec", 'w', encoding='utf-8') as f:
        f.write(installer_spec)
    
    print("Файл спецификации создан: KengaCAD_Installer.spec")
    
    # Запускаем PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--clean",
        "KengaCAD_Installer.spec"
    ]
    
    print("Запуск PyInstaller для создания установщика...")
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("Установщик успешно создан!")
        print("Файл установщика находится в папке dist/: KengaCAD_Installer.exe")
        return True
    else:
        print("Ошибка при создании установщика")
        return False


def main():
    success = create_installer()
    if success:
        print("\nУстановщик готов к использованию!")
        print("Найдите его в папке dist/KengaCAD_Installer.exe")
    else:
        print("\nОшибка при создании установщика")
        sys.exit(1)


if __name__ == "__main__":
    main()