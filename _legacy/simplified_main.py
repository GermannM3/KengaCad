"""
Упрощенная версия KengaCAD без зависимости от движка Kenga
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QStatusBar, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence

# Импорты UI компонентов
from ui.main_window import KengaCADMainWindow


class SimplifiedKengaCADApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        
        # Создаем главное окно
        self.window = KengaCADMainWindow()
        
        # Показываем предупреждение о необходимости движка
        self._show_engine_warning()
        
        self.window.show()
    
    def _show_engine_warning(self):
        """Показываем предупреждение о необходимости движка Kenga"""
        # Добавляем сообщение в статус бар
        self.window.statusBar().showMessage("ПРЕДУПРЕЖДЕНИЕ: Движок Kenga не подключен. 3D визуализация недоступна.")


def main():
    app = SimplifiedKengaCADApp(sys.argv)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()