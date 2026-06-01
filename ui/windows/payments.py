"""
Progressive Enterprises – Payments Module
Record and track incoming/outgoing payments.
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QLineEdit, QTextEdit, QFrame, QScrollArea,
    QDialog, QMessageBox, QTabWidget, QDateEdit
)
from PySide6.QtCore import QDate

from ui.components.data_table import DataTable
from ui.components.form_dialog import FormDialog, ValidationError
from db.manager import get_db
from db.models import Payment, Customer, Vendor
from core.auth import AuthSession


def _parse_amount(text: str) -> float:
    """Parse a monetary amount from text. Raises ValidationError on failure."""
    text = text.strip().lstrip("₹").strip()
    if not text:
        raise ValidationError("Amount is required.")
    try:
        val = float(text)
    except ValueError:
        raise ValidationError("Amount must be a number (e.g. 1500 or 1500.50).")
    if val <= 0:
        raise ValidationError("Amount must be greater than zero.")
    if val > 9_999_999:
        raise ValidationError("Amount exceeds maximum allowed value.")
    return val


class AddPaymentDialog(FormDialog):
    def __init__(self, payment_type: str = "receipt", parent=None):
        title = "Record Receipt" if payment_type == "receipt" else "Record Payment to Vendor"
        super().__init__(title, width=460, parent=parent)
        self._type = payment_type
        self._customers = []
        self._vendors = []
        self._build_fields()
        self.finalize()

    def _build_fields(self):
        if self._type == "receipt":
            self.add_field("Customer", QLabel("Loading..."))
            self._cust_combo = QComboBox()
            self.body_layout.addWidget(self._cust_combo)
        else:
            self._vend_combo = QComboBox()
            self.add_field("Vendor", self._vend_combo)

        self.amount_edit = QLineEdit()
        self.amount_edit.setPlaceholderText("Amount in ₹ (e.g. 5000)")
        self.add_field("Amount *", self.amount_edit)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Cash", "Card", "UPI", "Cheque", "NEFT/RTGS"])
        self.add_field("Payment Mode", self.mode_combo)

        self.ref_edit = QLineEdit()
        self.ref_edit.setPlaceholderText("Reference / Transaction No.")
        self.add_field("Reference No.", self.ref_edit)

        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.add_field("Payment Date", self.date_edit)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(55)
        self.add_field("Notes", self.notes_edit)

        # Load data
        session = get_db()
        try:
            if self._type == "receipt":
                self._customers = session.query(Customer).filter_by(is_active=True).all()
                for c in self._customers:
                    self._cust_combo.addItem(f"{c.name} – {c.phone}", c.id)
            else:
                self._vendors = session.query(Vendor).filter_by(is_active=True).all()
                self._vend_combo.addItem("— Select Vendor —", None)
                for v in self._vendors:
                    self._vend_combo.addItem(v.name, v.id)
        finally:
            session.close()

    def _collect(self):
        amount = _parse_amount(self.amount_edit.text())
        data = {
            "payment_type": self._type,
            "amount": amount,
            "mode": self.mode_combo.currentText(),
            "reference_no": self.ref_edit.text().strip() or None,
            "payment_date": self.date_edit.date().toPython(),
            "notes": self.notes_edit.toPlainText().strip() or None,
        }
        if self._type == "receipt":
            data["customer_id"] = getattr(self, "_cust_combo", None) and self._cust_combo.currentData()
        else:
            data["vendor_id"] = self._vend_combo.currentData()
        return data


class PaymentsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._payments = []
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

        title = QLabel("Payments")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Receipts tab
        receipts_tab = QWidget()
        rl = QVBoxLayout(receipts_tab); rl.setContentsMargins(12, 12, 12, 12)
        self.receipts_table = DataTable(
            columns=["Date", "Customer", "Amount", "Mode", "Reference", "Notes"],
            searchable=True,
            actions=[("➕  New Receipt", self._add_receipt)],
        )
        rl.addWidget(self.receipts_table)
        tabs.addTab(receipts_tab, "💰  Customer Receipts")

        # Payments tab
        pays_tab = QWidget()
        pl = QVBoxLayout(pays_tab); pl.setContentsMargins(12, 12, 12, 12)
        self.pays_table = DataTable(
            columns=["Date", "Vendor", "Amount", "Mode", "Reference", "Notes"],
            searchable=True,
            actions=[("➕  New Payment", self._add_payment)],
        )
        pl.addWidget(self.pays_table)
        tabs.addTab(pays_tab, "🏭  Vendor Payments")

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        session = get_db()
        try:
            receipts = (session.query(Payment)
                        .filter_by(payment_type="receipt")
                        .order_by(Payment.payment_date.desc()).limit(200).all())
            self.receipts_table.set_data([
                [p.payment_date.strftime("%d %b %Y"),
                 p.customer.name if p.customer else "—",
                 f"₹{p.amount:,.0f}", p.mode,
                 p.reference_no or "—", p.notes or "—"]
                for p in receipts
            ])
            payments = (session.query(Payment)
                        .filter_by(payment_type="payment")
                        .order_by(Payment.payment_date.desc()).limit(200).all())
            self.pays_table.set_data([
                [p.payment_date.strftime("%d %b %Y"),
                 p.vendor.name if p.vendor else "—",
                 f"₹{p.amount:,.0f}", p.mode,
                 p.reference_no or "—", p.notes or "—"]
                for p in payments
            ])
        finally:
            session.close()

    def _add_receipt(self):
        dlg = AddPaymentDialog("receipt", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_payment(dlg.get_data())

    def _add_payment(self):
        dlg = AddPaymentDialog("payment", parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._save_payment(dlg.get_data())

    def _save_payment(self, data: dict):
        user = AuthSession.current_user()
        session = get_db()
        try:
            p = Payment(**data, created_by=user.id if user else None)
            session.add(p); session.commit()
            self.refresh()
            QMessageBox.information(self, "Success", "Payment recorded.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
