"""
Progressive Enterprises – Premium Login Window
Frameless, fullscreen-capable, animated login with theme support.
"""

import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QWidget, QSizePolicy, QApplication
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PySide6.QtGui import QPixmap, QFont, QColor, QPainter, QLinearGradient, QBrush, QKeySequence, QShortcut, QAction

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

from core.auth import AuthSession
from ui.styles.theme import ThemeManager
import config


class LoginWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(config.APP_NAME)
        self.setMinimumSize(420, 540)
        self.resize(520, 640)
        self.setModal(True)
        self._drag_pos = None
        self._is_maximized = config.load_prefs().get("login_maximized", True)

        # No system frame – we draw our own
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowSystemMenuHint |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        self.field_labels = [] # To track labels for theme updates

        self._build_ui()
        self._apply_theme()

        # Register to listen for live theme changes
        ThemeManager.register_callback(self._apply_theme)

        # Keyboard shortcuts
        QShortcut(QKeySequence("F11"), self).activated.connect(self._toggle_fullscreen)

        # Always open maximized so it never appears as a tiny window
        if self._is_maximized:
            QTimer.singleShot(0, self.showMaximized)
        else:
            self._center_on_screen()

    def _center_on_screen(self):
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.center().x() - self.width() // 2,
            screen.center().y() - self.height() // 2
        )

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Custom title bar ───────────────────────────────────────────────
        self.title_bar = QWidget()
        self.title_bar.setFixedHeight(40)
        self.title_bar.mousePressEvent   = self._tb_press
        self.title_bar.mouseMoveEvent    = self._tb_move
        self.title_bar.mouseDoubleClickEvent = lambda e: self._toggle_fullscreen()

        tb = QHBoxLayout(self.title_bar)
        tb.setContentsMargins(14, 0, 8, 0)

        self.title_lbl = QLabel(config.APP_NAME)
        tb.addWidget(self.title_lbl)
        tb.addStretch()

        # Theme toggle
        self.theme_btn = QPushButton()
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setToolTip("Toggle Light/Dark Theme")
        self.theme_btn.clicked.connect(ThemeManager.toggle)
        tb.addWidget(self.theme_btn)

        # Maximize toggle
        self.fs_btn = QPushButton()
        self.fs_btn.setFixedSize(32, 32)
        self.fs_btn.setToolTip("Toggle Maximize (F11)")
        if not HAS_QTA: self.fs_btn.setText("🗖")
        self.fs_btn.clicked.connect(self._toggle_fullscreen)
        tb.addWidget(self.fs_btn)

        # Min / Close
        self.min_btn = QPushButton()
        self.min_btn.setFixedSize(32, 32)
        if not HAS_QTA: self.min_btn.setText("—")
        self.min_btn.clicked.connect(self.showMinimized)
        tb.addWidget(self.min_btn)

        self.close_btn = QPushButton()
        self.close_btn.setFixedSize(32, 32)
        if not HAS_QTA: self.close_btn.setText("✕")
        self.close_btn.clicked.connect(self.reject)
        tb.addWidget(self.close_btn)

        root.addWidget(self.title_bar)

        # ── Login Card ─────────────────────────────────────────────────────
        self.outer = QWidget()
        outer_layout = QVBoxLayout(self.outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # SAVED AS SELF SO WE CAN STYLE IT IN _apply_theme
        self.card = QFrame()
        self.card.setFixedWidth(400)
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(18)

        # Logo / Brand
        brand_row = QHBoxLayout()
        brand_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(config.LOGO_PATH):
            px = QPixmap(config.LOGO_PATH).scaled(
                56, 56, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("🏪")
            logo_lbl.setStyleSheet("font-size: 48px; background: transparent;")
        brand_row.addWidget(logo_lbl)
        card_layout.addLayout(brand_row)

        self.app_name = QLabel(config.APP_NAME)
        self.app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.app_name)

        self.version_lbl = QLabel(f"Version {config.APP_VERSION}")
        self.version_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.version_lbl)

        # Divider
        self.div = QFrame()
        self.div.setFrameShape(QFrame.Shape.HLine)
        card_layout.addWidget(self.div)

        # Sign in label
        self.sign_in = QLabel("Sign In")
        card_layout.addWidget(self.sign_in)

        # Username field
        user_lbl = QLabel("USERNAME")
        self.field_labels.append(user_lbl)
        card_layout.addWidget(user_lbl)

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        self.username_input.setFixedHeight(42)
        if HAS_QTA:
            self.user_action = self.username_input.addAction(
                qta.icon("mdi.account-outline"), QLineEdit.ActionPosition.LeadingPosition
            )
        card_layout.addWidget(self.username_input)

        # Password field
        pwd_lbl = QLabel("PASSWORD")
        self.field_labels.append(pwd_lbl)
        card_layout.addWidget(pwd_lbl)

        pwd_row = QHBoxLayout(); pwd_row.setSpacing(6)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Enter password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(42)
        self.password_input.returnPressed.connect(self._do_login)
        if HAS_QTA:
            self.pwd_action = self.password_input.addAction(
                qta.icon("mdi.lock-outline"), QLineEdit.ActionPosition.LeadingPosition
            )

        self.show_pwd_btn = QPushButton()
        self.show_pwd_btn.setFixedSize(42, 42)
        self.show_pwd_btn.setCheckable(True)
        self.show_pwd_btn.toggled.connect(self._toggle_pwd)
        if not HAS_QTA: self.show_pwd_btn.setText("👁")

        pwd_row.addWidget(self.password_input)
        pwd_row.addWidget(self.show_pwd_btn)
        card_layout.addLayout(pwd_row)

        # Error label
        self.error_lbl = QLabel("")
        self.error_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_lbl.setWordWrap(True)
        card_layout.addWidget(self.error_lbl)

        # Login button
        self.login_btn = QPushButton("Sign In")
        self.login_btn.setFixedHeight(44)
        self.login_btn.clicked.connect(self._do_login)
        card_layout.addWidget(self.login_btn)

        # Footer
        self.footer_lbl = QLabel(f"© 2026 {config.APP_NAME}  •  v{config.APP_VERSION}\nDeveloped by {config.DEVELOPER_COMPANY}")
        self.footer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.footer_lbl.setWordWrap(True)
        card_layout.addWidget(self.footer_lbl)

        outer_layout.addWidget(self.card)
        root.addWidget(self.outer, 1)

    def _apply_theme(self):
        T = ThemeManager.tokens()
        dk = ThemeManager.is_dark()

        # 1. Base Layouts (Background and Card)
        self.setStyleSheet(f"QDialog {{ background-color: {T['bg_base']}; }}")
        self.outer.setStyleSheet(f"background-color: {T['bg_base']};")

        self.card.setStyleSheet(f"""
            QFrame {{
                background-color: {T['bg_surface']};
                border: 1px solid {T['border']};
                border-radius: 14px;
            }}
        """)

        # 2. Text Elements (Guaranteed Visibility)
        self.title_lbl.setStyleSheet(f"color: {T['text_muted']}; font-weight: 700; font-size: 12px; border: none; background: transparent;")
        self.app_name.setStyleSheet(f"color: {T['text_primary']}; font-weight: 800; font-size: 18px; border: none; background: transparent;")
        self.version_lbl.setStyleSheet(f"color: {T['text_muted']}; font-size: 11px; border: none; background: transparent;")
        self.sign_in.setStyleSheet(f"color: {T['text_primary']}; font-weight: 800; font-size: 15px; border: none; background: transparent;")
        self.footer_lbl.setStyleSheet(f"color: {T['text_muted']}; font-size: 10px; border: none; background: transparent;")
        self.div.setStyleSheet(f"background-color: {T['border']}; max-height: 1px;")
        self.error_lbl.setStyleSheet(f"color: {T['danger']}; font-size: 12px; font-weight: 700; border: none; background: transparent;")

        for lbl in self.field_labels:
            lbl.setStyleSheet(f"color: {T['text_secondary']}; font-weight: 700; font-size: 11px; letter-spacing: 0.5px; border: none; background: transparent;")

        # 3. Inputs
        input_style = f"""
            QLineEdit {{
                background-color: {T['bg_input']};
                border: 1.5px solid {T['border_strong']};
                border-radius: 8px;
                padding: 10px;
                color: {T['text_primary']};
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 2px solid {T['accent']};
            }}
        """
        self.username_input.setStyleSheet(input_style)
        self.password_input.setStyleSheet(input_style)

        # 4. Buttons (Bulletproof Explicit Styling)
        btn_style = f"""
            QPushButton {{
                background-color: {T['accent']};
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {T['accent_hover']};
            }}
        """
        self.login_btn.setStyleSheet(btn_style)

        icon_btn_style = f"""
            QPushButton {{
                background-color: {T['bg_elevated']};
                border: 1px solid {T['border']};
                border-radius: 8px;
            }}
            QPushButton:hover {{
                border: 1px solid {T['accent']};
            }}
        """
        self.show_pwd_btn.setStyleSheet(icon_btn_style)

        tb_btn_style = f"""
            QPushButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {T['bg_elevated']};
            }}
        """
        self.theme_btn.setStyleSheet(tb_btn_style)
        self.fs_btn.setStyleSheet(tb_btn_style)
        self.min_btn.setStyleSheet(tb_btn_style)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{ background: transparent; border: none; border-radius: 4px; }}
            QPushButton:hover {{ background-color: {T['danger']}; color: #FFFFFF; }}
        """)

        # 5. Icons
        if HAS_QTA:
            icon_color = T['text_muted']
            self.theme_btn.setIcon(qta.icon("mdi.weather-sunny" if dk else "mdi.weather-night", color=icon_color))
            self.fs_btn.setIcon(qta.icon("mdi.window-maximize", color=icon_color))
            self.min_btn.setIcon(qta.icon("mdi.minus", color=icon_color))
            self.close_btn.setIcon(qta.icon("mdi.close", color=icon_color))

            self.user_action.setIcon(qta.icon("mdi.account-outline", color=icon_color))
            self.pwd_action.setIcon(qta.icon("mdi.lock-outline", color=icon_color))
            self._toggle_pwd(self.show_pwd_btn.isChecked())

    def _toggle_pwd(self, checked: bool):
        self.password_input.setEchoMode(
            QLineEdit.EchoMode.Normal if checked else QLineEdit.EchoMode.Password
        )
        if HAS_QTA:
            T = ThemeManager.tokens()
            color = T['accent'] if checked else T['text_muted']
            self.show_pwd_btn.setIcon(
                qta.icon("mdi.eye-off-outline" if checked else "mdi.eye-outline", color=color)
            )

    def _toggle_fullscreen(self):
        if self.isMaximized():
            self.showNormal()
            self._center_on_screen()
            config.save_prefs({"login_maximized": False})
        else:
            self.showMaximized()
            config.save_prefs({"login_maximized": True})

    def _do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        self.error_lbl.setText("")

        if not username or not password:
            self.error_lbl.setText("Please enter both username and password.")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("Signing in…")

        ok, msg = AuthSession.login(username, password)

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Sign In")

        if ok:
            self.accept()
        else:
            self.error_lbl.setText(f"❌  {msg}")
            self.password_input.clear()
            self.password_input.setFocus()

    # ── Drag support (frameless window) ───────────────────────────────────

    def _tb_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _tb_move(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            if not self.isFullScreen():
                self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            if not self.isFullScreen():
                self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None