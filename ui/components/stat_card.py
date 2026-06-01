"""
Progressive Enterprises – KPI Stat Card Widget
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QSizePolicy
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class StatCard(QWidget):
    """
    A KPI card displaying an icon, a large value, and a label.
    
    Usage:
        card = StatCard("💰", "Today's Revenue", "₹0", accent="#2563eb")
        card.update_value("₹12,450")
    """

    def __init__(self, icon: str, label: str, value: str = "—",
                 accent: str = "#2563eb", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self._accent = accent
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self._build_ui(icon, label, value)

    def _build_ui(self, icon: str, label: str, value: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(4)

        # Top row: icon + accent bar
        top = QHBoxLayout()
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(
            f"font-size: 22px; background: none;"
        )
        top.addWidget(icon_lbl)
        top.addStretch()

        accent_dot = QLabel("●")
        accent_dot.setStyleSheet(f"color: {self._accent}; font-size: 10px; background: none;")
        top.addWidget(accent_dot)
        layout.addLayout(top)

        # Value
        self._value_lbl = QLabel(value)
        self._value_lbl.setObjectName("StatValue")
        self._value_lbl.setWordWrap(True)
        self._value_lbl.setStyleSheet(
            f"font-size: 24px; font-weight: bold; color: #e2e8f0; background: none;"
        )
        layout.addWidget(self._value_lbl)

        # Label
        lbl = QLabel(label.upper())
        lbl.setObjectName("StatLabel")
        lbl.setWordWrap(True)
        lbl.setStyleSheet(
            "font-size: 10px; color: #8b949e; letter-spacing: 1px; background: none;"
        )
        layout.addWidget(lbl)

        self.setMinimumWidth(120)
        self.setMinimumHeight(70)

    def update_value(self, value: str):
        self._value_lbl.setText(value)
