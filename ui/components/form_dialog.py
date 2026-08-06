from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget, QSizePolicy,
    QApplication, QLineEdit, QComboBox, QTextEdit
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QScreen
from ui.components.responsive import fit_dialog_to_screen, refit_after_show


class FormDialog(QDialog):

    def __init__(self, title: str, subtitle: str = "",
                 width: int = 520, height: int = 0, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._preferred_width = width
        self._preferred_height = height if height and height > 0 else 0
        self._result_data = None
        self._first_show = True
        self._build_chrome(title, subtitle)
        self._adjust_size()
        
    def _adjust_size(self):
        fit_dialog_to_screen(
            self, self._preferred_width, self._preferred_height or 620,
            minimum_width=360, minimum_height=300,
        )

    def _build_chrome(self, title: str, subtitle: str):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        header = QWidget()
        header.setObjectName("DialogHeader")
        self._header = header
        h_layout = QVBoxLayout(header)
        h_layout.setContentsMargins(14, 8, 14, 8)
        h_layout.setSpacing(2)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("DialogHeaderTitle")
        title_lbl.setWordWrap(True)
        h_layout.addWidget(title_lbl)

        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setObjectName("DialogHeaderSub")
            h_layout.addWidget(sub_lbl)

        root.addWidget(header)

        self.error_frame = QFrame()
        self.error_frame.setObjectName("ToastError")
        self.error_frame.setStyleSheet("""
            QFrame { background-color: #7F1D1D; border-radius: 8px; padding: 8px; margin: 4px 0; }
            QLabel { color: #FCA5A5; }
        """)
        error_layout = QHBoxLayout(self.error_frame)
        error_layout.setContentsMargins(12, 8, 12, 8)
        error_layout.setSpacing(8)
        
        self.error_icon = QLabel("⚠")
        self.error_icon.setStyleSheet("font-size: 14px;")
        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        error_layout.addWidget(self.error_icon)
        error_layout.addWidget(self.error_label, 1)
        
        self.close_error_btn = QPushButton("×")
        self.close_error_btn.setFixedSize(20, 20)
        self.close_error_btn.setStyleSheet("""
            QPushButton { background: transparent; border: none; color: #FCA5A5; font-size: 16px; }
            QPushButton:hover { background: rgba(255,255,255,0.1); border-radius: 4px; }
        """)
        self.close_error_btn.clicked.connect(self._hide_error)
        error_layout.addWidget(self.close_error_btn)
        
        self.error_frame.hide()
        root.addWidget(self.error_frame)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("QScrollArea { background: transparent; }")

        body_wrapper = QWidget()
        body_wrapper.setObjectName("DialogBody")
        self.body_layout = QVBoxLayout(body_wrapper)
        self.body_layout.setContentsMargins(14, 12, 14, 12)
        self.body_layout.setSpacing(8)

        self.scroll.setWidget(body_wrapper)
        root.addWidget(self.scroll, 1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(sep2)

        footer = QWidget()
        footer.setObjectName("DialogFooter")
        f_layout = QHBoxLayout(footer)
        f_layout.setContentsMargins(14, 8, 14, 8)
        f_layout.setSpacing(8)
        f_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setMinimumHeight(32)
        self.cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("PrimaryBtn")
        self.save_btn.setMinimumHeight(32)
        self.save_btn.setMinimumWidth(80)
        self.save_btn.setDefault(True)
        self.save_btn.clicked.connect(self._on_save)

        f_layout.addWidget(self.cancel_btn)
        f_layout.addWidget(self.save_btn)
        root.addWidget(footer)

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_frame.show()
        
    def _hide_error(self):
        self.error_frame.hide()

    def add_field(self, label: str, widget, hint: str = ""):
        lbl = QLabel(label)
        lbl.setObjectName("FieldLabel")
        self.body_layout.addWidget(lbl)
        
        if isinstance(widget, (QLineEdit, QComboBox, QTextEdit)):
            widget.setMinimumWidth(200)
        
        self.body_layout.addWidget(widget)
        if hint:
            h = QLabel(hint)
            h.setObjectName("HintText")
            self.body_layout.addWidget(h)

    def add_row(self, *widgets):
        row = QHBoxLayout()
        row.setSpacing(8)
        for w in widgets:
            row.addWidget(w, 1)
        self.body_layout.addLayout(row)

    def add_field_row(self, *fields):
        """Add equally sized fields with labels above them to prevent label clipping."""
        row = QHBoxLayout()
        row.setSpacing(10)
        for label_text, widget in fields:
            container = QWidget()
            column = QVBoxLayout(container)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(4)
            label = QLabel(label_text)
            label.setObjectName("FieldLabel")
            column.addWidget(label)
            column.addWidget(widget)
            row.addWidget(container, 1)
        self.body_layout.addLayout(row)

    def add_separator(self):
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        self.body_layout.addWidget(sep)

    def add_section(self, title: str):
        lbl = QLabel(title)
        lbl.setObjectName("SectionTitle")
        self.body_layout.addWidget(lbl)

    def finalize(self):
        self.body_layout.addStretch()

    def _on_save(self):
        self._hide_error()
        try:
            data = self._collect()
            if data is not None:
                self._result_data = data
                self.accept()
        except ValidationError as e:
            self._show_error(str(e))
            self.scroll.verticalScrollBar().setValue(0)
        except Exception as e:
            self._show_error(f"Please check the form: {e}")
            self.scroll.verticalScrollBar().setValue(0)

    def showEvent(self, event):
        super().showEvent(event)
        refit_after_show(
            self, self._preferred_width, self._preferred_height or 620,
            minimum_width=360, minimum_height=300,
        )
        if self._first_show:
            self._first_show = False
            QTimer.singleShot(0, self._focus_first_field)

    def _focus_first_field(self):
        field = self.findChild(QLineEdit)
        if field and field.isEnabled():
            field.setFocus()

    def _collect(self) -> dict | None:
        return {}

    def get_data(self) -> dict | None:
        return self._result_data


class ValidationError(Exception):
    pass
