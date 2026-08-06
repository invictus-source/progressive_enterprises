"""Small, dependency-free helpers for screen-safe desktop layouts."""

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog


def available_geometry(widget=None):
    screen = widget.screen() if widget is not None and widget.screen() else QApplication.primaryScreen()
    return screen.availableGeometry() if screen else None


def fit_dialog_to_screen(
    dialog: QDialog,
    preferred_width: int,
    preferred_height: int,
    *,
    minimum_width: int = 360,
    minimum_height: int = 280,
):
    """Fit a dialog inside the usable screen without creating impossible minima."""
    geometry = available_geometry(dialog)
    if not geometry:
        dialog.resize(preferred_width, preferred_height)
        return

    max_width = max(320, int(geometry.width() * 0.96))
    max_height = max(260, int(geometry.height() * 0.94))
    width = min(preferred_width, max_width)
    height = min(preferred_height, max_height)
    dialog.setMinimumSize(min(minimum_width, width), min(minimum_height, height))
    dialog.setMaximumSize(max_width, max_height)
    dialog.resize(width, height)


def refit_after_show(dialog: QDialog, *args, **kwargs):
    """Re-fit once Qt knows which monitor owns the window."""
    QTimer.singleShot(0, lambda: fit_dialog_to_screen(dialog, *args, **kwargs))
