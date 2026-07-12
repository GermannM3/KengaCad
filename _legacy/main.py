"""
KengaCAD - CAD-программа для настройки траекторий роботов нанесения мастики
"""
import os
import sys
import traceback
os.environ.setdefault("QT_API", "pyqt5")

# Исправление пути к файлам pyqtribbon для PyInstaller
def _patch_pyqtribbon_datafile():
    """Переопределяем DataFile чтобы pyqtribbon находил стили в сборке."""
    try:
        import pyqtribbon
        import pyqtribbon.ribbonbar as ribbonbar_module
        from pathlib import Path
        import os
        
        # Сохраняем оригинальную функцию
        _original_datafile = ribbonbar_module.DataFile
        
        # Получаем путь к _internal в сборке
        if getattr(sys, 'frozen', False):
            internal_path = Path(sys.executable).parent / "_internal" / "pyqtribbon"
        else:
            # В режиме разработки используем обычный путь
            internal_path = Path(ribbonbar_module.__file__).parent
        
        def patched_datafile(filename):
            """Версия DataFile для сборки PyInstaller."""
            # Для стилей всегда используем путь в _internal
            if filename.startswith("styles/"):
                style_name = filename[7:]  # убираем "styles/"
                style_path = internal_path / "styles" / style_name
                if style_path.exists():
                    return str(style_path)
            # Для остальных файлов - оригинальный путь
            return _original_datafile(filename)
        
        ribbonbar_module.DataFile = patched_datafile
        print(f"[INFO] pyqtribbon DataFile patched. Styles path: {internal_path / 'styles'}")
    except Exception as e:
        print(f"[WARN] Could not patch pyqtribbon DataFile: {e}")

_patch_pyqtribbon_datafile()

import asyncio
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon
from ui.main_window import KengaCADMainWindow
from kengacad_app import KengaCADApp

def _kengacad_excepthook(exctype, value, tb):
    """Обработчик необработанных исключений — диалог закрывается, приложение завершается."""
    import os
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

        # Запускаем асинхронную инициализацию
        asyncio.run(init_app())

    def get_app(self):
        """Получение экземпляра приложения"""
        return self.app


def main():
    # Применить путь ODA из настроек до любых DWG-операций
    try:
        from cad.dwg_setup import get_odafc_path_from_config, apply_odafc_path
        path = get_odafc_path_from_config()
        if path:
            apply_odafc_path(path)
    except Exception:
        pass

    # Проверка обновлений при запуске (когда check_on_startup и check_url будут настроены)
    try:
        from updates import should_check_on_startup, check_for_updates
        if should_check_on_startup():
            found, new_ver, url = check_for_updates()
            # TODO: при наличии обновления — показать уведомление после загрузки окна
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
    window = KengaCADMainWindow(app_thread)
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