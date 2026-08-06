import os
import tempfile
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import config
from db.manager import DatabaseManager, get_db
from db.models import Customer, Payment, Product, Sale, SaleItem, StockMovement
from ui.windows.pos import POSPage, QuickProductDialog


class QuickSaleWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.temp_dir = tempfile.TemporaryDirectory(prefix="progressive-quick-sale-")
        config.DATA_DIR = cls.temp_dir.name
        config.DB_PATH = os.path.join(cls.temp_dir.name, "test.db")
        DatabaseManager.init()

    @classmethod
    def tearDownClass(cls):
        if DatabaseManager.engine is not None:
            DatabaseManager.engine.dispose()
        DatabaseManager.engine = None
        DatabaseManager.SessionLocal = None
        cls.temp_dir.cleanup()

    def setUp(self):
        session = get_db()
        try:
            session.query(Payment).delete()
            session.query(StockMovement).delete()
            session.query(SaleItem).delete()
            session.query(Sale).delete()
            session.query(Customer).delete()
            session.query(Product).delete()
            session.commit()
            product = Product(
                name="Quick Sale Inverter",
                barcode="QS-1001",
                selling_price=1000,
                gst_rate=18,
                stock_qty=2,
                min_stock=1,
                unit="Pcs",
            )
            session.add(product)
            session.commit()
            self.product_id = product.id
        finally:
            session.close()

    def test_credit_sale_uses_inline_customer_and_tracks_full_balance(self):
        session = get_db()
        try:
            customer = Customer(name="Ravi", phone="9876543210")
            session.add(customer)
            session.commit()
            customer_id = customer.id
        finally:
            session.close()

        page = POSPage()
        page.resize(760, 480)
        page.refresh()
        page._selected_customer_id = customer_id
        page.product_search.setText("QS-1001")
        self.app.processEvents()
        page._add_search_result()
        page.payment_mode_combo.setCurrentText("Credit")
        page._confirm_sale(False)

        session = get_db()
        try:
            sale = session.query(Sale).one()
            self.assertEqual(sale.customer_id, customer_id)
            self.assertEqual(sale.payment_mode, "Credit")
            self.assertAlmostEqual(sale.amount_received, 0.0)
            self.assertAlmostEqual(sale.balance_due, 1180.0)
            self.assertEqual(session.query(Payment).count(), 0)
        finally:
            session.close()

    def test_unknown_scanned_barcode_opens_quick_item_with_barcode_filled(self):
        dialog = QuickProductDialog("8901234567890")
        self.assertEqual(dialog.name_edit.text(), "")
        self.assertEqual(dialog.barcode_edit.text(), "8901234567890")

        named_dialog = QuickProductDialog("Television")
        self.assertEqual(named_dialog.name_edit.text(), "Television")
        self.assertEqual(named_dialog.barcode_edit.text(), "")

    def test_barcode_to_saved_walk_in_sale_updates_stock_and_ledger(self):
        page = POSPage()
        page.resize(760, 480)
        page.refresh()

        page.product_search.setText("QS-1001")
        self.app.processEvents()
        self.assertEqual(page.product_results.currentData(), self.product_id)

        page._add_search_result()
        self.assertEqual(len(page._cart), 1)
        page._confirm_sale(False)

        session = get_db()
        try:
            sale = session.query(Sale).one()
            product = session.get(Product, self.product_id)
            movement = session.query(StockMovement).filter_by(
                movement_type="Sale", reference_id=sale.id).one()
            self.assertIsNone(sale.customer_id)
            self.assertAlmostEqual(sale.grand_total, 1180.0)
            self.assertAlmostEqual(sale.amount_received, 1180.0)
            self.assertEqual(product.stock_qty, 1)
            self.assertEqual(movement.quantity, -1)
            self.assertEqual(movement.resulting_stock, 1)
        finally:
            session.close()

    def test_walk_in_credit_is_not_saved_without_customer(self):
        page = POSPage()
        page.resize(760, 480)
        page.refresh()
        page.product_search.setText("QS-1001")
        self.app.processEvents()
        page._add_search_result()
        page.payment_mode_combo.setCurrentText("Credit")

        page._confirm_sale(False)

        session = get_db()
        try:
            self.assertEqual(session.query(Sale).count(), 0)
            self.assertEqual(session.get(Product, self.product_id).stock_qty, 2)
        finally:
            session.close()


if __name__ == "__main__":
    unittest.main()
