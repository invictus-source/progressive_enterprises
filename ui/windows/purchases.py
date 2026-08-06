from datetime import datetime

from PySide6.QtCore import QDate, Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QCompleter, QDateEdit, QDialog, QDoubleSpinBox,
    QFrame, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QMessageBox, QPlainTextEdit, QPushButton, QScrollArea,
    QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

import config
from core.auth import AuthSession
from core.purchase_calculations import calculate_purchase_invoice, calculate_purchase_line
from db.manager import get_db
from db.models import (
    InventoryUnit, Payment, Product, Purchase, PurchaseItem, StockMovement, Vendor,
)
from ui.components.data_table import DataTable
from ui.components.responsive import fit_dialog_to_screen, refit_after_show


def _next_grn(session) -> str:
    today = datetime.now()
    prefix = f"GRN-{today.year}{today.month:02d}"
    last = (
        session.query(Purchase)
        .filter(Purchase.grn_no.like(f"{prefix}%"))
        .order_by(Purchase.grn_no.desc())
        .first()
    )
    seq = int(last.grn_no.split("-")[-1]) + 1 if last else 1
    return f"{prefix}-{seq:04d}"


def _serials(text: str) -> list[str]:
    values = []
    for raw in text.replace(",", "\n").splitlines():
        value = raw.strip().upper()
        if value and value not in values:
            values.append(value)
    return values


class NewPurchaseDialog(QDialog):
    """Invoice-first purchase entry which posts a GRN and stock together."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Record Vendor Invoice & Receive Stock")
        self.setModal(True)
        self._items: list[dict] = []
        self._vendors: list[Vendor] = []
        self._products: list[Product] = []
        self._editing_row: int | None = None
        self._build_ui()
        self._load_data()
        fit_dialog_to_screen(self, 1180, 820, minimum_width=700, minimum_height=500)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        content = QWidget()
        root = QVBoxLayout(content)
        root.setContentsMargins(18, 12, 18, 12)
        root.setSpacing(8)

        heading = QLabel("Record purchase bill")
        heading.setObjectName("PageTitle")
        subtitle = QLabel(
            "Enter the vendor invoice as printed. Posting creates the GRN, input-GST record, "
            "serial-number units and stock movement in one transaction."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #94a3b8;")
        root.addWidget(heading)
        root.addWidget(subtitle)

        header_box = QGroupBox("1  Invoice & receipt")
        header = QGridLayout(header_box)
        header.setHorizontalSpacing(12)
        header.setVerticalSpacing(3)
        self.vendor_combo = QComboBox()
        self.vendor_combo.setMinimumWidth(250)
        self.vendor_combo.currentIndexChanged.connect(self._vendor_changed)
        self.bill_no_edit = QLineEdit()
        self.bill_no_edit.setPlaceholderText("e.g. 1224")
        self.invoice_date_edit = QDateEdit(QDate.currentDate())
        self.invoice_date_edit.setCalendarPopup(True)
        self.received_date_edit = QDateEdit(QDate.currentDate())
        self.received_date_edit.setCalendarPopup(True)
        self.tax_combo = QComboBox()
        self.tax_combo.addItem("Auto from vendor GSTIN", None)
        self.tax_combo.addItem("Local · CGST + SGST", False)
        self.tax_combo.addItem("Interstate · IGST", True)
        self.tax_combo.currentIndexChanged.connect(self._tax_changed)
        self.place_edit = QLineEdit(config.COMPANY_STATE)
        self.place_edit.setPlaceholderText("Place of supply")

        fields = [
            ("Vendor *", self.vendor_combo), ("Vendor invoice no. *", self.bill_no_edit),
            ("Invoice date *", self.invoice_date_edit), ("Received date *", self.received_date_edit),
            ("Tax treatment", self.tax_combo), ("Place of supply", self.place_edit),
        ]
        for i, (label, widget) in enumerate(fields):
            col = i % 2
            row = (i // 2) * 2
            header.addWidget(QLabel(label), row, col)
            header.addWidget(widget, row + 1, col)
        root.addWidget(header_box)

        line_box = QGroupBox("2  Add invoice line")
        line_layout = QVBoxLayout(line_box)
        line_layout.setSpacing(4)
        picker = QGridLayout()
        self.product_combo = QComboBox()
        self.product_combo.setEditable(True)
        self.product_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.product_combo.setMinimumWidth(280)
        self.product_combo.currentIndexChanged.connect(self._product_changed)
        completer = QCompleter(self.product_combo.model(), self.product_combo)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.product_combo.setCompleter(completer)

        new_product_btn = QPushButton("+ New product")
        new_product_btn.clicked.connect(self._new_product)
        product_row = QHBoxLayout()
        product_row.setContentsMargins(0, 0, 0, 0)
        product_row.addWidget(self.product_combo, 1)
        product_row.addWidget(new_product_btn)

        self.qty_spin = QSpinBox()
        self.qty_spin.setRange(1, 9999)
        self.qty_spin.setValue(1)
        self.rate_spin = QDoubleSpinBox()
        self.rate_spin.setRange(0, 99_999_999)
        self.rate_spin.setDecimals(2)
        self.rate_spin.setPrefix("₹ ")
        self.discount_spin = QDoubleSpinBox()
        self.discount_spin.setRange(0, 100)
        self.discount_spin.setDecimals(2)
        self.discount_spin.setSuffix(" %")
        self.gst_combo = QComboBox()
        self.gst_combo.addItems([f"{r}%" for r in config.GST_SLABS])
        self.gst_combo.setCurrentText("18%")
        self.tax_inclusive_check = QCheckBox("Rate includes GST")
        self.tax_inclusive_check.setChecked(True)
        self.tax_inclusive_check.setToolTip(
            "Keep this checked when the printed rate already includes GST, as in most vendor bills."
        )

        picker.addWidget(QLabel("Product / model *"), 0, 0, 1, 5)
        picker.addLayout(product_row, 1, 0, 1, 5)
        for column, (label, widget) in enumerate([
            ("Qty *", self.qty_spin), ("Printed unit rate *", self.rate_spin),
            ("Discount", self.discount_spin), ("GST", self.gst_combo),
        ]):
            picker.addWidget(QLabel(label), 2, column)
            picker.addWidget(widget, 3, column)
        picker.addWidget(self.tax_inclusive_check, 3, 4)
        line_layout.addLayout(picker)

        self.product_meta = QLabel("Select a product to see its HSN, model and serial policy.")
        self.product_meta.setStyleSheet("color: #94a3b8; font-size: 11px;")
        line_layout.addWidget(self.product_meta)

        serial_row = QHBoxLayout()
        serial_col = QVBoxLayout()
        serial_col.addWidget(QLabel("Serial / IMEI numbers (one per line; required for serial-tracked products)"))
        self.serial_edit = QPlainTextEdit()
        self.serial_edit.setFixedHeight(42)
        self.serial_edit.setPlaceholderText("A3E6J905195 CE63\nA3E6J905140 CE63")
        serial_col.addWidget(self.serial_edit)
        serial_row.addLayout(serial_col, 1)
        self.add_item_btn = QPushButton("Add line")
        self.add_item_btn.setObjectName("PrimaryBtn")
        self.add_item_btn.setMinimumHeight(38)
        self.add_item_btn.clicked.connect(self._add_item)
        serial_row.addWidget(self.add_item_btn, alignment=Qt.AlignmentFlag.AlignBottom)
        line_layout.addLayout(serial_row)
        self.item_error_lbl = QLabel("")
        self.item_error_lbl.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
        line_layout.addWidget(self.item_error_lbl)
        root.addWidget(line_box)

        self.items_table = QTableWidget()
        self.items_table.setColumnCount(10)
        self.items_table.setHorizontalHeaderLabels([
            "Product", "HSN", "Qty", "Printed rate", "Basic rate", "Disc.",
            "Taxable", "GST", "Serials", "Line total",
        ])
        self.items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.items_table.setAlternatingRowColors(True)
        self.items_table.setMinimumHeight(135)
        self.items_table.verticalHeader().setVisible(False)
        self.items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.items_table.setColumnWidth(0, 200)
        for col in range(1, 10):
            self.items_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.cellDoubleClicked.connect(self._edit_item)
        root.addWidget(self.items_table, 1)
        table_actions = QHBoxLayout()
        table_hint = QLabel("Double-click a line to edit it.")
        table_hint.setStyleSheet("color: #64748b; font-size: 10px;")
        remove_line_btn = QPushButton("Remove selected line")
        remove_line_btn.clicked.connect(self._remove_selected_item)
        table_actions.addWidget(table_hint)
        table_actions.addStretch()
        table_actions.addWidget(remove_line_btn)
        root.addLayout(table_actions)

        footer = QVBoxLayout()
        payment_box = QGroupBox("3  Payment")
        payment = QGridLayout(payment_box)
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["Credit / Unpaid", "Cash", "UPI", "Bank Transfer", "Cheque"])
        self.paid_spin = QDoubleSpinBox()
        self.paid_spin.setRange(0, 999_999_999)
        self.paid_spin.setDecimals(2)
        self.paid_spin.setPrefix("₹ ")
        self.paid_spin.valueChanged.connect(self._update_balance)
        self.payment_combo.currentTextChanged.connect(self._payment_mode_changed)
        self.balance_lbl = QLabel("Balance: ₹0.00")
        payment.addWidget(QLabel("Mode"), 0, 0)
        payment.addWidget(self.payment_combo, 1, 0)
        payment.addWidget(QLabel("Paid now"), 0, 1)
        payment.addWidget(self.paid_spin, 1, 1)
        payment.addWidget(self.balance_lbl, 1, 2)
        footer.addWidget(payment_box)

        totals_box = QGroupBox("Invoice totals")
        totals = QGridLayout(totals_box)
        self.taxable_lbl = QLabel("₹0.00")
        self.gst_lbl = QLabel("₹0.00")
        self.round_lbl = QLabel("₹0.00")
        self.total_lbl = QLabel("₹0.00")
        self.total_lbl.setStyleSheet("font-size: 20px; font-weight: 800; color: #60a5fa;")
        self.round_check = QCheckBox("Round to nearest ₹")
        self.round_check.setChecked(True)
        self.round_check.toggled.connect(self._refresh_table)
        totals.addWidget(QLabel("Taxable"), 0, 0)
        totals.addWidget(self.taxable_lbl, 0, 1, alignment=Qt.AlignmentFlag.AlignRight)
        totals.addWidget(QLabel("GST"), 0, 2)
        totals.addWidget(self.gst_lbl, 0, 3, alignment=Qt.AlignmentFlag.AlignRight)
        totals.addWidget(QLabel("Round off"), 1, 0)
        totals.addWidget(self.round_lbl, 1, 1, alignment=Qt.AlignmentFlag.AlignRight)
        totals.addWidget(QLabel("Grand total"), 1, 2)
        totals.addWidget(self.total_lbl, 1, 3, alignment=Qt.AlignmentFlag.AlignRight)
        totals.addWidget(self.round_check, 2, 0, 1, 4)
        footer.addWidget(totals_box)
        root.addLayout(footer)

        actions = QHBoxLayout()
        actions.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Post purchase & receive stock")
        save_btn.setObjectName("SuccessBtn")
        save_btn.setMinimumHeight(40)
        save_btn.clicked.connect(self._save)
        actions.addWidget(cancel_btn)
        actions.addWidget(save_btn)
        root.addLayout(actions)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _load_data(self, select_product_id=None):
        session = get_db()
        try:
            self._vendors = session.query(Vendor).filter_by(is_active=True).order_by(Vendor.name).all()
            self._products = session.query(Product).filter_by(is_active=True).order_by(Product.name).all()
            # Detach the simple master records so the dialog never holds a DB session open.
            for record in [*self._vendors, *self._products]:
                session.expunge(record)
        finally:
            session.close()

        current_vendor = self.vendor_combo.currentData()
        self.vendor_combo.blockSignals(True)
        self.vendor_combo.clear()
        self.vendor_combo.addItem("— Select vendor —", None)
        for vendor in self._vendors:
            gst = f" · {vendor.gstin}" if vendor.gstin else ""
            self.vendor_combo.addItem(f"{vendor.name}{gst}", vendor.id)
        idx = self.vendor_combo.findData(current_vendor)
        if idx >= 0:
            self.vendor_combo.setCurrentIndex(idx)
        self.vendor_combo.blockSignals(False)

        self.product_combo.blockSignals(True)
        self.product_combo.clear()
        self.product_combo.addItem("— Select product —", None)
        for product in self._products:
            details = " · ".join(x for x in [product.brand, product.model_no] if x)
            self.product_combo.addItem(f"{product.name}{' · ' + details if details else ''}", product.id)
        if select_product_id:
            idx = self.product_combo.findData(select_product_id)
            if idx >= 0:
                self.product_combo.setCurrentIndex(idx)
        self.product_combo.blockSignals(False)
        self._vendor_changed()
        self._product_changed()

    def _vendor_changed(self):
        vendor = next((v for v in self._vendors if v.id == self.vendor_combo.currentData()), None)
        if vendor and vendor.city and not self.place_edit.text().strip():
            self.place_edit.setText(vendor.city)
        self._tax_changed()

    def _is_interstate(self) -> bool:
        forced = self.tax_combo.currentData()
        if forced is not None:
            return bool(forced)
        vendor = next((v for v in self._vendors if v.id == self.vendor_combo.currentData()), None)
        vendor_code = (vendor.gstin or "")[:2] if vendor else ""
        company_code = str(config.COMPANY_STATE_CODE or "").zfill(2)
        return bool(vendor_code and company_code and vendor_code != company_code)

    def _tax_changed(self):
        for item in self._items:
            item["calc"] = calculate_purchase_line(
                qty=item["qty"], invoice_rate=item["invoice_rate"],
                discount_pct=item["discount_pct"], gst_rate=item["gst_rate"],
                tax_inclusive=item["tax_inclusive"], interstate=self._is_interstate(),
            )
        self._refresh_table()

    def _product_changed(self):
        product = next((p for p in self._products if p.id == self.product_combo.currentData()), None)
        if not product:
            self.product_meta.setText("Select a product to see its HSN, model and serial policy.")
            return
        self.rate_spin.setValue(float(product.purchase_price or 0))
        self.gst_combo.setCurrentText(f"{int(product.gst_rate or 0)}%")
        policy = "Serial numbers required" if product.track_serials else "Serial numbers optional"
        self.product_meta.setText(
            f"Brand: {product.brand or '—'}   ·   Model: {product.model_no or '—'}   ·   "
            f"HSN: {product.hsn_code or '—'}   ·   {policy}"
        )

    def _new_product(self):
        from ui.windows.inventory import AddEditProductDialog

        dialog = AddEditProductDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        session = get_db()
        try:
            product = Product(**dialog.get_data())
            session.add(product)
            session.commit()
            product_id = product.id
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Could not add product", str(exc))
            return
        finally:
            session.close()
        self._load_data(select_product_id=product_id)

    def _add_item(self):
        self.item_error_lbl.clear()
        product = next((p for p in self._products if p.id == self.product_combo.currentData()), None)
        if not product:
            self.item_error_lbl.setText("Select a product from the list.")
            return
        qty = self.qty_spin.value()
        serial_numbers = _serials(self.serial_edit.toPlainText())
        if product.track_serials and len(serial_numbers) != qty:
            self.item_error_lbl.setText(f"{product.name} requires {qty} unique serial number(s).")
            return
        if serial_numbers and len(serial_numbers) != qty:
            self.item_error_lbl.setText(f"Enter exactly {qty} unique serial number(s), or leave the box empty.")
            return
        used = {sn for i, item in enumerate(self._items) if i != self._editing_row for sn in item["serials"]}
        duplicate = next((sn for sn in serial_numbers if sn in used), None)
        if duplicate:
            self.item_error_lbl.setText(f"Serial number {duplicate} is already used in this invoice.")
            return
        try:
            calc = calculate_purchase_line(
                qty=qty, invoice_rate=self.rate_spin.value(),
                discount_pct=self.discount_spin.value(),
                gst_rate=float(self.gst_combo.currentText().replace("%", "")),
                tax_inclusive=self.tax_inclusive_check.isChecked(),
                interstate=self._is_interstate(),
            )
        except ValueError as exc:
            self.item_error_lbl.setText(str(exc))
            return
        item = {
            "product_id": product.id, "product_name": product.name,
            "hsn_code": product.hsn_code, "qty": qty,
            "invoice_rate": self.rate_spin.value(),
            "discount_pct": self.discount_spin.value(),
            "gst_rate": float(self.gst_combo.currentText().replace("%", "")),
            "tax_inclusive": self.tax_inclusive_check.isChecked(),
            "serials": serial_numbers, "calc": calc,
        }
        if self._editing_row is None:
            self._items.append(item)
        else:
            self._items[self._editing_row] = item
        self._clear_line_editor()
        self._refresh_table()

    def _clear_line_editor(self):
        self._editing_row = None
        self.add_item_btn.setText("Add line")
        self.qty_spin.setValue(1)
        self.rate_spin.setValue(0)
        self.discount_spin.setValue(0)
        self.serial_edit.clear()
        self.product_combo.setCurrentIndex(0)

    def _edit_item(self, row, _column=0):
        if not 0 <= row < len(self._items):
            return
        item = self._items[row]
        self._editing_row = row
        self.product_combo.setCurrentIndex(self.product_combo.findData(item["product_id"]))
        self.qty_spin.setValue(item["qty"])
        self.rate_spin.setValue(item["invoice_rate"])
        self.discount_spin.setValue(item["discount_pct"])
        self.gst_combo.setCurrentText(f"{int(item['gst_rate'])}%")
        self.tax_inclusive_check.setChecked(item["tax_inclusive"])
        self.serial_edit.setPlainText("\n".join(item["serials"]))
        self.add_item_btn.setText("Update line")

    def _remove_item(self, row):
        if 0 <= row < len(self._items):
            self._items.pop(row)
            self._clear_line_editor()
            self._refresh_table()

    def _remove_selected_item(self):
        self._remove_item(self.items_table.currentRow())

    def _invoice_totals(self):
        return calculate_purchase_invoice(
            [item["calc"] for item in self._items],
            round_to_rupee=self.round_check.isChecked(),
        )

    def _refresh_table(self):
        if not hasattr(self, "items_table"):
            return
        self.items_table.setRowCount(len(self._items))
        for row, item in enumerate(self._items):
            calc = item["calc"]
            values = [
                item["product_name"], item["hsn_code"] or "—", str(item["qty"]),
                f"₹{calc.invoice_rate:,.2f}", f"₹{calc.basic_rate:,.2f}",
                f"{item['discount_pct']:g}%", f"₹{calc.taxable_amount:,.2f}",
                f"{item['gst_rate']:g}% · ₹{calc.gst_amount:,.2f}",
                f"{len(item['serials'])}/{item['qty']}", f"₹{calc.line_total:,.2f}",
            ]
            for col, value in enumerate(values):
                self.items_table.setItem(row, col, QTableWidgetItem(value))

        totals = self._invoice_totals()
        self.taxable_lbl.setText(f"₹{totals.taxable_amount:,.2f}")
        tax_name = "IGST" if self._is_interstate() else "CGST + SGST"
        self.gst_lbl.setText(f"₹{totals.total_gst:,.2f} · {tax_name}")
        self.round_lbl.setText(f"₹{totals.round_off:+,.2f}")
        self.total_lbl.setText(f"₹{totals.grand_total:,.2f}")
        self.paid_spin.setMaximum(float(totals.grand_total))
        self._update_balance()

    def _update_balance(self):
        if not hasattr(self, "balance_lbl"):
            return
        total = float(self._invoice_totals().grand_total)
        balance = max(0.0, total - self.paid_spin.value())
        self.balance_lbl.setText(f"Balance: ₹{balance:,.2f}")

    def _payment_mode_changed(self, mode: str):
        if mode == "Credit / Unpaid":
            self.paid_spin.setValue(0)
        elif self.paid_spin.value() == 0:
            self.paid_spin.setValue(float(self._invoice_totals().grand_total))

    def showEvent(self, event):
        super().showEvent(event)
        refit_after_show(self, 1180, 820, minimum_width=700, minimum_height=500)

    def _save(self):
        vendor_id = self.vendor_combo.currentData()
        bill_no = self.bill_no_edit.text().strip()
        if not vendor_id:
            QMessageBox.warning(self, "Vendor required", "Select the vendor who issued this invoice.")
            return
        if not bill_no:
            QMessageBox.warning(self, "Invoice number required", "Enter the vendor invoice number.")
            return
        if not self._items:
            QMessageBox.warning(self, "No items", "Add at least one invoice line.")
            return
        invoice_date = self.invoice_date_edit.date().toPython()
        received_date = self.received_date_edit.date().toPython()
        if received_date < invoice_date:
            QMessageBox.warning(self, "Check dates", "Received date cannot be before the vendor invoice date.")
            return

        session = get_db()
        try:
            duplicate = session.query(Purchase).filter_by(vendor_id=vendor_id, bill_no=bill_no).first()
            if duplicate:
                raise ValueError(
                    f"Invoice {bill_no} is already recorded for this vendor as {duplicate.grn_no}."
                )
            all_serials = [sn for item in self._items for sn in item["serials"]]
            existing = (
                session.query(InventoryUnit)
                .filter(InventoryUnit.serial_number.in_(all_serials)).first()
                if all_serials else None
            )
            if existing:
                raise ValueError(f"Serial number {existing.serial_number} already exists in inventory.")

            totals = self._invoice_totals()
            paid = round(self.paid_spin.value(), 2)
            if paid > float(totals.grand_total):
                raise ValueError("Paid amount cannot exceed the invoice grand total.")
            if paid > 0 and self.payment_combo.currentText() == "Credit / Unpaid":
                raise ValueError("Select the actual payment mode for the amount paid now.")
            user = AuthSession.current_user()
            grn = _next_grn(session)
            purchase = Purchase(
                grn_no=grn, bill_no=bill_no, vendor_id=vendor_id,
                purchase_date=datetime.combine(received_date, datetime.now().time()),
                invoice_date=invoice_date, received_date=received_date,
                place_of_supply=self.place_edit.text().strip() or config.COMPANY_STATE,
                tax_treatment="Interstate" if self._is_interstate() else "Local",
                status="Posted", subtotal=float(totals.subtotal),
                discount_amount=float(totals.discount_amount),
                taxable_amount=float(totals.taxable_amount),
                cgst_amount=float(totals.cgst_amount), sgst_amount=float(totals.sgst_amount),
                igst_amount=float(totals.igst_amount), total_gst=float(totals.total_gst),
                round_off=float(totals.round_off), grand_total=float(totals.grand_total),
                payment_mode=self.payment_combo.currentText(), amount_paid=paid,
                balance_due=round(float(totals.grand_total) - paid, 2),
                created_by=user.id if user else None,
            )
            session.add(purchase)
            session.flush()

            for item in self._items:
                calc = item["calc"]
                line = PurchaseItem(
                    purchase_id=purchase.id, product_id=item["product_id"],
                    product_name=item["product_name"], qty=item["qty"],
                    unit_price=float(calc.basic_rate), invoice_rate=float(calc.invoice_rate),
                    is_tax_inclusive=item["tax_inclusive"],
                    discount_pct=item["discount_pct"],
                    discount_amount=float(calc.discount_amount), hsn_code=item["hsn_code"],
                    gst_rate=item["gst_rate"], taxable_amount=float(calc.taxable_amount),
                    gst_amount=float(calc.gst_amount), line_total=float(calc.line_total),
                )
                session.add(line)
                session.flush()
                product = session.get(Product, item["product_id"])
                product.stock_qty = int(product.stock_qty or 0) + item["qty"]
                product.purchase_price = float(calc.basic_rate)
                session.add(StockMovement(
                    product_id=product.id, movement_type="Purchase",
                    quantity=item["qty"], resulting_stock=product.stock_qty,
                    reference_type="Purchase", reference_id=purchase.id,
                    notes=f"{grn} · vendor invoice {bill_no}",
                    created_by=user.id if user else None,
                ))
                warranty_expiry = (
                    QDate(received_date.year, received_date.month, received_date.day)
                    .addMonths(int(product.warranty_months or 0)).toPython()
                    if product.warranty_months else None
                )
                for serial_number in item["serials"]:
                    session.add(InventoryUnit(
                        product_id=product.id, purchase_item_id=line.id,
                        serial_number=serial_number, status="In Stock",
                        received_at=datetime.combine(received_date, datetime.min.time()),
                        warranty_expiry=warranty_expiry,
                    ))
            if paid > 0:
                payment_mode = {
                    "Bank Transfer": "NEFT/RTGS",
                }.get(self.payment_combo.currentText(), self.payment_combo.currentText())
                session.add(Payment(
                    payment_type="payment", vendor_id=vendor_id,
                    purchase_id=purchase.id, amount=paid, mode=payment_mode,
                    payment_date=datetime.combine(received_date, datetime.now().time()),
                    notes=f"Payment recorded while posting {grn}",
                    created_by=user.id if user else None,
                ))
            session.commit()
        except Exception as exc:
            session.rollback()
            QMessageBox.critical(self, "Purchase not posted", str(exc))
            return
        finally:
            session.close()
        QMessageBox.information(
            self, "Purchase posted",
            f"{grn} was created. Stock, serial units and input GST were updated together."
        )
        self.accept()


class PurchaseDetailDialog(QDialog):
    def __init__(self, purchase_id: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Purchase details")
        fit_dialog_to_screen(self, 900, 560, minimum_width=520, minimum_height=360)
        root = QVBoxLayout(self)
        session = get_db()
        try:
            purchase = session.get(Purchase, purchase_id)
            if not purchase:
                root.addWidget(QLabel("Purchase not found."))
                return
            title = QLabel(f"{purchase.grn_no}  ·  Vendor invoice {purchase.bill_no or '—'}")
            title.setObjectName("PageTitle")
            root.addWidget(title)
            root.addWidget(QLabel(
                f"{purchase.vendor.name if purchase.vendor else 'Unknown vendor'}   ·   "
                f"Invoice: {(purchase.invoice_date or purchase.purchase_date.date()).strftime('%d %b %Y')}   ·   "
                f"Received: {(purchase.received_date or purchase.purchase_date.date()).strftime('%d %b %Y')}   ·   "
                f"{purchase.tax_treatment or 'Local'}"
            ))
            table = QTableWidget(len(purchase.items), 8)
            table.setHorizontalHeaderLabels([
                "Product", "HSN", "Qty", "Printed rate", "Discount", "Taxable", "GST", "Serial numbers",
            ])
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
            for row, item in enumerate(purchase.items):
                serials = ", ".join(unit.serial_number for unit in item.inventory_units) or "—"
                values = [
                    item.product_name, item.hsn_code or "—", str(item.qty),
                    f"₹{(item.invoice_rate or item.unit_price):,.2f}", f"{item.discount_pct or 0:g}%",
                    f"₹{item.taxable_amount:,.2f}", f"₹{item.gst_amount:,.2f}", serials,
                ]
                for col, value in enumerate(values):
                    table.setItem(row, col, QTableWidgetItem(value))
            root.addWidget(table)
            total = QLabel(
                f"Taxable ₹{purchase.taxable_amount:,.2f}   +   GST ₹{purchase.total_gst:,.2f}   "
                f"+   Round off ₹{(purchase.round_off or 0):+.2f}   =   ₹{purchase.grand_total:,.2f}\n"
                f"Paid ₹{purchase.amount_paid:,.2f}   ·   Balance ₹{purchase.balance_due:,.2f}"
            )
            total.setAlignment(Qt.AlignmentFlag.AlignRight)
            total.setStyleSheet("font-size: 15px; font-weight: 700;")
            root.addWidget(total)
        finally:
            session.close()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        root.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)


class PurchasesPage(QWidget):
    def __init__(self):
        super().__init__()
        self._purchase_ids: list[int] = []
        self._build_ui()

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

        title = QLabel("Purchases / GRN")
        title.setObjectName("PageTitle")
        layout.addWidget(title)
        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("color: #94a3b8;")
        layout.addWidget(self.summary_lbl)
        self.table = DataTable(
            columns=[
                "GRN", "Vendor invoice", "Vendor", "Invoice date", "Received",
                "Qty", "Input GST", "Grand total", "Balance", "Status",
            ],
            searchable=True,
            actions=[("➕  Record purchase", self._new_purchase), ("View details", self._view)],
        )
        self.table.row_double_clicked.connect(self._view)
        layout.addWidget(self.table)
        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        session = get_db()
        try:
            purchases = session.query(Purchase).order_by(Purchase.purchase_date.desc()).limit(500).all()
            self._purchase_ids = [purchase.id for purchase in purchases]
            rows = []
            for purchase in purchases:
                invoice_date = purchase.invoice_date or purchase.purchase_date.date()
                received_date = purchase.received_date or purchase.purchase_date.date()
                rows.append([
                    purchase.grn_no, purchase.bill_no or "—",
                    purchase.vendor.name if purchase.vendor else "—",
                    invoice_date.strftime("%d %b %Y"), received_date.strftime("%d %b %Y"),
                    str(sum(item.qty for item in purchase.items)), f"₹{purchase.total_gst:,.2f}",
                    f"₹{purchase.grand_total:,.2f}", f"₹{purchase.balance_due:,.2f}",
                    purchase.status or "Posted",
                ])
            self.table.set_data(rows)
            self.summary_lbl.setText(
                f"{len(purchases)} bills   ·   Input GST ₹{sum(p.total_gst for p in purchases):,.2f}   ·   "
                f"Payable ₹{sum(p.balance_due for p in purchases):,.2f}"
            )
        finally:
            session.close()

    def _selected_id(self):
        idx = self.table.get_selected_original_index()
        if idx is None or not 0 <= idx < len(self._purchase_ids):
            QMessageBox.information(self, "Select purchase", "Select a purchase to view its details.")
            return None
        return self._purchase_ids[idx]

    def _new_purchase(self):
        dialog = NewPurchaseDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _view(self, _idx=None):
        purchase_id = self._selected_id()
        if purchase_id:
            PurchaseDetailDialog(purchase_id, self).exec()
