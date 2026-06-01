"""
Progressive Enterprises – Application Entry Point
"""

import sys
import os

# Ensure project root is in path (needed as .exe)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── DPI Scaling (must be set before QApplication) ─────────────────────────
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")

# ── Qt Plugin Path (frozen .exe via PyInstaller) ───────────────────────────
if getattr(sys, "frozen", False):
    # _MEIPASS is the unpacked _internal folder; tell Qt where plugins live
    _base = sys._MEIPASS
    _plugin_path = os.path.join(_base, "PySide6", "plugins")
    if os.path.isdir(_plugin_path):
        os.environ.setdefault("QT_PLUGIN_PATH", _plugin_path)

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
from PySide6.QtGui import QFont

from ui.styles.theme import ThemeManager
import config


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(config.APP_NAME)
    app.setApplicationVersion(config.APP_VERSION)
    app.setStyle("Fusion")

    # Load saved preferences (theme, font scale)
    prefs = config.load_prefs()
    ThemeManager.load_from_prefs()
    app.setStyleSheet(ThemeManager.build_stylesheet())

    # Restore font size
    font_size = prefs.get("font_scale", 10)
    try:
        font_size = int(font_size)
    except (ValueError, TypeError):
        font_size = 10
    font = QFont("Segoe UI", max(9, min(font_size, 18)))
    app.setFont(font)

    # ── First-run Setup Wizard ─────────────────────────────────────────────
    if config.is_first_run():
        from ui.windows.setup_wizard import SetupWizard
        wizard = SetupWizard()
        result = wizard.exec()
        if result != QDialog.DialogCode.Accepted:
            sys.exit(0)  # User cancelled setup – exit cleanly

    # ── Initialise Database ────────────────────────────────────────────────
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

    # ── Login Window ───────────────────────────────────────────────────────
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
    main()