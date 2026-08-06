import bcrypt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QStackedWidget, QWidget, QFrame,
    QSizePolicy, QFileDialog, QMessageBox, QScrollArea
)
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont, QColor

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

import config
from ui.components.responsive import fit_dialog_to_screen, refit_after_show
from ui.styles.theme import ThemeManager

STEPS = [
    ("🏠", "Welcome",         "Let's get your store set up"),
    ("🏢", "Company Info",    "Tell us about your business"),
    ("👤", "Admin Account",   "Create your administrator login"),
    ("💾", "Data Storage",    "Where should data be saved?"),
    ("✅", "All Done!",       "Your system is ready"),
]

class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Setup – {config.APP_NAME}")
        self.setModal(True)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self._step = 0
        self._build_ui()
        self._go_to(0)
        fit_dialog_to_screen(self, 900, 640, minimum_width=520, minimum_height=420)

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("WizardStep")
        self.left_panel.setFixedWidth(220)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        brand = QWidget()
        brand.setFixedHeight(100)
        brand.setStyleSheet("""
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #1D4ED8, stop:1 #7C3AED);
        """)
        bl = QVBoxLayout(brand)
        bl.setContentsMargins(20, 16, 20, 16)
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        if config.LOGO_PATH and __import__("os").path.exists(config.LOGO_PATH):
            px = QPixmap(config.LOGO_PATH).scaled(
                48, 48, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("🏪")
            logo_lbl.setStyleSheet("font-size: 36px; background: transparent;")
        app_lbl = QLabel(config.APP_NAME)
        app_lbl.setStyleSheet("font-size: 12px; font-weight: 800; color: #FFF; background: transparent; letter-spacing: 0.5px;")
        app_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bl.addWidget(logo_lbl)
        bl.addWidget(app_lbl)
        left_layout.addWidget(brand)

        steps_widget = QWidget()
        steps_layout = QVBoxLayout(steps_widget)
        steps_layout.setContentsMargins(16, 24, 16, 16)
        steps_layout.setSpacing(8)

        self._step_widgets = []
        for i, (icon, title, _) in enumerate(STEPS):
            row = QHBoxLayout(); row.setSpacing(12)
            num_lbl = QLabel(str(i + 1))
            num_lbl.setFixedSize(32, 32)
            num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num_lbl.setObjectName("StepIndicatorPending")
            text_lbl = QLabel(title)
            text_lbl.setObjectName("StepLabel")
            row.addWidget(num_lbl)
            row.addWidget(text_lbl)
            row.addStretch()
            container = QWidget()
            container.setLayout(row)
            steps_layout.addWidget(container)
            self._step_widgets.append((num_lbl, text_lbl, icon))

        steps_layout.addStretch()
        left_layout.addWidget(steps_widget, 1)

        ver = QLabel(f"v{config.APP_VERSION}")
        ver.setStyleSheet("color: rgba(255,255,255,0.3); font-size: 10px; padding: 8px;")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(ver)

        root.addWidget(self.left_panel)

        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        title_bar = QWidget()
        title_bar.setFixedHeight(46)
        title_bar.setStyleSheet("background: transparent; border-bottom: 1px solid rgba(255,255,255,0.06);")
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(24, 0, 12, 0)
        self.step_title_lbl = QLabel("Welcome")
        self.step_title_lbl.setStyleSheet("font-size: 13px; font-weight: 700; color: #94A3B8;")
        tb_layout.addWidget(self.step_title_lbl)
        tb_layout.addStretch()
        right.addWidget(title_bar)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._page_welcome())
        self.stack.addWidget(self._page_company())
        self.stack.addWidget(self._page_admin())
        self.stack.addWidget(self._page_storage())
        self.stack.addWidget(self._page_done())
        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        page_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        page_scroll.setWidget(self.stack)
        right.addWidget(page_scroll, 1)

        footer = QWidget()
        footer.setFixedHeight(62)
        footer.setObjectName("DialogFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(28, 0, 28, 0)

        self.back_btn = QPushButton("← Back")
        self.back_btn.setObjectName("GhostBtn")
        self.back_btn.setFixedWidth(100)
        self.back_btn.clicked.connect(self._prev)
        self.back_btn.setVisible(False)

        self.next_btn = QPushButton("Next →")
        self.next_btn.setObjectName("PrimaryBtn")
        self.next_btn.setFixedWidth(120)
        self.next_btn.clicked.connect(self._next)

        fl.addWidget(self.back_btn)
        fl.addStretch()
        fl.addWidget(self.next_btn)
        right.addWidget(footer)

        right_widget = QWidget()
        right_widget.setLayout(right)
        root.addWidget(right_widget, 1)

    def showEvent(self, event):
        super().showEvent(event)
        refit_after_show(self, 900, 640, minimum_width=520, minimum_height=420)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "left_panel"):
            self.left_panel.setVisible(event.size().width() >= 720)

    def _card(self, *widgets) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24)
        vl.setSpacing(16)
        for widget in widgets:
            vl.addWidget(widget)
        return w

    def _field(self, label_text: str, widget) -> QWidget:
        w = QWidget(); vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0); vl.setSpacing(5)
        lbl = QLabel(label_text.upper())
        lbl.setObjectName("FieldLabel")
        vl.addWidget(lbl); vl.addWidget(widget)
        return w

    def _page_welcome(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(60, 60, 60, 40)
        vl.setSpacing(20)
        vl.setAlignment(Qt.AlignmentFlag.AlignTop)

        icon = QLabel("🏪")
        icon.setStyleSheet("font-size: 64px; background: transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        h1 = QLabel(f"Welcome to {config.APP_NAME}")
        h1.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {ThemeManager.t('text_primary')};")
        h1.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel(
            "This wizard will guide you through the initial setup of your<br>"
            "Business Management Suite. It only takes a few minutes."
        )
        sub.setStyleSheet("font-size: 13px; color: #94A3B8; line-height: 1.6;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setWordWrap(True)

        features = [
            ("🧾", "Point of Sale & Invoice Generation"),
            ("📦", "Inventory & Stock Management"),
            ("💳", "EMI & Finance Tracking"),
            ("📊", "GST Reports & Analytics"),
        ]
        feat_widget = QWidget()
        feat_layout = QVBoxLayout(feat_widget)
        feat_layout.setSpacing(8)
        for emoji, text in features:
            row = QHBoxLayout()
            e = QLabel(emoji); e.setFixedWidth(24); e.setStyleSheet("background:transparent;")
            t = QLabel(text); t.setStyleSheet("color: #94A3B8; font-size: 12px; background:transparent;")
            row.addWidget(e); row.addWidget(t); row.addStretch()
            feat_layout.addLayout(row)

        vl.addStretch()
        vl.addWidget(icon)
        vl.addWidget(h1)
        vl.addWidget(sub)
        vl.addSpacing(16)
        vl.addWidget(feat_widget)
        vl.addStretch()
        return w

    def _page_company(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24); vl.setSpacing(14)

        h = QLabel("Company Information")
        h.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {ThemeManager.t('text_primary')};")
        vl.addWidget(h)
        sub = QLabel("This information appears on invoices and GST reports.")
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        vl.addWidget(sub)
        vl.addSpacing(6)

        self.w_company_name = QLineEdit(); self.w_company_name.setPlaceholderText("e.g. Progressive Enterprises *")
        self.w_company_name.setText(config.COMPANY_NAME)
        self.w_company_addr = QTextEdit(); self.w_company_addr.setFixedHeight(60)
        self.w_company_addr.setPlaceholderText("Full address including city and PIN")
        self.w_company_addr.setPlainText(config.COMPANY_ADDRESS)
        self.w_company_phone = QLineEdit(); self.w_company_phone.setPlaceholderText("+91-XXXXXXXXXX")
        self.w_company_email = QLineEdit(); self.w_company_email.setPlaceholderText("info@company.com")
        self.w_company_gstin = QLineEdit(); self.w_company_gstin.setPlaceholderText("15-character GSTIN")
        self.w_company_state = QLineEdit(); self.w_company_state.setPlaceholderText("e.g. Rajasthan")
        self.w_company_state_code = QLineEdit(); self.w_company_state_code.setPlaceholderText("e.g. 08")
        self.w_company_state_code.setFixedWidth(80)

        for lbl, wid in [
            ("Company Name *", self.w_company_name),
            ("Address", self.w_company_addr),
            ("Phone", self.w_company_phone),
            ("Email", self.w_company_email),
            ("GSTIN", self.w_company_gstin),
            ("State", self.w_company_state),
        ]:
            vl.addWidget(self._field(lbl, wid))

        row = QHBoxLayout()
        row.addWidget(self._field("State Code", self.w_company_state_code))
        row.addStretch()
        vl.addLayout(row)
        vl.addStretch()
        return w

    def _page_admin(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24); vl.setSpacing(14)

        h = QLabel("Administrator Account")
        h.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {ThemeManager.t('text_primary')};")
        vl.addWidget(h)
        sub = QLabel("Create the primary login credentials for your staff.")
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        vl.addWidget(sub)
        vl.addSpacing(6)

        self.w_admin_name = QLineEdit(); self.w_admin_name.setPlaceholderText("Full name *")
        self.w_admin_user = QLineEdit(); self.w_admin_user.setPlaceholderText("Username (no spaces) *")
        self.w_admin_pwd = QLineEdit()
        self.w_admin_pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.w_admin_pwd.setPlaceholderText("Password (min 6 chars) *")
        self.w_admin_pwd2 = QLineEdit()
        self.w_admin_pwd2.setEchoMode(QLineEdit.EchoMode.Password)
        self.w_admin_pwd2.setPlaceholderText("Confirm password *")

        for lbl, wid in [
            ("Full Name *", self.w_admin_name),
            ("Username *", self.w_admin_user),
            ("Password *", self.w_admin_pwd),
            ("Confirm Password *", self.w_admin_pwd2),
        ]:
            vl.addWidget(self._field(lbl, wid))

        self.admin_err = QLabel("")
        self.admin_err.setStyleSheet("color: #F87171; font-size: 11px; background:transparent;")
        vl.addWidget(self.admin_err)
        vl.addStretch()
        return w

    def _page_storage(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(40, 32, 40, 24); vl.setSpacing(14)

        h = QLabel("Data Storage Location")
        h.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {ThemeManager.t('text_primary')};")
        vl.addWidget(h)
        sub = QLabel(
            "Your data is stored in a dedicated folder that persists through app updates.\n"
            "The default location is recommended for most users."
        )
        sub.setStyleSheet("color: #94A3B8; font-size: 12px;")
        sub.setWordWrap(True)
        vl.addWidget(sub)
        vl.addSpacing(10)

        lbl = QLabel("CURRENT DATA FOLDER")
        lbl.setObjectName("FieldLabel")
        vl.addWidget(lbl)

        self.data_path_lbl = QLabel(config.DATA_DIR)
        self.data_path_lbl.setObjectName("Card")
        self.data_path_lbl.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 11px; padding: 14px; "
            "color: #60A5FA; border-radius: 10px;"
        )
        self.data_path_lbl.setWordWrap(True)
        vl.addWidget(self.data_path_lbl)

        change_btn = QPushButton("📂  Change Location")
        change_btn.setObjectName("GhostBtn")
        change_btn.setFixedWidth(180)
        change_btn.clicked.connect(self._change_data_dir)
        vl.addWidget(change_btn)

        note = QLabel(
            "⚠️  Changing the data location requires restarting the setup.\n"
            f"The developer account ({config.DEV_USERNAME}) is always available as a fallback."
        )
        note.setStyleSheet("color: #F59E0B; font-size: 11px; background: transparent;")
        note.setWordWrap(True)
        vl.addWidget(note)
        vl.addStretch()
        return w

    def _page_done(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(60, 60, 60, 40)
        vl.setSpacing(20)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon = QLabel("🎉")
        icon.setStyleSheet("font-size: 72px; background: transparent;")
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        h = QLabel("Setup Complete!")
        h.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {ThemeManager.t('text_primary')};")
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel(
            "Your Business Suite is ready to use.\n"
            "Click 'Launch App' to begin."
        )
        sub.setStyleSheet("color: #94A3B8; font-size: 13px; line-height: 1.7;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vl.addStretch()
        for widget in [icon, h, sub]:
            vl.addWidget(widget)
        vl.addStretch()
        return w

    def _go_to(self, step: int):
        self._step = step
        self.stack.setCurrentIndex(step)
        name, title, sub = STEPS[step][1], STEPS[step][1], STEPS[step][2]
        self.step_title_lbl.setText(f"Step {step + 1} of {len(STEPS)} — {title}")

        self.back_btn.setVisible(step > 0)
        if step == len(STEPS) - 1:
            self.next_btn.setText("🚀  Launch App")
        else:
            self.next_btn.setText("Next  →")

        for i, (num_lbl, text_lbl, icon) in enumerate(self._step_widgets):
            if i < step:
                num_lbl.setText("✓")
                num_lbl.setObjectName("StepIndicatorDone")
                text_lbl.setObjectName("StepLabelActive")
            elif i == step:
                num_lbl.setText(str(i + 1))
                num_lbl.setObjectName("StepIndicatorActive")
                text_lbl.setObjectName("StepLabelActive")
            else:
                num_lbl.setText(str(i + 1))
                num_lbl.setObjectName("StepIndicatorPending")
                text_lbl.setObjectName("StepLabel")
            num_lbl.style().unpolish(num_lbl)
            num_lbl.style().polish(num_lbl)
            text_lbl.style().unpolish(text_lbl)
            text_lbl.style().polish(text_lbl)

    def _validate_current(self) -> bool:
        if self._step == 1:
            if not self.w_company_name.text().strip():
                QMessageBox.warning(self, "Required", "Company name is required.")
                return False
        elif self._step == 2:
            name = self.w_admin_name.text().strip()
            user = self.w_admin_user.text().strip()
            pwd = self.w_admin_pwd.text()
            pwd2 = self.w_admin_pwd2.text()
            self.admin_err.setText("")
            if not name or not user or not pwd:
                self.admin_err.setText("All fields are required.")
                return False
            if " " in user:
                self.admin_err.setText("Username cannot contain spaces.")
                return False
            if len(pwd) < 6:
                self.admin_err.setText("Password must be at least 6 characters.")
                return False
            if pwd != pwd2:
                self.admin_err.setText("Passwords do not match.")
                return False
        return True

    def _next(self):
        if self._step == len(STEPS) - 1:
            self._finish()
            return
        if not self._validate_current():
            return
        self._go_to(self._step + 1)

    def _prev(self):
        if self._step > 0:
            self._go_to(self._step - 1)

    def _change_data_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose Data Folder", config.DATA_DIR)
        if d:
            import os
            new_dir = os.path.join(d, config.DATA_DIR_NAME, "data")
            config.set_custom_data_dir(new_dir)
            self.data_path_lbl.setText(new_dir)

    def _finish(self):
        pwd = self.w_admin_pwd.text()
        pwd_hash = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt()).decode()
        company_data = {
            "company_name":       self.w_company_name.text().strip(),
            "company_address":    self.w_company_addr.toPlainText().strip(),
            "company_phone":      self.w_company_phone.text().strip(),
            "company_email":      self.w_company_email.text().strip(),
            "company_gstin":      self.w_company_gstin.text().strip(),
            "company_state":      self.w_company_state.text().strip(),
            "company_state_code": self.w_company_state_code.text().strip(),
        }
        config.mark_setup_complete(
            company_data,
            self.w_admin_user.text().strip(),
            pwd_hash
        )
        self.accept()
