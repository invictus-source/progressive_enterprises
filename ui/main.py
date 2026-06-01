"""
Progressive Enterprises – Main Application Window
Sidebar + stacked-widget layout. Supports Ctrl+/- zoom, theme toggle, window controls.
Responsive design for various screen sizes.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
    QLabel, QStatusBar, QFrame, QPushButton, QApplication, QSizePolicy,
    QScrollArea
)
from PySide6.QtCore import Qt, QTimer, QSize
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut, QFont, QScreen

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

from ui.styles.theme import ThemeManager
from ui.components.sidebar import Sidebar
from ui.components.toast import ToastManager
from core.auth import AuthSession
import config


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        
        self._compute_initial_size()
        
        prefs = config.load_prefs()
        ThemeManager.load_from_prefs()
        ThemeManager.apply_to_app()

        # Restore font size
        saved_scale = prefs.get("font_scale", 10)
        font = QApplication.font()
        font.setPointSize(int(saved_scale) if isinstance(saved_scale, (int, float)) else 10)
        QApplication.setFont(font)

        self._pages: dict[str, QWidget] = {}
        self._setup_ui()
        self._setup_shortcuts()
        self._setup_status_bar()
        self._register_pages()

        ThemeManager.register_callback(self._on_theme_change)

        self.showMaximized()
        QTimer.singleShot(50, lambda: self._navigate("dashboard"))
        
    def _compute_initial_size(self):
        screen = QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            # Use 80% of screen as minimum so it always fills most of the display.
            # Hard floor at 800x500 for very small/embedded screens.
            self._min_width  = max(800, int(available.width()  * 0.80))
            self._min_height = max(500, int(available.height() * 0.80))
        else:
            self._min_width  = 1024
            self._min_height = 600
        self.setMinimumSize(self._min_width, self._min_height)

    # ── UI Construction ────────────────────────────────────────────────────────

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_requested.connect(self._navigate)
        root.addWidget(self.sidebar)

        # Main content (topbar + stack)
        content_area = QVBoxLayout()
        content_area.setContentsMargins(0, 0, 0, 0)
        content_area.setSpacing(0)

        # Top Bar
        self.top_bar = QWidget()
        self.top_bar.setObjectName("TopBar")
        self.top_bar.setMinimumHeight(42)
        tb = QHBoxLayout(self.top_bar)
        tb.setContentsMargins(16, 0, 12, 0)
        tb.setSpacing(6)

        tb.addStretch()

        # Zoom out
        zoom_out = QPushButton()
        zoom_out.setObjectName("IconBtn")
        zoom_out.setFixedSize(32, 32)
        zoom_out.setToolTip("Zoom Out  (Ctrl+-)")
        zoom_out.clicked.connect(self._zoom_out)
        if HAS_QTA:
            zoom_out.setIcon(qta.icon("mdi.magnify-minus-outline", color="#94A3B8"))
        else:
            zoom_out.setText("—")
        tb.addWidget(zoom_out)

        # Zoom in
        zoom_in = QPushButton()
        zoom_in.setObjectName("IconBtn")
        zoom_in.setFixedSize(32, 32)
        zoom_in.setToolTip("Zoom In  (Ctrl++)")
        zoom_in.clicked.connect(self._zoom_in)
        if HAS_QTA:
            zoom_in.setIcon(qta.icon("mdi.magnify-plus-outline", color="#94A3B8"))
        else:
            zoom_in.setText("+")
        tb.addWidget(zoom_in)

        # Theme toggle
        self.theme_btn = QPushButton()
        self.theme_btn.setObjectName("IconBtn")
        self.theme_btn.setFixedSize(32, 32)
        self.theme_btn.setToolTip("Toggle Light/Dark Theme")
        self.theme_btn.clicked.connect(ThemeManager.toggle)
        self._update_theme_btn()
        tb.addWidget(self.theme_btn)

        # Menu toggle for small screens
        self.menu_toggle = QPushButton()
        self.menu_toggle.setObjectName("IconBtn")
        self.menu_toggle.setFixedSize(32, 32)
        self.menu_toggle.setToolTip("Toggle Sidebar")
        self.menu_toggle.clicked.connect(self._toggle_sidebar)
        if HAS_QTA:
            self.menu_toggle.setIcon(qta.icon("mdi.menu", color="#94A3B8"))
        else:
            self.menu_toggle.setText("☰")
        self.menu_toggle.hide()
        tb.insertWidget(0, self.menu_toggle)
        
        # Responsive handling
        self._update_responsive_layout()
        
        content_area.addWidget(self.top_bar)

        # Content stack with toast container
        self.stack_container = QWidget()
        stack_layout = QVBoxLayout(self.stack_container)
        stack_layout.setContentsMargins(0, 0, 0, 0)
        stack_layout.setSpacing(0)
        
        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentArea")
        stack_layout.addWidget(self.stack, 1)
        
        # Toast container overlay
        self.toast_container = QWidget()
        self.toast_container.setStyleSheet("background: transparent;")
        toast_layout = QVBoxLayout(self.toast_container)
        toast_layout.setContentsMargins(16, 16, 16, 0)
        toast_layout.setSpacing(8)
        toast_layout.addStretch(999)
        ToastManager.set_container(self.toast_container)
        
        content_area.addWidget(self.stack_container, 1)
        content_area.addWidget(self.toast_container, 0)
        
        content_widget = QWidget()
        content_widget.setLayout(content_area)
        root.addWidget(content_widget, 1)

    def _register_pages(self):
        """Lazy-import pages and add them to the stack."""
        from ui.windows.dashboard     import DashboardPage
        from ui.windows.pos           import POSPage
        from ui.windows.sales_history import SalesHistoryPage
        from ui.windows.inventory     import InventoryPage
        from ui.windows.purchases   import PurchasesPage
        from ui.windows.customers   import CustomersPage
        from ui.windows.vendors     import VendorsPage
        from ui.windows.emi_finance import EMIFinancePage
        from ui.windows.payments    import PaymentsPage
        from ui.windows.gst_reports import GSTReportsPage
        from ui.windows.reports     import ReportsPage
        from ui.windows.user_mgmt   import UserMgmtPage
        from ui.windows.settings    import SettingsPage

        page_map: dict[str, type] = {
            "dashboard":    DashboardPage,
            "pos":          POSPage,
            "sales_history": SalesHistoryPage,
            "inventory":    InventoryPage,
            "purchases":    PurchasesPage,
            "customers":    CustomersPage,
            "vendors":      VendorsPage,
            "emi_finance":  EMIFinancePage,
            "payments":     PaymentsPage,
            "gst_reports":  GSTReportsPage,
            "reports":      ReportsPage,
            "user_mgmt":    UserMgmtPage,
            "settings":     SettingsPage,
        }

        for key, PageClass in page_map.items():
            try:
                page = PageClass()
                self._pages[key] = page
                self.stack.addWidget(page)
                
                if key == "sales_history":
                    page.modify_sale_requested.connect(self._handle_modify_sale)
                    
            except Exception as e:
                placeholder = self._make_placeholder(key, str(e))
                self._pages[key] = placeholder
                self.stack.addWidget(placeholder)

    def _make_placeholder(self, key: str, error: str = "") -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w); vl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("🚧"); icon.setStyleSheet("font-size: 48px; background:transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg = QLabel(f"{key.replace('_', ' ').title()}\n\n{error}")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: #4E6D8C; font-size: 14px; background:transparent;")
        msg.setWordWrap(True)
        for w_ in [icon, msg]: vl.addWidget(w_)
        return w

    # ── Navigation ─────────────────────────────────────────────────────────────

    def _navigate(self, key: str):
        page = self._pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.sidebar.set_page(key)

        # Update top-bar title



        # Refresh page
        if hasattr(page, "refresh") and page != self._pages.get("_refreshed_" + key):
            try:
                page.refresh()
            except Exception as e:
                print(f"[NAV] refresh error for {key}: {e}")

    def _handle_modify_sale(self, sale_id: int):
        from db.manager import get_db
        from db.models import Sale
        session = get_db()
        try:
            sale = session.query(Sale).get(sale_id)
            if not sale: return
            
            pos_page = self._pages.get("pos")
            if pos_page and hasattr(pos_page, "load_sale_for_edit"):
                self._navigate("pos")
                pos_page.load_sale_for_edit(sale)
        finally:
            session.close()
    
    def _toggle_sidebar(self):
        if self.sidebar.isVisible():
            self.sidebar.hide()
            self.sidebar.set_hidden_mode(True)
        else:
            self.sidebar.show()
            self.sidebar.set_hidden_mode(False)
    
    def _update_responsive_layout(self):
        width = self.width()
        if width < 1100:
            self.sidebar.set_collapsed(True)
        else:
            self.sidebar.set_collapsed(False)
        if width < 768:
            self.menu_toggle.show()
        else:
            self.menu_toggle.hide()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_responsive_layout()

    # ── Keyboard Shortcuts ─────────────────────────────────────────────────────

    def _setup_shortcuts(self):
        QShortcut(QKeySequence("Ctrl++"),  self).activated.connect(self._zoom_in)
        QShortcut(QKeySequence("Ctrl+="),  self).activated.connect(self._zoom_in)
        QShortcut(QKeySequence("Ctrl+-"),  self).activated.connect(self._zoom_out)
        QShortcut(QKeySequence("F11"),     self).activated.connect(self._toggle_fullscreen)
        QShortcut(QKeySequence("Ctrl+D"),  self).activated.connect(lambda: self._navigate("dashboard"))
        QShortcut(QKeySequence("Ctrl+P"),  self).activated.connect(lambda: self._navigate("pos"))
        QShortcut(QKeySequence("Ctrl+I"),  self).activated.connect(lambda: self._navigate("inventory"))

    def _zoom_in(self):
        font = QApplication.font()
        size = min(font.pointSize() + 1, 18)
        font.setPointSize(size)
        QApplication.setFont(font)
        ThemeManager._apply()
        config.save_prefs({"font_scale": size})

    def _zoom_out(self):
        font = QApplication.font()
        size = max(font.pointSize() - 1, 9)
        font.setPointSize(size)
        QApplication.setFont(font)
        ThemeManager._apply()
        config.save_prefs({"font_scale": size})

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    # ── Theme ──────────────────────────────────────────────────────────────────

    def _on_theme_change(self):
        self._update_theme_btn()

    def _update_theme_btn(self):
        if not HAS_QTA:
            self.theme_btn.setText("☀" if ThemeManager.is_dark() else "🌙")
            return
        icon_name = "mdi.weather-sunny" if ThemeManager.is_dark() else "mdi.weather-night"
        self.theme_btn.setIcon(qta.icon(icon_name, color="#94A3B8"))

    # ── Status Bar ─────────────────────────────────────────────────────────────

    def _setup_status_bar(self):
        bar = QStatusBar()
        self.setStatusBar(bar)
        user = AuthSession.current_user()
        if user:
            bar.showMessage(
                f"  {config.COMPANY_NAME}  ·  "
                f"Signed in as {user.full_name} ({user.role.capitalize()})  ·  "
                f"Data: {config.DATA_DIR}"
            )

    def closeEvent(self, event: QCloseEvent):
        AuthSession.logout()
        event.accept()