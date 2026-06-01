"""
Progressive Enterprises – Sales History Module
Dedicated page to view past sales, search invoices, and reprint them.
"""

from datetime import date, datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QLineEdit,
    QTableWidget, QTableWidgetItem, QMessageBox, QDateEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QDate, Signal

from db.manager import get_db
from db.models import Sale, Product, Payment, EMIRecord

class SalesHistoryPage(QWidget):
    # Emit (sale_id) to signal main window to switch to POS for editing
    modify_sale_requested = Signal(int)

    def __init__(self):
        super().__init__()
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
        layout.setSpacing(12)

        title = QLabel("Sales History")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # Filter bar
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by invoice, customer...")
        self.search_input.setMinimumWidth(180)
        self.search_input.setMaximumWidth(300)

        self.from_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.from_date.setCalendarPopup(True)
        
        self.to_date = QDateEdit(QDate.currentDate())
        self.to_date.setCalendarPopup(True)

        search_btn = QPushButton("Search")
        search_btn.setObjectName("PrimaryBtn")
        search_btn.clicked.connect(self.refresh)

        for w in [self.search_input, QLabel("From:"), self.from_date, QLabel("To:"), self.to_date, search_btn]:
            filter_bar.addWidget(w)
        filter_bar.addStretch()
        
        layout.addLayout(filter_bar)

        # Action bar
        action_bar = QHBoxLayout()
        action_bar.addStretch()

        self.reprint_btn = QPushButton("🖨️ Reprint")
        self.reprint_btn.setObjectName("IconBtn")
        self.reprint_btn.clicked.connect(self._reprint_selected)
        
        self.modify_btn = QPushButton("✏️ Modify")
        self.modify_btn.setObjectName("PrimaryBtn")
        self.modify_btn.clicked.connect(self._modify_selected)
        
        self.cancel_btn = QPushButton("🚫 Cancel Sale")
        self.cancel_btn.setObjectName("DangerBtn")
        self.cancel_btn.clicked.connect(self._cancel_selected)

        action_bar.addWidget(self.reprint_btn)
        action_bar.addWidget(self.modify_btn)
        action_bar.addWidget(self.cancel_btn)
        
        layout.addLayout(action_bar)

        # Table
        self.table = QTableWidget()
        cols = ["ID", "Invoice No", "Date", "Customer", "Items", "Grand Total", "Payment Mode"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.hideColumn(0) # Hide ID

        layout.addWidget(self.table, 1)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

        self.refresh()

    def refresh(self):
        search_text = self.search_input.text().strip().lower()
        from_d = self.from_date.date().toPython()
        to_d = self.to_date.date().toPython()
        start = datetime.combine(from_d, datetime.min.time())
        end = datetime.combine(to_d, datetime.max.time())

        session = get_db()
        try:
            query = session.query(Sale).filter(
                Sale.sale_date.between(start, end),
                Sale.is_cancelled == False
            )
            
            # Simple manual routing of text search since customer is a joined relationship
            # or we fetch and filter in python for smaller scale (ERP typical)
            sales = query.order_by(Sale.sale_date.desc()).all()
            
            if search_text:
                filtered_sales = []
                for s in sales:
                    cust_name = (s.customer.name if s.customer else "Walk-in").lower()
                    if search_text in s.invoice_no.lower() or search_text in cust_name:
                        filtered_sales.append(s)
                sales = filtered_sales

            self.table.setRowCount(len(sales))
            for r, s in enumerate(sales):
                cust_name = s.customer.name if s.customer else "Walk-in"
                # Store real ID in the first hidden col
                
                vals = [
                    str(s.id),
                    s.invoice_no,
                    s.sale_date.strftime("%d %b %Y %H:%M"),
                    cust_name,
                    str(len(s.items)),
                    f"₹{s.grand_total:,.2f}",
                    s.payment_mode
                ]
                
                for c, val in enumerate(vals):
                    item = QTableWidgetItem(val)
                    if c == 0:
                        item.setData(Qt.UserRole, s.id)
                    self.table.setItem(r, c, item)

        finally:
            session.close()

    def _reprint_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a sale to reprint.")
            return
            
        sale_id = self.table.item(row, 0).data(Qt.UserRole)
        
        session = get_db()
        try:
            sale_obj = session.query(Sale).get(sale_id)
            if not sale_obj:
                return
                
            from core.invoice_gen import generate_invoice
            pdf_path = generate_invoice(sale_obj)
            
            from ui.components.export_dialog import ExportReadyDialog
            ExportReadyDialog(pdf_path, self).exec()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reprint invoice:\\n{e}")
        finally:
            session.close()

    def _cancel_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a sale to cancel.")
            return

        sale_id = self.table.item(row, 0).data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, "Confirm Cancellation", 
            "Are you sure you want to cancel this sale?\\n\\nThis will restore product stock and reverse any linked payment receipts.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        session = get_db()
        try:
            sale = session.query(Sale).get(sale_id)
            if not sale or sale.is_cancelled:
                return

            # 1. Mark as cancelled
            sale.is_cancelled = True

            # 2. Restore Stock
            for item in sale.items:
                product = session.query(Product).get(item.product_id)
                if product:
                    product.stock_qty += item.qty

            # 3. Handle Payments
            if sale.amount_received > 0 and sale.payment_mode != "EMI":
                # Delete receipt payment entry
                session.query(Payment).filter_by(sale_id=sale.id).delete()
            
            # 4. Handle EMI
            if sale.payment_mode == "EMI" and sale.emi_record:
                sale.emi_record.status = "Closed"
                sale.emi_record.notes = (sale.emi_record.notes or "") + "\\nSale Cancelled."

            session.commit()
            QMessageBox.information(self, "Cancelled", f"Invoice {sale.invoice_no} has been cancelled and stock restored.")
            self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", f"Failed to cancel sale:\\n{e}")
        finally:
            session.close()

    def _modify_selected(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "No Selection", "Please select a sale to modify.")
            return

        sale_id = self.table.item(row, 0).data(Qt.UserRole)
        confirm = QMessageBox.question(
            self, "Modify Sale", 
            "Modifying a sale will cancel the original invoice and load its items back into the POS cart.\\n\\nDo you wish to proceed?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.modify_sale_requested.emit(sale_id)
