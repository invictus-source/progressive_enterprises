# Progressive Enterprises — ERP Suite

> A full-featured desktop ERP application for a local electronics shop, built with Python, PySide6, and SQLAlchemy. Covers POS billing, inventory management, EMI/finance tracking, GST reporting, and more.

---

## Quick Start

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

On first launch, the setup wizard will guide you through creating an admin account and entering your company details. After that, you'll be presented with the login screen.

---

## Project Structure

```
progressive/
├── main.py                     Application entry point
├── config.py                   Paths, settings (secrets loaded from .env)
├── .env.example                Template for environment variables
├── requirements.txt            Python dependencies
├── build_installer.ps1          PyInstaller + Inno Setup build script
├── progressive.iss             Inno Setup installer config
├── convert_icon.py             PNG → ICO converter for app logo
├── assets/
│   ├── logo.png                Application logo (PNG)
│   └── logo.ico                Application icon (ICO)
├── core/
│   ├── auth.py                 bcrypt authentication & role checks
│   ├── invoice_gen.py          PDF invoice generation (reportlab)
│   └── excel_export.py         Excel report export (openpyxl)
├── db/
│   ├── models.py               15 SQLAlchemy ORM models
│   ├── manager.py              Database singleton, init, seed data
│   └── migrations.py           Schema migration engine
└── ui/
    ├── main.py                 MainWindow — sidebar + stacked pages
    ├── styles/
    │   ├── theme.py            Theme manager & 700+ line QSS builder
    │   └── login.py            Login-specific stylesheet
    ├── components/
    │   ├── sidebar.py          Collapsible navigation sidebar
    │   ├── data_table.py       Reusable live-search data table
    │   ├── stat_card.py        KPI metric card widget
    │   ├── form_dialog.py      Styled base dialog for CRUD forms
    │   ├── toast.py             Toast notification widget
    │   └── export_dialog.py    Export success dialog with open/folder buttons
    └── windows/
        ├── login.py            Login window with bcrypt auth
        ├── dashboard.py        6 KPI cards + recent sales + overdue EMIs
        ├── customers.py        Customer CRUD + ledger popup
        ├── vendors.py          Vendor CRUD + purchase history
        ├── inventory.py        Product management + stock adjust + low-stock alerts
        ├── pos.py              Full POS — search, cart, GST, invoice
        ├── purchases.py        GRN entry, stock increment, GST-in
        ├── emi_finance.py      EMI records, schedule, overdue tracker
        ├── payments.py         Customer receipts + vendor payments
        ├── gst_reports.py      GSTR-1 style monthly report + Excel export
        ├── reports.py          Date-range sales reports + Excel export
        ├── sales_history.py    Full sale record viewer
        ├── user_mgmt.py        User management with role protection
        ├── settings.py         Company info, dev panel, about
        └── setup_wizard.py     First-run setup wizard
```

---

## Modules

### Authentication & Roles

| Role | Capabilities |
|---|---|
| **Developer** | Full access including dev panel, DB backup, user management |
| **Admin** | All business operations + user management |
| **Staff** | POS, inventory, customers, vendors, purchases |

- Passwords hashed with **bcrypt** — never stored in plaintext
- Login attempt tracking with visual feedback
- Session-based role enforcement across all windows

### Point of Sale (POS)

- Live product search by name or SKU
- Cart system with quantity editing and line totals
- Automatic GST calculation (CGST + SGST for intra-state)
- Stock deduction on sale completion
- PDF invoice generation with company branding
- Sale record persisted with all line items

### Inventory

- Product listing with category filter
- Stock adjustment dialog (add/remove/reason)
- Low-stock rows highlighted in red
- Category management from within the view
- GST slab selection per product

### Customers & Vendors

- Full CRUD for both entities
- Customer ledger popup with **Sales**, **EMI**, and **Payments** tabs
- Vendor purchase history popup
- GSTIN, banking details, and ID proof fields
- Soft-delete with `is_active` flag

### EMI / Finance

- Create EMI schemes against customer sales
- Auto-generate monthly instalment schedule
- Overdue tracker with days-past-due calculation
- Mark-as-paid with date and mode tracking
- 9 pre-seeded finance providers

### Purchases

- GRN (Goods Received Note) entry linked to vendors
- Automatic stock increment on purchase confirmation
- GST-in tracking for input tax credit
- Purchase history from vendor detail view

### Payments

- Customer payment receipts with mode and reference
- Vendor payment tracking with mode and reference
- Payment modes: Cash, UPI, Bank Transfer, Cheque, Card

### GST Reports

- GSTR-1 style outward supply report
- Inward supply report for input tax credit
- Monthly/annual period filter
- Net GST payable computation
- Excel export for filing

### Reports

- Date-range filtered sales reports
- 4 KPI summary cards (revenue, orders, avg value, products sold)
- Tab views: Transactions, Product-wise, Daily summary
- Excel export with formatted sheets

### Settings

- Editable company name, address, GSTIN, contact info
- Developer-only panel with DB backup/restore
- About tab with version and tech stack info

---

## Data Models

The application uses **15 SQLAlchemy ORM models** backed by SQLite:

| Model | Purpose |
|---|---|
| `User` | Authentication and role management |
| `Customer` | Customer records and GST details |
| `Vendor` | Supplier/vendor records with banking |
| `Category` | Product categories |
| `Product` | Inventory items with pricing and stock |
| `Sale` | Sale header with totals and GST |
| `SaleItem` | Individual line items per sale |
| `Purchase` | Purchase header linked to vendor |
| `PurchaseItem` | Individual line items per purchase |
| `Payment` | Customer and vendor payments |
| `EMIRecord` | EMI scheme header |
| `EMISchedule` | Individual instalment entries |
| `FinanceProvider` | EMI finance company details |
| `Settings` | Persistent key-value app settings |
| `Migration` | Schema version tracking |

All monetary fields use `Float` for INR values. Relationships use SQLAlchemy `relationship()` with back-populates for easy traversal.

---

## Configuration

All secrets and configurable values are isolated in a `.env` file (loaded via `python-dotenv`). Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

### Environment Variables

| Variable | Description |
|---|---|
| `APP_NAME` | Application display name |
| `APP_FULL_NAME` | Full application name with subtitle |
| `APP_VERSION` | Version string shown in About |
| `APP_PUBLISHER` | Publisher name |
| `DEVELOPER_COMPANY` | Developer company name shown in footer |
| `DEV_USERNAME` | Developer account username |
| `DEV_PASSWORD` | Developer account password |
| `DEV_FULL_NAME` | Developer account display name |
| `DB_NAME` | SQLite database filename |
| `DATA_DIR_NAME` | Folder name for AppData data directory |
| `COMPANY_NAME` | Default company name (overridden by settings.json after setup) |
| `COMPANY_ADDRESS` | Default address |
| `COMPANY_PHONE` | Default phone |
| `COMPANY_EMAIL` | Default email |
| `COMPANY_GSTIN` | Default GST identification number |
| `COMPANY_STATE` | Default state |
| `COMPANY_STATE_CODE` | Default state code |

Company details are initially loaded from `.env` defaults, then overridden by `settings.json` after the setup wizard runs.

Data paths can also be overridden with the `PROGRESSIVE_DATA_DIR` environment variable, or configured via the launcher JSON file stored in AppData.

---

## Theming

The app ships with a **dark mode** theme built in QSS (Qt Style Sheets):

- Managed by `ui/styles/theme.py` — a `ThemeManager` class with 60+ color tokens
- Tokens cover backgrounds, text, accents, borders, inputs, tables, and states
- Theme preference persisted to `prefs.json` in the data directory
- Font scale adjustable from Settings (9–18pt range)

---

## Building the Windows Installer from Linux

PyInstaller is not a cross-compiler, so a Windows executable must be produced on
Windows. Linux is the normal development environment; the included GitHub Actions
workflow supplies the Windows build machine.

1. Push the source to GitHub.
2. Open **Actions → Build Windows Installer**.
3. Select **Run workflow**, enter a `MAJOR.MINOR.PATCH` version, and start it.
4. Download `ProgressiveEnterprises-Windows-<version>` from the completed run.

The artifact contains:

- `ProgressiveEnterprises_Setup_<version>_x64.exe`
- A matching SHA-256 checksum file

The workflow runs the automated tests, creates a 64-bit PyInstaller bundle on
Windows, runs the packaged app against a disposable test database, compiles the
Inno Setup installer, and uploads the result.

On a Windows development machine the same build can be run directly:

```powershell
.\build_installer.ps1 -Version 1.0.0
```

### Installer data safety

- A clean computer starts the setup wizard and creates a new database on first run.
- Upgrades and reinstalls reuse the same application identity and preserve data.
- Uninstall removes application files but intentionally keeps business data.
- `.env`, database, settings, preference, invoice, export and backup files are
  never embedded in the installer.

---

## Data Storage

| Path | Contents |
|---|---|
| `DATA_DIR/progressive.db` | SQLite database (all business data) |
| `DATA_DIR/invoices/` | Generated PDF invoices |
| `DATA_DIR/exports/` | Exported Excel reports |
| `DATA_DIR/backups/` | Database backups from Settings |
| `DATA_DIR/settings.json` | Company info and setup state |
| `DATA_DIR/prefs.json` | Theme and UI preferences |

On Windows the default data directory is
`%APPDATA%\ProgressiveEnterprises\data`. It is created automatically on first
run and is outside the application installation directory. Backing up the entire
data directory preserves the database, documents, settings and backups.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI Framework | PySide6 (Qt for Python) |
| Database | SQLite via SQLAlchemy 2.0 ORM |
| Authentication | bcrypt password hashing |
| PDF Invoices | reportlab |
| Excel Export | openpyxl |
| Icons | qtawesome (Font Awesome 5/6) |
| Charts | matplotlib |
| Packaging | PyInstaller + Inno Setup |

---

## License

Proprietary — Progressive Enterprises & Emberflock Labs. All rights reserved.
