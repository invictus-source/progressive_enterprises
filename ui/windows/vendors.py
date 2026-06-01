"""
Progressive Enterprises – Vendors Module
Vendor list with search, add/edit dialog, and purchase history popup.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QTextEdit, QDialog, QMessageBox,
    QTabWidget, QTableWidget, QTableWidgetItem, QFrame, QScrollArea
)
from PySide6.QtCore import Qt

from ui.components.data_table import DataTable
from ui.components.form_dialog import FormDialog, ValidationError
from db.manager import get_db
from db.models import Vendor, Purchase, Payment


class AddEditVendorDialog(FormDialog):
    def __init__(self, vendor: Vendor = None, parent=None):
        mode = "Edit Vendor" if vendor else "Add New Vendor"
        super().__init__(mode, "Fill in the vendor / supplier details", width=560, parent=parent)
        self._vendor = vendor
        self._build_fields()
        if vendor:
            self._populate(vendor)
        self.finalize()

    def _build_fields(self):
        self.add_section("Business Information")
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Vendor / Company Name")
        self.add_field("Name *", self.name_edit)

        row1 = QHBoxLayout()
        self.phone_edit = QLineEdit(); self.phone_edit.setPlaceholderText("Primary Phone")
        self.alt_phone_edit = QLineEdit(); self.alt_phone_edit.setPlaceholderText("Alternate Phone")
        row1.addWidget(QLabel("Phone *")); row1.addWidget(self.phone_edit)
        row1.addWidget(QLabel("Alt")); row1.addWidget(self.alt_phone_edit)
        self.body_layout.addLayout(row1)

        self.email_edit = QLineEdit(); self.email_edit.setPlaceholderText("Email")
        self.add_field("Email", self.email_edit)

        self.gstin_edit = QLineEdit(); self.gstin_edit.setPlaceholderText("GSTIN")
        self.add_field("GSTIN", self.gstin_edit)

        self.add_section("Address")
        self.address_edit = QTextEdit(); self.address_edit.setFixedHeight(60)
        self.address_edit.setPlaceholderText("Full address...")
        self.add_field("Address", self.address_edit)

        self.city_edit = QLineEdit(); self.city_edit.setPlaceholderText("City")
        self.add_field("City", self.city_edit)

        self.add_section("Banking Details")
        self.bank_name_edit = QLineEdit(); self.bank_name_edit.setPlaceholderText("Bank Name")
        self.add_field("Bank Name", self.bank_name_edit)

        bank_row = QHBoxLayout()
        self.bank_acc_edit = QLineEdit(); self.bank_acc_edit.setPlaceholderText("Account Number")
        self.bank_ifsc_edit = QLineEdit(); self.bank_ifsc_edit.setPlaceholderText("IFSC Code")
        bank_row.addWidget(QLabel("Account")); bank_row.addWidget(self.bank_acc_edit)
        bank_row.addWidget(QLabel("IFSC")); bank_row.addWidget(self.bank_ifsc_edit)
        self.body_layout.addLayout(bank_row)

        self.add_section("Notes")
        self.notes_edit = QTextEdit(); self.notes_edit.setFixedHeight(50)
        self.add_field("Notes", self.notes_edit)

    def _populate(self, v: Vendor):
        self.name_edit.setText(v.name or "")
        self.phone_edit.setText(v.phone or "")
        self.alt_phone_edit.setText(v.alt_phone or "")
        self.email_edit.setText(v.email or "")
        self.gstin_edit.setText(v.gstin or "")
        self.address_edit.setPlainText(v.address or "")
        self.city_edit.setText(v.city or "")
        self.bank_name_edit.setText(v.bank_name or "")
        self.bank_acc_edit.setText(v.bank_account or "")
        self.bank_ifsc_edit.setText(v.bank_ifsc or "")
        self.notes_edit.setPlainText(v.notes or "")

    def _collect(self):
        name = self.name_edit.text().strip()
        phone = self.phone_edit.text().strip()
        if not name:
            raise ValidationError("Vendor name is required.")
        if not phone:
            raise ValidationError("Phone number is required.")
        return {
            "name": name, "phone": phone,
            "alt_phone": self.alt_phone_edit.text().strip() or None,
            "email": self.email_edit.text().strip() or None,
            "gstin": self.gstin_edit.text().strip() or None,
            "address": self.address_edit.toPlainText().strip() or None,
            "city": self.city_edit.text().strip() or None,
            "bank_name": self.bank_name_edit.text().strip() or None,
            "bank_account": self.bank_acc_edit.text().strip() or None,
            "bank_ifsc": self.bank_ifsc_edit.text().strip() or None,
            "notes": self.notes_edit.toPlainText().strip() or None,
        }


class VendorsPage(QWidget):
    def __init__(self):
        super().__init__()
        self._vendors: list[Vendor] = []
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
        title = QLabel("Vendors / Suppliers")
        title.setObjectName("PageTitle")
        hdr.addWidget(title)
        hdr.addStretch()
        layout.addLayout(hdr)

        self.table = DataTable(
            columns=["#", "Name", "Phone", "City", "GSTIN", "Registered"],
            searchable=True,
            actions=[
                ("➕  Add Vendor", self._add),
                ("✏️  Edit",        self._edit),
                ("📋  Purchases",  self._view_purchases),
                ("🗑  Deactivate", self._deactivate),
            ],
        )
        self.table.row_double_clicked.connect(self._view_purchases)
        layout.addWidget(self.table)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        session = get_db()
        try:
            self._vendors = session.query(Vendor).filter_by(is_active=True).order_by(Vendor.name).all()
            rows = [
                [str(i), v.name, v.phone, v.city or "—", v.gstin or "—", v.created_at.strftime("%d %b %Y")]
                for i, v in enumerate(self._vendors, 1)
            ]
            self.table.set_data(rows)
        finally:
            session.close()

    def _selected(self) -> Vendor | None:
        idx = self.table.get_selected_original_index()
        if idx is None:
            QMessageBox.information(self, "Select Vendor", "Please select a vendor first.")
            return None
        return self._vendors[idx]

    def _add(self):
        dlg = AddEditVendorDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_db()
            try:
                v = Vendor(**dlg.get_data())
                session.add(v)
                session.commit()
                self.refresh()
                QMessageBox.information(self, "Success", "Vendor added successfully.")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def _edit(self):
        vendor = self._selected()
        if not vendor:
            return
        session = get_db()
        try:
            v = session.query(Vendor).get(vendor.id)
            dlg = AddEditVendorDialog(vendor=v, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for k, val in dlg.get_data().items():
                    setattr(v, k, val)
                session.commit()
                self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def _view_purchases(self, idx=None):
        vendor = self._selected()
        if not vendor:
            return
        session = get_db()
        try:
            v = session.query(Vendor).get(vendor.id)
            dlg = QDialog(self)
            dlg.setWindowTitle(f"Purchase History – {v.name}")
            dlg.setMinimumSize(700, 480)
            vl = QVBoxLayout(dlg)
            header = QLabel(f"📋  Purchases from: {v.name}")
            header.setStyleSheet("font-size: 15px; font-weight: bold; color: #e2e8f0;")
            vl.addWidget(header)
            t = QTableWidget()
            t.setColumnCount(6)
            t.setHorizontalHeaderLabels(["GRN No.", "Bill No.", "Date", "Items", "Total", "Balance"])
            t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t.setAlternatingRowColors(True)
            t.verticalHeader().setVisible(False)
            purchases = session.query(Purchase).filter_by(vendor_id=v.id).order_by(Purchase.purchase_date.desc()).all()
            t.setRowCount(len(purchases))
            for r, p in enumerate(purchases):
                for c, val in enumerate([p.grn_no, p.bill_no or "—", p.purchase_date.strftime("%d %b %Y"),
                                          str(len(p.items)), f"₹{p.grand_total:,.0f}", f"₹{p.balance_due:,.0f}"]):
                    t.setItem(r, c, QTableWidgetItem(val))
            vl.addWidget(t)
            close = QPushButton("Close"); close.clicked.connect(dlg.accept)
            vl.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
            dlg.exec()
        finally:
            session.close()

    def _deactivate(self):
        vendor = self._selected()
        if not vendor:
            return
        reply = QMessageBox.question(self, "Confirm", f"Deactivate vendor '{vendor.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            session = get_db()
            try:
                v = session.query(Vendor).get(vendor.id)
                v.is_active = False
                session.commit()
                self.refresh()
            finally:
                session.close()
