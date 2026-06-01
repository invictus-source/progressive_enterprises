import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QPixmap

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

from ui.styles.theme import ThemeManager
from core.auth import AuthSession
import config


def _icon(name: str, color: str = "#94A3B8", size: int = 18):
    if HAS_QTA:
        return qta.icon(name, color=color, scale_factor=1.0)
    return None


NAV_ITEMS = [
    ("MAIN",        None,                None,                          None),
    (None,          "Dashboard",         "mdi.view-dashboard-outline",  "dashboard"),
    ("SALES",       None,                None,                          None),
    (None,          "Point of Sale",     "mdi.cart-outline",            "pos"),
    (None,          "Sales History",     "mdi.receipt",                 "sales_history"),
    (None,          "Customers",         "mdi.account-group-outline",   "customers"),
    ("INVENTORY",   None,                None,                          None),
    (None,          "Inventory",         "mdi.package-variant-closed",  "inventory"),
    (None,          "Purchases / GRN",   "mdi.truck-delivery-outline",  "purchases"),
    (None,          "Vendors",           "mdi.store-outline",           "vendors"),
    ("FINANCE",     None,                None,                          None),
    (None,          "EMI & Finance",     "mdi.credit-card-outline",     "emi_finance"),
    (None,          "Payments",          "mdi.cash-multiple",           "payments"),
    (None,          "GST Reports",       "mdi.file-chart-outline",      "gst_reports"),
    ("ANALYTICS",   None,                None,                          None),
    (None,          "Reports",           "mdi.chart-bar",               "reports"),
    ("ADMIN",       None,                None,                          None),
    (None,          "Users",             "mdi.account-key-outline",     "user_mgmt"),
    (None,          "Settings",          "mdi.cog-outline",             "settings"),
]


class Sidebar(QWidget):
    page_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._expanded_width = 240
        self._collapsed_width = 60
        self._is_collapsed = False
        self._is_hidden = False
        self._active_key: str = "dashboard"
        self._nav_buttons: dict[str, QPushButton] = {}
        self._section_labels: dict[str, QLabel] = {}
        self._section_height = 60
        self._build_ui()

        ThemeManager.register_callback(self._on_theme_change)

    def set_collapsed(self, collapsed: bool):
        self._is_collapsed = collapsed
        if collapsed:
            self.setFixedWidth(self._collapsed_width)
        else:
            self.setFixedWidth(self._expanded_width)
        self._update_visibility()

    def set_hidden_mode(self, hidden: bool):
        self._is_hidden = hidden
        self._update_visibility()

    def _update_visibility(self):
        for page_key, btn in self._nav_buttons.items():
            if self._is_collapsed:
                btn.setText("")
                btn.setToolTip(next((n for s, n, i, p in NAV_ITEMS if p == page_key), ""))
            else:
                name = next((n for s, n, i, p in NAV_ITEMS if p == page_key), "")
                btn.setText(f"  {name}")
                btn.setToolTip("")
        
        for section_key, lbl in self._section_labels.items():
            lbl.setVisible(not self._is_collapsed)

        if hasattr(self, 'dev_credit'):
            self.dev_credit.setVisible(not self._is_collapsed)

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.brand = QWidget()
        self.brand.setObjectName("BrandBlock")
        self.brand.setMinimumHeight(60)
        bl = QVBoxLayout(self.brand)
        bl.setContentsMargins(16, 14, 16, 10)
        bl.setSpacing(3)

        logo_name_row = QHBoxLayout(); logo_name_row.setSpacing(10)
        logo_lbl = QLabel()
        logo_lbl.setFixedSize(36, 36)
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if os.path.exists(config.LOGO_PATH):
            px = QPixmap(config.LOGO_PATH).scaled(
                36, 36, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("🏪")
            logo_lbl.setStyleSheet("font-size: 26px; background: transparent;")
        logo_name_row.addWidget(logo_lbl)

        name_col = QVBoxLayout(); name_col.setSpacing(1)
        name_lbl = QLabel(config.APP_NAME)
        name_lbl.setObjectName("BrandName")
        name_lbl.setWordWrap(True)
        ver_lbl = QLabel(f"v{config.APP_VERSION}")
        ver_lbl.setObjectName("BrandSub")
        name_col.addWidget(name_lbl)
        name_col.addWidget(ver_lbl)
        logo_name_row.addLayout(name_col)
        logo_name_row.addStretch()
        bl.addLayout(logo_name_row)
        root.addWidget(self.brand)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("background: transparent;")

        nav_container = QWidget()
        nav_container.setStyleSheet("background: transparent;")
        self._nav_layout = QVBoxLayout(nav_container)
        self._nav_layout.setContentsMargins(0, 8, 0, 8)
        self._nav_layout.setSpacing(1)

        for section, name, icon_name, page_key in NAV_ITEMS:
            if section is not None:
                lbl = QLabel(section)
                lbl.setObjectName("NavSection")
                self._nav_layout.addWidget(lbl)
                self._section_labels[section] = lbl
            elif name and page_key:
                btn = QPushButton()
                btn.setObjectName("NavBtn")
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                btn.setMinimumHeight(34)

                icon_color = ThemeManager.t("accent") if page_key == self._active_key else "#94A3B8"
                if HAS_QTA and icon_name:
                    ic = _icon(icon_name, icon_color, 18)
                    if ic:
                        btn.setIcon(ic)
                        btn.setIconSize(QSize(18, 18))

                btn.setText(f"  {name}")
                btn.setProperty("active", page_key == self._active_key)
                btn.clicked.connect(lambda checked, k=page_key: self._on_nav_click(k))
                self._nav_layout.addWidget(btn)
                self._nav_buttons[page_key] = btn

        self._nav_layout.addStretch()
        scroll.setWidget(nav_container)
        root.addWidget(scroll, 1)

        self.user_block = QWidget()
        self.user_block.setObjectName("UserBlock")
        self.user_block.setMinimumHeight(50)
        ub = QHBoxLayout(self.user_block)
        ub.setContentsMargins(14, 10, 14, 10)
        ub.setSpacing(10)

        self.avatar_lbl = QLabel("?")
        self.avatar_lbl.setObjectName("UserAvatar")
        self.avatar_lbl.setFixedSize(36, 36)
        self.avatar_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        user_info = QVBoxLayout(); user_info.setSpacing(2)
        self.user_name_lbl = QLabel("—")
        self.user_name_lbl.setObjectName("UserName")
        self.user_role_lbl = QLabel("—")
        self.user_role_lbl.setObjectName("UserRole")
        user_info.addWidget(self.user_name_lbl)
        user_info.addWidget(self.user_role_lbl)

        ub.addWidget(self.avatar_lbl)
        ub.addLayout(user_info)
        ub.addStretch()

        logout_btn = QPushButton()
        logout_btn.setObjectName("IconBtn")
        logout_btn.setFixedSize(32, 32)
        logout_btn.setToolTip("Sign Out")
        if HAS_QTA:
            logout_btn.setIcon(qta.icon("mdi.logout", color="#4E6D8C"))
        else:
            logout_btn.setText("⇥")
        logout_btn.clicked.connect(self._on_logout)
        ub.addWidget(logout_btn)

        root.addWidget(self.user_block)

        self.dev_credit = QLabel(f"⚡ {config.DEVELOPER_COMPANY}")
        self.dev_credit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.dev_credit.setStyleSheet(
            "color: #4E6D8C; font-size: 9px; padding: 4px 0; background: transparent;"
        )
        self.dev_credit.setVisible(not self._is_collapsed)
        root.addWidget(self.dev_credit)

        self._update_user_info()

    def _on_nav_click(self, key: str):
        self._set_active(key)
        self.page_requested.emit(key)

    def _set_active(self, key: str):
        self._active_key = key
        accent = ThemeManager.t("accent")
        for k, btn in self._nav_buttons.items():
            active = (k == key)
            btn.setProperty("active", active)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            if HAS_QTA:
                icon_name = next(
                    (i for sec, n, i, p in NAV_ITEMS if p == k), None)
                if icon_name:
                    color = accent if active else "#94A3B8"
                    btn.setIcon(qta.icon(icon_name, color=color))
                    btn.setIconSize(QSize(18, 18))

    def set_page(self, key: str):
        self._set_active(key)

    def _update_user_info(self):
        user = AuthSession.current_user()
        if user:
            name = user.full_name or user.username
            initials = "".join(p[0].upper() for p in name.split()[:2])
            self.avatar_lbl.setText(initials or "?")
            self.user_name_lbl.setText(name)
            self.user_role_lbl.setText(user.role.capitalize())

    def _on_logout(self):
        from PySide6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self, "Sign Out",
            "Are you sure you want to sign out?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            AuthSession.logout()
            self.window().close()

    def _on_theme_change(self):
        accent = ThemeManager.t("accent")
        self._set_active(self._active_key)


    def get_selected_original_index(self):
        return None