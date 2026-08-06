import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

if getattr(sys, "frozen", False):
    _base = sys._MEIPASS
    _plugin_path = os.path.join(_base, "PySide6", "plugins")
    if os.path.isdir(_plugin_path):
        os.environ.setdefault("QT_PLUGIN_PATH", _plugin_path)

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtGui import QFont

from ui.styles.theme import ThemeManager
import config


def _run_packaged_self_test() -> int:
    """Exercise packaged imports, Qt and a disposable database, then exit."""
    try:
        from db.manager import DatabaseManager
        DatabaseManager.init()
        import core.excel_export  # noqa: F401
        from core.invoice_gen import generate_invoice  # noqa: F401
        from ui.main import MainWindow  # noqa: F401
        from ui.windows.pos import POSPage  # noqa: F401
        from ui.windows.purchases import PurchasesPage  # noqa: F401
        if not os.path.isfile(config.DB_PATH):
            return 3
        return 0
    except Exception:
        import traceback
        error_text = traceback.format_exc()
        try:
            os.makedirs(config.DATA_DIR, exist_ok=True)
            with open(os.path.join(config.DATA_DIR, "self_test_error.log"), "w", encoding="utf-8") as log:
                log.write(error_text)
        except OSError:
            pass
        traceback.print_exc()
        return 2


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setStyle("Fusion")

    prefs = config.load_prefs()
    ThemeManager.load_from_prefs()
    app.setStyleSheet(ThemeManager.build_stylesheet())

    font_size = config.normalize_font_size(prefs.get("font_scale", 10))
    font = QFont("Segoe UI", font_size)
    app.setFont(font)

    if "--self-test" in sys.argv:
        return _run_packaged_self_test()

    if config.is_first_run():
        from ui.windows.setup_wizard import SetupWizard
        wizard = SetupWizard()
        result = wizard.exec()
        if result != QDialog.DialogCode.Accepted:
            sys.exit(0)

    try:
        from db.manager import DatabaseManager
        DatabaseManager.init()
    except Exception as db_err:
        QMessageBox.critical(
            None, "Database Error",
            f"Failed to initialise database:\n{db_err}\n\n"
            f"Data directory: {config.DATA_DIR}\n\n"
            "Please check disk space and permissions, then restart."
        )
        sys.exit(1)

    from ui.windows.login import LoginWindow
    login = LoginWindow()
    result = login.exec()

    if result == QDialog.DialogCode.Accepted:
        from ui.main import MainWindow
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    sys.exit(main())
