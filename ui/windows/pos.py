from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QScrollArea, QSizePolicy, QListWidget, QListWidgetItem,
    QSpinBox, QGridLayout, QApplication
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIntValidator, QDoubleValidator, QKeySequence, QShortcut

from db.manager import get_db
from db.models import (
    Product, Customer, Sale, SaleItem, Payment, FinanceProvider, StockMovement,
)
from core.auth import AuthSession
from ui.components.toast import Toast, show_toast, show_success, show_warning, show_error
from ui.components.form_dialog import FormDialog, ValidationError
import config


class QuickCustomerDialog(FormDialog):
    """The only customer details needed while a customer is waiting."""

    def __init__(self, suggested_name: str = "", parent=None):
        super().__init__(
            "Add Customer to This Bill",
            "Name is enough. Phone is optional and other details can be added later.",
            width=440, height=340, parent=parent,
        )
        self.name_edit = QLineEdit(suggested_name)
        self.name_edit.setPlaceholderText("Customer name")
        self.phone_edit = QLineEdit()
        self.phone_edit.setPlaceholderText("Phone number (optional)")
        self.add_field("Customer Name *", self.name_edit)
        self.add_field("Phone", self.phone_edit)
        self.save_btn.setText("Add Customer")
        self.finalize()

    def _collect(self):
        name = self.name_edit.text().strip()
        if not name:
            raise ValidationError("Enter the customer name.")
        return {"name": name, "phone": self.phone_edit.text().strip()}


class QuickProductDialog(FormDialog):
    """Short product form used without leaving an in-progress bill."""

    def __init__(self, suggested_name: str = "", parent=None):
        super().__init__(
            "Add New Item to This Bill",
            "Enter the sale details now. Full product details can be added later.",
            width=500, height=560, parent=parent,
        )
        looks_like_barcode = bool(
            suggested_name
            and " " not in suggested_name
            and len(suggested_name) >= 8
            and sum(character.isdigit() for character in suggested_name) >= 4
        )
        self.name_edit = QLineEdit("" if looks_like_barcode else suggested_name)
        self.name_edit.setPlaceholderText("e.g. Luminous Eco Volt 1050")
        self.add_field("Item Name *", self.name_edit)

        self.brand_edit = QLineEdit()
        self.brand_edit.setPlaceholderText("e.g. Luminous")
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("Model number")
        self.add_field_row(("Brand", self.brand_edit), ("Model", self.model_edit))

        self.price_edit = QLineEdit()
        self.price_edit.setPlaceholderText("0.00")
        self.price_edit.setValidator(QDoubleValidator(0.01, 9_999_999, 2))
        self.add_field("Sale Price before GST (₹) *", self.price_edit)

        self.stock_spin = QSpinBox()
        self.stock_spin.setRange(1, 99_999)
        self.stock_spin.setValue(1)
        self.stock_spin.setSuffix(" pcs available")
        self.gst_combo = QComboBox()
        self.gst_combo.addItems([f"{rate}%" for rate in config.GST_SLABS])
        self.gst_combo.setCurrentText("18%")
        self.add_field_row(("Stock Available Now", self.stock_spin), ("GST Rate", self.gst_combo))

        self.barcode_edit = QLineEdit()
        self.barcode_edit.setPlaceholderText("Scan or type barcode (optional)")
        if looks_like_barcode:
            self.barcode_edit.setText(suggested_name)
        self.add_field("Barcode / SKU", self.barcode_edit)
        self.save_btn.setText("Save & Add to Bill")
        self.finalize()

    def _collect(self):
        name = self.name_edit.text().strip()
        if not name:
            raise ValidationError("Enter the item name.")
        try:
            selling_price = float(self.price_edit.text().strip())
        except ValueError:
            raise ValidationError("Enter a valid sale price.")
        if selling_price <= 0:
            raise ValidationError("Sale price must be greater than zero.")
        return {
            "name": name,
            "brand": self.brand_edit.text().strip() or None,
            "model_no": self.model_edit.text().strip() or None,
            "selling_price": selling_price,
            "purchase_price": 0.0,
            "stock_qty": self.stock_spin.value(),
            "min_stock": 1,
            "gst_rate": float(self.gst_combo.currentText().replace("%", "")),
            "barcode": self.barcode_edit.text().strip() or None,
            "unit": "Pcs",
        }

class CustomerSearchWidget(QWidget):
    customer_selected = Signal(object, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries: list[tuple] = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or phone…")
        self.search_input.setMinimumHeight(34)
        self.search_input.textChanged.connect(self._on_text_changed)
        self.search_input.installEventFilter(self)
        layout.addWidget(self.search_input)

        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setMaximumHeight(224)
        self.list_widget.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.list_widget.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget.setFrameShape(QFrame.Shape.StyledPanel)
        self.list_widget.setStyleSheet(
            "QListWidget {"
            "  border-radius: 8px; font-size: 13px;"
            "}"
            "QListWidget::item {"
            "  padding: 8px 10px; border-radius: 4px;"
            "}"
        )
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        self.list_widget.setVisible(False)
        layout.addWidget(self.list_widget)

    def load_customers(self, customers: list):
        self._all_entries = [(None, "Walk-in Customer")]
        for c in customers:
            display = f"{c.name}  –  {c.phone}" if c.phone else c.name
            self._all_entries.append((c.id, display))

    def set_customer(self, customer_id, display_text: str):
        self.search_input.blockSignals(True)
        self.search_input.setText(display_text)
        self.search_input.blockSignals(False)
        self.list_widget.setVisible(False)

    def clear_selection(self):
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.list_widget.setVisible(False)

    def _populate_list(self, filter_text: str = ""):
        ft = filter_text.strip().lower()
        matches = [
            (cid, disp) for cid, disp in self._all_entries
            if not ft or ft in disp.lower()
        ]
        self.list_widget.clear()
        for cid, disp in matches:
            item = QListWidgetItem(disp)
            item.setData(Qt.ItemDataRole.UserRole, cid)
            self.list_widget.addItem(item)
        self.list_widget.setVisible(bool(matches))

    def _hide_list(self):
        self.list_widget.setVisible(False)

    def _on_text_changed(self, text: str):
        if not text.strip():
            self._populate_list("")
            self.customer_selected.emit(None, "Walk-in Customer")
        else:
            self._populate_list(text)

    def _on_item_clicked(self, item: QListWidgetItem):
        cid  = item.data(Qt.ItemDataRole.UserRole)
        disp = item.text()
        self.search_input.blockSignals(True)
        self.search_input.setText(disp)
        self.search_input.blockSignals(False)
        self.list_widget.setVisible(False)
        self.customer_selected.emit(cid, disp)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.search_input:
            if event.type() == QEvent.Type.FocusIn:
                self._populate_list(self.search_input.text())
            elif event.type() == QEvent.Type.FocusOut:
                QTimer.singleShot(80, self._hide_list)
            elif event.type() == QEvent.Type.KeyPress:
                key = event.key()
                if self.list_widget.isVisible():
                    if key == Qt.Key.Key_Down:
                        cur = self.list_widget.currentRow()
                        self.list_widget.setCurrentRow(
                            min(cur + 1, self.list_widget.count() - 1))
                        return True
                    elif key == Qt.Key.Key_Up:
                        cur = self.list_widget.currentRow()
                        self.list_widget.setCurrentRow(max(cur - 1, 0))
                        return True
                    elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                        item = self.list_widget.currentItem()
                        if item:
                            self._on_item_clicked(item)
                        return True
                    elif key == Qt.Key.Key_Escape:
                        self._hide_list()
                        return True
        return super().eventFilter(obj, event)

def _next_invoice_no(session) -> str:
    today = datetime.now()
    prefix = f"INV-{today.year}{today.month:02d}"
    last = (session.query(Sale)
            .filter(Sale.invoice_no.like(f"{prefix}%"))
            .order_by(Sale.invoice_no.desc()).first())
    if last:
        seq = int(last.invoice_no.split("-")[-1]) + 1
    else:
        seq = 1
    return f"{prefix}-{seq:04d}"

class CartItem:
    def __init__(self, product: Product, qty: int = 1, discount_pct: float = 0.0):
        self.product = product
        self.qty = qty
        self.discount_pct = discount_pct
        self._recalc()

    def _recalc(self):
        base = self.product.selling_price * self.qty
        self.line_discount = base * self.discount_pct / 100
        self.taxable = base - self.line_discount
        self.gst_amount = self.taxable * self.product.gst_rate / 100
        self.line_total = self.taxable + self.gst_amount

class POSPage(QWidget):
    def __init__(self):
        super().__init__()
        self._cart: list[CartItem] = []
        self._customers: list[Customer] = []
        self._selected_customer_id = None
        self._customer_data = {}
        self._build_ui()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 8, 12)
        root.setSpacing(12)

        left_scroll = QScrollArea()
        self.left_scroll = left_scroll
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setSpacing(10)
        left.setContentsMargins(4, 4, 4, 4)

        title = QLabel("New Sale / Billing")
        title.setObjectName("PageTitle")
        left.addWidget(title)

        search_frame = QFrame(); search_frame.setObjectName("Card")
        sf_layout = QVBoxLayout(search_frame)
        sf_layout.setContentsMargins(12, 10, 12, 10)
        sf_layout.setSpacing(8)

        search_row = QGridLayout()
        search_row.setSpacing(8)

        self.product_search = QLineEdit()
        self.product_search.setObjectName("SearchBar")
        self.product_search.setPlaceholderText("Type product name, brand or scan barcode…")
        self.product_search.setMinimumHeight(34)
        self.product_search.textChanged.connect(self._search_products)
        self.product_search.returnPressed.connect(self._add_search_result)
        search_row.addWidget(self.product_search, 0, 0)

        self.product_results = QComboBox()
        self.product_results.setMinimumWidth(200)
        self.product_results.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.product_results.setMinimumContentsLength(12)
        self.product_results.setMinimumHeight(34)
        self.product_results.currentIndexChanged.connect(self._on_product_select)
        search_row.addWidget(self.product_results, 1, 0, 1, 2)

        self.quick_product_btn = QPushButton("＋ New Item")
        self.quick_product_btn.setObjectName("GhostBtn")
        self.quick_product_btn.setMinimumHeight(34)
        self.quick_product_btn.setToolTip("Create an item without leaving this bill (F3)")
        self.quick_product_btn.clicked.connect(self._quick_add_product)
        search_row.addWidget(self.quick_product_btn, 0, 1)
        search_row.setColumnStretch(0, 1)
        sf_layout.addLayout(search_row)

        qty_row = QHBoxLayout()
        qty_row.setSpacing(10)

        qty_lbl = QLabel("Qty:")
        qty_lbl.setStyleSheet("font-weight: 600; color: #94a3b8;")
        qty_row.addWidget(qty_lbl)

        self.qty_input = QLineEdit("1")
        self.qty_input.setMinimumHeight(38)
        self.qty_input.setMinimumWidth(50)
        self.qty_input.setMaximumWidth(80)
        self.qty_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qty_input.setValidator(QIntValidator(1, 9999))
        self.qty_input.setPlaceholderText("Qty")
        qty_row.addWidget(self.qty_input)

        disc_lbl = QLabel("Disc %:")
        disc_lbl.setStyleSheet("font-weight: 600; color: #94a3b8;")
        qty_row.addWidget(disc_lbl)

        self.disc_input = QLineEdit("0")
        self.disc_input.setMinimumHeight(38)
        self.disc_input.setMinimumWidth(40)
        self.disc_input.setMaximumWidth(70)
        self.disc_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.disc_input.setPlaceholderText("0")
        self.disc_input.setToolTip("Item-level discount percentage (0 – 100)")
        qty_row.addWidget(self.disc_input)

        self.stock_lbl = QLabel("")
        self.stock_lbl.setStyleSheet("color: #60a5fa; font-size: 11px;")
        qty_row.addWidget(self.stock_lbl)
        qty_row.addStretch()

        self.add_to_cart_btn = QPushButton("＋  Add Item")
        self.add_to_cart_btn.setObjectName("PrimaryBtn")
        self.add_to_cart_btn.setMinimumHeight(34)
        self.add_to_cart_btn.setMinimumWidth(120)
        self.add_to_cart_btn.clicked.connect(self._add_to_cart)
        qty_row.addWidget(self.add_to_cart_btn)
        sf_layout.addLayout(qty_row)

        left.addWidget(search_frame)

        cart_header = QLabel("Items in this bill")
        cart_header.setObjectName("SectionTitle")
        left.addWidget(cart_header)

        self.cart_table = QTableWidget()
        self.cart_table.setColumnCount(7)
        self.cart_table.setHorizontalHeaderLabels(
            ["Product", "Rate", "Qty", "Disc%", "Taxable", "GST", "Total"])
        self.cart_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.verticalHeader().setVisible(False)
        self.cart_table.horizontalHeader().setStretchLastSection(True)
        self.cart_table.setMinimumHeight(120)
        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        left.addWidget(self.cart_table, 1)
        self.cart_table.cellDoubleClicked.connect(self._edit_cart_item)

        cart_actions = QHBoxLayout()
        hint_lbl = QLabel("Tip: Double-click an item to change quantity or discount")
        hint_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        hint_lbl.setWordWrap(True)
        cart_actions.addWidget(hint_lbl)
        cart_actions.addStretch()
        self.remove_btn = QPushButton("🗑  Remove Selected")
        self.remove_btn.setMinimumHeight(28)
        self.remove_btn.clicked.connect(self._remove_from_cart)
        cart_actions.addWidget(self.remove_btn)
        left.addLayout(cart_actions)

        left_scroll.setWidget(left_widget)
        root.addWidget(left_scroll, 3)

        right_scroll = QScrollArea()
        self.right_scroll = right_scroll
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setSpacing(10)
        right.setContentsMargins(4, 4, 4, 4)

        cust_frame = QFrame(); cust_frame.setObjectName("Card")
        cf = QVBoxLayout(cust_frame); cf.setContentsMargins(12, 10, 12, 10)
        cf.setSpacing(6)

        cust_header = QGridLayout()
        cust_lbl = QLabel("Customer (optional)")
        cust_lbl.setStyleSheet("font-weight: 700; font-size: 12px;")
        cust_header.addWidget(cust_lbl, 0, 0, 1, 2)
        self.quick_customer_btn = QPushButton("＋ New Customer")
        self.quick_customer_btn.setObjectName("GhostBtn")
        self.quick_customer_btn.setMinimumHeight(24)
        self.quick_customer_btn.setToolTip("Add a customer without leaving this bill (F2)")
        self.quick_customer_btn.clicked.connect(self._quick_add_customer)
        cust_header.addWidget(self.quick_customer_btn, 1, 0)
        self.clear_customer_btn = QPushButton("✕  Clear")
        self.clear_customer_btn.setObjectName("FlatBtn")
        self.clear_customer_btn.setMinimumHeight(24)
        self.clear_customer_btn.clicked.connect(self._clear_customer)
        cust_header.addWidget(self.clear_customer_btn, 1, 1)
        cust_header.setColumnStretch(0, 1)
        cf.addLayout(cust_header)

        self.customer_picker = CustomerSearchWidget()
        self.customer_picker.customer_selected.connect(self._on_customer_selected)
        cf.addWidget(self.customer_picker)

        self.selected_customer_lbl = QLabel("Walk-in Customer — no details needed")
        self.selected_customer_lbl.setStyleSheet("color: #60a5fa; font-size: 11px; padding: 2px 0;")
        self.selected_customer_lbl.setWordWrap(True)
        cf.addWidget(self.selected_customer_lbl)

        right.addWidget(cust_frame)

        totals_frame = QFrame(); totals_frame.setObjectName("Card")
        tf = QVBoxLayout(totals_frame); tf.setContentsMargins(14, 12, 14, 12); tf.setSpacing(6)

        summary_hdr = QHBoxLayout()
        summary_hdr.addWidget(QLabel("Bill Summary"))
        summary_hdr.addStretch()
        tf.addLayout(summary_hdr)
        tf.addWidget(self._h_line())

        def add_row(label, widget, bold=False):
            row = QHBoxLayout()
            lbl = QLabel(label)
            lbl.setObjectName("SectionTitle" if bold else "MutedText")
            row.addWidget(lbl); row.addStretch(); row.addWidget(widget)
            tf.addLayout(row)
            return widget

        self.lbl_subtotal  = QLabel("₹0.00")
        self.lbl_discount  = QLabel("₹0.00")
        self.lbl_extra_disc = QLabel("₹0.00")
        self.lbl_taxable   = QLabel("₹0.00")
        self.lbl_cgst      = QLabel("₹0.00")
        self.lbl_sgst      = QLabel("₹0.00")
        self.lbl_grand     = QLabel("₹0.00")
        self.lbl_grand.setStyleSheet("font-size: 20px; font-weight: bold; color: #60a5fa;")

        add_row("Subtotal", self.lbl_subtotal)
        add_row("Item Discounts", self.lbl_discount)

        extra_disc_row = QHBoxLayout()
        extra_disc_lbl = QLabel("Extra Discount (₹)")
        extra_disc_lbl.setObjectName("MutedText")
        extra_disc_row.addWidget(extra_disc_lbl)
        extra_disc_row.addStretch()
        self.extra_discount_input = QLineEdit("0")
        self.extra_discount_input.setMinimumWidth(60)
        self.extra_discount_input.setMaximumWidth(120)
        self.extra_discount_input.setMinimumHeight(26)
        self.extra_discount_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.extra_discount_input.setPlaceholderText("0.00")
        self.extra_discount_input.setToolTip("Flat discount applied on the whole bill (e.g. 50 = ₹50 off)")
        self.extra_discount_input.textChanged.connect(self._update_totals)
        extra_disc_row.addWidget(self.extra_discount_input)
        tf.addLayout(extra_disc_row)

        add_row("Taxable Amount", self.lbl_taxable)
        add_row("CGST", self.lbl_cgst)
        add_row("SGST", self.lbl_sgst)
        tf.addWidget(self._h_line())

        grand_row = QHBoxLayout()
        grand_lbl = QLabel("GRAND TOTAL")
        grand_lbl.setObjectName("SectionTitle")
        grand_row.addWidget(grand_lbl); grand_row.addStretch(); grand_row.addWidget(self.lbl_grand)
        tf.addLayout(grand_row)
        right.addWidget(totals_frame)

        pay_frame = QFrame(); pay_frame.setObjectName("Card")
        pf = QVBoxLayout(pay_frame); pf.setContentsMargins(12, 10, 12, 10)
        pf.setSpacing(6)
        pf.addWidget(QLabel("Payment Mode"))
        self.payment_mode_combo = QComboBox()
        self.payment_mode_combo.addItems(["Cash", "UPI", "Card", "Credit", "EMI", "Mixed"])
        self.payment_mode_combo.setMinimumHeight(32)
        self.payment_mode_combo.currentTextChanged.connect(self._on_payment_mode_changed)
        pf.addWidget(self.payment_mode_combo)

        self.provider_lbl = QLabel("Finance Provider")
        self.provider_lbl.hide()
        self.finance_provider_combo = QComboBox()
        self.finance_provider_combo.setMinimumHeight(32)
        self.finance_provider_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.finance_provider_combo.setMinimumContentsLength(10)
        self.finance_provider_combo.hide()
        pf.addWidget(self.provider_lbl)
        pf.addWidget(self.finance_provider_combo)

        self.amount_received_lbl = QLabel("Amount Received")
        pf.addWidget(self.amount_received_lbl)
        self.amount_received_input = QLineEdit()
        self.amount_received_input.setMinimumHeight(32)
        self.amount_received_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.amount_received_input.setValidator(QDoubleValidator(0, 9999999, 2))
        self.amount_received_input.setText("0.00")
        self.amount_received_input.textChanged.connect(self._update_balance)
        pf.addWidget(self.amount_received_input)

        self.lbl_balance = QLabel("Balance: ₹0.00")
        self.lbl_balance.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: bold;")
        self.lbl_balance.setWordWrap(True)
        pf.addWidget(self.lbl_balance)

        self.payment_hint = QLabel("")
        self.payment_hint.setObjectName("HintText")
        self.payment_hint.setWordWrap(True)
        pf.addWidget(self.payment_hint)

        right.addWidget(pay_frame)
        right.addStretch()

        sale_actions = QVBoxLayout()
        sale_actions.setSpacing(8)

        self.confirm_btn = QPushButton("Save & Print Bill  (F4)")
        self.confirm_btn.setObjectName("SuccessBtn")
        self.confirm_btn.setMinimumHeight(40)
        self.confirm_btn.clicked.connect(lambda: self._confirm_sale(True))
        sale_actions.addWidget(self.confirm_btn)

        self.save_only_btn = QPushButton("Save Only")
        self.save_only_btn.setObjectName("GhostBtn")
        self.save_only_btn.setMinimumHeight(34)
        self.save_only_btn.setToolTip("Save the sale without opening the invoice")
        self.save_only_btn.clicked.connect(lambda: self._confirm_sale(False))
        sale_actions.addWidget(self.save_only_btn)
        right.addLayout(sale_actions)

        clear_btn = QPushButton("🗑  Clear Cart")
        clear_btn.setObjectName("DangerBtn")
        clear_btn.setMinimumHeight(34)
        clear_btn.clicked.connect(self._clear_cart)
        right.addWidget(clear_btn)

        right_scroll.setWidget(right_widget)
        root.addWidget(right_scroll, 2)

        QShortcut(QKeySequence("F2"), self).activated.connect(self._quick_add_customer)
        QShortcut(QKeySequence("F3"), self).activated.connect(self._quick_add_product)
        QShortcut(QKeySequence("F4"), self).activated.connect(
            lambda: self._confirm_sale(True))
        QShortcut(QKeySequence("Ctrl+L"), self).activated.connect(
            self._focus_product_search)

        self._update_compact_table()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_compact_table()

    def _update_compact_table(self):
        """Keep the bill readable by hiding accounting detail on narrow screens."""
        if not hasattr(self, "cart_table"):
            return
        compact = self.width() < 980
        very_compact = compact and QApplication.font().pointSize() >= 14
        self.cart_table.setColumnHidden(1, very_compact)
        for column in (3, 4, 5):  # discount, taxable and GST remain in Bill Summary
            self.cart_table.setColumnHidden(column, compact)
        header = self.cart_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in (1, 2, 6):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.quick_product_btn.setText("＋ Item" if compact else "＋ New Item")
        self.add_to_cart_btn.setText("＋ Add" if compact else "＋  Add Item")
        self.quick_customer_btn.setText("＋ Customer" if compact else "＋ New Customer")
        self.clear_customer_btn.setText("✕" if compact else "✕  Clear")
        self.clear_customer_btn.setMaximumWidth(42 if compact else 16_777_215)
        self.remove_btn.setText("Remove" if compact else "🗑  Remove Selected")
        self.confirm_btn.setText("Save & Print (F4)" if compact else "Save & Print Bill  (F4)")
        self.customer_picker.search_input.setPlaceholderText(
            "Find customer…" if compact else "Search by name or phone…")
        if self._selected_customer_id is None:
            self.selected_customer_lbl.setText(
                "Walk-in Customer" if compact else "Walk-in Customer — no details needed")

    def _h_line(self):
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
        return f

    def _focus_product_search(self):
        self.product_search.setFocus()
        self.product_search.selectAll()

    def _quick_add_customer(self):
        suggested = self.customer_picker.search_input.text().strip()
        dlg = QuickCustomerDialog(suggested, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.get_data()
        session = get_db()
        try:
            phone = data["phone"]
            existing = None
            if phone:
                existing = session.query(Customer).filter(
                    Customer.phone == phone, Customer.is_active == True).first()
            if existing:
                customer_id = existing.id
                display = f"{existing.name}  –  {existing.phone}"
            else:
                customer = Customer(name=data["name"], phone=phone)
                session.add(customer)
                session.commit()
                customer_id = customer.id
                display = f"{customer.name}  –  {customer.phone}" if customer.phone else customer.name
        except Exception as exc:
            session.rollback()
            show_error(self, f"Could not add customer: {exc}")
            return
        finally:
            session.close()

        self._load_customers(reset_selection=False)
        self._selected_customer_id = customer_id
        self.customer_picker.set_customer(customer_id, display)
        self.selected_customer_lbl.setText(f"✓  {display}")
        self._focus_product_search()

    def _quick_add_product(self):
        suggested = self.product_search.text().strip()
        dlg = QuickProductDialog(suggested, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        data = dlg.get_data()
        session = get_db()
        try:
            barcode = data.get("barcode")
            if barcode and session.query(Product).filter(Product.barcode == barcode).first():
                show_warning(self, "This barcode is already used by another item.")
                return
            product = Product(**data)
            session.add(product)
            session.flush()
            user = AuthSession.current_user()
            session.add(StockMovement(
                product_id=product.id,
                movement_type="Opening",
                quantity=product.stock_qty,
                resulting_stock=product.stock_qty,
                reference_type="Quick Sale",
                notes="Item created while making a bill",
                created_by=user.id if user else None,
            ))
            session.commit()
            product_id = product.id
            product_name = product.name
        except Exception as exc:
            session.rollback()
            show_error(self, f"Could not add item: {exc}")
            return
        finally:
            session.close()

        self.product_search.setText(product_name)
        index = self.product_results.findData(product_id)
        if index >= 0:
            self.product_results.setCurrentIndex(index)
        self._add_to_cart()

    def _add_search_result(self):
        if self.product_results.currentData():
            self._add_to_cart()
        else:
            self._quick_add_product()

    def refresh(self):
        self._load_customers()
        self._load_providers()
        self._search_products("")
        QTimer.singleShot(0, self._focus_product_search)

    def _on_payment_mode_changed(self, text: str):
        if text == "EMI":
            self.amount_received_lbl.setText("Down Payment")
            self.provider_lbl.show()
            self.finance_provider_combo.show()
            self.amount_received_input.setEnabled(True)
            self.payment_hint.setText("Enter any down payment. A registered customer is required for EMI.")
            self.amount_received_input.setText("0.00")
            self._update_balance()
        elif text == "Credit":
            self.amount_received_lbl.setText("Amount Received")
            self.provider_lbl.hide()
            self.finance_provider_combo.hide()
            self.amount_received_input.setText("0.00")
            self.amount_received_input.setEnabled(False)
            self.payment_hint.setText("A customer is required so the balance can be tracked.")
            self._update_balance()
        else:
            self.amount_received_lbl.setText("Amount Received")
            self.provider_lbl.hide()
            self.finance_provider_combo.hide()
            self.amount_received_input.setEnabled(True)
            self.payment_hint.setText(
                "Enter the amount received now." if text == "Mixed" else "")
            if text in ("Cash", "UPI", "Card"):
                try:
                    grand = float(self.lbl_grand.text().replace("₹", "").replace(",", ""))
                except ValueError:
                    grand = 0.0
                self.amount_received_input.setText(f"{grand:.2f}")
            self._update_balance()

    def _load_providers(self):
        session = get_db()
        try:
            fps = session.query(FinanceProvider).filter_by(is_active=True).all()
            self.finance_provider_combo.clear()
            self.finance_provider_combo.addItem("— Select Provider —", None)
            for fp in fps:
                self.finance_provider_combo.addItem(fp.name, fp.id)
        finally:
            session.close()

    def _load_customers(self, reset_selection: bool = True):
        session = get_db()
        try:
            self._customers = session.query(Customer).filter_by(
                is_active=True).order_by(Customer.name).all()
            self.customer_picker.load_customers(self._customers)
            if reset_selection:
                self._selected_customer_id = None
                self.customer_picker.clear_selection()
                self.selected_customer_lbl.setText(
                    "Walk-in Customer" if self.width() < 980
                    else "Walk-in Customer — no details needed")
        finally:
            session.close()

    def _on_customer_selected(self, customer_id, display_text: str):
        self._selected_customer_id = customer_id
        if customer_id is None:
            self.selected_customer_lbl.setText(
                "Walk-in Customer" if self.width() < 980
                else "Walk-in Customer — no details needed")
        else:
            self.selected_customer_lbl.setText(f"✓  {display_text}")

    def _clear_customer(self):
        self._selected_customer_id = None
        self.customer_picker.clear_selection()
        self.selected_customer_lbl.setText(
            "Walk-in Customer" if self.width() < 980
            else "Walk-in Customer — no details needed")

    def _search_products(self, text: str):
        session = get_db()
        try:
            q = session.query(Product).filter(Product.is_active == True, Product.stock_qty > 0)
            if text.strip():
                q = q.filter(
                    (Product.name.ilike(f"%{text}%")) |
                    (Product.brand.ilike(f"%{text}%")) |
                    (Product.barcode.ilike(f"%{text}%"))
                )
            products = q.limit(30).all()
            self.product_results.clear()
            if products:
                self.product_results.addItem("Select an item", None)
            else:
                self.product_results.addItem("No match — click New Item", None)
            for p in products:
                label = f"{p.name} | ₹{p.selling_price:,.0f} | Stock: {p.stock_qty}"
                if p.brand:
                    label = f"{p.brand} {label}"
                self.product_results.addItem(label, p.id)

            typed = text.strip().lower()
            exact_index = -1
            if typed:
                for index, product in enumerate(products, start=1):
                    if ((product.barcode and product.barcode.lower() == typed)
                            or product.name.lower() == typed):
                        exact_index = index
                        break
            if exact_index >= 0:
                self.product_results.setCurrentIndex(exact_index)
            elif len(products) == 1 and typed:
                self.product_results.setCurrentIndex(1)
        finally:
            session.close()

    def _on_product_select(self):
        product_id = self.product_results.currentData()
        if not product_id:
            self.stock_lbl.setText("")
            return
        session = get_db()
        try:
            product = session.get(Product, product_id)
            if product:
                self.stock_lbl.setText(f"Available: {product.stock_qty} {product.unit or 'Pcs'}")
                max_qty = max(1, product.stock_qty) if product.stock_qty > 0 else 1
                self.qty_input.setValidator(QIntValidator(1, max_qty))
        finally:
            session.close()

    def _add_to_cart(self):
        product_id = self.product_results.currentData()
        if not product_id:
            return

        qty_text = self.qty_input.text().strip()
        if not qty_text:
            show_warning(self, "Please enter a quantity."); return
        try:
            qty = int(qty_text)
            if qty < 1:
                show_warning(self, "Quantity must be at least 1."); return
        except ValueError:
            show_warning(self, "Please enter a valid whole number for quantity."); return

        disc_text = self.disc_input.text().strip()
        try:
            disc_pct = float(disc_text) if disc_text else 0.0
            if not (0.0 <= disc_pct <= 100.0):
                show_warning(self, "Discount must be between 0 and 100."); return
        except ValueError:
            show_warning(self, "Discount % must be a number (e.g. 10 or 5.5)."); return

        session = get_db()
        try:
            product = session.get(Product, product_id)
            if not product or product.stock_qty <= 0:
                show_warning(self, "This product is out of stock."); return
            if qty > product.stock_qty:
                show_warning(self, f"Only {product.stock_qty} items available in stock."); return
            session.expunge(product)
        finally:
            session.close()

        for item in self._cart:
            if item.product.id == product_id:
                new_qty = item.qty + qty
                if new_qty <= item.product.stock_qty:
                    item.qty = new_qty
                    if disc_pct != 0.0:
                        item.discount_pct = disc_pct
                    item._recalc()
                    self._refresh_cart()
                    self.qty_input.setText("1")
                    self.disc_input.setText("0")
                    self.product_search.clear()
                    self._focus_product_search()
                else:
                    show_warning(self, "Cannot add more than available stock.")
                return

        self._cart.append(CartItem(product, qty, disc_pct))
        self._refresh_cart()
        self.qty_input.setText("1")
        self.disc_input.setText("0")
        self.product_search.clear()
        self._focus_product_search()

    def _remove_from_cart(self):
        row = self.cart_table.currentRow()
        if 0 <= row < len(self._cart):
            self._cart.pop(row)
            self._refresh_cart()

    def _clear_cart(self):
        self._cart.clear()
        self._refresh_cart()

    def load_sale_for_edit(self, sale_obj):
        session = get_db()
        try:
            db_sale = session.get(Sale, sale_obj.id)
            if not db_sale.is_cancelled:
                db_sale.is_cancelled = True

                from db.models import Payment
                for item in db_sale.items:
                    product = session.get(Product, item.product_id)
                    if product:
                        product.stock_qty += item.qty
                        user = AuthSession.current_user()
                        session.add(StockMovement(
                            product_id=product.id,
                            movement_type="Sale Cancelled",
                            quantity=item.qty,
                            resulting_stock=product.stock_qty,
                            reference_type="Sale",
                            reference_id=db_sale.id,
                            notes=f"Stock restored from {db_sale.invoice_no}",
                            created_by=user.id if user else None,
                        ))

                if db_sale.amount_received > 0 and db_sale.payment_mode != "EMI":
                    session.query(Payment).filter_by(sale_id=db_sale.id).delete()

                if db_sale.payment_mode == "EMI" and db_sale.emi_record:
                    db_sale.emi_record.status = "Closed"
                    db_sale.emi_record.notes = (db_sale.emi_record.notes or "") + "\\nModified via POS."

                session.commit()

            self._cart.clear()

            for item in db_sale.items:
                product = session.get(Product, item.product_id)
                if product:
                    ci = CartItem(product, item.qty, item.discount_pct)
                    self._cart.append(ci)

            self._refresh_cart()

            if db_sale.customer_id:
                matched = False
                for cid, disp in self.customer_picker._all_entries:
                    if cid == db_sale.customer_id:
                        self._selected_customer_id = cid
                        self.customer_picker.set_customer(cid, disp)
                        self.selected_customer_lbl.setText(f"✓  {disp}")
                        matched = True
                        break
                if not matched:
                    self._selected_customer_id = db_sale.customer_id
                    self.selected_customer_lbl.setText("Customer (ID restored)")

            show_success(self, f"Original invoice {db_sale.invoice_no} has been cancelled.\nItems and customer have been loaded into POS for modification.")
        except Exception as e:
            session.rollback()
            show_error(self, f"Failed to load sale for editing:\n{e}")
        finally:
            session.close()

    def _refresh_cart(self):
        self.cart_table.setRowCount(len(self._cart))
        for r, item in enumerate(self._cart):
            vals = [
                item.product.name,
                f"₹{item.product.selling_price:,.2f}",
                str(item.qty),
                f"{item.discount_pct:.1f}%",
                f"₹{item.taxable:,.2f}",
                f"₹{item.gst_amount:,.2f}",
                f"₹{item.line_total:,.2f}",
            ]
            for c, v in enumerate(vals):
                self.cart_table.setItem(r, c, QTableWidgetItem(v))
        self._update_totals()

    def _extra_discount_value(self) -> float:
        try:
            v = float(self.extra_discount_input.text().strip() or 0)
            return max(0.0, v)
        except ValueError:
            return 0.0

    def _update_totals(self):
        subtotal      = sum(i.product.selling_price * i.qty for i in self._cart)
        item_discount = sum(i.line_discount for i in self._cart)
        after_items   = subtotal - item_discount
        extra_disc    = min(self._extra_discount_value(), after_items)
        total_discount = item_discount + extra_disc

        taxable   = after_items - extra_disc
        gst_total = sum(
            (taxable * i.product.gst_rate / 100) * (i.taxable / after_items)
            if after_items > 0 else 0
            for i in self._cart
        )
        if after_items > 0:
            gst_total = sum(
                i.gst_amount * (1 - extra_disc / after_items)
                for i in self._cart
            )
        else:
            gst_total = 0.0
        cgst  = gst_total / 2
        sgst  = gst_total / 2
        grand = taxable + gst_total

        disc_color = "#f87171" if total_discount > 0 else "#8b949e"
        self.lbl_discount.setStyleSheet(f"color: {disc_color}; font-weight: 600;")
        self.lbl_extra_disc.setStyleSheet(f"color: {disc_color}; font-weight: 600;")

        self.lbl_subtotal.setText(f"₹{subtotal:,.2f}")
        self.lbl_discount.setText(f"- ₹{item_discount:,.2f}")
        self.lbl_extra_disc.setText(f"- ₹{extra_disc:,.2f}")
        self.lbl_taxable.setText(f"₹{taxable:,.2f}")
        self.lbl_cgst.setText(f"₹{cgst:,.2f}")
        self.lbl_sgst.setText(f"₹{sgst:,.2f}")
        self.lbl_grand.setText(f"₹{grand:,.2f}")

        mode = self.payment_mode_combo.currentText()
        if mode in ("Cash", "UPI", "Card", "Credit"):
            received_default = 0.0 if mode == "Credit" else grand
            self.amount_received_input.blockSignals(True)
            self.amount_received_input.setText(f"{received_default:.2f}")
            self.amount_received_input.blockSignals(False)
        self._update_balance()

    def _update_balance(self):
        try:
            grand = float(self.lbl_grand.text().replace("₹", "").replace(",", ""))
        except Exception:
            grand = 0.0

        received_text = self.amount_received_input.text().strip()
        try:
            received = float(received_text) if received_text else 0.0
        except ValueError:
            received = 0.0

        balance = received - grand
        color = "#4ade80" if balance >= 0 else "#f87171"
        self.lbl_balance.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: bold;")
        if balance >= 0:
            self.lbl_balance.setText(f"Change: ₹{balance:,.2f}")
        else:
            self.lbl_balance.setText(f"Balance Due: ₹{abs(balance):,.2f}")

    def _edit_cart_item(self, row: int, _col: int):
        if row < 0 or row >= len(self._cart):
            return
        item = self._cart[row]

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Edit — {item.product.name}")
        dlg.setModal(True)
        dlg.setFixedWidth(340)
        vl = QVBoxLayout(dlg)
        vl.setContentsMargins(20, 18, 20, 18)
        vl.setSpacing(12)

        vl.addWidget(QLabel(f"<b>{item.product.name}</b>"))
        vl.addWidget(QLabel(f"Rate: ₹{item.product.selling_price:,.2f}  |  Stock: {item.product.stock_qty}"))

        form_row1 = QHBoxLayout()
        form_row1.addWidget(QLabel("Quantity:"))
        qty_e = QLineEdit(str(item.qty))
        qty_e.setFixedWidth(90)
        qty_e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_row1.addWidget(qty_e)
        vl.addLayout(form_row1)

        form_row2 = QHBoxLayout()
        form_row2.addWidget(QLabel("Discount %:"))
        disc_e = QLineEdit(f"{item.discount_pct:.2f}")
        disc_e.setFixedWidth(90)
        disc_e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        form_row2.addWidget(disc_e)
        vl.addLayout(form_row2)

        err_lbl = QLabel("")
        err_lbl.setStyleSheet("color: #f87171; font-size: 11px;")
        vl.addWidget(err_lbl)

        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dlg.reject)
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("PrimaryBtn")

        def _apply():
            try:
                new_qty = int(qty_e.text().strip())
                if new_qty < 1:
                    err_lbl.setText("Qty must be at least 1."); return
                if new_qty > item.product.stock_qty:
                    err_lbl.setText(f"Max stock is {item.product.stock_qty}."); return
            except ValueError:
                err_lbl.setText("Qty must be a whole number."); return
            try:
                new_disc = float(disc_e.text().strip() or 0)
                if not (0.0 <= new_disc <= 100.0):
                    err_lbl.setText("Discount must be 0 – 100."); return
            except ValueError:
                err_lbl.setText("Discount must be a number (e.g. 10)."); return
            item.qty = new_qty
            item.discount_pct = new_disc
            item._recalc()
            dlg.accept()

        apply_btn.clicked.connect(_apply)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        vl.addLayout(btn_row)

        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._refresh_cart()

    def _confirm_sale(self, print_invoice: bool = True):
        if not self._cart:
            show_warning(self, "Add at least one product before completing the sale.")
            return

        session = get_db()
        try:
            grand = float(self.lbl_grand.text().replace("₹", "").replace(",", ""))

            received_text = self.amount_received_input.text().strip()
            try:
                received = float(received_text) if received_text else 0.0
            except ValueError:
                received = 0.0

            balance = max(0.0, grand - received)
            mode = self.payment_mode_combo.currentText()

            if balance > 0 and not self._selected_customer_id:
                show_warning(
                    self,
                    "Add a customer before saving credit or a pending balance. "
                    "Use the + New Customer button; the bill will stay open."
                )
                return

            if mode == "EMI":
                provider_id = self.finance_provider_combo.currentData()
                if not provider_id:
                    show_warning(self, "Please select a Finance Provider for EMI."); return
                if not self._selected_customer_id:
                    show_warning(self, "EMI requires a registered customer."); return
            else:
                provider_id = None

            # Cash tendered may be higher than the bill because change is due;
            # accounting records only the amount actually applied to the sale.
            applied_received = min(max(received, 0.0), grand)

            subtotal      = sum(i.product.selling_price * i.qty for i in self._cart)
            item_discount = sum(i.line_discount for i in self._cart)
            after_items = subtotal - item_discount
            extra_disc = min(self._extra_discount_value(), after_items)
            discount = item_discount + extra_disc
            if after_items > 0:
                gst_scale = 1 - extra_disc / after_items
            else:
                gst_scale = 1.0
            taxable   = after_items - extra_disc
            gst_total = sum(i.gst_amount for i in self._cart) * gst_scale

            customer_id = self._selected_customer_id
            invoice_no = _next_invoice_no(session)
            user = AuthSession.current_user()

            sale = Sale(
                invoice_no=invoice_no,
                customer_id=customer_id,
                subtotal=subtotal,
                discount_amount=discount,
                taxable_amount=taxable,
                cgst_amount=gst_total / 2,
                sgst_amount=gst_total / 2,
                total_gst=gst_total,
                grand_total=grand,
                payment_mode=mode,
                amount_received=applied_received,
                balance_due=balance,
                created_by=user.id if user else None,
            )
            session.add(sale)
            session.flush()

            for item in self._cart:
                line_scale = gst_scale if after_items > 0 else 1.0
                line_taxable = item.taxable * line_scale
                line_gst = item.gst_amount * line_scale
                si = SaleItem(
                    sale_id=sale.id,
                    product_id=item.product.id,
                    product_name=item.product.name,
                    qty=item.qty,
                    unit_price=item.product.selling_price,
                    discount_pct=item.discount_pct,
                    gst_rate=item.product.gst_rate,
                    taxable_amount=line_taxable,
                    gst_amount=line_gst,
                    line_total=line_taxable + line_gst,
                )
                session.add(si)
                p = session.get(Product, item.product.id)
                p.stock_qty -= item.qty
                session.add(StockMovement(
                    product_id=p.id,
                    movement_type="Sale",
                    quantity=-item.qty,
                    resulting_stock=p.stock_qty,
                    reference_type="Sale",
                    reference_id=sale.id,
                    notes=f"Sold on {invoice_no}",
                    created_by=user.id if user else None,
                ))

            if mode == "EMI":
                from ui.windows.emi_finance import NewEMIDialog
                session.commit()

                dlg = NewEMIDialog(parent=self)
                if customer_id:
                    for i in range(dlg.customer_combo.count()):
                        if dlg.customer_combo.itemData(i) == customer_id:
                            dlg.customer_combo.setCurrentIndex(i)
                            dlg.customer_combo.setEnabled(False)
                            break
                dlg.provider_combo.setCurrentIndex(dlg.provider_combo.findData(provider_id))
                dlg.loan_edit.setText(f"{grand:.2f}")
                dlg.down_edit.setText(f"{applied_received:.2f}")

                if dlg.exec() == QDialog.DialogCode.Accepted:
                    s2 = get_db()
                    try:
                        from db.models import EMIRecord
                        last_emi = s2.query(EMIRecord).filter_by(customer_id=customer_id).order_by(EMIRecord.id.desc()).first()
                        if last_emi and last_emi.sale_id is None:
                            last_emi.sale_id = sale.id
                            s2.commit()
                    finally:
                        s2.close()
                else:
                    show_warning(self, "Sale saved as EMI, but no loan schedule was created. You can create it manually later from the Finance tab.")

            else:
                if applied_received > 0:
                    pmt = Payment(
                        payment_type="receipt",
                        customer_id=customer_id,
                        sale_id=sale.id,
                        amount=applied_received,
                        mode=mode,
                        notes=f"Auto-receipt for Sale {invoice_no}",
                        created_by=user.id if user else None
                    )
                    session.add(pmt)
                session.commit()

            show_success(self, f"Invoice {invoice_no} created!\nGrand Total: ₹{grand:,.2f}\nBalance Due: ₹{balance:,.2f}")

            if print_invoice:
                try:
                    from core.invoice_gen import generate_invoice
                    sale_obj = session.get(Sale, sale.id)
                    pdf_path = generate_invoice(sale_obj)
                    from ui.components.export_dialog import ExportReadyDialog
                    ExportReadyDialog(pdf_path, self).exec()
                except Exception as inv_err:
                    show_warning(self, f"Sale saved, but the invoice could not be opened: {inv_err}")

            self._clear_cart()
            self._clear_customer()
            self.extra_discount_input.setText("0")
            self.payment_mode_combo.setCurrentText("Cash")
            self._focus_product_search()

        except Exception as e:
            session.rollback()
            show_error(self, f"Sale failed: {e}")
        finally:
            session.close()
