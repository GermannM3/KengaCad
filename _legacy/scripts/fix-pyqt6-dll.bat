@echo off
echo Reinstalling PyQt6...
pip uninstall PyQt6 PyQt6-Qt6 PyQt6-sip -y
pip install --no-cache-dir PyQt6==6.6.1
echo.
echo Testing...
python -c "from PyQt6.QtWidgets import QApplication; print('OK: PyQt6 loaded')"
if errorlevel 1 (
    echo.
    echo If error persists, install VC++ Redistributable: https://aka.ms/vs/17/release/vc_redist.x64.exe
)
