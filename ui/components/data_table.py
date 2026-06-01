"""
Progressive Enterprises – Reusable Data Table Widget
Sortable, filterable QTableWidget with alternating rows.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QPushButton
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class DataTable(QWidget):
    """
    A polished table widget with an optional search bar and action buttons.
    
    Usage:
        table = DataTable(
            columns=["Name", "Phone", "City"],
            searchable=True,
            actions=[("➕ Add", self.on_add), ("🗑 Delete", self.on_delete)],
        )
        table.set_data([
            ["John Doe", "9876543210", "Jaipur"],
            ...
        ])
    """

    row_clicked = Signal(int)       # emits the original data-row index
    row_double_clicked = Signal(int)

    def __init__(
        self,
        columns: list[str],
        searchable: bool = True,
        actions: list[tuple] = None,
        parent=None,
    ):
        super().__init__(parent)
        self._columns = columns
        self._all_data: list[list] = []
        self._filtered_data: list[list] = []
        self._original_indices: list[int] = []

        self._build_ui(searchable, actions or [])

    def _build_ui(self, searchable: bool, actions: list):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Top bar: search + action buttons
        top_bar = QHBoxLayout()
        top_bar.setSpacing(8)

        if searchable:
            self._search = QLineEdit()
            self._search.setObjectName("SearchBar")
            self._search.setPlaceholderText("🔍  Search...")
            self._search.setMinimumHeight(32)
            self._search.textChanged.connect(self._apply_filter)
            top_bar.addWidget(self._search)
        else:
            top_bar.addStretch()

        for label, callback in actions:
            btn = QPushButton(label)
            btn.setObjectName("PrimaryBtn")
            btn.setMinimumHeight(32)
            btn.clicked.connect(callback)
            top_bar.addWidget(btn)

        if top_bar.count() > 0:
            layout.addLayout(top_bar)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._columns))
        self._table.setHorizontalHeaderLabels(self._columns)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(True)
        self._table.clicked.connect(self._on_clicked)
        self._table.doubleClicked.connect(self._on_double_clicked)

        layout.addWidget(self._table)

        # Row count label
        self._count_label = QLabel("0 records")
        self._count_label.setStyleSheet("color: #6e7681; font-size: 11px;")
        layout.addWidget(self._count_label)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_data(self, data: list[list], resize_columns: bool = True):
        """Load a 2D list into the table (one sublist per row)."""
        self._all_data = data
        self._apply_filter(getattr(self, '_search', None) and self._search.text() or "")
        if resize_columns:
            header = self._table.horizontalHeader()
            for i in range(len(self._columns) - 1):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(len(self._columns) - 1, QHeaderView.ResizeMode.Stretch)

    def get_selected_original_index(self) -> int | None:
        """Returns the data-index (into _all_data) of the selected row, or None."""
        rows = self._table.selectedItems()
        if not rows:
            return None
        visual_row = self._table.currentRow()
        if visual_row < len(self._original_indices):
            return self._original_indices[visual_row]
        return None

    def get_selected_row_data(self) -> list | None:
        idx = self.get_selected_original_index()
        if idx is not None:
            return self._all_data[idx]
        return None

    def clear_selection(self):
        self._table.clearSelection()

    def set_column_width(self, col: int, width: int):
        self._table.setColumnWidth(col, width)

    def hide_column(self, col: int):
        self._table.setColumnHidden(col, True)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _apply_filter(self, text: str = ""):
        text = text.lower().strip()
        self._filtered_data = []
        self._original_indices = []

        for idx, row in enumerate(self._all_data):
            if not text or any(text in str(cell).lower() for cell in row):
                self._filtered_data.append(row)
                self._original_indices.append(idx)

        self._populate_table()

    def _populate_table(self):
        self._table.setRowCount(len(self._filtered_data))
        for r, row in enumerate(self._filtered_data):
            for c, cell in enumerate(row):
                item = QTableWidgetItem(str(cell) if cell is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                self._table.setItem(r, c, item)
        n = len(self._filtered_data)
        total = len(self._all_data)
        self._count_label.setText(
            f"{n} record{'s' if n != 1 else ''}" +
            (f" (of {total})" if n != total else "")
        )

    def _on_clicked(self, index):
        orig = self.get_selected_original_index()
        if orig is not None:
            self.row_clicked.emit(orig)

    def _on_double_clicked(self, index):
        orig = self.get_selected_original_index()
        if orig is not None:
            self.row_double_clicked.emit(orig)
