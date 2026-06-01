"""
Progressive Enterprises – Application Configuration
All paths are computed at runtime — DO NOT hardcode paths here.
"""

import os
import sys
import json

# ── App Meta ──────────────────────────────────────────────────────────────────
APP_NAME        = "Progressive Enterprises"
APP_FULL_NAME   = "Progressive Enterprises – Business Suite"
APP_VERSION     = "1.0.0"
APP_PUBLISHER   = "Progressive Enterprises"
DEVELOPER_COMPANY = "Emberflock Labs"

# ── Data Directory (survives updates / reinstalls) ────────────────────────────
# Default: C:\Users\<user>\AppData\Roaming\ProgressiveEnterprises\data\
# Override by setting env var PROGRESSIVE_DATA_DIR before launching.

_default_appdata = os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                                "ProgressiveEnterprises", "data")
_launcher_json = os.path.join(os.path.expanduser("~"), "AppData", "Roaming",
                              "ProgressiveEnterprises", "launcher.json")

_appdata = os.environ.get("PROGRESSIVE_DATA_DIR")

if not _appdata and os.path.exists(_launcher_json):
    try:
        with open(_launcher_json, "r", encoding="utf-8") as _f:
            _appdata = json.load(_f).get("custom_data_dir")
    except Exception:
        pass

if not _appdata:
    _appdata = _default_appdata

DATA_DIR     = _appdata
DB_PATH      = os.path.join(DATA_DIR, "progressive.db")
INVOICES_DIR = os.path.join(DATA_DIR, "invoices")
EXPORTS_DIR  = os.path.join(DATA_DIR, "exports")
BACKUPS_DIR  = os.path.join(DATA_DIR, "backups")
PREFS_FILE   = os.path.join(DATA_DIR, "prefs.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# Ensure directories exist
for _d in [DATA_DIR, INVOICES_DIR, EXPORTS_DIR, BACKUPS_DIR]:
    os.makedirs(_d, exist_ok=True)

def set_custom_data_dir(new_dir: str):
    """Save custom data directory preference so it survives restarts."""
    global DATA_DIR, DB_PATH, INVOICES_DIR, EXPORTS_DIR, BACKUPS_DIR, PREFS_FILE, SETTINGS_FILE
    
    os.makedirs(os.path.dirname(_launcher_json), exist_ok=True)
    with open(_launcher_json, "w", encoding="utf-8") as f:
        json.dump({"custom_data_dir": new_dir}, f)
        
    DATA_DIR = new_dir
    DB_PATH      = os.path.join(DATA_DIR, "progressive.db")
    INVOICES_DIR = os.path.join(DATA_DIR, "invoices")
    EXPORTS_DIR  = os.path.join(DATA_DIR, "exports")
    BACKUPS_DIR  = os.path.join(DATA_DIR, "backups")
    PREFS_FILE   = os.path.join(DATA_DIR, "prefs.json")
    SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
    
    for _d in [DATA_DIR, INVOICES_DIR, EXPORTS_DIR, BACKUPS_DIR]:
        os.makedirs(_d, exist_ok=True)

# ── Developer / Seed Account ──────────────────────────────────────────────────
DEV_USERNAME  = "ayushjha"
DEV_PASSWORD  = "Ayush@2106"     # plain text; hashed on first-run DB seed
DEV_FULL_NAME = "Ayush Jha"

# ── Company Info (loaded from settings.json, with defaults) ──────────────────
def _load_settings() -> dict:
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def _save_settings(data: dict):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

_settings = _load_settings()

COMPANY_NAME        = _settings.get("company_name",        "Progressive Enterprises")
COMPANY_ADDRESS     = _settings.get("company_address",     "Shop No. 1, Main Market, Your City – 000000")
COMPANY_PHONE       = _settings.get("company_phone",       "+91-XXXXXXXXXX")
COMPANY_EMAIL       = _settings.get("company_email",       "info@progressiveenterprises.com")
COMPANY_GSTIN       = _settings.get("company_gstin",       "00AAAAA0000A1Z5")
COMPANY_STATE       = _settings.get("company_state",       "Rajasthan")
COMPANY_STATE_CODE  = _settings.get("company_state_code",  "08")

# ── GST Slabs ─────────────────────────────────────────────────────────────────
GST_SLABS = [0, 5, 12, 18, 28]

# Backward compat alias
DB_NAME = "progressive.db"

# ── First-run Detection ───────────────────────────────────────────────────────
def is_first_run() -> bool:
    """True if the DB does not exist yet (genuine first install)."""
    return not os.path.exists(DB_PATH)

def mark_setup_complete(company_data: dict, admin_username: str, admin_pwd_hash: str):
    """Called by the setup wizard after completion."""
    global COMPANY_NAME, COMPANY_ADDRESS, COMPANY_PHONE, COMPANY_EMAIL
    global COMPANY_GSTIN, COMPANY_STATE, COMPANY_STATE_CODE
    COMPANY_NAME       = company_data.get("company_name",  COMPANY_NAME)
    COMPANY_ADDRESS    = company_data.get("company_address", COMPANY_ADDRESS)
    COMPANY_PHONE      = company_data.get("company_phone", COMPANY_PHONE)
    COMPANY_EMAIL      = company_data.get("company_email", COMPANY_EMAIL)
    COMPANY_GSTIN      = company_data.get("company_gstin", COMPANY_GSTIN)
    COMPANY_STATE      = company_data.get("company_state", COMPANY_STATE)
    COMPANY_STATE_CODE = company_data.get("company_state_code", COMPANY_STATE_CODE)
    _save_settings({**company_data, "_setup_done": True,
                    "_admin_username": admin_username,
                    "_admin_pwd_hash": admin_pwd_hash})

def update_company_settings(data: dict):
    """Persist company info changes from the Settings page."""
    global COMPANY_NAME, COMPANY_ADDRESS, COMPANY_PHONE, COMPANY_EMAIL
    global COMPANY_GSTIN, COMPANY_STATE, COMPANY_STATE_CODE
    curr = _load_settings()
    curr.update(data)
    _save_settings(curr)
    COMPANY_NAME       = data.get("company_name",       COMPANY_NAME)
    COMPANY_ADDRESS    = data.get("company_address",    COMPANY_ADDRESS)
    COMPANY_PHONE      = data.get("company_phone",      COMPANY_PHONE)
    COMPANY_EMAIL      = data.get("company_email",      COMPANY_EMAIL)
    COMPANY_GSTIN      = data.get("company_gstin",      COMPANY_GSTIN)
    COMPANY_STATE      = data.get("company_state",      COMPANY_STATE)
    COMPANY_STATE_CODE = data.get("company_state_code", COMPANY_STATE_CODE)

# ── User Preferences (theme, zoom, etc.) ─────────────────────────────────────
def load_prefs() -> dict:
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"theme": "dark", "font_scale": 1.0, "fullscreen_login": False}

def save_prefs(data: dict):
    curr = load_prefs()
    curr.update(data)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(curr, f, indent=2)

# ── Assets ────────────────────────────────────────────────────────────────────
_base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
ASSETS_DIR  = os.path.join(_base, "assets")
LOGO_PATH   = os.path.join(ASSETS_DIR, "logo.png")
