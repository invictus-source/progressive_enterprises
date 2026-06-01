"""
Progressive Enterprises – Reports Module
Sales reports, profit summary, date-range filtering, Excel/PDF export.
"""

from datetime import date, datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTabWidget, QTableWidget, QTableWidgetItem, QMessageBox,
    QDateEdit, QFrame, QScrollArea
)
from PySide6.QtCore import Qt, QDate

from db.manager import get_db
from db.models import Sale, SaleItem, Product, Customer


class ReportsPage(QWidget):
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
        layout.setContentsMargins(24, 20, 24, 20); layout.setSpacing(12)

        title = QLabel("Reports & Analytics")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        # Filter bar
        filter_bar = QHBoxLayout(); filter_bar.setSpacing(10)
        self.from_date = QDateEdit(QDate.currentDate().addDays(-30))
        self.from_date.setCalendarPopup(True)
        self.to_date = QDateEdit(QDate.currentDate())
        self.to_date.setCalendarPopup(True)

        run_btn = QPushButton("Generate"); run_btn.setObjectName("PrimaryBtn")
        run_btn.clicked.connect(self.refresh)
        export_btn = QPushButton("📥  Export Excel"); export_btn.clicked.connect(self._export)

        for w in [QLabel("From:"), self.from_date, QLabel("To:"), self.to_date,
                  run_btn, export_btn]:
            filter_bar.addWidget(w)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        # KPI row
        kpi = QHBoxLayout(); kpi.setSpacing(12)
        self.kpi_sales   = self._kpi_card("Total Sales", "₹0")
        self.kpi_txns    = self._kpi_card("Transactions", "0")
        self.kpi_profit  = self._kpi_card("Est. Profit", "₹0")
        self.kpi_avg     = self._kpi_card("Avg. Order", "₹0")
        for card in [self.kpi_sales, self.kpi_txns, self.kpi_profit, self.kpi_avg]:
            kpi.addWidget(card)
        layout.addLayout(kpi)

        # Tabs
        tabs = QTabWidget(); layout.addWidget(tabs)

        # Sales summary tab
        st = QWidget(); sl = QVBoxLayout(st); sl.setContentsMargins(8,8,8,8)
        self.sales_table = self._make_table(["Invoice", "Date", "Customer", "Items", "Total", "GST", "Mode"])
        sl.addWidget(self.sales_table)
        tabs.addTab(st, "🧾  Sales Transactions")

        # Product-wise tab
        pt = QWidget(); pl = QVBoxLayout(pt); pl.setContentsMargins(8,8,8,8)
        self.product_table = self._make_table(["Product", "Units Sold", "Revenue", "GST Collected", "Est. Profit"])
        pl.addWidget(self.product_table)
        tabs.addTab(pt, "📦  Product-wise Sales")

        # Daily summary tab
        dt = QWidget(); dl = QVBoxLayout(dt); dl.setContentsMargins(8,8,8,8)
        self.daily_table = self._make_table(["Date", "Transactions", "Revenue", "GST", "Profit"])
        dl.addWidget(self.daily_table)
        tabs.addTab(dt, "📅  Daily Summary")

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.refresh()

    def _kpi_card(self, label: str, value: str) -> QFrame:
        f = QFrame(); f.setObjectName("StatCard")
        vl = QVBoxLayout(f); vl.setContentsMargins(16,12,16,12)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet("font-size: 22px; font-weight: bold; color: #60a5fa;")
        lbl_lbl = QLabel(label.upper())
        lbl_lbl.setStyleSheet("font-size: 10px; color: #8b949e; letter-spacing:1px;")
        vl.addWidget(val_lbl); vl.addWidget(lbl_lbl)
        f._val_lbl = val_lbl
        return f

    def _make_table(self, cols):
        t = QTableWidget()
        t.setColumnCount(len(cols))
        t.setHorizontalHeaderLabels(cols)
        t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        t.setAlternatingRowColors(True)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def refresh(self):
        from_d = self.from_date.date().toPython()
        to_d = self.to_date.date().toPython()
        start = datetime.combine(from_d, datetime.min.time())
        end = datetime.combine(to_d, datetime.max.time())

        session = get_db()
        try:
            sales = session.query(Sale).filter(
                Sale.sale_date.between(start, end),
                Sale.is_cancelled == False
            ).order_by(Sale.sale_date.desc()).all()

            total_rev = sum(s.grand_total for s in sales)
            total_gst = sum(s.total_gst for s in sales)

            # Estimate profit (selling - purchase cost of items)
            est_profit = 0.0
            product_summary: dict[int, dict] = {}
            for s in sales:
                for it in s.items:
                    pid = it.product_id
                    if pid not in product_summary:
                        product_summary[pid] = {
                            "name": it.product_name, "qty": 0,
                            "revenue": 0.0, "gst": 0.0, "profit": 0.0
                        }
                    p = product_summary[pid]
                    p["qty"] += it.qty
                    p["revenue"] += it.taxable_amount
                    p["gst"] += it.gst_amount
                    prod = session.query(Product).get(pid)
                    if prod:
                        p["profit"] += (it.unit_price - prod.purchase_price) * it.qty
                    est_profit += p["profit"]

            avg_order = total_rev / len(sales) if sales else 0

            self.kpi_sales._val_lbl.setText(f"₹{total_rev:,.0f}")
            self.kpi_txns._val_lbl.setText(str(len(sales)))
            self.kpi_profit._val_lbl.setText(f"₹{est_profit:,.0f}")
            self.kpi_avg._val_lbl.setText(f"₹{avg_order:,.0f}")

            # Sales table
            self.sales_table.setRowCount(len(sales))
            for r, s in enumerate(sales):
                for c, v in enumerate([
                    s.invoice_no,
                    s.sale_date.strftime("%d %b %Y"),
                    s.customer.name if s.customer else "Walk-in",
                    str(len(s.items)),
                    f"₹{s.grand_total:,.0f}",
                    f"₹{s.total_gst:,.0f}",
                    s.payment_mode,
                ]):
                    self.sales_table.setItem(r, c, QTableWidgetItem(v))

            # Product table
            sorted_prods = sorted(product_summary.values(), key=lambda x: x["revenue"], reverse=True)
            self.product_table.setRowCount(len(sorted_prods))
            for r, p in enumerate(sorted_prods):
                for c, v in enumerate([
                    p["name"], str(p["qty"]),
                    f"₹{p['revenue']:,.0f}", f"₹{p['gst']:,.0f}", f"₹{p['profit']:,.0f}",
                ]):
                    self.product_table.setItem(r, c, QTableWidgetItem(v))

            # Daily summary
            daily: dict[str, dict] = {}
            for s in sales:
                d = s.sale_date.strftime("%d %b %Y")
                if d not in daily:
                    daily[d] = {"txns": 0, "rev": 0.0, "gst": 0.0, "profit": 0.0}
                daily[d]["txns"] += 1
                daily[d]["rev"] += s.grand_total
                daily[d]["gst"] += s.total_gst
            self.daily_table.setRowCount(len(daily))
            for r, (d, vals) in enumerate(sorted(daily.items(), reverse=True)):
                for c, v in enumerate([d, str(vals["txns"]), f"₹{vals['rev']:,.0f}",
                                        f"₹{vals['gst']:,.0f}", f"₹{vals['profit']:,.0f}"]):
                    self.daily_table.setItem(r, c, QTableWidgetItem(v))
        finally:
            session.close()

    def _export(self):
        try:
            from core.excel_export import export_sales_report
            from_d = self.from_date.date().toPython()
            to_d = self.to_date.date().toPython()
            path = export_sales_report(from_d, to_d)
            from ui.components.export_dialog import ExportReadyDialog
            ExportReadyDialog(path, self).exec()
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
