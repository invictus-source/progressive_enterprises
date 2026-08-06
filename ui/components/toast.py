from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGraphicsOpacityEffect
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property, QPoint
from PySide6.QtGui import QColor

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False


class ToastManager:
    _instance = None
    _container = None
    
    @classmethod
    def set_container(cls, container: QWidget):
        cls._container = container
    
    @classmethod
    def show(cls, message: str, level: str = "info", duration: int = 4000):
        if cls._container is None:
            print(f"[Toast] No container set, fallback to print: {message}")
            return
        toast = Toast(message, level, duration, cls._container)
        toast.show_toast()


class Toast(QFrame):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    STYLES = {
        "dark": {
            "info": {"bg": "#1E3A5F", "border": "#3B82F6", "text": "#93C5FD"},
            "success": {"bg": "#064E3B", "border": "#10B981", "text": "#6EE7B7"},
            "warning": {"bg": "#78350F", "border": "#F59E0B", "text": "#FCD34D"},
            "error": {"bg": "#7F1D1D", "border": "#EF4444", "text": "#FCA5A5"},
        },
        "light": {
            "info": {"bg": "#DBEAFE", "border": "#3B82F6", "text": "#1E40AF"},
            "success": {"bg": "#D1FAE5", "border": "#10B981", "text": "#065F46"},
            "warning": {"bg": "#FEF3C7", "border": "#F59E0B", "text": "#92400E"},
            "error": {"bg": "#FEE2E2", "border": "#EF4444", "text": "#991B1B"},
        }
    }
    
    ICONS = {
        "info": "mdi.information-outline",
        "success": "mdi.check-circle-outline",
        "warning": "mdi.alert-outline",
        "error": "mdi.alert-circle-outline",
    }
    
    def __init__(self, message: str, level: str = "info", duration: int = 4000, parent=None):
        super().__init__(parent)
        self._duration = duration
        self._level = level
        self._build_ui(message)
        
    def _build_ui(self, message: str):
        self.setObjectName("Toast")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        
        from ui.styles.theme import ThemeManager
        theme = "dark" if ThemeManager.is_dark() else "light"
        style = self.STYLES[theme].get(self._level, self.STYLES[theme]["info"])
        
        self.setStyleSheet(f"""
            QFrame#Toast {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-radius: 10px;
                padding: 4px;
            }}
            QLabel {{
                color: {style['text']};
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {style['text']};
                padding: 4px;
                border-radius: 4px;
                min-width: 24px;
                min-height: 24px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.1);
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)
        
        icon_lbl = QLabel()
        if HAS_QTA:
            try:
                icon = qta.icon(self.ICONS.get(self._level, self.ICONS["info"]), color=style['text'], scale_factor=1.2)
                icon_lbl.setPixmap(icon.pixmap(20, 20))
            except Exception:
                icon_lbl.setText("●")
                icon_lbl.setStyleSheet(f"color: {style['text']}; font-size: 12px;")
        else:
            icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
            icon_lbl.setText(icons.get(self._level, "ℹ"))
        layout.addWidget(icon_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(msg_lbl, 1)
        
        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.clicked.connect(self.hide_toast)
        layout.addWidget(close_btn)
        
        self.setFixedWidth(380)
        self.adjustSize()
        
    def show_toast(self):
        if self.parent() is None:
            return

        parent = self.parent()
        self._parent = parent

        # Toasts are overlays. Installing another layout on a page that already
        # owns one causes Qt warnings and can disturb the page geometry.
        visible_toasts = [
            child for child in parent.children()
            if isinstance(child, Toast) and child is not self and child.isVisible()
        ]
        self.adjustSize()
        x = max(12, parent.width() - self.width() - 16)
        y = 16 + sum(child.height() + 8 for child in visible_toasts)
        self.move(x, y)
        self.raise_()
        self.show()
        
        self.opacity = QGraphicsOpacityEffect(self)
        self.opacity.setOpacity(0.0)
        self.setGraphicsEffect(self.opacity)
        
        QTimer.singleShot(50, self._fade_in)
        
        if self._duration > 0:
            QTimer.singleShot(self._duration, self.hide_toast)
    
    def _fade_in(self):
        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(0.0)
        self.anim.setEndValue(1.0)
        self.anim.start()
    
    def hide_toast(self):
        self.anim_out = QPropertyAnimation(self.opacity, b"opacity")
        self.anim_out.setDuration(150)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self._remove_self)
        self.anim_out.start()
    
    def _remove_self(self):
        self.deleteLater()
        
    @staticmethod
    def info(parent, message: str, duration: int = 4000):
        return Toast(message, Toast.INFO, duration, parent)
    
    @staticmethod
    def success(parent, message: str, duration: int = 4000):
        return Toast(message, Toast.SUCCESS, duration, parent)
    
    @staticmethod
    def warning(parent, message: str, duration: int = 5000):
        return Toast(message, Toast.WARNING, duration, parent)
    
    @staticmethod
    def error(parent, message: str, duration: int = 6000):
        return Toast(message, Toast.ERROR, duration, parent)


class InlineMessage(QFrame):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    
    def __init__(self, message: str, level: str = "info", parent=None, closable: bool = True):
        super().__init__(parent)
        self._level = level
        self._build_ui(message, closable)
        
    def _build_ui(self, message: str, closable: bool):
        from ui.styles.theme import ThemeManager
        theme = "dark" if ThemeManager.is_dark() else "light"
        style = Toast.STYLES[theme].get(self._level, Toast.STYLES[theme]["info"])
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {style['bg']};
                border: 1px solid {style['border']};
                border-radius: 8px;
                padding: 2px;
            }}
            QLabel {{
                color: {style['text']};
                background: transparent;
            }}
            QPushButton {{
                background: transparent;
                border: none;
                color: {style['text']};
                padding: 2px;
                min-width: 20px;
                min-height: 20px;
            }}
            QPushButton:hover {{
                background: rgba(255,255,255,0.15);
                border-radius: 4px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        icons = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}
        icon_lbl = QLabel(icons.get(self._level, "ℹ"))
        icon_lbl.setStyleSheet("font-size: 14px;")
        layout.addWidget(icon_lbl)
        
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        layout.addWidget(msg_lbl, 1)
        
        if closable:
            close_btn = QPushButton("×")
            close_btn.setFixedSize(20, 20)
            close_btn.clicked.connect(self.hide)
            layout.addWidget(close_btn)
    
    @staticmethod
    def create_info(message: str, parent=None, closable: bool = True):
        return InlineMessage(message, InlineMessage.INFO, parent, closable)
    
    @staticmethod
    def create_success(message: str, parent=None, closable: bool = True):
        return InlineMessage(message, InlineMessage.SUCCESS, parent, closable)
    
    @staticmethod
    def create_warning(message: str, parent=None, closable: bool = True):
        return InlineMessage(message, InlineMessage.WARNING, parent, closable)
    
    @staticmethod
    def create_error(message: str, parent=None, closable: bool = True):
        return InlineMessage(message, InlineMessage.ERROR, parent, closable)


def show_toast(widget: QWidget, message: str, level: str = "info", duration: int = 4000):
    Toast(message, level, duration, widget).show_toast()


def show_success(widget: QWidget, message: str, duration: int = 4000):
    show_toast(widget, message, Toast.SUCCESS, duration)


def show_warning(widget: QWidget, message: str, duration: int = 5000):
    show_toast(widget, message, Toast.WARNING, duration)


def show_error(widget: QWidget, message: str, duration: int = 6000):
    show_toast(widget, message, Toast.ERROR, duration)
