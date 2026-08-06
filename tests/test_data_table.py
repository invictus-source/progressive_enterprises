import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ui.components.data_table import DataTable


class DataTableSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_selection_keeps_original_record_after_visual_sort(self):
        table = DataTable(["Name", "Amount"])
        table.set_data([["Beta", "2"], ["Alpha", "1"]])
        table._table.sortItems(0, Qt.SortOrder.AscendingOrder)
        table._table.selectRow(0)
        self.assertEqual(table.get_selected_original_index(), 1)

    def test_filter_keeps_original_record_identity(self):
        table = DataTable(["Name"])
        table.set_data([["Battery"], ["Television"], ["Inverter"]])
        table._search.setText("invert")
        table._table.selectRow(0)
        self.assertEqual(table.get_selected_original_index(), 2)

    def test_cleared_selection_does_not_keep_a_hidden_active_record(self):
        table = DataTable(["Name"])
        table.set_data([["Battery"], ["Inverter"]])
        table._table.selectRow(0)
        table.clear_selection()
        self.assertIsNone(table.get_selected_original_index())


if __name__ == "__main__":
    unittest.main()
