import os
import shutil
import zipfile
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTextEdit, QFrame, QGroupBox, QMessageBox,
    QTabWidget, QFileDialog, QProgressDialog, QScrollArea
)
from PySide6.QtCore import Qt

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

from ui.styles.theme import ThemeManager
from core.auth import AuthSession
import config

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()
        self._load_values()

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        company_tab = QWidget()
        ct = QVBoxLayout(company_tab)
        ct.setContentsMargins(28, 24, 28, 20)
        ct.setSpacing(14)

        header = QLabel("Company Information")
        header.setObjectName("SectionTitle")
        ct.addWidget(header)
        sub = QLabel("This information appears on all invoices and GST reports.")
        sub.setStyleSheet("color: #4E6D8C; font-size: 11px;")
        ct.addWidget(sub)

        def row(label: str, widget) -> QHBoxLayout:
            h = QHBoxLayout()
            lbl = QLabel(label.upper())
            lbl.setObjectName("FieldLabel")
            lbl.setMinimumWidth(120)
            h.addWidget(lbl); h.addWidget(widget)
            ct.addLayout(h)

        self.company_name_edit  = QLineEdit()
        self.company_addr_edit  = QTextEdit(); self.company_addr_edit.setFixedHeight(58)
        self.company_phone_edit = QLineEdit()
        self.company_email_edit = QLineEdit()
        self.company_gstin_edit = QLineEdit()
        self.company_state_edit = QLineEdit()
        self.company_sc_edit    = QLineEdit(); self.company_sc_edit.setMaximumWidth(100)

        row("Company Name", self.company_name_edit)
        row("Address",      self.company_addr_edit)
        row("Phone",        self.company_phone_edit)
        row("Email",        self.company_email_edit)
        row("GSTIN",        self.company_gstin_edit)
        row("State",        self.company_state_edit)
        row("State Code",   self.company_sc_edit)

        ct.addStretch()
        save_btn = QPushButton("💾  Save Company Settings")
        save_btn.setObjectName("PrimaryBtn")
        save_btn.setMinimumHeight(36)
        save_btn.setMinimumWidth(180)
        save_btn.clicked.connect(self._save_company)
        ct.addWidget(save_btn, alignment=Qt.AlignmentFlag.AlignRight)

        tabs.addTab(company_tab, "🏢  Company")

        display_tab = QWidget()
        dt = QVBoxLayout(display_tab)
        dt.setContentsMargins(28, 24, 28, 24); dt.setSpacing(16)

        dt.addWidget(self._section("Appearance"))

        theme_row = QHBoxLayout()
        theme_lbl = QLabel("Theme:")
        self.dark_btn  = QPushButton("🌙  Dark Theme")
        self.light_btn = QPushButton("☀️  Light Theme")
        self.dark_btn.setObjectName("PrimaryBtn" if ThemeManager.is_dark() else "GhostBtn")
        self.light_btn.setObjectName("GhostBtn"  if ThemeManager.is_dark() else "PrimaryBtn")
        self.dark_btn.setMinimumWidth(120)
        self.light_btn.setMinimumWidth(120)
        self.dark_btn.clicked.connect(lambda: self._set_theme("dark"))
        self.light_btn.clicked.connect(lambda: self._set_theme("light"))
        theme_row.addWidget(theme_lbl)
        theme_row.addWidget(self.dark_btn)
        theme_row.addWidget(self.light_btn)
        theme_row.addStretch()
        dt.addLayout(theme_row)

        hint = QLabel("Keyboard shortcuts:  Ctrl++  /  Ctrl+-  →  Zoom In / Out   |   F11  →  Fullscreen")
        hint.setStyleSheet("color: #4E6D8C; font-size: 11px;")
        dt.addWidget(hint)
        dt.addStretch()
        tabs.addTab(display_tab, "🎨  Display")

        data_tab = QWidget()
        dl = QVBoxLayout(data_tab)
        dl.setContentsMargins(28, 24, 28, 24); dl.setSpacing(16)

        dl.addWidget(self._section("Data Directory"))

        path_frame = QFrame(); path_frame.setObjectName("Card")
        pfl = QVBoxLayout(path_frame); pfl.setContentsMargins(16, 14, 16, 14)
        self.data_dir_lbl = QLabel(config.DATA_DIR)
        self.data_dir_lbl.setStyleSheet(
            "font-family: Consolas,monospace; font-size: 11px; color: #60A5FA;")
        self.data_dir_lbl.setWordWrap(True)
        pfl.addWidget(self.data_dir_lbl)
        dl.addWidget(path_frame)

        dl.addWidget(self._section("Backup & Restore"))

        backup_row = QHBoxLayout()
        backup_btn = QPushButton("📦  Create ZIP Backup")
        backup_btn.setObjectName("PrimaryBtn"); backup_btn.setMinimumWidth(160)
        backup_btn.clicked.connect(self._create_backup)
        restore_btn = QPushButton("♻️  Restore from Backup")
        restore_btn.setObjectName("WarningBtn"); restore_btn.setMinimumWidth(160)
        restore_btn.clicked.connect(self._restore_backup)
        backup_row.addWidget(backup_btn); backup_row.addWidget(restore_btn); backup_row.addStretch()
        dl.addLayout(backup_row)

        self.backup_status = QLabel("")
        self.backup_status.setStyleSheet("color: #10B981; font-size: 11px;")
        dl.addWidget(self.backup_status)
        dl.addStretch()
        tabs.addTab(data_tab, "💾  Data & Backup")

        if AuthSession.is_developer():
            dev_tab = QWidget()
            dvl = QVBoxLayout(dev_tab)
            dvl.setContentsMargins(28, 24, 28, 24); dvl.setSpacing(14)

            warn = QLabel("⚠️  Developer Panel – Restricted")
            warn.setStyleSheet("color: #F59E0B; font-size: 14px; font-weight: 700;")
            dvl.addWidget(warn)

            info_box = QGroupBox("Application Info")
            ibl = QVBoxLayout(info_box)
            import sys
            for lbl, val in [
                ("App", config.APP_FULL_NAME),
                ("Version", config.APP_VERSION),
                ("Python", sys.version.split()[0]),
                ("DB Path", config.DB_PATH),
                ("Data Dir", config.DATA_DIR),
                ("Invoices", config.INVOICES_DIR),
                ("Exports", config.EXPORTS_DIR),
            ]:
                ibl.addWidget(QLabel(f"<b>{lbl}:</b>  {val}"))
            dvl.addWidget(info_box)
            dvl.addStretch()
            tabs.addTab(dev_tab, "🔧  Developer")

        about_tab = QWidget()
        al = QVBoxLayout(about_tab)
        al.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel("🏪"); logo.setStyleSheet("font-size: 72px; background:transparent;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        al.addWidget(logo)
        for text, style in [
            (config.APP_NAME, "font-size: 18px; font-weight: 800; color: #E8F4FD;"),
            (f"Version {config.APP_VERSION}", "color: #4E6D8C; font-size: 12px;"),
            ("", ""),
            (f"Developed by {config.DEVELOPER_COMPANY}", "font-size: 13px; font-weight: 700; color: #60a5fa;"),
            (f"Built for {config.APP_PUBLISHER}", "color: #8b949e; font-size: 11px;"),
            ("", ""),
            (f"© {__import__('datetime').date.today().year} {config.DEVELOPER_COMPANY}. All rights reserved.", "color: #4E6D8C; font-size: 10px;"),
        ]:
            lbl = QLabel(text); lbl.setStyleSheet(style + " background:transparent;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            al.addWidget(lbl)
        tabs.addTab(about_tab, "ℹ️  About")

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def _section(self, text: str) -> QLabel:
        lbl = QLabel(text); lbl.setObjectName("SectionTitle")
        return lbl

    def _load_values(self):
        self.company_name_edit.setText(config.COMPANY_NAME)
        self.company_addr_edit.setPlainText(config.COMPANY_ADDRESS)
        self.company_phone_edit.setText(config.COMPANY_PHONE)
        self.company_email_edit.setText(config.COMPANY_EMAIL)
        self.company_gstin_edit.setText(config.COMPANY_GSTIN)
        self.company_state_edit.setText(config.COMPANY_STATE)
        self.company_sc_edit.setText(config.COMPANY_STATE_CODE)
        self.data_dir_lbl.setText(config.DATA_DIR)

    def _save_company(self):
        data = {
            "company_name":       self.company_name_edit.text().strip(),
            "company_address":    self.company_addr_edit.toPlainText().strip(),
            "company_phone":      self.company_phone_edit.text().strip(),
            "company_email":      self.company_email_edit.text().strip(),
            "company_gstin":      self.company_gstin_edit.text().strip(),
            "company_state":      self.company_state_edit.text().strip(),
            "company_state_code": self.company_sc_edit.text().strip(),
        }
        config.update_company_settings(data)
        QMessageBox.information(self, "Saved", "Company settings saved successfully.")

    def _set_theme(self, name: str):
        ThemeManager.set_theme(name)
        config.save_prefs({"theme": name})
        self.dark_btn.setObjectName("PrimaryBtn" if name == "dark" else "GhostBtn")
        self.light_btn.setObjectName("PrimaryBtn" if name == "light" else "GhostBtn")
        for btn in [self.dark_btn, self.light_btn]:
            btn.style().unpolish(btn); btn.style().polish(btn)

    def _create_backup(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"progressive_backup_{timestamp}.zip"
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Backup", os.path.join(config.BACKUPS_DIR, default_name),
            "ZIP Archives (*.zip)"
        )
        if not dest:
            return
        try:
            with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
                for root, dirs, files in os.walk(config.DATA_DIR):
                    dirs[:] = [d for d in dirs if os.path.join(root, d) != config.BACKUPS_DIR]
                    for file in files:
                        abs_path = os.path.join(root, file)
                        arcname = os.path.relpath(abs_path, config.DATA_DIR)
                        zf.write(abs_path, arcname)
            size_mb = os.path.getsize(dest) / (1024 * 1024)
            self.backup_status.setText(f"✅  Backup saved: {os.path.basename(dest)}  ({size_mb:.2f} MB)")
            QMessageBox.information(self, "Backup Created",
                f"Backup saved to:\n{dest}\n\nSize: {size_mb:.2f} MB")
        except Exception as e:
            QMessageBox.critical(self, "Backup Failed", str(e))

    def _restore_backup(self):
        src, _ = QFileDialog.getOpenFileName(
            self, "Select Backup ZIP", config.BACKUPS_DIR,
            "ZIP Archives (*.zip)"
        )
        if not src:
            return
        reply = QMessageBox.warning(
            self, "Restore Backup",
            f"⚠️  This will OVERWRITE your current data with the backup.\n\n"
            f"Backup: {os.path.basename(src)}\n\n"
            f"Are you sure? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            safety_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_zip = os.path.join(config.BACKUPS_DIR, f"pre_restore_{safety_stamp}.zip")
            with zipfile.ZipFile(safety_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for root, dirs, files in os.walk(config.DATA_DIR):
                    dirs[:] = [d for d in dirs if os.path.join(root, d) != config.BACKUPS_DIR]
                    for file in files:
                        abs_path = os.path.join(root, file)
                        zf.write(abs_path, os.path.relpath(abs_path, config.DATA_DIR))

            with zipfile.ZipFile(src, "r") as zf:
                zf.extractall(config.DATA_DIR)

            QMessageBox.information(
                self, "Restore Complete",
                "Backup restored successfully.\n\n"
                f"A safety backup of your previous data was saved as:\n{safety_zip}\n\n"
                "Please restart the application for changes to take effect."
            )
        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", str(e))

    def refresh(self):
        self._load_values()
