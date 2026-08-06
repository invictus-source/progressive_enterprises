from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTextEdit, QScrollArea,
    QDialog, QMessageBox, QFrame, QInputDialog, QCheckBox, QSpinBox
)
from PySide6.QtCore import Qt

from ui.components.data_table import DataTable
from ui.components.form_dialog import FormDialog, ValidationError
from ui.components.toast import show_toast, show_success, show_warning, show_error
from db.manager import get_db
from db.models import Product, Category, StockMovement
from core.auth import AuthSession
import config


def _parse_price(text: str, field: str) -> float:
    text = text.strip().lstrip("₹").strip()
    if not text:
        return 0.0
    try:
        val = float(text)
    except ValueError:
        raise ValidationError(f"{field} must be a number (e.g. 1250.00).")
    if val < 0:
        raise ValidationError(f"{field} cannot be negative.")
    if val > 9_999_999:
        raise ValidationError(f"{field} exceeds maximum allowed value.")
    return val


def _parse_stock(text: str, field: str, default: int = 0) -> int:
    text = text.strip()
    if not text:
        return default
    try:
        val = int(text)
    except ValueError:
        raise ValidationError(f"{field} must be a whole number (e.g. 10).")
    if val < 0:
        raise ValidationError(f"{field} cannot be negative.")
    if val > 99_999:
        raise ValidationError(f"{field} exceeds maximum allowed value.")
    return val


class AddEditProductDialog(FormDialog):
    def __init__(self, product: Product = None, parent=None):
        mode = "Edit Product" if product else "Add New Product"
        super().__init__(mode, "Fill in the product details", width=580, parent=parent)
        self._product = product
        self._categories = []
        self._build_fields()
        if product:
            self._populate(product)
        self.finalize()

    def _build_fields(self):
        self.add_section("Product Information")
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Product Name *")
        self.add_field("Product Name *", self.name_edit)

        self.brand_edit = QLineEdit(); self.brand_edit.setPlaceholderText("Brand (e.g. Samsung)")
        self.model_edit = QLineEdit(); self.model_edit.setPlaceholderText("Model No.")
        self.add_field_row(("Brand", self.brand_edit), ("Model", self.model_edit))

        self.barcode_edit = QLineEdit(); self.barcode_edit.setPlaceholderText("Barcode / SKU")
        self.track_serials_check = QCheckBox("Track one serial / IMEI per physical unit")
        self.add_field_row(("Barcode / SKU", self.barcode_edit), ("Serial Tracking", self.track_serials_check))

        self.category_combo = QComboBox()
        self._load_categories()
        self.add_field("Category", self.category_combo)

        self.add_section("Pricing & Tax")
        self.purchase_price_edit = QLineEdit()
        self.purchase_price_edit.setPlaceholderText("0.00")
        self.selling_price_edit = QLineEdit()
        self.selling_price_edit.setPlaceholderText("0.00")
        self.add_field_row(
            ("Purchase Price before GST (₹)", self.purchase_price_edit),
            ("Selling Price before GST (₹)", self.selling_price_edit),
        )

        self.gst_combo = QComboBox()
        self.gst_combo.addItems([f"{r}%" for r in config.GST_SLABS])
        self.gst_combo.setCurrentText("18%")
        self.hsn_edit = QLineEdit(); self.hsn_edit.setPlaceholderText("HSN Code")
        self.add_field_row(("GST Rate", self.gst_combo), ("HSN Code", self.hsn_edit))

        self.add_section("Stock")
        self.stock_edit = QLineEdit()
        self.stock_edit.setPlaceholderText("0")
        self.min_stock_edit = QLineEdit()
        self.min_stock_edit.setPlaceholderText("2")
        self.min_stock_edit.setText("2")
        self.unit_edit = QLineEdit(); self.unit_edit.setText("Pcs"); self.unit_edit.setFixedWidth(80)
        self.add_field_row(
            ("Opening Stock", self.stock_edit),
            ("Min Alert", self.min_stock_edit),
            ("Unit", self.unit_edit),
        )

        self.warranty_spin = QSpinBox()
        self.warranty_spin.setRange(0, 120)
        self.warranty_spin.setSuffix(" months")
        self.add_field("Default Warranty", self.warranty_spin)

        self.add_section("Notes")
        self.desc_edit = QTextEdit(); self.desc_edit.setFixedHeight(55)
        self.desc_edit.setPlaceholderText("Product description / notes")
        self.add_field("Description", self.desc_edit)

    def _load_categories(self):
        session = get_db()
        try:
            self._categories = session.query(Category).order_by(Category.name).all()
            self.category_combo.clear()
            self.category_combo.addItem("— No Category —", None)
            for cat in self._categories:
                self.category_combo.addItem(cat.name, cat.id)
        finally:
            session.close()

    def _populate(self, p: Product):
        self.name_edit.setText(p.name or "")
        self.brand_edit.setText(p.brand or "")
        self.model_edit.setText(p.model_no or "")
        self.barcode_edit.setText(p.barcode or "")
        self.track_serials_check.setChecked(bool(p.track_serials))
        self.warranty_spin.setValue(int(p.warranty_months or 0))
        self.purchase_price_edit.setText(str(p.purchase_price or 0))
        self.selling_price_edit.setText(str(p.selling_price or 0))
        self.gst_combo.setCurrentText(f"{int(p.gst_rate)}%")
        self.hsn_edit.setText(p.hsn_code or "")
        self.stock_edit.setText(str(p.stock_qty or 0))
        self.stock_edit.setEnabled(False)
        self.stock_edit.setToolTip("Use Adjust Stock or Purchases / GRN to change current stock.")
        self.min_stock_edit.setText(str(p.min_stock or 2))
        self.unit_edit.setText(p.unit or "Pcs")
        self.desc_edit.setPlainText(p.description or "")
        if p.category_id:
            idx = self.category_combo.findData(p.category_id)
            if idx >= 0:
                self.category_combo.setCurrentIndex(idx)

    def _collect(self):
        name = self.name_edit.text().strip()
        if not name:
            raise ValidationError("Product name is required.")
        gst_rate = float(self.gst_combo.currentText().replace("%", ""))
        purchase_price = _parse_price(self.purchase_price_edit.text(), "Purchase Price")
        selling_price = _parse_price(self.selling_price_edit.text(), "Selling Price")
        stock_qty = _parse_stock(self.stock_edit.text(), "Opening Stock", default=0)
        min_stock = _parse_stock(self.min_stock_edit.text(), "Min Alert", default=2)
        if not self._product and self.track_serials_check.isChecked() and stock_qty > 0:
            raise ValidationError(
                "Opening stock must be 0 for a serial-tracked product. "
                "Use Purchases / GRN to receive each unit with its serial number."
            )
        return {
            "name": name,
            "brand": self.brand_edit.text().strip() or None,
            "model_no": self.model_edit.text().strip() or None,
            "barcode": self.barcode_edit.text().strip() or None,
            "track_serials": self.track_serials_check.isChecked(),
            "warranty_months": self.warranty_spin.value(),
            "category_id": self.category_combo.currentData(),
            "hsn_code": self.hsn_edit.text().strip() or None,
            "gst_rate": gst_rate,
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "stock_qty": stock_qty,
            "min_stock": min_stock,
            "unit": self.unit_edit.text().strip() or "Pcs",
            "description": self.desc_edit.toPlainText().strip() or None,
        }


class InventoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self._products: list[Product] = []
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

        hdr = QHBoxLayout()
        title = QLabel("Inventory / Products")
        title.setObjectName("PageTitle")
        hdr.addWidget(title)
        hdr.addStretch()

        self.cat_combo = QComboBox()
        self.cat_combo.setFixedWidth(180)
        self.cat_combo.currentIndexChanged.connect(self.refresh)
        hdr.addWidget(QLabel("Category:"))
        hdr.addWidget(self.cat_combo)

        layout.addLayout(hdr)

        self.summary_bar = QLabel("")
        self.summary_bar.setStyleSheet("color: #6e7681; font-size: 11px;")
        layout.addWidget(self.summary_bar)

        self.table = DataTable(
            columns=["#", "Name", "Brand / Model", "Category", "Stock", "Tracking", "Purchase ₹", "Selling ₹", "GST%"],
            searchable=True,
            actions=[
                ("➕  Add Product",   self._add),
                ("✏️  Edit",           self._edit),
                ("📥  Adjust Stock",  self._adjust_stock),
                ("⏸  Deactivate",    self._deactivate),
            ],
        )
        self.table.row_double_clicked.connect(self._edit)
        layout.addWidget(self.table)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        session = get_db()
        try:
            cats = session.query(Category).order_by(Category.name).all()
            current_cat_id = self.cat_combo.currentData()
            self.cat_combo.blockSignals(True)
            self.cat_combo.clear()
            self.cat_combo.addItem("All Categories", None)
            for cat in cats:
                self.cat_combo.addItem(cat.name, cat.id)
            if current_cat_id:
                idx = self.cat_combo.findData(current_cat_id)
                if idx >= 0:
                    self.cat_combo.setCurrentIndex(idx)
            self.cat_combo.blockSignals(False)

            q = session.query(Product).filter_by(is_active=True)
            cat_id = self.cat_combo.currentData()
            if cat_id:
                q = q.filter(Product.category_id == cat_id)
            self._products = q.order_by(Product.name).all()

            rows = []
            for i, p in enumerate(self._products, 1):
                stock_str = str(p.stock_qty)
                rows.append([
                    str(i), p.name, " / ".join(x for x in [p.brand, p.model_no] if x) or "—",
                    p.category.name if p.category else "—",
                    stock_str, "Serial" if p.track_serials else "Quantity",
                    f"₹{p.purchase_price:,.0f}", f"₹{p.selling_price:,.0f}",
                    f"{int(p.gst_rate)}%",
                ])
            self.table.set_data(rows)

            low = sum(1 for p in self._products if p.stock_qty <= p.min_stock)
            total_val = sum(p.stock_qty * p.purchase_price for p in self._products)
            self.summary_bar.setText(
                f"  {len(self._products)} products  •  "
                f"⚠️  {low} low stock  •  "
                f"Inventory value: ₹{total_val:,.0f}"
            )

            for r in range(self.table._table.rowCount()):
                orig = self.table._original_indices[r] if r < len(self.table._original_indices) else None
                if orig is not None and self._products[orig].stock_qty <= self._products[orig].min_stock:
                    for c in range(self.table._table.columnCount()):
                        item = self.table._table.item(r, c)
                        if item:
                            item.setForeground(__import__(
                                "PySide6.QtGui", fromlist=["QColor"]).QColor("#f87171"))
        finally:
            session.close()

    def _selected(self) -> Product | None:
        idx = self.table.get_selected_original_index()
        if idx is None:
            show_warning(self, "Please select a product.")
            return None
        return self._products[idx]

    def _add(self):
        dlg = AddEditProductDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_db()
            try:
                p = Product(**dlg.get_data())
                session.add(p)
                session.commit()
                self.refresh()
                show_success(self, "Product added.")
            except Exception as e:
                session.rollback()
                show_error(self, str(e))
            finally:
                session.close()

    def _edit(self, idx=None):
        product = self._selected()
        if not product:
            return
        session = get_db()
        try:
            p = session.query(Product).get(product.id)
            dlg = AddEditProductDialog(product=p, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for k, v in dlg.get_data().items():
                    setattr(p, k, v)
                session.commit()
                self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def _adjust_stock(self):
        product = self._selected()
        if not product:
            return
        if product.track_serials:
            show_warning(
                self,
                "This product is serial-tracked. Use Purchases / GRN to add stock "
                "so every physical unit has a serial number.",
            )
            return
        val, ok = QInputDialog.getInt(
            self, "Adjust Stock",
            f"Enter adjustment for '{product.name}'\n(positive=add, negative=reduce):",
            0, -product.stock_qty, 99999
        )
        if ok and val != 0:
            session = get_db()
            try:
                p = session.query(Product).get(product.id)
                p.stock_qty += val
                user = AuthSession.current_user()
                session.add(StockMovement(
                    product_id=p.id,
                    movement_type="Adjustment",
                    quantity=val,
                    resulting_stock=p.stock_qty,
                    reference_type="Manual",
                    notes="Manual stock adjustment from Inventory",
                    created_by=user.id if user else None,
                ))
                session.commit()
                self.refresh()
                show_success(self, f"Stock adjusted. New stock: {p.stock_qty}")
            except Exception as e:
                session.rollback()
                show_error(self, str(e))
            finally:
                session.close()

    def _deactivate(self):
        product = self._selected()
        if not product:
            return
        reply = QMessageBox.question(self, "Confirm", f"Deactivate '{product.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = get_db()
            try:
                p = session.query(Product).get(product.id)
                p.is_active = False
                session.commit()
                self.refresh()
            finally:
                session.close()
