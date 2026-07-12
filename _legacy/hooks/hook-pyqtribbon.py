"""
PyInstaller hook for pyqtribbon - собираем все файлы
"""
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Собираем все подмодули
hiddenimports = collect_submodules('pyqtribbon')

# Собираем все файлы данных
datas = collect_data_files('pyqtribbon', include_py_files=False)
