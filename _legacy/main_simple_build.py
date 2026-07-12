"""
KengaCAD - CAD-программа для настройки траекторий роботов нанесения мастики
Упрощённая версия для сборки (без pyqtribbon)
"""
import os
import sys
import traceback
os.environ.setdefault("QT_API", "pyqt5")
import asyncio
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QIcon, QPixmap
from ui.main_window_simple import KengaCADMainWindowSimple
from kengacad_app import KengaCADApp

def _kengacad_excepthook(exctype, value, tb):
    """Обработчик необработанных исключений."""
    msg = "".join(traceback.format_exception(exctype, value, tb))
    print(msg, file=sys.stderr, flush=True)
    app = QApplication.instance()
    if app:
        try:
            box = QMessageBox()
            box.setIcon(QMessageBox.Critical)
            box.setWindowTitle("Ошибка")
            box.setText(f"Произошла ошибка:\n{exctype.__name__}: {value}")
            box.setInformativeText("Приложение будет закрыто. Подробности в консоли.")
            box.setDetailedText(msg)
            box.setStandardButtons(QMessageBox.Ok)
            box.setWindowFlags(box.windowFlags() | Qt.WindowStaysOnTopHint)
            box.exec_()
        except Exception:
            pass
    os._exit(1)


def _assets_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "_internal" / "assets"
    return Path(__file__).resolve().parent / "assets"


class KengaCADAppThread(QThread):
    """Поток для запуска асинхронного приложения KengaCAD"""
    app_initialized = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.app = None

    def run(self):
        """Запуск асинхронного приложения"""
        async def init_app():
            self.app = KengaCADApp()
            success = await self.app.initialize()
            self.app_initialized.emit(success)
            return self.app

        asyncio.run(init_app())

    def get_app(self):
        """Получение экземпляра приложения"""
        return self.app


def main():
    # Применить путь ODA из настроек
    try:
        from cad.dwg_setup import get_odafc_path_from_config, apply_odafc_path
        path = get_odafc_path_from_config()
        if path:
            apply_odafc_path(path)
    except Exception:
        pass

    app = QApplication(sys.argv)
    sys.excepthook = _kengacad_excepthook

    assets = _assets_dir()
    for name in ("logo.ico", "logo.png"):
        icon_path = assets / name
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break

    # Заставка при запуске
    splash = None
    for name in ("logo.png", "logo.ico"):
        logo_path = assets / name
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            if not pixmap.isNull():
                size = min(400, max(pixmap.width(), pixmap.height()))
                scaled = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                splash = QSplashScreen(scaled)
                splash.setMask(scaled.mask())
                splash.show()
                splash.showMessage("  KengaCAD — загрузка...", Qt.AlignBottom | Qt.AlignHCenter)
                app.processEvents()
            break

    # Создаем и запускаем поток для асинхронного приложения
    app_thread = KengaCADAppThread()
    window = KengaCADMainWindowSimple(app_thread)
    app_thread.app_initialized.connect(lambda success: window.on_app_initialized(success, app_thread))

    def _finish_splash():
        if splash:
            splash.finish(window)

    app_thread.app_initialized.connect(lambda _: _finish_splash())
    app_thread.start()

    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
