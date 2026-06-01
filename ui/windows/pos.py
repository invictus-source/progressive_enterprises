"""
Progressive Enterprises – Point of Sale (POS) Module
Full sale creation with product search, cart, GST calculation, and invoice PDF.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFrame,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QDialog, QScrollArea, QSizePolicy, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QIntValidator, QDoubleValidator

from db.manager import get_db
from db.models import Product, Customer, Sale, SaleItem, Payment, FinanceProvider
from core.auth import AuthSession
from ui.components.toast import Toast, show_toast, show_success, show_warning, show_error
import config
# ── Searchable Customer Dropdown ─────────────────────────────────────────────

class CustomerSearchWidget(QWidget):
    """
    Inline searchable customer picker.

    Architecture: an inline QListWidget (NoFocus) sits directly below the
    search QLineEdit in the same layout.  Because the list has NoFocus, clicking
    a row never steals keyboard focus from the search input — so FocusOut never
    fires during a click, eliminating the race condition that caused immediate
    deselection with the old floating-popup approach.
    """
    customer_selected = Signal(object, str)   # (customer_id | None, display_text)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_entries: list[tuple] = []   # (id_or_None, display_str)
        self._build_ui()

    # ── Build ────────────────────────────────────────────────────

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

        # ── Inline list (no floating window) ─────────────────────
        # NoFocus: mouse clicks register itemClicked but never move
        # keyboard focus away from search_input  → no race condition.
        self.list_widget = QListWidget()
        self.list_widget.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list_widget.setMaximumHeight(224)      # ~7 rows × 32px
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

    # ── Public API ───────────────────────────────────────────────

    def load_customers(self, customers: list):
        """Rebuild the full entry list from a fresh DB query result."""
        self._all_entries = [(None, "Walk-in Customer")]
        for c in customers:
            display = f"{c.name}  –  {c.phone}" if c.phone else c.name
            self._all_entries.append((c.id, display))

    def set_customer(self, customer_id, display_text: str):
        """Programmatically select a customer (used by load_sale_for_edit)."""
        self.search_input.blockSignals(True)
        self.search_input.setText(display_text)
        self.search_input.blockSignals(False)
        self.list_widget.setVisible(False)

    def clear_selection(self):
        """Reset to empty / walk-in state."""
        self.search_input.blockSignals(True)
        self.search_input.clear()
        self.search_input.blockSignals(False)
        self.list_widget.setVisible(False)

    # ── Internal ─────────────────────────────────────────────────

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
        """Called only by real user keystrokes (blockSignals guards programmatic changes)."""
        if not text.strip():
            self._populate_list("")            # show all on empty
            self.customer_selected.emit(None, "Walk-in Customer")
        else:
            self._populate_list(text)

    def _on_item_clicked(self, item: QListWidgetItem):
        """User clicked a list row — always fires before any FocusOut because
        the list has NoFocus, so keyboard focus never leaves the search input."""
        cid  = item.data(Qt.ItemDataRole.UserRole)
        disp = item.text()
        # Update input text silently (no textChanged → no recursive emission)
        self.search_input.blockSignals(True)
        self.search_input.setText(disp)
        self.search_input.blockSignals(False)
        self.list_widget.setVisible(False)
        self.customer_selected.emit(cid, disp)

    # ── Event filter (on search_input only) ──────────────────────

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent
        if obj is self.search_input:
            if event.type() == QEvent.Type.FocusIn:
                # Show list whenever the text box gains focus
                self._populate_list(self.search_input.text())
            elif event.type() == QEvent.Type.FocusOut:
                # Focus is leaving the input to somewhere OTHER than our list
                # (list has NoFocus so it can never be the destination).
                # Small delay so any pending itemClicked from the list fires first
                # (belt-and-suspenders; with NoFocus this shouldn't race).
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
    """Generate the next sequential invoice number."""
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

        # ── Left Panel: Product Search + Cart (in scroll area) ────────────
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setSpacing(10)
        left.setContentsMargins(4, 4, 4, 4)

        # Title
        title = QLabel("Point of Sale")
        title.setObjectName("PageTitle")
        left.addWidget(title)

        # Product Search
        search_frame = QFrame(); search_frame.setObjectName("Card")
        sf_layout = QVBoxLayout(search_frame)
        sf_layout.setContentsMargins(12, 10, 12, 10)
        sf_layout.setSpacing(8)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.product_search = QLineEdit()
        self.product_search.setObjectName("SearchBar")
        self.product_search.setPlaceholderText("Search by name, brand, barcode...")
        self.product_search.setMinimumHeight(34)
        self.product_search.textChanged.connect(self._search_products)
        search_row.addWidget(self.product_search, 3)

        self.product_results = QComboBox()
        self.product_results.setMinimumWidth(200)
        self.product_results.setMinimumHeight(34)
        self.product_results.currentIndexChanged.connect(self._on_product_select)
        search_row.addWidget(self.product_results, 3)
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

        self.add_to_cart_btn = QPushButton("➕  Add to Cart")
        self.add_to_cart_btn.setObjectName("PrimaryBtn")
        self.add_to_cart_btn.setMinimumHeight(34)
        self.add_to_cart_btn.setMinimumWidth(120)
        self.add_to_cart_btn.clicked.connect(self._add_to_cart)
        qty_row.addWidget(self.add_to_cart_btn)
        sf_layout.addLayout(qty_row)

        left.addWidget(search_frame)

        # Cart Table
        cart_header = QLabel("Shopping Cart")
        cart_header.setStyleSheet("font-size: 14px; font-weight: bold; color: #e2e8f0;")
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

        # Cart action hint + remove button
        cart_actions = QHBoxLayout()
        hint_lbl = QLabel("💡 Double-click a row to edit qty / discount")
        hint_lbl.setStyleSheet("color: #64748B; font-size: 10px;")
        hint_lbl.setWordWrap(True)
        cart_actions.addWidget(hint_lbl)
        cart_actions.addStretch()
        remove_btn = QPushButton("🗑  Remove Selected")
        remove_btn.setMinimumHeight(28)
        remove_btn.clicked.connect(self._remove_from_cart)
        cart_actions.addWidget(remove_btn)
        left.addLayout(cart_actions)

        left_scroll.setWidget(left_widget)
        root.addWidget(left_scroll, 3)

        # ── Right Panel: Customer + Totals + Payment (in scroll area) ────
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        right_scroll.setFrameShape(QFrame.Shape.NoFrame)
        right_widget = QWidget()
        right = QVBoxLayout(right_widget)
        right.setSpacing(10)
        right.setContentsMargins(4, 4, 4, 4)

        # Customer selection with searchable dropdown
        cust_frame = QFrame(); cust_frame.setObjectName("Card")
        cf = QVBoxLayout(cust_frame); cf.setContentsMargins(12, 10, 12, 10)
        cf.setSpacing(6)

        cust_header = QHBoxLayout()
        cust_lbl = QLabel("Customer")
        cust_lbl.setStyleSheet("font-weight: 700; font-size: 12px;")
        cust_header.addWidget(cust_lbl)
        cust_header.addStretch()
        self.clear_customer_btn = QPushButton("✕  Clear")
        self.clear_customer_btn.setObjectName("FlatBtn")
        self.clear_customer_btn.setMinimumHeight(24)
        self.clear_customer_btn.clicked.connect(self._clear_customer)
        cust_header.addWidget(self.clear_customer_btn)
        cf.addLayout(cust_header)

        # ── Searchable dropdown replaces the broken QCompleter approach ──
        self.customer_picker = CustomerSearchWidget()
        self.customer_picker.customer_selected.connect(self._on_customer_selected)
        cf.addWidget(self.customer_picker)

        self.selected_customer_lbl = QLabel("Walk-in Customer")
        self.selected_customer_lbl.setStyleSheet("color: #60a5fa; font-size: 11px; padding: 2px 0;")
        self.selected_customer_lbl.setWordWrap(True)
        cf.addWidget(self.selected_customer_lbl)

        right.addWidget(cust_frame)

        # Totals card
        totals_frame = QFrame(); totals_frame.setObjectName("Card")
        tf = QVBoxLayout(totals_frame); tf.setContentsMargins(14, 12, 14, 12); tf.setSpacing(6)

        summary_hdr = QHBoxLayout()
        summary_hdr.addWidget(QLabel("Bill Summary"))
        summary_hdr.addStretch()
        tf.addLayout(summary_hdr)
        tf.addWidget(self._h_line())

        def add_row(label, widget, bold=False):
            row = QHBoxLayout()
            lbl = QLabel(label); lbl.setStyleSheet("color: #8b949e;")
            if bold: lbl.setStyleSheet("font-weight: bold; color: #e2e8f0;")
            row.addWidget(lbl); row.addStretch(); row.addWidget(widget)
            tf.addLayout(row)
            return widget

        self.lbl_subtotal  = QLabel("₹0.00")
        self.lbl_discount  = QLabel("₹0.00")   # item-level discounts
        self.lbl_extra_disc = QLabel("₹0.00")  # bill-level extra discount
        self.lbl_taxable   = QLabel("₹0.00")
        self.lbl_cgst      = QLabel("₹0.00")
        self.lbl_sgst      = QLabel("₹0.00")
        self.lbl_grand     = QLabel("₹0.00")
        self.lbl_grand.setStyleSheet("font-size: 20px; font-weight: bold; color: #60a5fa;")

        add_row("Subtotal", self.lbl_subtotal)
        add_row("Item Discounts", self.lbl_discount)

        # Extra bill-level discount row
        extra_disc_row = QHBoxLayout()
        extra_disc_lbl = QLabel("Extra Discount (₹)")
        extra_disc_lbl.setStyleSheet("color: #8b949e;")
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
        grand_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #e2e8f0;")
        grand_row.addWidget(grand_lbl); grand_row.addStretch(); grand_row.addWidget(self.lbl_grand)
        tf.addLayout(grand_row)
        right.addWidget(totals_frame)

        # Payment mode
        pay_frame = QFrame(); pay_frame.setObjectName("Card")
        pf = QVBoxLayout(pay_frame); pf.setContentsMargins(12, 10, 12, 10)
        pf.setSpacing(6)
        pf.addWidget(QLabel("Payment Mode"))
        self.payment_mode_combo = QComboBox()
        self.payment_mode_combo.addItems(["Cash", "Card", "UPI", "EMI", "Mixed"])
        self.payment_mode_combo.setMinimumHeight(32)
        self.payment_mode_combo.currentTextChanged.connect(self._on_payment_mode_changed)
        pf.addWidget(self.payment_mode_combo)
        
        self.provider_lbl = QLabel("Finance Provider")
        self.provider_lbl.hide()
        self.finance_provider_combo = QComboBox()
        self.finance_provider_combo.setMinimumHeight(32)
        self.finance_provider_combo.hide()
        pf.addWidget(self.provider_lbl)
        pf.addWidget(self.finance_provider_combo)

        pf.addWidget(QLabel("Amount Received (Down Payment if EMI)"))
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

        right.addWidget(pay_frame)
        right.addStretch()

        # Action buttons
        self.confirm_btn = QPushButton("✅  Confirm Sale & Print Invoice")
        self.confirm_btn.setObjectName("SuccessBtn")
        self.confirm_btn.setMinimumHeight(40)
        self.confirm_btn.clicked.connect(self._confirm_sale)
        right.addWidget(self.confirm_btn)

        clear_btn = QPushButton("🗑  Clear Cart")
        clear_btn.setObjectName("DangerBtn")
        clear_btn.setMinimumHeight(34)
        clear_btn.clicked.connect(self._clear_cart)
        right.addWidget(clear_btn)

        right_scroll.setWidget(right_widget)
        root.addWidget(right_scroll, 1)

    def _h_line(self):
        f = QFrame(); f.setFrameShape(QFrame.Shape.HLine)
        return f

    def refresh(self):
        self._load_customers()
        self._load_providers()
        self._search_products("")

    def _on_payment_mode_changed(self, text: str):
        if text == "EMI":
            self.provider_lbl.show()
            self.finance_provider_combo.show()
            self.lbl_balance.setText("Loan Amount: ₹0.00")
        else:
            self.provider_lbl.hide()
            self.finance_provider_combo.hide()
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

    def _load_customers(self):
        session = get_db()
        try:
            self._customers = session.query(Customer).filter_by(
                is_active=True).order_by(Customer.name).all()
            self.customer_picker.load_customers(self._customers)
            # Reset to walk-in on every reload
            self._selected_customer_id = None
            self.customer_picker.clear_selection()
            self.selected_customer_lbl.setText("Walk-in Customer")
        finally:
            session.close()

    def _on_customer_selected(self, customer_id, display_text: str):
        """Slot called by CustomerSearchWidget when user picks a customer."""
        self._selected_customer_id = customer_id
        if customer_id is None:
            self.selected_customer_lbl.setText("Walk-in Customer")
        else:
            self.selected_customer_lbl.setText(f"✓  {display_text}")

    def _clear_customer(self):
        self._selected_customer_id = None
        self.customer_picker.clear_selection()
        self.selected_customer_lbl.setText("Walk-in Customer")

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
            self.product_results.addItem("— Select Product —", None)
            for p in products:
                label = f"{p.name} | ₹{p.selling_price:,.0f} | Stock: {p.stock_qty}"
                if p.brand:
                    label = f"{p.brand} {label}"
                self.product_results.addItem(label, p.id)
        finally:
            session.close()

    def _on_product_select(self):
        product_id = self.product_results.currentData()
        if not product_id:
            self.stock_lbl.setText("")
            return
        session = get_db()
        try:
            product = session.query(Product).get(product_id)
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

        # ── Validate qty ────────────────────────────────────────────────────
        qty_text = self.qty_input.text().strip()
        if not qty_text:
            show_warning(self, "Please enter a quantity."); return
        try:
            qty = int(qty_text)
            if qty < 1:
                show_warning(self, "Quantity must be at least 1."); return
        except ValueError:
            show_warning(self, "Please enter a valid whole number for quantity."); return

        # ── Validate discount ────────────────────────────────────────────────
        disc_text = self.disc_input.text().strip()
        try:
            disc_pct = float(disc_text) if disc_text else 0.0
            if not (0.0 <= disc_pct <= 100.0):
                show_warning(self, "Discount must be between 0 and 100."); return
        except ValueError:
            show_warning(self, "Discount % must be a number (e.g. 10 or 5.5)."); return

        session = get_db()
        try:
            product = session.query(Product).get(product_id)
            if not product or product.stock_qty <= 0:
                show_warning(self, "This product is out of stock."); return
            if qty > product.stock_qty:
                show_warning(self, f"Only {product.stock_qty} items available in stock."); return
            session.expunge(product)
        finally:
            session.close()

        # If product already in cart: update qty (keep existing discount unless user changed it)
        for item in self._cart:
            if item.product.id == product_id:
                new_qty = item.qty + qty
                if new_qty <= item.product.stock_qty:
                    item.qty = new_qty
                    if disc_pct != 0.0:          # only override if user explicitly set a discount
                        item.discount_pct = disc_pct
                    item._recalc()
                    self._refresh_cart()
                    self.qty_input.setText("1")
                    self.disc_input.setText("0")
                else:
                    show_warning(self, "Cannot add more than available stock.")
                return

        self._cart.append(CartItem(product, qty, disc_pct))
        self._refresh_cart()
        self.qty_input.setText("1")
        self.disc_input.setText("0")

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
            db_sale = session.query(Sale).get(sale_obj.id)
            if not db_sale.is_cancelled:
                db_sale.is_cancelled = True
                
                from db.models import Payment
                for item in db_sale.items:
                    product = session.query(Product).get(item.product_id)
                    if product: product.stock_qty += item.qty
                    
                if db_sale.amount_received > 0 and db_sale.payment_mode != "EMI":
                    session.query(Payment).filter_by(sale_id=db_sale.id).delete()
                    
                if db_sale.payment_mode == "EMI" and db_sale.emi_record:
                    db_sale.emi_record.status = "Closed"
                    db_sale.emi_record.notes = (db_sale.emi_record.notes or "") + "\\nModified via POS."
                
                session.commit()
                
            self._cart.clear()
            
            for item in db_sale.items:
                product = session.query(Product).get(item.product_id)
                if product:
                    ci = CartItem(product, item.qty, item.discount_pct)
                    self._cart.append(ci)
            
            self._refresh_cart()
            
            # Set customer
            if db_sale.customer_id:
                # Find matching entry in the picker's loaded list
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
        """Parse the extra bill-level discount input. Returns 0 on invalid input."""
        try:
            v = float(self.extra_discount_input.text().strip() or 0)
            return max(0.0, v)
        except ValueError:
            return 0.0

    def _update_totals(self):
        subtotal      = sum(i.product.selling_price * i.qty for i in self._cart)
        item_discount = sum(i.line_discount for i in self._cart)
        after_items   = subtotal - item_discount          # after per-item discounts
        extra_disc    = min(self._extra_discount_value(), after_items)  # cap at after-item total
        total_discount = item_discount + extra_disc

        # GST calculated on net taxable (after ALL discounts)
        taxable   = after_items - extra_disc
        gst_total = sum(
            (taxable * i.product.gst_rate / 100) * (i.taxable / after_items)
            if after_items > 0 else 0
            for i in self._cart
        )
        # Simpler: recalculate GST proportionally
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

        # Colour extra discount label red when non-zero
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

        self.amount_received_input.blockSignals(True)
        self.amount_received_input.setText(f"{grand:.2f}")
        self.amount_received_input.blockSignals(False)
        self._update_balance()

    def _update_balance(self):
        # Parse grand total from label
        try:
            grand = float(self.lbl_grand.text().replace("₹", "").replace(",", ""))
        except Exception:
            grand = 0.0
        
        # Parse amount received from input
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
        """Double-click a cart row → edit qty and/or discount in a small dialog."""
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

    def _confirm_sale(self):
        if not self._cart:
            show_warning(self, "Please add products to the cart first.")
            return

        session = get_db()
        try:
            grand = float(self.lbl_grand.text().replace("₹", "").replace(",", ""))

            # Parse received amount
            received_text = self.amount_received_input.text().strip()
            try:
                received = float(received_text) if received_text else 0.0
            except ValueError:
                received = 0.0

            balance = max(0.0, grand - received)
            mode = self.payment_mode_combo.currentText()

            if mode == "EMI":
                provider_id = self.finance_provider_combo.currentData()
                if not provider_id:
                    show_warning(self, "Please select a Finance Provider for EMI."); return
                if not self._selected_customer_id:
                    show_warning(self, "EMI requires a registered customer."); return
            else:
                provider_id = None

            subtotal      = sum(i.product.selling_price * i.qty for i in self._cart)
            item_discount = sum(i.line_discount for i in self._cart)
            extra_disc    = self._extra_discount_value()
            discount      = item_discount + extra_disc

            # Proportional GST reduction for extra discount
            after_items = subtotal - item_discount
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
                amount_received=received,
                balance_due=balance,
                created_by=user.id if user else None,
            )
            session.add(sale)
            session.flush()  # get sale.id

            for item in self._cart:
                si = SaleItem(
                    sale_id=sale.id,
                    product_id=item.product.id,
                    product_name=item.product.name,
                    qty=item.qty,
                    unit_price=item.product.selling_price,
                    discount_pct=item.discount_pct,
                    gst_rate=item.product.gst_rate,
                    taxable_amount=item.taxable,
                    gst_amount=item.gst_amount,
                    line_total=item.line_total,
                )
                session.add(si)
                # Deduct stock
                p = session.query(Product).get(item.product.id)
                p.stock_qty -= item.qty
                
            # Payment Ledger Entry / EMI linking
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
                dlg.down_edit.setText(f"{received:.2f}")
                
                if dlg.exec() == QDialog.DialogCode.Accepted:
                    # The dialog created the EMIRecord. We should link it to the sale.
                    # Since NewEMIDialog currently leaves sale_id=None, we will manually update it.
                    s2 = get_db()
                    try:
                        # Find the most recently created EMI record for this customer
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
                # Normal Payment tracking for non-EMI
                if received > 0:
                    pmt = Payment(
                        payment_type="receipt",
                        customer_id=customer_id,
                        sale_id=sale.id,
                        amount=received,
                        mode=mode,
                        notes=f"Auto-receipt for Sale {invoice_no}",
                        created_by=user.id if user else None
                    )
                    session.add(pmt)
                session.commit()

            show_success(self, f"Invoice {invoice_no} created!\nGrand Total: ₹{grand:,.2f}\nBalance Due: ₹{balance:,.2f}")

            # Try to generate PDF invoice
            try:
                from core.invoice_gen import generate_invoice
                # Reload sale with relationships
                sale_obj = session.query(Sale).get(sale.id)
                pdf_path = generate_invoice(sale_obj)
                from ui.components.export_dialog import ExportReadyDialog
                ExportReadyDialog(pdf_path, self).exec()
            except Exception as inv_err:
                print(f"[POS] Invoice PDF error: {inv_err}")

            self._clear_cart()

        except Exception as e:
            session.rollback()
            show_error(self, f"Sale failed: {e}")
        finally:
            session.close()
