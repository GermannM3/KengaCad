"""
Упрощенная версия KengaCAD без зависимости от движка Kenga
"""
import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QStatusBar, QMenuBar, QToolBar, QLabel, QFileDialog, 
                             QMessageBox, QScrollArea, QGroupBox, QHBoxLayout)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence, QIcon

from ui.ribbon_bar import KengaCADRibbonBar
from ui.command_line import CommandLine
from ui.drawing_area import DrawingArea


class KengaCADMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KengaCAD - Программа для настройки траекторий роботов")
        self.setGeometry(100, 100, 1400, 900)

        # Установка иконки окна
        self._set_window_icon()

        # Инициализация UI
        self._setup_ui()

        # Статус бар
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("ПРЕДУПРЕЖДЕНИЕ: Движок Kenga не подключен. 3D визуализация недоступна.")
        
        # Показываем предупреждение пользователю
        self._show_engine_warning()
    
    def _show_engine_warning(self):
        """Показ предупреждения о необходимости движка Kenga"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Information)
        msg.setWindowTitle("Информация")
        msg.setText("Для полной функциональности KengaCAD требуется движок Kenga.")
        msg.setInformativeText(
            "Текущий режим: упрощенная версия без 3D визуализации.\n" +
            "Для полноценной работы:\n" +
            "1. Установите движок Kenga отдельно\n" +
            "2. Запустите его перед использованием KengaCAD\n" +
            "3. Убедитесь, что команда 'kenga' доступна в PATH"
        )
        msg.exec()
    
    def _set_window_icon(self):
        """Установка иконки окна"""
        try:
            from PyQt6.QtGui import QPixmap, QIcon
            import os
            logo_path = os.path.join("assets", "logo.png")
            if os.path.exists(logo_path):
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    self.setWindowIcon(QIcon(pixmap))
        except Exception as e:
            print(f"Не удалось загрузить иконку: {e}")

    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        # Создание меню
        self._create_menu()

        # Создание Ribbon бара (аналог AutoCAD Ribbon)
        self.ribbon = KengaCADRibbonBar(self)
        self.setMenuWidget(self.ribbon)

        # Центральная область - область рисования
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Область рисования (2D предпросмотр в упрощенной версии)
        self.drawing_area = DrawingArea()
        self.layout.addWidget(self.drawing_area)

        # Командная строка (как в AutoCAD)
        self.command_line = CommandLine()
        self.command_line.returnPressed.connect(self._execute_command)
        self.layout.addWidget(self.command_line)

    def _create_menu(self):
        """Создание меню приложения"""
        menubar = self.menuBar()

        # Меню Файл
        file_menu = menubar.addMenu('Файл')

        new_action = QAction('Новый', self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_file)
        file_menu.addAction(new_action)

        open_action = QAction('Открыть', self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        save_action = QAction('Сохранить', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_file)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        exit_action = QAction('Выход', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню Правка
        edit_menu = menubar.addMenu('Правка')

        undo_action = QAction('Отменить', self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction('Повторить', self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._redo)
        edit_menu.addAction(redo_action)

    def _new_file(self):
        """Создать новый файл"""
        self.statusBar().showMessage("Создание нового файла...")

    def _open_file(self):
        """Открыть файл"""
        fname, _ = QFileDialog.getOpenFileName(self, 'Открыть файл', '',
                                              'CAD файлы (*.dxf *.json);;Все файлы (*)')
        if fname:
            self.statusBar().showMessage(f"Открыт файл: {fname}")

    def _save_file(self):
        """Сохранить файл"""
        fname, _ = QFileDialog.getSaveFileName(self, 'Сохранить файл', '',
                                              'CAD файлы (*.dxf *.json);;Все файлы (*)')
        if fname:
            self.statusBar().showMessage(f"Сохранен файл: {fname}")

    def _undo(self):
        """Отменить действие"""
        self.statusBar().showMessage("Отмена последнего действия")

    def _redo(self):
        """Повторить действие"""
        self.statusBar().showMessage("Повтор последнего действия")

    def _execute_command(self):
        """Выполнить команду из командной строки"""
        cmd = self.command_line.text().strip()
        if cmd:
            self.statusBar().showMessage(f"Выполнено: {cmd}")
            self.command_line.clear()

            # Парсинг команды
            self._parse_command(cmd)

    def _parse_command(self, cmd):
        """Разбор и выполнение команды"""
        parts = cmd.split()
        if not parts:
            return

        command = parts[0].upper()

        if command == "LINE":
            self.statusBar().showMessage("Создание линии...")
            # TODO: Реализовать создание линии
        elif command == "CIRCLE":
            self.statusBar().showMessage("Создание окружности...")
            # TODO: Реализовать создание окружности
        elif command == "POINT":
            self.statusBar().showMessage("Создание точки...")
            # TODO: Реализовать создание точки
        elif command == "MOVE":
            self.statusBar().showMessage("Перемещение объекта...")
            # TODO: Реализовать перемещение объекта
        elif command == "ROTATE":
            self.statusBar().showMessage("Поворот объекта...")
            # TODO: Реализовать поворот объекта
        elif command == "TRAJECTORY":
            self.statusBar().showMessage("Создание траектории...")
            # TODO: Реализовать создание траектории
        elif command == "SIMULATE":
            self.statusBar().showMessage("Запуск симуляции...")
            # В упрощенной версии показываем сообщение
            QMessageBox.information(self, "Симуляция", 
                                  "Для запуска симуляции требуется движок Kenga.\n" +
                                  "Установите движок Kenga и перезапустите приложение.")
        elif command == "LOAD_ROBOT":
            self.statusBar().showMessage("Загрузка модели робота...")
            # В упрощенной версии показываем сообщение
            QMessageBox.information(self, "Загрузка робота", 
                                  "Для загрузки модели робота требуется движок Kenga.\n" +
                                  "Установите движок Kenga и перезапустите приложение.")
        elif command == "SET_JOINT":
            self.statusBar().showMessage("Установка угла сустава...")
            # TODO: Реализовать установку угла сустава
        elif command == "CAMERA":
            self.statusBar().showMessage("Управление камерой...")
            # TODO: Реализовать управление камерой
        elif command == "HELP":
            self._show_help()
        else:
            self.statusBar().showMessage(f"Неизвестная команда: {command}")

    def _show_help(self):
        """Показать справку по командам"""
        help_text = """
Доступные команды:
LINE - создание линии
CIRCLE - создание окружности
POINT - создание точки
MOVE - перемещение объекта
ROTATE - поворот объекта
TRAJECTORY - создание траектории
SIMULATE - запуск симуляции (требует движок Kenga)
LOAD_ROBOT - загрузка модели робота (требует движок Kenga)
SET_JOINT - установка угла сустава
CAMERA - управление камерой
HELP - показать эту справку
        """
        QMessageBox.information(self, "Справка", help_text)


def main():
    app = QApplication(sys.argv)
    try:
        window = KengaCADMainWindow()
        window.show()
        print("KengaCAD успешно запущен (упрощенная версия)")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Ошибка запуска KengaCAD: {e}")
        # Показываем сообщение об ошибке
        from PyQt6.QtWidgets import QMessageBox
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle("Ошибка запуска")
        msg_box.setText(f"Произошла ошибка при запуске KengaCAD: {str(e)}")
        msg_box.setInformativeText("Проверьте, что все зависимости установлены.")
        msg_box.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()