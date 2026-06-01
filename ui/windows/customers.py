"""
Progressive Enterprises – Customers Module
Customer list with search, add/edit dialog, and ledger popup.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit, QComboBox, QTextEdit, QDialog,
    QMessageBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt

from ui.components.data_table import DataTable
from ui.components.form_dialog import FormDialog, ValidationError
from ui.components.toast import show_toast, show_success, show_warning, show_error
from db.manager import get_db
from db.models import Customer, Sale, Payment, EMIRecord


class AddEditCustomerDialog(FormDialog):
    def __init__(self, customer: Customer = None, parent=None):
        mode = "Edit Customer" if customer else "Add New Customer"
        super().__init__(mode, "Fill in the customer details below", width=560, parent=parent)
        self._customer = customer
        self._build_fields()
        if customer:
            self._populate(customer)
        self.finalize()

    def _build_fields(self):
        self.add_section("Personal Information")
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Full Name")
        self.add_field("Full Name *", self.name_edit)

        row1 = QHBoxLayout()
        self.phone_edit = QLineEdit(); self.phone_edit.setPlaceholderText("Primary Phone")
        self.alt_phone_edit = QLineEdit(); self.alt_phone_edit.setPlaceholderText("Alternate Phone")
        row1.addWidget(QLabel("Phone *")); row1.addWidget(self.phone_edit)
        row1.addWidget(QLabel("Alt Phone")); row1.addWidget(self.alt_phone_edit)
        self.body_layout.addLayout(row1)

        self.email_edit = QLineEdit(); self.email_edit.setPlaceholderText("Email Address")
        self.add_field("Email", self.email_edit)

        self.add_section("Address")
        self.address_edit = QTextEdit(); self.address_edit.setPlaceholderText("Full Address")
        self.address_edit.setFixedHeight(70)
        self.add_field("Address", self.address_edit)

        self.city_edit = QLineEdit(); self.city_edit.setPlaceholderText("City")
        self.add_field("City", self.city_edit)

        self.add_section("ID & GST Details")
        id_row = QHBoxLayout()
        self.id_type_combo = QComboBox()
        self.id_type_combo.addItems(["Aadhaar", "PAN", "Voter ID", "Passport", "Driving License", "Other"])
        self.id_no_edit = QLineEdit(); self.id_no_edit.setPlaceholderText("ID Number")
        id_row.addWidget(QLabel("ID Type")); id_row.addWidget(self.id_type_combo)
        id_row.addWidget(QLabel("ID No.")); id_row.addWidget(self.id_no_edit)
        self.body_layout.addLayout(id_row)

        self.gstin_edit = QLineEdit(); self.gstin_edit.setPlaceholderText("GSTIN (if applicable)")
        self.add_field("GSTIN", self.gstin_edit)

        self.add_section("Notes")
        self.notes_edit = QTextEdit(); self.notes_edit.setPlaceholderText("Internal notes...")
        self.notes_edit.setFixedHeight(60)
        self.add_field("Notes", self.notes_edit)

    def _populate(self, c: Customer):
        self.name_edit.setText(c.name or "")
        self.phone_edit.setText(c.phone or "")
        self.alt_phone_edit.setText(c.alt_phone or "")
        self.email_edit.setText(c.email or "")
        self.address_edit.setPlainText(c.address or "")
        self.city_edit.setText(c.city or "")
        self.gstin_edit.setText(c.gstin or "")
        self.id_no_edit.setText(c.id_proof_no or "")
        self.notes_edit.setPlainText(c.notes or "")
        if c.id_proof_type:
            idx = self.id_type_combo.findText(c.id_proof_type)
            if idx >= 0:
                self.id_type_combo.setCurrentIndex(idx)

    def _collect(self):
        name = self.name_edit.text().strip()
        phone = self.phone_edit.text().strip()
        if not name:
            raise ValidationError("Customer name is required.")
        if not phone:
            raise ValidationError("Phone number is required.")
        return {
            "name": name, "phone": phone,
            "alt_phone": self.alt_phone_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "address": self.address_edit.toPlainText().strip() or None,
            "city": self.city_edit.text().strip() or None,
            "gstin": self.gstin_edit.text().strip() or None,
            "id_proof_type": self.id_type_combo.currentText(),
            "id_proof_no": self.id_no_edit.text().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }


class CustomerLedgerDialog(QDialog):
    """Shows all transactions for a customer."""
    def __init__(self, customer: Customer, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Ledger – {customer.name}")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        self._customer = customer
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel(f"📒  Customer Ledger: {self._customer.name}  •  {self._customer.phone}")
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #e2e8f0; padding-bottom: 8px;")
        layout.addWidget(header)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Sales tab
        sales_widget = QWidget()
        self.sales_table = self._make_table(["Invoice No", "Date", "Items", "Total", "Paid", "Balance", "Mode"])
        QVBoxLayout(sales_widget).addWidget(self.sales_table)
        tabs.addTab(sales_widget, "🧾  Sales")

        # EMI tab
        emi_widget = QWidget()
        self.emi_table = self._make_table(["Sale", "Finance Co.", "Loan Amt", "Tenure", "EMI/Month", "Status"])
        QVBoxLayout(emi_widget).addWidget(self.emi_table)
        tabs.addTab(emi_widget, "💳  EMI Records")

        # Payments tab
        pay_widget = QWidget()
        self.pay_table = self._make_table(["Date", "Amount", "Mode", "Reference", "Notes"])
        QVBoxLayout(pay_widget).addWidget(self.pay_table)
        tabs.addTab(pay_widget, "💰  Payments")

        close_btn = QPushButton("Close")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _make_table(self, cols):
        t = QTableWidget()
        t.setColumnCount(len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def _load_data(self):
        session = get_db()
        try:
            cid = self._customer.id
            # Sales
            sales = session.query(Sale).filter_by(customer_id=cid, is_cancelled=False).order_by(Sale.sale_date.desc()).all()
            self.sales_table.setRowCount(len(sales))
            for r, s in enumerate(sales):
                for c, val in enumerate([
                    s.invoice_no,
                    s.sale_date.strftime("%d %b %Y"),
                    str(len(s.items)),
                    f"₹{s.grand_total:,.0f}",
                    f"₹{s.amount_received:,.0f}",
                    f"₹{s.balance_due:,.0f}",
                    s.payment_mode,
                ]):
                    self.sales_table.setItem(r, c, QTableWidgetItem(val))

            # EMI
            emis = session.query(EMIRecord).filter_by(customer_id=cid).all()
            self.emi_table.setRowCount(len(emis))
            for r, e in enumerate(emis):
                for c, val in enumerate([
                    e.sale.invoice_no if e.sale else "—",
                    e.finance_provider.name if e.finance_provider else "—",
                    f"₹{e.loan_amount:,.0f}",
                    f"{e.tenure_months} months",
                    f"₹{e.monthly_installment:,.0f}",
                    e.status,
                ]):
                    self.emi_table.setItem(r, c, QTableWidgetItem(val))

            # Payments
            payments = session.query(Payment).filter_by(customer_id=cid).order_by(Payment.payment_date.desc()).all()
            self.pay_table.setRowCount(len(payments))
            for r, p in enumerate(payments):
                for c, val in enumerate([
                    p.payment_date.strftime("%d %b %Y"),
                    f"₹{p.amount:,.0f}",
                    p.mode,
                    p.reference_no or "—",
                    p.notes or "—",
                ]):
                    self.pay_table.setItem(r, c, QTableWidgetItem(val))
        finally:
            session.close()


class CustomersPage(QWidget):
    def __init__(self):
        super().__init__()
        self._customers: list[Customer] = []
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

        # Header
        hdr = QHBoxLayout()
        title = QLabel("Customers")
        title.setObjectName("PageTitle")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        # Table
        self.table = DataTable(
            columns=["#", "Name", "Phone", "City", "GSTIN", "Registered"],
            searchable=True,
            actions=[
                ("➕  Add Customer", self._add_customer),
                ("📒  Ledger",       self._view_ledger),
                ("✏️  Edit",          self._edit_customer),
                ("🗑  Deactivate",   self._deactivate),
            ],
        )
        self.table.row_double_clicked.connect(self._view_ledger)
        layout.addWidget(self.table)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        session = get_db()
        try:
            self._customers = session.query(Customer).filter_by(is_active=True).order_by(Customer.name).all()
            rows = []
            for i, c in enumerate(self._customers, 1):
                rows.append([
                    str(i), c.name, c.phone,
                    c.city or "—", c.gstin or "—",
                    c.created_at.strftime("%d %b %Y"),
                ])
            self.table.set_data(rows)
        finally:
            session.close()

    def _selected_customer(self) -> Customer | None:
        idx = self.table.get_selected_original_index()
        if idx is None:
            show_warning(self, "Please select a customer first.")
            return None
        return self._customers[idx]

    def _add_customer(self):
        dlg = AddEditCustomerDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            session = get_db()
            try:
                c = Customer(**data)
                session.add(c)
                session.commit()
                self.refresh()
                show_success(self, f"Customer '{data['name']}' added successfully.")
            except Exception as e:
                session.rollback()
                show_error(self, str(e))
            finally:
                session.close()

    def _edit_customer(self):
        customer = self._selected_customer()
        if not customer:
            return
        session = get_db()
        try:
            # Re-fetch to get a live object
            c = session.query(Customer).get(customer.id)
            dlg = AddEditCustomerDialog(customer=c, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    setattr(c, k, v)
                session.commit()
                self.refresh()
                show_success(self, "Customer updated.")
        except Exception as e:
            session.rollback()
            show_error(self, str(e))
        finally:
            session.close()

    def _view_ledger(self, idx=None):
        customer = self._selected_customer()
        if not customer:
            return
        session = get_db()
        try:
            c = session.query(Customer).get(customer.id)
            dlg = CustomerLedgerDialog(c, parent=self)
            dlg.exec()
        finally:
            session.close()

    def _deactivate(self):
        customer = self._selected_customer()
        if not customer:
            return
        reply = QMessageBox.question(
            self, "Confirm",
            f"Deactivate customer '{customer.name}'?\nThis won't delete their records.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            session = get_db()
            try:
                c = session.query(Customer).get(customer.id)
                c.is_active = False
                session.commit()
                self.refresh()
            finally:
                session.close()
