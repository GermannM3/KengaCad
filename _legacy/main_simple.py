"""
KengaCAD - CAD-программа для настройки траекторий роботов (упрощенная версия)
"""
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from ui.main_window import KengaCADMainWindow


def main():
    app = QApplication(sys.argv)
    try:
        window = KengaCADMainWindow()  # Запускаем без app_thread для упрощенной версии
        window.show()
        print("KengaCAD успешно запущен (упрощенная версия)")
        sys.exit(app.exec())
    except Exception as e:
        print(f"Ошибка запуска KengaCAD: {e}")
        # Показываем сообщение об ошибке
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.setWindowTitle("Ошибка запуска")
        msg_box.setText(f"Произошла ошибка при запуске KengaCAD: {str(e)}")
        msg_box.setInformativeText("Приложение запущено в упрощенном режиме без подключения к движку Kenga.")
        msg_box.exec()
        sys.exit(1)


if __name__ == "__main__":
    main()