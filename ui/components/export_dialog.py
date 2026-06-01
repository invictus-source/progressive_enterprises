"""
Progressive Enterprises – Export Viewer Dialog
Provides clear context about a generated export (PDF/Excel) and options to open/print/explore.
"""

import os
import subprocess
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy, QWidget
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices

try:
    import qtawesome as qta
    HAS_QTA = True
except ImportError:
    HAS_QTA = False

class ExportReadyDialog(QDialog):
    def __init__(self, filepath: str, parent=None):
        super().__init__(parent)
        self.filepath = filepath
        self.filename = os.path.basename(filepath)
        self.setWindowTitle("Export Successful")
        self.setFixedSize(480, 260)
        self.setModal(True)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("DialogHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 0)
        
        title = QLabel("📄 Document Ready")
        title.setObjectName("DialogHeaderTitle")
        hl.addWidget(title)
        
        sub = QLabel("Your export has been successfully generated.")
        sub.setObjectName("DialogHeaderSub")
        hl.addWidget(sub)
        root.addWidget(header)

        # Body
        body = QWidget()
        body.setObjectName("DialogBody")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(24, 24, 24, 24)
        bl.setSpacing(16)

        msg = QLabel("The following file is ready:")
        msg.setStyleSheet("color: #64748B; font-size: 13px; font-weight: 500;")
        bl.addWidget(msg)

        # File Box
        file_box = QFrame()
        file_box.setObjectName("Card")
        file_box.setStyleSheet(file_box.styleSheet() + "background: rgba(59, 130, 246, 0.05); border: 1px solid rgba(59, 130, 246, 0.2);")
        fbl = QHBoxLayout(file_box)
        fbl.setContentsMargins(16, 12, 16, 12)
        
        icon = QLabel("📊" if self.filename.endswith(".xlsx") else "🧾")
        icon.setStyleSheet("font-size: 24px; background: transparent;")
        
        name_lbl = QLabel(self.filename)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px; background: transparent;")
        name_lbl.setWordWrap(True)
        
        fbl.addWidget(icon)
        fbl.addSpacing(8)
        fbl.addWidget(name_lbl, 1)
        bl.addWidget(file_box)
        root.addWidget(body, 1)

        # Footer (Actions)
        footer = QWidget()
        footer.setObjectName("DialogFooter")
        fl = QHBoxLayout(footer)
        fl.setContentsMargins(20, 16, 20, 16)
        fl.setSpacing(12)

        # Folder Button
        folder_btn = QPushButton("Show in Folder")
        folder_btn.setObjectName("GhostBtn")
        folder_btn.setFixedHeight(38)
        if HAS_QTA:
            folder_btn.setIcon(qta.icon("mdi.folder-search-outline", color="#94A3B8"))
        folder_btn.clicked.connect(self._show_in_folder)
        fl.addWidget(folder_btn)

        fl.addStretch()

        # Print Button
        print_btn = QPushButton("Print")
        print_btn.setObjectName("PrimaryBtn")
        print_btn.setStyleSheet("background: #0284C7;") # Unique blue variant
        print_btn.setFixedHeight(38)
        if HAS_QTA:
            print_btn.setIcon(qta.icon("mdi.printer", color="white"))
        print_btn.clicked.connect(self._print_document)
        fl.addWidget(print_btn)

        # Open Button
        open_btn = QPushButton("Open File")
        open_btn.setObjectName("SuccessBtn")
        open_btn.setFixedHeight(38)
        if HAS_QTA:
            open_btn.setIcon(qta.icon("mdi.open-in-new", color="white"))
        open_btn.clicked.connect(self._open_document)
        fl.addWidget(open_btn)

        root.addWidget(footer)

    def _open_document(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.filepath))
        self.accept()

    def _print_document(self):
        if os.name == 'nt':
            try:
                os.startfile(self.filepath, "print")
                self.accept()
            except Exception as e:
                from PySide6.QtWidgets import QMessageBox
                if "1155" in str(e):
                    QMessageBox.information(
                        self, "Print", 
                        "No default PDF printer found.\\nOpening the document instead so you can print it manually."
                    )
                    QDesktopServices.openUrl(QUrl.fromLocalFile(self.filepath))
                else:
                    QMessageBox.warning(self, "Print Error", f"Could not print document.\\n{e}")
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.filepath))
            self.accept()

    def _show_in_folder(self):
        if os.name == 'nt':
            subprocess.Popen(f'explorer /select,"{os.path.normpath(self.filepath)}"')
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(self.filepath)))
        self.accept()
