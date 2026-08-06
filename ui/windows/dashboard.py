from datetime import date, datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QGridLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from ui.components.stat_card import StatCard
from db.manager import get_db
from db.models import Sale, Customer, Product, EMIRecord, EMIPayment, Purchase
import config


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self):
        super().__init__()
        self._kpi_cards = []
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
        layout.setSpacing(16)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title_lbl = QLabel("Dashboard")
        title_lbl.setObjectName("PageTitle")
        sub_lbl = QLabel(f"Welcome back!  •  {date.today().strftime('%A, %d %B %Y')}")
        sub_lbl.setObjectName("PageSubtitle")
        sub_lbl.setWordWrap(True)
        sub_lbl.setMinimumWidth(280)
        title_block.addWidget(title_lbl)
        title_block.addWidget(sub_lbl)
        header.addLayout(title_block)
        header.addStretch()

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setMinimumHeight(32)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        layout.addLayout(header)

        self.card_revenue   = StatCard("💰", "Today's Revenue",  "₹0",    "#2563eb")
        self.card_sales     = StatCard("🧾", "Sales Today",      "0",     "#7c3aed")
        self.card_customers = StatCard("👥", "Total Customers",  "0",     "#0891b2")
        self.card_emi       = StatCard("💳", "Pending EMIs",     "0",     "#d97706")
        self.card_stock     = StatCard("📦", "Low Stock Items",  "0",     "#dc2626")
        self.card_due       = StatCard("⚠️",  "Outstanding Due",  "₹0",    "#059669")

        self._kpi_cards = [
            self.card_revenue, self.card_sales,   self.card_customers,
            self.card_emi,     self.card_stock,   self.card_due
        ]

        self.kpi_grid = QGridLayout()
        self.kpi_grid.setSpacing(12)
        self._layout_kpi_cards(3)
        layout.addLayout(self.kpi_grid)

        qa_frame = QFrame()
        qa_frame.setObjectName("Card")
        qa_layout = QHBoxLayout(qa_frame)
        qa_layout.setContentsMargins(14, 10, 14, 10)
        qa_layout.setSpacing(10)

        qa_lbl = QLabel("Quick Actions")
        qa_lbl.setObjectName("FieldLabel")
        qa_layout.addWidget(qa_lbl)
        qa_layout.addStretch()

        quick_actions = [
            ("🛒  New Sale",      "#2563eb", "pos"),
            ("📦  New Purchase / GRN", "#7c3aed", "purchases"),
            ("👤  New Customer",  "#0891b2", "customers"),
            ("💳  Manage EMI",    "#d97706", "emi_finance"),
        ]
        for label, color, destination in quick_actions:
            btn = QPushButton(label)
            btn.setObjectName("PrimaryBtn")
            btn.setMinimumHeight(32)
            btn.setStyleSheet(
                f"QPushButton {{ background-color: {color}; color: white; border: none; "
                f"border-radius: 8px; padding: 8px 14px; font-weight: bold; }}"
                f"QPushButton:hover {{ opacity: 0.85; }}"
            )
            btn.clicked.connect(
                lambda _checked=False, page=destination: self.navigate_requested.emit(page)
            )
            qa_layout.addWidget(btn)

        layout.addWidget(qa_frame)

        bottom = QHBoxLayout()
        bottom.setSpacing(14)

        left_frame = QFrame()
        left_frame.setObjectName("Card")
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(8)

        left_title = QLabel("Recent Sales")
        left_title.setObjectName("SectionTitle")
        left_layout.addWidget(left_title)

        self.recent_sales_table = QTableWidget()
        self.recent_sales_table.setColumnCount(5)
        self.recent_sales_table.setHorizontalHeaderLabels(["Invoice", "Customer", "Date", "Amount", "Mode"])
        self.recent_sales_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recent_sales_table.setAlternatingRowColors(True)
        self.recent_sales_table.verticalHeader().setVisible(False)
        self.recent_sales_table.horizontalHeader().setStretchLastSection(True)
        self.recent_sales_table.setMinimumHeight(120)
        left_layout.addWidget(self.recent_sales_table, 1)
        bottom.addWidget(left_frame, 3)

        right_frame = QFrame()
        right_frame.setObjectName("Card")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(14, 14, 14, 14)
        right_layout.setSpacing(8)

        right_title = QLabel("Overdue EMIs")
        right_title.setObjectName("SectionTitle")
        right_layout.addWidget(right_title)

        self.overdue_table = QTableWidget()
        self.overdue_table.setColumnCount(4)
        self.overdue_table.setHorizontalHeaderLabels(["Customer", "Provider", "Due Date", "Amount"])
        self.overdue_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.overdue_table.setAlternatingRowColors(True)
        self.overdue_table.verticalHeader().setVisible(False)
        self.overdue_table.horizontalHeader().setStretchLastSection(True)
        self.overdue_table.setMinimumHeight(120)
        right_layout.addWidget(self.overdue_table, 1)
        bottom.addWidget(right_frame, 2)

        layout.addLayout(bottom, 1)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def _layout_kpi_cards(self, cols: int):
        while self.kpi_grid.count():
            item = self.kpi_grid.takeAt(0)
        for i, card in enumerate(self._kpi_cards):
            row = i // cols
            col = i % cols
            self.kpi_grid.addWidget(card, row, col)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        w = self.width()
        if w < 700:
            cols = 2
        elif w < 1200:
            cols = 3
        else:
            cols = 6
        self._layout_kpi_cards(cols)

    def refresh(self):
        session = get_db()
        try:
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())
            today_end = datetime.combine(today, datetime.max.time())

            today_sales = session.query(Sale).filter(
                Sale.sale_date.between(today_start, today_end),
                Sale.is_cancelled == False
            ).all()
            revenue = sum(s.grand_total for s in today_sales)
            self.card_revenue.update_value(f"₹{revenue:,.0f}")
            self.card_sales.update_value(str(len(today_sales)))

            cust_count = session.query(Customer).filter_by(is_active=True).count()
            self.card_customers.update_value(str(cust_count))

            pending_emi = session.query(EMIPayment).filter_by(is_paid=False).filter(
                EMIPayment.due_date <= today
            ).count()
            self.card_emi.update_value(str(pending_emi))

            low_stock = session.query(Product).filter(
                Product.is_active == True,
                Product.stock_qty <= Product.min_stock
            ).count()
            self.card_stock.update_value(str(low_stock))

            total_due = session.query(Sale).filter(
                Sale.is_cancelled == False
            ).all()
            outstanding = sum(s.balance_due for s in total_due)
            self.card_due.update_value(f"₹{outstanding:,.0f}")

            recent = session.query(Sale).filter(
                Sale.is_cancelled == False
            ).order_by(Sale.sale_date.desc()).limit(10).all()

            self.recent_sales_table.setRowCount(len(recent))
            for r, sale in enumerate(recent):
                cust_name = sale.customer.name if sale.customer else "Walk-in"
                self._set_cell(self.recent_sales_table, r, 0, sale.invoice_no)
                self._set_cell(self.recent_sales_table, r, 1, cust_name)
                self._set_cell(self.recent_sales_table, r, 2, sale.sale_date.strftime("%d %b %Y"))
                self._set_cell(self.recent_sales_table, r, 3, f"₹{sale.grand_total:,.0f}")
                self._set_cell(self.recent_sales_table, r, 4, sale.payment_mode)

            self.recent_sales_table.horizontalHeader().setSectionResizeMode(
                QHeaderView.ResizeMode.ResizeToContents)

            overdue = session.query(EMIPayment).filter(
                EMIPayment.is_paid == False,
                EMIPayment.due_date < today
            ).order_by(EMIPayment.due_date).limit(10).all()

            self.overdue_table.setRowCount(len(overdue))
            for r, ep in enumerate(overdue):
                rec = ep.emi_record
                cust_name = rec.customer.name if rec.customer else "—"
                provider = rec.finance_provider.name if rec.finance_provider else "—"
                self._set_cell(self.overdue_table, r, 0, cust_name)
                self._set_cell(self.overdue_table, r, 1, provider)
                self._set_cell(self.overdue_table, r, 2, ep.due_date.strftime("%d %b %Y"))
                self._set_cell(self.overdue_table, r, 3, f"₹{ep.amount_due:,.0f}")

        except Exception as e:
            print(f"[Dashboard] Refresh error: {e}")
        finally:
            session.close()

    @staticmethod
    def _set_cell(table: QTableWidget, row: int, col: int, text: str):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)
        table.setItem(row, col, item)
