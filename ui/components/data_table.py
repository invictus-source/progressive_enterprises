from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QHeaderView, QLabel, QLineEdit, QPushButton,
    QGridLayout, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont


class DataTable(QWidget):

    row_clicked = Signal(int)
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
        self._action_buttons: list[QPushButton] = []

        self._build_ui(searchable, actions or [])

    def _build_ui(self, searchable: bool, actions: list):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._toolbar = QGridLayout()
        self._toolbar.setSpacing(8)

        if searchable:
            self._search = QLineEdit()
            self._search.setObjectName("SearchBar")
            self._search.setPlaceholderText("Search records…")
            self._search.setClearButtonEnabled(True)
            self._search.setAccessibleName("Search records")
            self._search.setMinimumHeight(32)
            self._search.textChanged.connect(self._apply_filter)

        for index, (label, callback) in enumerate(actions):
            btn = QPushButton(label)
            btn.setObjectName("PrimaryBtn" if index == 0 else "SecondaryBtn")
            btn.setMinimumHeight(32)
            btn.clicked.connect(callback)
            self._action_buttons.append(btn)

        if searchable or actions:
            layout.addLayout(self._toolbar)
            self._arrange_toolbar(1200)

        self._table = QTableWidget()
        self._table.setColumnCount(len(self._columns))
        self._table.setHorizontalHeaderLabels(self._columns)
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._table.setWordWrap(False)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setSortingEnabled(True)
        self._table.clicked.connect(self._on_clicked)
        self._table.doubleClicked.connect(self._on_double_clicked)

        layout.addWidget(self._table)

        self._count_label = QLabel("0 records")
        self._count_label.setObjectName("MutedText")
        layout.addWidget(self._count_label)

    def set_data(self, data: list[list], resize_columns: bool = True):
        self._all_data = data
        self._apply_filter(getattr(self, '_search', None) and self._search.text() or "")
        if resize_columns:
            header = self._table.horizontalHeader()
            for i in range(len(self._columns) - 1):
                header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
                self._table.resizeColumnToContents(i)
                self._table.setColumnWidth(i, self._table.columnWidth(i) + 18)
            header.setSectionResizeMode(len(self._columns) - 1, QHeaderView.ResizeMode.Stretch)

    def get_selected_original_index(self) -> int | None:
        if not self._table.selectionModel().hasSelection():
            return None
        row = self._table.currentRow()
        if row < 0:
            return None
        item = self._table.item(row, 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

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
        sorting = self._table.isSortingEnabled()
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(self._filtered_data))
        for r, row in enumerate(self._filtered_data):
            original_index = self._original_indices[r]
            for c, cell in enumerate(row):
                item = QTableWidgetItem(str(cell) if cell is not None else "")
                item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
                item.setData(Qt.ItemDataRole.UserRole, original_index)
                item.setToolTip(item.text())
                self._table.setItem(r, c, item)
        self._table.setSortingEnabled(sorting)
        n = len(self._filtered_data)
        total = len(self._all_data)
        self._count_label.setText(
            ("No records found" if n == 0 else f"{n} record{'s' if n != 1 else ''}") +
            (f" (of {total})" if n != total else "")
        )

    def _arrange_toolbar(self, width: int):
        widgets = ([self._search] if hasattr(self, "_search") else []) + self._action_buttons
        for widget in widgets:
            self._toolbar.removeWidget(widget)
        count = max(1, len(self._action_buttons))
        if hasattr(self, "_search"):
            if width < 960:
                self._toolbar.addWidget(self._search, 0, 0, 1, max(2, min(count, 4)))
                start_row = 1
            else:
                self._toolbar.addWidget(self._search, 0, 0)
                start_row = 0
        else:
            start_row = 0

        for index, button in enumerate(self._action_buttons):
            if width < 680:
                row, column = start_row + index // 2, index % 2
            else:
                row = start_row
                column = index + (1 if start_row == 0 and hasattr(self, "_search") else 0)
            self._toolbar.addWidget(button, row, column)
        if hasattr(self, "_search") and width >= 960:
            self._toolbar.setColumnStretch(0, 1)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._arrange_toolbar(event.size().width())

    def _on_clicked(self, index):
        orig = self.get_selected_original_index()
        if orig is not None:
            self.row_clicked.emit(orig)

    def _on_double_clicked(self, index):
        orig = self.get_selected_original_index()
        if orig is not None:
            self.row_double_clicked.emit(orig)
