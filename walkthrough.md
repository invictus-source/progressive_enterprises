# Progressive Enterprises – ERP Suite Build Walkthrough

## What Was Built

A **comprehensive ERP desktop application** for a local electronics shop, built entirely in Python + PySide6. The app covers every major business operation from POS to EMI tracking to GST filing.

---

## Project Structure

```
progressive/
├── main.py                 # Entry point (updated)
├── config.py               # ✅ NEW – company config & dev credentials
├── requirements.txt        # ✅ NEW
├── db/
│   ├── models.py           # ✅ NEW – 15 SQLAlchemy ORM tables
│   └── manager.py          # ✅ NEW – DB singleton + first-run seed
├── core/
│   ├── auth.py             # ✅ NEW – bcrypt auth & role checks
│   ├── invoice_gen.py      # ✅ NEW – PDF invoice (reportlab)
│   └── excel_export.py     # ✅ NEW – Excel export (openpyxl)
└── ui/
    ├── main.py             # ✅ REBUILT – sidebar + stacked pages
    ├── styles/theme.py     # ✅ NEW – 700-line dark QSS stylesheet
    ├── components/
    │   ├── sidebar.py      # ✅ NEW – collapsible nav sidebar
    │   ├── data_table.py   # ✅ NEW – reusable live-search table
    │   ├── stat_card.py    # ✅ NEW – KPI card widget
    │   └── form_dialog.py  # ✅ NEW – styled base dialog
    └── windows/
        ├── login.py        # ✅ REBUILT – dark card, bcrypt login
        ├── dashboard.py    # ✅ NEW – 6 KPIs + recent sales + overdue EMIs
        ├── customers.py    # ✅ NEW – CRUD + ledger popup (sales/EMI/payments)
        ├── vendors.py      # ✅ NEW – CRUD + purchase history
        ├── inventory.py    # ✅ NEW – products, stock adjust, low-stock alerts
        ├── pos.py          # ✅ NEW – full POS cart, GST, stock deduct, invoice
        ├── purchases.py    # ✅ NEW – GRN entry, stock increment, GST-in
        ├── emi_finance.py  # ✅ NEW – EMI records, schedule, overdue tracker
        ├── payments.py     # ✅ NEW – customer receipts + vendor payments
        ├── gst_reports.py  # ✅ NEW – GSTR-1 style monthly GST report + export
        ├── reports.py      # ✅ NEW – date-range sales/product/daily reports
        ├── user_mgmt.py    # ✅ NEW – user CRUD with role protection
        └── settings.py     # ✅ NEW – company info, dev panel, about
```

## Verification Results

| Check | Result |
|---|---|
| Syntax check across all 20 .py files | ✅ ALL OK |
| Dependencies installed | ✅ All installed |
| DB init + seeding | ✅ 10 categories, 9 finance providers, dev user |
| Auth: dev login | ✅ dev/dev@2024 works |

---

## How to Run

```powershell
# From d:\Projects\progressive\
.venv\Scripts\python main.py
```

**Login credentials:**
- **Username**: [dev](file:///d:/Projects/progressive/core/auth.py#62-65)
- **Password**: `dev@2024`

> Change these in [config.py](file:///d:/Projects/progressive/config.py) before production.

---

## Key Features by Module

| Module | Highlights |
|---|---|
| **Login** | Dark card UI, bcrypt auth, login attempt tracking |
| **Dashboard** | 6 live KPI cards, recent sales, overdue EMI table |
| **POS** | Product search, cart, GST calc (CGST+SGST), stock deduction, PDF invoice |
| **Inventory** | Category filter, stock adjust dialog, red-highlight for low stock |
| **Customers** | Full CRUD + ledger popup with Sales/EMI/Payments tabs |
| **Vendors** | Full CRUD + purchase history popup, banking details |
| **Purchases** | GRN entry, stock auto-increment, GST-in tracking |
| **EMI / Finance** | Auto-schedule generation, overdue tracker, mark-as-paid, 9 seeded providers |
| **Payments** | Customer receipts + vendor payments, mode/reference tracking |
| **GST Reports** | Month/year filter, outward + inward supplies, net GST payable, Excel export |
| **Reports** | Date-range filter, 4 KPI cards, transactions/product-wise/daily tabs, Excel export |
| **User Mgmt** | Admin+ only, bcrypt passwords, role hierarchy enforcement |
| **Settings** | Company info editor, developer-only DB backup, About tab |

---

## Next Steps (Future)

- **Barcode scanner** support in POS (USB HID input already compatible via keyboard events)
- **Logo upload** in Settings → stamp on invoices
- **SMS/WhatsApp** reminders for overdue EMIs
- **PyInstaller .exe** build: `pyinstaller --onefile --windowed main.py`
