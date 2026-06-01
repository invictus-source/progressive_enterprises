from datetime import date, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDialog, QMessageBox, QScrollArea,
    QTableWidget, QTableWidgetItem, QTabWidget, QFrame, QLineEdit,
    QTextEdit, QDateEdit, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QColor

from ui.components.data_table import DataTable
from ui.components.form_dialog import FormDialog, ValidationError
from db.manager import get_db
from db.models import EMIRecord, EMIPayment, FinanceProvider, Customer, Sale
from core.auth import AuthSession

class AddFinanceProviderDialog(FormDialog):
    def __init__(self, provider=None, parent=None):
        super().__init__("Finance Provider", width=440, parent=parent)
        self._provider = provider
        self.name_edit = QLineEdit(); self.name_edit.setPlaceholderText("Provider Name *")
        self.contact_edit = QLineEdit(); self.contact_edit.setPlaceholderText("Contact Person")
        self.phone_edit = QLineEdit(); self.phone_edit.setPlaceholderText("Phone")
        self.email_edit = QLineEdit(); self.email_edit.setPlaceholderText("Email")
        self.notes_edit = QTextEdit(); self.notes_edit.setFixedHeight(55)
        for lbl, w in [("Name *", self.name_edit), ("Contact Person", self.contact_edit),
                        ("Phone", self.phone_edit), ("Email", self.email_edit), ("Notes", self.notes_edit)]:
            self.add_field(lbl, w)
        if provider:
            self.name_edit.setText(provider.name or "")
            self.contact_edit.setText(provider.contact_person or "")
            self.phone_edit.setText(provider.phone or "")
            self.email_edit.setText(provider.email or "")
            self.notes_edit.setPlainText(provider.notes or "")
        self.finalize()

    def _collect(self):
        name = self.name_edit.text().strip()
        if not name: raise ValidationError("Name is required.")
        return {"name": name,
                "contact_person": self.contact_edit.text().strip() or None,
                "phone": self.phone_edit.text().strip() or None,
                "email": self.email_edit.text().strip() or None,
                "notes": self.notes_edit.toPlainText().strip() or None}

class NewEMIDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Create New EMI Record")
        self.setMinimumSize(600, 560)
        self.setModal(True)
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20); root.setSpacing(14)

        def row(lbl, *widgets):
            h = QHBoxLayout()
            h.addWidget(QLabel(lbl))
            for w in widgets: h.addWidget(w)
            root.addLayout(h)

        self.customer_combo = QComboBox(); self.customer_combo.setMinimumWidth(200)
        row("Customer *", self.customer_combo)

        self.provider_combo = QComboBox()
        self.loan_acc_edit = QLineEdit(); self.loan_acc_edit.setPlaceholderText("Loan Account No.")
        row("Finance Provider *", self.provider_combo, self.loan_acc_edit)

        self.loan_edit = QLineEdit(); self.loan_edit.setPlaceholderText("Loan Amount (₹)")
        self.down_edit = QLineEdit(); self.down_edit.setPlaceholderText("Down Payment (₹)")
        row("Loan Amount *", self.loan_edit, QLabel("Down Payment"), self.down_edit)

        self.tenure_edit = QLineEdit(); self.tenure_edit.setPlaceholderText("Months (1–60)")
        self.tenure_edit.setText("12")
        self.interest_edit = QLineEdit(); self.interest_edit.setPlaceholderText("Rate % (e.g. 12.5)")
        row("Tenure (months)", self.tenure_edit, QLabel("Interest Rate %"), self.interest_edit)

        self.proc_fee_edit = QLineEdit(); self.proc_fee_edit.setPlaceholderText("Processing Fee (₹)")
        row("Processing Fee", self.proc_fee_edit)

        self.start_date_edit = QDateEdit(QDate.currentDate()); self.start_date_edit.setCalendarPopup(True)
        row("Start Date", self.start_date_edit)

        self.emi_lbl = QLabel("Monthly EMI: ₹0.00")
        self.emi_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #60a5fa;")
        root.addWidget(self.emi_lbl)

        self.val_error_lbl = QLabel("")
        self.val_error_lbl.setStyleSheet("color: #f87171; font-size: 11px; font-weight: 600;")
        root.addWidget(self.val_error_lbl)

        for field in [self.loan_edit, self.down_edit, self.tenure_edit, self.interest_edit]:
            field.textChanged.connect(self._recalc)

        btn_row = QHBoxLayout(); btn_row.addStretch()
        cancel = QPushButton("Cancel"); cancel.clicked.connect(self.reject)
        save = QPushButton("Create EMI"); save.setObjectName("SuccessBtn"); save.clicked.connect(self._save)
        for b in [cancel, save]: b.setFixedHeight(36); btn_row.addWidget(b)
        root.addLayout(btn_row)

    def _load_data(self):
        session = get_db()
        try:
            for c in session.query(Customer).filter_by(is_active=True).all():
                self.customer_combo.addItem(f"{c.name} – {c.phone}", c.id)
            for fp in session.query(FinanceProvider).filter_by(is_active=True).all():
                self.provider_combo.addItem(fp.name, fp.id)
        finally:
            session.close()

    def _recalc(self):
        try:
            loan = float(self.loan_edit.text().strip().lstrip("₹") or 0)
            down = float(self.down_edit.text().strip().lstrip("₹") or 0)
            tenure = int(self.tenure_edit.text().strip() or 0)
            rate = float(self.interest_edit.text().strip().rstrip("%") or 0)
        except ValueError:
            return
        principal = max(0.0, loan - down)
        if tenure > 0 and principal > 0:
            if rate > 0:
                r = rate / 12 / 100
                emi = principal * r * (1 + r)**tenure / ((1 + r)**tenure - 1)
            else:
                emi = principal / tenure
            self.emi_lbl.setText(f"Monthly EMI: ₹{emi:,.2f}")
        else:
            self.emi_lbl.setText("Monthly EMI: ₹0.00")

    def _save(self):
        self.val_error_lbl.setText("")
        customer_id = self.customer_combo.currentData()
        provider_id = self.provider_combo.currentData()
        if not customer_id:
            self.val_error_lbl.setText("Please select a customer."); return
        if not provider_id:
            self.val_error_lbl.setText("Please select a finance provider."); return
        try:
            loan_text = self.loan_edit.text().strip().lstrip("₹").strip()
            if not loan_text:
                raise ValueError("Loan Amount is required.")
            loan = float(loan_text)
            if loan <= 0:
                raise ValueError("Loan amount must be greater than 0.")
            down_text = self.down_edit.text().strip().lstrip("₹").strip()
            down = float(down_text) if down_text else 0.0
            tenure_text = self.tenure_edit.text().strip()
            if not tenure_text:
                raise ValueError("Tenure (months) is required.")
            tenure = int(tenure_text)
            if not (1 <= tenure <= 60):
                raise ValueError("Tenure must be between 1 and 60 months.")
            rate_text = self.interest_edit.text().strip().rstrip("%").strip()
            rate = float(rate_text) if rate_text else 0.0
            if rate < 0 or rate > 50:
                raise ValueError("Interest rate must be between 0% and 50%.")
            proc_text = self.proc_fee_edit.text().strip().lstrip("₹").strip()
            proc_fee = float(proc_text) if proc_text else 0.0
        except ValueError as e:
            self.val_error_lbl.setText(str(e))
            return
        principal = max(0.0, loan - down)
        if rate > 0:
            r = rate / 12 / 100
            emi = principal * r * (1 + r)**tenure / ((1 + r)**tenure - 1)
        else:
            emi = principal / tenure if tenure else principal

        session = get_db()
        try:
            start = self.start_date_edit.date().toPython()
            rec = EMIRecord(
                sale_id=None, customer_id=customer_id,
                finance_provider_id=provider_id,
                loan_amount=loan, down_payment=down,
                processing_fee=proc_fee,
                tenure_months=tenure, monthly_installment=round(emi, 2),
                interest_rate=rate,
                loan_account_no=self.loan_acc_edit.text().strip() or None,
                start_date=start, status="Active",
            )
            session.add(rec); session.flush()
            for i in range(1, tenure + 1):
                due_date = date(start.year + (start.month + i - 1) // 12,
                                (start.month + i - 1) % 12 + 1, start.day)
                ep = EMIPayment(emi_record_id=rec.id, installment_no=i,
                                due_date=due_date, amount_due=round(emi, 2))
                session.add(ep)
            session.commit()
            QMessageBox.information(self, "Success", f"EMI record created.\n{tenure} installments of ₹{emi:,.2f} generated.")
            self.accept()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

class EMIFinancePage(QWidget):
    def __init__(self):
        super().__init__()
        self._records = []
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

        title = QLabel("EMI / Finance")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        tabs = QTabWidget()
        layout.addWidget(tabs)

        emi_tab = QWidget()
        emi_layout = QVBoxLayout(emi_tab)
        emi_layout.setContentsMargins(12, 12, 12, 12)

        self.emi_table = DataTable(
            columns=["#", "Customer", "Finance Co.", "Loan Amt", "EMI/mo", "Tenure", "Start", "Status"],
            searchable=True,
            actions=[
                ("➕  New EMI",    self._new_emi),
                ("📋  Schedule",  self._view_schedule),
            ],
        )
        self.emi_table.row_double_clicked.connect(self._view_schedule)
        emi_layout.addWidget(self.emi_table)
        tabs.addTab(emi_tab, "💳  EMI Records")

        overdue_tab = QWidget()
        overdue_layout = QVBoxLayout(overdue_tab)
        overdue_layout.setContentsMargins(12, 12, 12, 12)

        self.overdue_table = DataTable(
            columns=["Customer", "Finance Co.", "Inst #", "Due Date", "Amount Due", "Penalty"],
            searchable=True,
            actions=[("✅  Mark Paid", self._mark_paid)],
        )
        self._overdue_items = []
        overdue_layout.addWidget(self.overdue_table)
        tabs.addTab(overdue_tab, "⚠️  Overdue Installments")

        fp_tab = QWidget()
        fp_layout = QVBoxLayout(fp_tab)
        fp_layout.setContentsMargins(12, 12, 12, 12)

        self.fp_table = DataTable(
            columns=["#", "Name", "Contact", "Phone", "Email"],
            searchable=True,
            actions=[
                ("➕  Add Provider", self._add_provider),
                ("✏️  Edit",          self._edit_provider),
            ],
        )
        self._providers = []
        fp_layout.addWidget(self.fp_table)
        tabs.addTab(fp_tab, "🏦  Finance Providers")

        self._tabs = tabs

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        self._load_emi_records()
        self._load_overdue()
        self._load_providers()

    def _load_emi_records(self):
        session = get_db()
        try:
            self._records = session.query(EMIRecord).order_by(EMIRecord.created_at.desc()).all()
            rows = []
            for i, r in enumerate(self._records, 1):
                rows.append([
                    str(i),
                    r.customer.name if r.customer else "—",
                    r.finance_provider.name if r.finance_provider else "—",
                    f"₹{r.loan_amount:,.0f}",
                    f"₹{r.monthly_installment:,.0f}",
                    f"{r.tenure_months} mo.",
                    r.start_date.strftime("%d %b %Y"),
                    r.status,
                ])
            self.emi_table.set_data(rows)
        finally:
            session.close()

    def _load_overdue(self):
        session = get_db()
        try:
            today = date.today()
            items = (session.query(EMIPayment)
                     .filter(EMIPayment.is_paid == False, EMIPayment.due_date < today)
                     .order_by(EMIPayment.due_date).all())
            self._overdue_items = items
            rows = []
            for ep in items:
                r = ep.emi_record
                rows.append([
                    r.customer.name if r.customer else "—",
                    r.finance_provider.name if r.finance_provider else "—",
                    str(ep.installment_no),
                    ep.due_date.strftime("%d %b %Y"),
                    f"₹{ep.amount_due:,.0f}",
                    f"₹{ep.penalty:,.0f}",
                ])
            self.overdue_table.set_data(rows)
        finally:
            session.close()

    def _load_providers(self):
        session = get_db()
        try:
            self._providers = session.query(FinanceProvider).filter_by(is_active=True).all()
            rows = [
                [str(i), fp.name, fp.contact_person or "—", fp.phone or "—", fp.email or "—"]
                for i, fp in enumerate(self._providers, 1)
            ]
            self.fp_table.set_data(rows)
        finally:
            session.close()

    def _new_emi(self):
        dlg = NewEMIDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self.refresh()

    def _view_schedule(self, idx=None):
        orig = self.emi_table.get_selected_original_index()
        if orig is None:
            QMessageBox.information(self, "Select Record", "Please select an EMI record.")
            return
        rec = self._records[orig]
        session = get_db()
        try:
            payments = (session.query(EMIPayment)
                        .filter_by(emi_record_id=rec.id)
                        .order_by(EMIPayment.installment_no).all())
            dlg = QDialog(self)
            dlg.setWindowTitle(f"EMI Schedule – {rec.customer.name if rec.customer else '?'}")
            dlg.setMinimumSize(640, 500)
            vl = QVBoxLayout(dlg)
            vl.setContentsMargins(20, 20, 20, 20)
            info = QLabel(
                f"Provider: {rec.finance_provider.name}  •  Loan: ₹{rec.loan_amount:,.0f}  •  "
                f"EMI: ₹{rec.monthly_installment:,.0f}/mo  •  Status: {rec.status}"
            )
            info.setStyleSheet("color: #8b949e; font-size: 12px;")
            vl.addWidget(info)

            t = QTableWidget(); t.setColumnCount(5)
            t.setHorizontalHeaderLabels(["#", "Due Date", "Amount", "Paid Date", "Status"])
            t.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            t.setAlternatingRowColors(True)
            t.verticalHeader().setVisible(False)
            t.setRowCount(len(payments))
            today = date.today()
            for r, ep in enumerate(payments):
                status = "✅ Paid" if ep.is_paid else ("🔴 Overdue" if ep.due_date < today else "⏳ Pending")
                for c, v in enumerate([
                    str(ep.installment_no),
                    ep.due_date.strftime("%d %b %Y"),
                    f"₹{ep.amount_due:,.0f}",
                    ep.paid_date.strftime("%d %b %Y") if ep.paid_date else "—",
                    status,
                ]):
                    item = QTableWidgetItem(v)
                    if "Overdue" in status:
                        item.setForeground(QColor("#f87171"))
                    elif "Paid" in status:
                        item.setForeground(QColor("#4ade80"))
                    t.setItem(r, c, item)
            vl.addWidget(t)
            close = QPushButton("Close"); close.clicked.connect(dlg.accept)
            vl.addWidget(close, alignment=Qt.AlignmentFlag.AlignRight)
            dlg.exec()
        finally:
            session.close()

    def _mark_paid(self):
        orig = self.overdue_table.get_selected_original_index()
        if orig is None:
            QMessageBox.information(self, "Select", "Please select an overdue installment.")
            return
        ep_record = self._overdue_items[orig]
        session = get_db()
        try:
            ep = session.query(EMIPayment).get(ep_record.id)
            ep.is_paid = True
            ep.paid_date = date.today()
            ep.amount_paid = ep.amount_due
            session.commit()
            self.refresh()
            QMessageBox.information(self, "Done", "Installment marked as paid.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()

    def _add_provider(self):
        dlg = AddFinanceProviderDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            session = get_db()
            try:
                fp = FinanceProvider(**dlg.get_data())
                session.add(fp); session.commit()
                self.refresh()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def _edit_provider(self):
        orig = self.fp_table.get_selected_original_index()
        if orig is None: return
        fp = self._providers[orig]
        session = get_db()
        try:
            fp = session.query(FinanceProvider).get(fp.id)
            dlg = AddFinanceProviderDialog(provider=fp, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                for k, v in dlg.get_data().items(): setattr(fp, k, v)
                session.commit(); self.refresh()
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
