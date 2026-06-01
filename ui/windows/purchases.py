from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame, QScrollArea,
    QTableWidget, QTableWidgetItem, QDialog, QMessageBox,
    QHeaderView, QDateEdit
)
from PySide6.QtCore import Qt, QDate

from db.manager import get_db
from db.models import Purchase, PurchaseItem, Vendor, Product
from ui.components.data_table import DataTable
from core.auth import AuthSession
import config

def _next_grn(session) -> str:
    today = datetime.now()
    prefix = f"GRN-{today.year}{today.month:02d}"
    last = session.query(Purchase).filter(Purchase.grn_no.like(f"{prefix}%")).order_by(Purchase.grn_no.desc()).first()
    seq = int(last.grn_no.split("-")[-1]) + 1 if last else 1
    return f"{prefix}-{seq:04d}"

def _parse_int(text: str, field: str, min_val: int = 1, max_val: int = 9999) -> int:
    text = text.strip()
    if not text:
        raise ValueError(f"{field} is required.")
    try:
        val = int(text)
    except ValueError:
        raise ValueError(f"{field} must be a whole number (e.g. 5).")
    if val < min_val:
        raise ValueError(f"{field} must be at least {min_val}.")
    if val > max_val:
        raise ValueError(f"{field} must be no more than {max_val}.")
    return val

def _parse_float(text: str, field: str, min_val: float = 0.0, max_val: float = 999999.0) -> float:
    text = text.strip().lstrip("₹").strip()
    if not text:
        raise ValueError(f"{field} is required.")
    try:
        val = float(text)
    except ValueError:
        raise ValueError(f"{field} must be a number (e.g. 1250.00).")
    if val < min_val:
        raise ValueError(f"{field} must be at least {min_val}.")
    if val > max_val:
        raise ValueError(f"{field} must be no more than {max_val}.")
    return val

class NewPurchaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Purchase / GRN Entry")
        self.setMinimumSize(900, 620)
        self.setModal(True)
        self._items: list[dict] = []
        self._vendors: list[Vendor] = []
        self._products: list[Product] = []
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(14)

        hdr = QHBoxLayout()
        hdr.setSpacing(14)

        self.vendor_combo = QComboBox(); self.vendor_combo.setMinimumWidth(200)
        self.bill_no_edit = QLineEdit(); self.bill_no_edit.setPlaceholderText("Vendor Bill No.")
        self.date_edit = QDateEdit(QDate.currentDate()); self.date_edit.setCalendarPopup(True)

        for lbl, w in [("Vendor", self.vendor_combo), ("Bill No.", self.bill_no_edit), ("Date", self.date_edit)]:
            col = QVBoxLayout()
            col.addWidget(QLabel(lbl))
            col.addWidget(w)
            hdr.addLayout(col)
        root.addLayout(hdr)

        add_row = QHBoxLayout(); add_row.setSpacing(10)
        self.product_combo = QComboBox(); self.product_combo.setMinimumWidth(250)

        self.qty_edit = QLineEdit()
        self.qty_edit.setPlaceholderText("Qty (e.g. 5)")
        self.qty_edit.setFixedWidth(90)

        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("Unit Price (₹)")
        self.price_edit.setFixedWidth(130)

        self.gst_combo = QComboBox()
        self.gst_combo.addItems([f"{r}%" for r in config.GST_SLABS])
        self.gst_combo.setCurrentText("18%")

        add_item_btn = QPushButton("Add Item"); add_item_btn.setObjectName("PrimaryBtn")
        add_item_btn.clicked.connect(self._add_item)

        for lbl, w in [("Product", self.product_combo), ("Qty *", self.qty_edit),
                        ("Unit Price * (₹)", self.price_edit), ("GST", self.gst_combo)]:
            col = QVBoxLayout(); col.addWidget(QLabel(lbl)); col.addWidget(w)
            add_row.addLayout(col)
        add_row.addWidget(add_item_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        root.addLayout(add_row)

        self.item_error_lbl = QLabel("")
        self.item_error_lbl.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
        root.addWidget(self.item_error_lbl)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(["Product", "Qty", "Unit Price", "GST%", "Taxable", "GST Amt", "Total"])
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.items_table, 1)

        bottom = QHBoxLayout()
        self.totals_lbl = QLabel("Grand Total: ₹0.00")
        self.totals_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #60a5fa;")
        bottom.addWidget(self.totals_lbl)
        bottom.addStretch()
        remove_btn = QPushButton("Remove Selected"); remove_btn.clicked.connect(self._remove_item)
        save_btn = QPushButton("Save GRN"); save_btn.setObjectName("SuccessBtn")
        save_btn.clicked.connect(self._save)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        for b in [remove_btn, cancel_btn, save_btn]:
            b.setFixedHeight(36); bottom.addWidget(b)
        root.addLayout(bottom)

    def _load_data(self):
        session = get_db()
        try:
            self._vendors = session.query(Vendor).filter_by(is_active=True).all()
            self.vendor_combo.addItem("— Select Vendor —", None)
            for v in self._vendors:
                self.vendor_combo.addItem(v.name, v.id)
            self._products = session.query(Product).filter_by(is_active=True).order_by(Product.name).all()
            self.product_combo.addItem("— Select Product —", None)
            for p in self._products:
                self.product_combo.addItem(f"{p.name} ({p.brand or ''})", p.id)
        finally:
            session.close()

    def _add_item(self):
        self.item_error_lbl.setText("")
        pid = self.product_combo.currentData()
        if not pid:
            self.item_error_lbl.setText("Please select a product.")
            return
        product = next((p for p in self._products if p.id == pid), None)
        if not product:
            return
        try:
            qty = _parse_int(self.qty_edit.text(), "Qty", 1, 9999)
            price = _parse_float(self.price_edit.text(), "Unit Price", 0.0, 999999.0)
        except ValueError as e:
            self.item_error_lbl.setText(str(e))
            return

        gst_rate = float(self.gst_combo.currentText().replace("%", ""))
        taxable = qty * price
        gst_amt = taxable * gst_rate / 100
        self._items.append({
            "product": product,
            "qty": qty, "unit_price": price, "gst_rate": gst_rate,
            "taxable": taxable, "gst_amt": gst_amt, "total": taxable + gst_amt,
        })
        self._refresh_table()
        self.qty_edit.clear()
        self.price_edit.clear()

    def _remove_item(self):
        row = self.items_table.currentRow()
        if 0 <= row < len(self._items):
            self._items.pop(row)
            self._refresh_table()

    def _refresh_table(self):
        self.items_table.setRowCount(len(self._items))
        grand = 0.0
        for r, it in enumerate(self._items):
            for c, v in enumerate([
                it["product"].name, str(it["qty"]), f"₹{it['unit_price']:,.2f}",
                f"{it['gst_rate']}%", f"₹{it['taxable']:,.2f}",
                f"₹{it['gst_amt']:,.2f}", f"₹{it['total']:,.2f}",
            ]):
                self.items_table.setItem(r, c, QTableWidgetItem(v))
            grand += it["total"]
        self.totals_lbl.setText(f"Grand Total: ₹{grand:,.2f}")

    def _save(self):
        if not self._items:
            QMessageBox.warning(self, "Empty", "Please add items.")
            return
        session = get_db()
        try:
            grn = _next_grn(session)
            subtotal = sum(i["qty"] * i["unit_price"] for i in self._items)
            gst_total = sum(i["gst_amt"] for i in self._items)
            grand = subtotal + gst_total
            user = AuthSession.current_user()

            purchase = Purchase(
                grn_no=grn,
                bill_no=self.bill_no_edit.text().strip() or None,
                vendor_id=self.vendor_combo.currentData(),
                purchase_date=self.date_edit.date().toPython(),
                subtotal=subtotal,
                taxable_amount=subtotal,
                cgst_amount=gst_total / 2, sgst_amount=gst_total / 2,
                total_gst=gst_total, grand_total=grand,
                amount_paid=grand, balance_due=0.0,
                created_by=user.id if user else None,
            )
            session.add(purchase)
            session.flush()
            for it in self._items:
                pi = PurchaseItem(
                    purchase_id=purchase.id, product_id=it["product"].id,
                    product_name=it["product"].name, qty=it["qty"],
                    unit_price=it["unit_price"], gst_rate=it["gst_rate"],
                    taxable_amount=it["taxable"], gst_amount=it["gst_amt"],
                    line_total=it["total"],
                )
                session.add(pi)
                p = session.query(Product).get(it["product"].id)
                p.stock_qty += it["qty"]
                p.purchase_price = it["unit_price"]
            session.commit()
            QMessageBox.information(self, "Success", f"GRN {grn} saved. Stock updated.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

class PurchasesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._purchases = []
        self._build_ui()

    def _build_ui(self):
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(14)

        hdr = QHBoxLayout()
        title = QLabel("Purchases / GRN"); title.setObjectName("PageTitle")
        hdr.addWidget(title); hdr.addStretch()
        layout.addLayout(hdr)

        self.table = DataTable(
            columns=["GRN No.", "Bill No.", "Vendor", "Date", "Items", "Total", "Balance"],
            searchable=True,
            actions=[("➕  New Purchase", self._new_purchase)],
        )
        layout.addWidget(self.table)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        session = get_db()
        try:
            self._purchases = session.query(Purchase).order_by(Purchase.purchase_date.desc()).limit(200).all()
            rows = []
            for p in self._purchases:
                rows.append([
                    p.grn_no, p.bill_no or "—",
                    p.vendor.name if p.vendor else "—",
                    p.purchase_date.strftime("%d %b %Y"),
                    str(len(p.items)),
                    f"₹{p.grand_total:,.0f}",
                    f"₹{p.balance_due:,.0f}",
                ])
            self.table.set_data(rows)
        finally:
            session.close()

    def _new_purchase(self):
        dlg = NewPurchaseDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()
