from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QComboBox, QTabWidget, QMessageBox,
    QFrame, QScrollArea
)
from PySide6.QtCore import Qt
from sqlalchemy import and_, or_

from db.manager import get_db
from db.models import Sale, SaleItem, Purchase, PurchaseItem

_MONTHS = ["January","February","March","April","May","June",
           "July","August","September","October","November","December"]

class GSTReportsPage(QWidget):
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

        title = QLabel("GST Reports")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        filter_bar = QHBoxLayout()
        self.month_combo = QComboBox()
        self.month_combo.addItems(_MONTHS)
        self.month_combo.setCurrentIndex(date.today().month - 1)
        self.year_combo = QComboBox()
        for y in range(date.today().year, 2023, -1):
            self.year_combo.addItem(str(y), y)
        run_btn = QPushButton("Generate Report"); run_btn.setObjectName("PrimaryBtn")
        run_btn.clicked.connect(self.refresh)
        export_btn = QPushButton("📥 Export to Excel"); export_btn.clicked.connect(self._export)

        for w in [QLabel("Month:"), self.month_combo, QLabel("Year:"), self.year_combo,
                  run_btn, export_btn]:
            filter_bar.addWidget(w)
        filter_bar.addStretch()
        layout.addLayout(filter_bar)

        self.summary_lbl = QLabel("")
        self.summary_lbl.setStyleSheet("color: #60a5fa; font-size: 12px;")
        layout.addWidget(self.summary_lbl)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        out_tab = QWidget()
        ol = QVBoxLayout(out_tab); ol.setContentsMargins(8, 8, 8, 8)
        self.out_table = self._make_table(["Invoice", "Date", "Customer", "Taxable", "CGST", "SGST", "IGST", "Total GST", "Grand Total"])
        ol.addWidget(self.out_table)
        tabs.addTab(out_tab, "📤  Outward Supplies (Sales)")

        in_tab = QWidget()
        il = QVBoxLayout(in_tab); il.setContentsMargins(8, 8, 8, 8)
        self.in_table = self._make_table(["GRN No.", "Invoice Date", "Vendor", "Taxable", "CGST", "SGST", "IGST", "Total GST", "Grand Total"])
        il.addWidget(self.in_table)
        tabs.addTab(in_tab, "📥  Inward Supplies (Purchases)")

        scroll.setWidget(content)
        page_layout.addWidget(scroll)
        self.refresh()

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
        month = self.month_combo.currentIndex() + 1
        year = self.year_combo.currentData()
        from datetime import datetime
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)

        session = get_db()
        try:
            sales = session.query(Sale).filter(
                Sale.sale_date >= start, Sale.sale_date < end,
                Sale.is_cancelled == False
            ).order_by(Sale.sale_date).all()
            self.out_table.setRowCount(len(sales) + 1)
            tot_taxable = tot_cgst = tot_sgst = tot_igst = tot_grand = 0.0
            for r, s in enumerate(sales):
                for c, v in enumerate([
                    s.invoice_no,
                    s.sale_date.strftime("%d %b %Y"),
                    s.customer.name if s.customer else "Walk-in",
                    f"₹{s.taxable_amount:,.2f}",
                    f"₹{s.cgst_amount:,.2f}",
                    f"₹{s.sgst_amount:,.2f}",
                    f"₹{s.igst_amount:,.2f}",
                    f"₹{s.total_gst:,.2f}",
                    f"₹{s.grand_total:,.2f}",
                ]):
                    self.out_table.setItem(r, c, QTableWidgetItem(v))
                tot_taxable += s.taxable_amount; tot_cgst += s.cgst_amount
                tot_sgst += s.sgst_amount; tot_igst += s.igst_amount; tot_grand += s.grand_total
            for c, v in enumerate(["TOTAL", "", "", f"₹{tot_taxable:,.2f}",
                                    f"₹{tot_cgst:,.2f}", f"₹{tot_sgst:,.2f}",
                                    f"₹{tot_igst:,.2f}",
                                    f"₹{(tot_cgst+tot_sgst+tot_igst):,.2f}", f"₹{tot_grand:,.2f}"]):
                item = QTableWidgetItem(v)
                item.setForeground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#60a5fa"))
                self.out_table.setItem(len(sales), c, item)

            purchases = session.query(Purchase).filter(
                or_(
                    and_(Purchase.invoice_date.is_not(None),
                         Purchase.invoice_date >= start.date(), Purchase.invoice_date < end.date()),
                    and_(Purchase.invoice_date.is_(None),
                         Purchase.purchase_date >= start, Purchase.purchase_date < end),
                )
            ).order_by(Purchase.purchase_date).all()
            self.in_table.setRowCount(len(purchases) + 1)
            ptot_taxable = ptot_cgst = ptot_sgst = ptot_igst = ptot_grand = 0.0
            for r, p in enumerate(purchases):
                for c, v in enumerate([
                    p.grn_no, (p.invoice_date or p.purchase_date.date()).strftime("%d %b %Y"),
                    p.vendor.name if p.vendor else "—",
                    f"₹{p.taxable_amount:,.2f}",
                    f"₹{p.cgst_amount:,.2f}",
                    f"₹{p.sgst_amount:,.2f}",
                    f"₹{p.igst_amount:,.2f}",
                    f"₹{p.total_gst:,.2f}",
                    f"₹{p.grand_total:,.2f}",
                ]):
                    self.in_table.setItem(r, c, QTableWidgetItem(v))
                ptot_taxable += p.taxable_amount; ptot_cgst += p.cgst_amount
                ptot_sgst += p.sgst_amount; ptot_igst += p.igst_amount; ptot_grand += p.grand_total
            for c, v in enumerate(["TOTAL", "", "", f"₹{ptot_taxable:,.2f}",
                                    f"₹{ptot_cgst:,.2f}", f"₹{ptot_sgst:,.2f}",
                                    f"₹{ptot_igst:,.2f}",
                                    f"₹{(ptot_cgst+ptot_sgst+ptot_igst):,.2f}", f"₹{ptot_grand:,.2f}"]):
                item = QTableWidgetItem(v)
                item.setForeground(__import__("PySide6.QtGui", fromlist=["QColor"]).QColor("#60a5fa"))
                self.in_table.setItem(len(purchases), c, item)

            output_gst = tot_cgst + tot_sgst + tot_igst
            input_gst = ptot_cgst + ptot_sgst + ptot_igst
            net_gst = output_gst - input_gst
            self.summary_lbl.setText(
                f"Output GST: ₹{output_gst:,.2f}  •  "
                f"Input GST: ₹{input_gst:,.2f}  •  "
                f"Net GST Payable: ₹{net_gst:,.2f}"
            )
        finally:
            session.close()

    def _export(self):
        try:
            from core.excel_export import export_gst_report
            month = self.month_combo.currentIndex() + 1
            year = self.year_combo.currentData()
            path = export_gst_report(month, year)
            from ui.components.export_dialog import ExportReadyDialog
            ExportReadyDialog(path, self).exec()
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))
