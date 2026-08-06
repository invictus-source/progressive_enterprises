import base64

from PySide6.QtWidgets import QApplication
import PySide6.QtSvg


class ThemeManager:
    _current: str = "dark"
    _callbacks: list = []

    THEMES = {
            "dark": {
                "bg_base": "#0F172A",
                "bg_surface": "#1E293B",
                "bg_elevated": "#334155",
                "bg_input": "#0F172A",
                "border": "#334155",
                "border_strong": "#475569",

                "accent": "#60A5FA",
                "accent_hover": "#93C5FD",
                "accent_dark": "#3B82F6",
                "success": "#34D399",
                "success_dark": "#10B981",
                "danger": "#F87171",
                "danger_dark": "#EF4444",
                "warning": "#FBBF24",
                "warning_dark": "#F59E0B",
                "purple": "#A78BFA",
                "cyan": "#22D3EE",

                "text_primary": "#F8FAFC",
                "text_secondary": "#CBD5E1",
                "text_muted": "#94A3B8",
                "sidebar_w": 240,
            },
            "light": {
                "bg_base": "#F8FAFC",
                "bg_surface": "#FFFFFF",
                "bg_elevated": "#F1F5F9",
                "bg_input": "#FFFFFF",
                "border": "#E2E8F0",
                "border_strong": "#CBD5E1",

                "accent": "#2563EB",
                "accent_hover": "#1D4ED8",
                "accent_dark": "#1E40AF",
                "success": "#059669",
                "success_dark": "#047857",
                "danger": "#DC2626",
                "danger_dark": "#B91C1C",
                "warning": "#B45309",
                "warning_dark": "#92400E",
                "purple": "#7C3AED",
                "cyan": "#0891B2",

                "text_primary": "#0F172A",
                "text_secondary": "#334155",
                "text_muted": "#64748B",
                "sidebar_w": 240,
            }
    }

    @classmethod
    def load_from_prefs(cls):
        import config
        prefs = config.load_prefs()
        cls._current = prefs.get("theme", "dark")

    @classmethod
    def current(cls) -> str:
        return cls._current

    @classmethod
    def tokens(cls) -> dict:
        return cls.THEMES[cls._current]

    @classmethod
    def t(cls, key: str) -> str:
        return cls.THEMES[cls._current][key]

    @classmethod
    def is_dark(cls) -> bool:
        return cls._current == "dark"

    @classmethod
    def toggle(cls):
        cls._current = "light" if cls._current == "dark" else "dark"
        import config
        config.save_prefs({"theme": cls._current})
        cls._apply()
        for cb in cls._callbacks:
            try:
                cb()
            except Exception:
                pass

    @classmethod
    def set_theme(cls, name: str):
        if name in cls.THEMES and cls._current != name:
            cls._current = name
            import config
            config.save_prefs({"theme": cls._current})
            cls._apply()
            for cb in cls._callbacks:
                try: cb()
                except Exception: pass

    @classmethod
    def register_callback(cls, fn):
        if fn not in cls._callbacks:
            cls._callbacks.append(fn)

    @classmethod
    def _apply(cls):
        app = QApplication.instance()
        if app:
            app.setStyleSheet(cls.build_stylesheet())

    @classmethod
    def apply_to_app(cls):
        cls._apply()

    @classmethod
    def build_stylesheet(cls) -> str:
        T = cls.THEMES[cls._current]
        dk = cls.is_dark()
        a = T["accent"]
        ah = T["accent_hover"]
        ad = T["accent_dark"]
        g1 = "#2563EB" if dk else "#3B82F6"
        g2 = "#1D4ED8" if dk else "#2563EB"
        sel = "rgba(59,130,246,0.18)" if dk else "rgba(37,99,235,0.10)"

        icon_color = T['text_secondary']

        raw_down = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{icon_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m6 9 6 6 6-6"/></svg>"""
        raw_up = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{icon_color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m18 15-6-6-6 6"/></svg>"""

        b64_down = base64.b64encode(raw_down.encode('utf-8')).decode('utf-8')
        b64_up = base64.b64encode(raw_up.encode('utf-8')).decode('utf-8')

        down_arrow_svg = f"url(\"data:image/svg+xml;base64,{b64_down}\")"
        up_arrow_svg = f"url(\"data:image/svg+xml;base64,{b64_up}\")"

        return f"""
/* ==========================================================
   Progressive Enterprises – {cls._current.upper()} THEME
   ========================================================== */

* {{
    font-family: 'Segoe UI', 'Inter', 'Roboto', Arial, sans-serif;
    outline: none;
}}

QMainWindow, QWidget {{
    background-color: {T['bg_base']};
    color: {T['text_primary']};
}}

QDialog {{
    background-color: {T['bg_surface']};
    color: {T['text_primary']};
}}

/* ── Sidebar ──────────────────────────────────────────────── */
#Sidebar {{
    background-color: {T['bg_surface']};
    border-right: 1px solid {T['border']};
}}

#BrandBlock {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {'#0F172A' if dk else '#1E3A5F'},
        stop:1 {'#1B2838' if dk else '#2563EB'});
}}

#BrandName {{
    font-size: 15px; font-weight: 800;
    color: #FFFFFF; letter-spacing: 0.3px;
    background: transparent;
}}
#BrandSub {{
    font-size: 10px; color: rgba(255,255,255,0.6);
    background: transparent; letter-spacing: 0.5px;
}}

#NavSection {{
    font-size: 9px; font-weight: 800; letter-spacing: 2px;
    color: {T['text_muted']}; padding: 14px 18px 4px;
    background: transparent; text-transform: uppercase;
}}

QPushButton#NavBtn {{
    background: transparent; border: none;
    padding: 9px 14px; text-align: left;
    font-size: 13px; font-weight: 500;
    color: {T['text_secondary']};
    border-radius: 8px; margin: 1px 8px;
}}
QPushButton#NavBtn:hover {{
    background-color: {T['bg_elevated']};
    color: {T['text_primary']};
}}
QPushButton#NavBtn[active="true"] {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {sel}, stop:1 transparent);
    color: {a}; font-weight: 700;
    border-left: 3px solid {a};
    border-radius: 0 8px 8px 0;
    margin-left: 0; padding-left: 11px;
}}

#UserBlock {{
    background-color: {T['bg_elevated']};
    border-top: 1px solid {T['border']};
}}
#UserAvatar {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {a}, stop:1 {T['purple']});
    border-radius: 18px; color: #FFF;
    font-size: 14px; font-weight: 800;
}}
#UserName {{
    font-size: 12px; font-weight: 700;
    color: {T['text_primary']}; background: transparent;
}}
#UserRole {{
    font-size: 10px; color: {T['text_muted']}; background: transparent;
}}

/* ── Top Bar ──────────────────────────────────────────────── */
#TopBar {{
    background-color: {T['bg_surface']};
    border-bottom: 1px solid {T['border']};
    min-height: 40px;
}}
#PageTitle {{
    font-size: 18px; font-weight: 700;
    color: {T['text_primary']}; background: transparent;
}}
#PageSubtitle {{
    font-size: 11px; color: {T['text_muted']}; background: transparent;
}}

/* ── Cards ────────────────────────────────────────────────── */
#Card {{
    background-color: {T['bg_surface']};
    border: 1px solid {T['border']};
    border-radius: 14px;
}}

/* Stat cards – coloured variants */
#StatCard {{
    background-color: {T['bg_surface']};
    border: 1px solid {T['border']};
    border-radius: 14px; padding: 6px;
}}

#StatCardBlue {{
    background-color: {'#1E293B' if dk else '#F0F9FF'};
    border: 1px solid {'#334155' if dk else '#BAE6FD'};
    border-radius: 12px;
}}
#StatCardGreen {{
    background-color: {'#1E293B' if dk else '#F0FDF4'};
    border: 1px solid {'#334155' if dk else '#BBF7D0'};
    border-radius: 12px;
}}
#StatCardPurple {{
    background-color: {'#1E293B' if dk else '#FAF5FF'};
    border: 1px solid {'#334155' if dk else '#E9D5FF'};
    border-radius: 12px;
}}
#StatCardOrange {{
    background-color: {'#1E293B' if dk else '#FFFBEB'};
    border: 1px solid {'#334155' if dk else '#FEF08A'};
    border-radius: 12px;
}}
#StatCardRed {{
    background-color: {'#1E293B' if dk else '#FEF2F2'};
    border: 1px solid {'#334155' if dk else '#FECACA'};
    border-radius: 12px;
}}
#StatCardCyan {{
    background-color: {'#1E293B' if dk else '#ECFEFF'};
    border: 1px solid {'#334155' if dk else '#A5F3FC'};
    border-radius: 12px;
}}

#StatValue {{
    font-size: 26px; font-weight: 800;
    color: {T['text_primary']}; background: transparent;
}}
#StatLabel {{
    font-size: 10px; letter-spacing: 1px; font-weight: 600;
    color: {T['text_secondary']}; background: transparent;
}}
#StatIcon {{
    font-size: 28px; background: transparent;
}}
#StatChange {{
    font-size: 11px; font-weight: 700; background: transparent;
}}

/* ── Buttons ──────────────────────────────────────────────── */
QPushButton {{
    background-color: {T['bg_elevated']};
    color: {T['text_primary']};
    border: 1px solid {T['border_strong']};
    border-radius: 9px; padding: 8px 18px;
    font-size: 13px; font-weight: 500;
}}
QPushButton:hover {{
    background-color: {T['border']};
    border-color: {a}; color: {T['text_primary']};
}}
QPushButton:pressed {{ background-color: {T['bg_base']}; }}
QPushButton:disabled {{ color: {T['text_muted']}; border-color: {T['border']}; }}

QPushButton#PrimaryBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {g1}, stop:1 {g2});
    color: #FFF; border: none; font-weight: 700; padding: 9px 22px;
    border-radius: 9px;
}}
QPushButton#PrimaryBtn:hover {{ background: {ah}; }}
QPushButton#PrimaryBtn:pressed {{ background: {ad}; }}

QPushButton#SuccessBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {T['success']}, stop:1 {T['success_dark']});
    color: #FFF; border: none; font-weight: 700; border-radius: 9px;
}}
QPushButton#SuccessBtn:hover {{ background: {T['success']}; }}

QPushButton#DangerBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {T['danger']}, stop:1 {T['danger_dark']});
    color: #FFF; border: none; font-weight: 700; border-radius: 9px;
}}
QPushButton#DangerBtn:hover {{ background: {T['danger']}; }}

QPushButton#WarningBtn {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {T['warning']}, stop:1 {T['warning_dark']});
    color: #FFF; border: none; font-weight: 700; border-radius: 9px;
}}
QPushButton#WarningBtn:hover {{ background: {T['warning']}; }}

QPushButton#GhostBtn {{
    background: transparent; border: 1.5px solid {T['border_strong']};
    color: {T['text_primary']}; border-radius: 9px; padding: 8px 18px;
}}
QPushButton#GhostBtn:hover {{
    border-color: {a}; color: {a};
    background: {sel};
}}

QPushButton#IconBtn {{
    background: {T['bg_elevated']}; border: 1px solid {T['border']};
    border-radius: 8px; padding: 6px 10px;
    color: {T['text_secondary']};
}}
QPushButton#IconBtn:hover {{ border-color: {a}; color: {a}; }}

QPushButton#FlatBtn {{
    background: transparent; border: none;
    color: {a}; padding: 4px; border-radius: 4px;
}}
QPushButton#FlatBtn:hover {{ color: {ah}; background: {sel}; }}

QPushButton#TitleBarBtn {{
    background: transparent; border: none;
    color: {T['text_secondary']}; border-radius: 6px;
    padding: 4px 8px; font-size: 14px;
}}
QPushButton#TitleBarBtn:hover {{
    background: {T['bg_elevated']}; color: {T['text_primary']};
}}
QPushButton#CloseBtn {{
    background: transparent; border: none;
    color: {T['text_secondary']}; border-radius: 6px;
    padding: 4px 8px; font-size: 14px;
}}
QPushButton#CloseBtn:hover {{ background: {T['danger']}; color: #FFF; }}

/* ── Inputs ───────────────────────────────────────────────── */
QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QDoubleSpinBox {{
    background-color: {T['bg_input']};
    border: 1.5px solid {T['border_strong']};
    border-radius: 9px; padding: 9px 13px;
    color: {T['text_primary']};
    selection-background-color: {a};
    selection-color: #FFF;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {a};
}}
QLineEdit:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {T['bg_elevated']};
    color: {T['text_muted']}; border-color: {T['border']};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    width: 18px; border: none; background: {T['bg_elevated']};
}}
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right;
    border-radius: 0 8px 0 0;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right;
    border-radius: 0 0 8px 0;
}}

/* ── Updated ComboBox ─────────────────────────────────────── */
QComboBox {{
    background-color: {T['bg_input']};
    border: 1.5px solid {T['border_strong']};
    border-radius: 9px; 
    padding: 8px 36px 8px 12px;
    color: {T['text_primary']};
    min-width: 120px;
}}
QComboBox:focus {{ border-color: {a}; }}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 32px;
    border: none;
    background: transparent;
}}
QComboBox::down-arrow {{
    image: {down_arrow_svg};
    width: 16px;
    height: 16px;
}}
QComboBox QAbstractItemView {{
    background-color: {T['bg_surface']};
    border: 1px solid {T['border_strong']};
    selection-background-color: {sel};
    selection-color: {T['text_primary']};
    color: {T['text_primary']};
    border-radius: 8px; padding: 4px;
    outline: none;
}}

/* ── DateEdit ─────────────────────────────────────────────── */
QDateEdit {{
    background-color: {T['bg_input']};
    border: 1.5px solid {T['border_strong']};
    border-radius: 9px; padding: 8px 30px 8px 10px;
    color: {T['text_primary']};
}}
QDateEdit:focus {{ border-color: {a}; }}
QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
}}
QDateEdit::down-arrow {{
    image: {down_arrow_svg};
    width: 16px; height: 16px;
}}
QCalendarWidget {{
    background-color: {T['bg_surface']};
    color: {T['text_primary']};
}}
QCalendarWidget QAbstractItemView {{
    background-color: {T['bg_surface']};
    selection-background-color: {a};
    color: {T['text_primary']};
}}

/* ── Tables ───────────────────────────────────────────────── */
QTableWidget {{
    background-color: {T['bg_surface']};
    border: 1px solid {T['border']};
    border-radius: 12px;
    gridline-color: {T['border']};
    alternate-background-color: {T['bg_elevated']};
    selection-background-color: {sel};
    selection-color: {T['text_primary']};
}}
QTableWidget::item {{ padding: 8px 12px; border: none; }}
QTableWidget::item:hover {{ background-color: {T['bg_elevated']}; }}
QTableWidget::item:selected {{
    background-color: {sel};
    color: {T['text_primary']};
}}
QTableWidget:focus {{ border-color: {a}; }}
QHeaderView::section {{
    background-color: {T['bg_elevated']};
    color: {T['text_muted']};
    border: none;
    border-bottom: 2px solid {T['border']};
    border-right: 1px solid {T['border']};
    padding: 10px 12px;
    font-weight: 700; font-size: 10px;
    letter-spacing: 1px; text-transform: uppercase;
}}
QHeaderView::section:last {{ border-right: none; }}

/* ── Tabs ─────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {T['border']};
    border-radius: 0 12px 12px 12px;
    background-color: {T['bg_surface']};
    top: -1px;
}}
QTabBar::tab {{
    background-color: {T['bg_elevated']};
    color: {T['text_muted']};
    border: 1px solid {T['border']};
    border-bottom: none;
    border-radius: 8px 8px 0 0;
    padding: 9px 20px; margin-right: 3px;
    font-weight: 500; font-size: 12px;
}}
QTabBar::tab:selected {{
    background-color: {T['bg_surface']};
    color: {a}; font-weight: 700;
    border-top: 2px solid {a};
}}
QTabBar::tab:hover:!selected {{ color: {T['text_primary']}; }}

/* ── Scrollbars ───────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent; width: 7px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {T['border_strong']}; border-radius: 4px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {T['text_muted']}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: transparent; height: 7px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {T['border_strong']}; border-radius: 4px; min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {T['text_muted']}; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── Labels ───────────────────────────────────────────────── */
QLabel {{ background: transparent; color: {T['text_primary']}; }}

#SectionTitle {{
    font-size: 13px; font-weight: 700;
    color: {T['text_primary']}; background: transparent;
}}
#FieldLabel {{
    font-size: 10px; font-weight: 700;
    color: {T['text_muted']}; letter-spacing: 0.5px;
    background: transparent;
}}
#HintText {{
    font-size: 10px; color: {T['text_muted']};
    background: transparent;
}}
#MutedText {{ color: {T['text_muted']}; font-size: 11px; background:transparent;}}
#AccentText {{ color: {a}; font-weight: 700; background: transparent; }}
#PageTitle {{
    font-size: 18px; font-weight: 700;
    color: {T['text_primary']}; background: transparent;
}}

/* ── Badges ───────────────────────────────────────────────── */
#BadgeSuccess {{
    background-color: {'#064E3B' if dk else '#D1FAE5'};
    color: {'#6EE7B7' if dk else '#065F46'};
    border-radius: 12px; padding: 2px 10px; border: none;
    font-size: 10px; font-weight: 700;
}}
#BadgeDanger {{
    background-color: {'#450A0A' if dk else '#FEE2E2'};
    color: {'#FCA5A5' if dk else '#991B1B'};
    border-radius: 12px; padding: 2px 10px; border: none;
    font-size: 10px; font-weight: 700;
}}
#BadgeWarning {{
    background-color: {'#451A03' if dk else '#FEF3C7'};
    color: {'#FCD34D' if dk else '#92400E'};
    border-radius: 12px; padding: 2px 10px; border: none;
    font-size: 10px; font-weight: 700;
}}
#BadgeInfo {{
    background-color: {'#1B3A6B' if dk else '#DBEAFE'};
    color: {'#93C5FD' if dk else '#1E40AF'};
    border-radius: 12px; padding: 2px 10px; border: none;
    font-size: 10px; font-weight: 700;
}}

/* ── Separators ───────────────────────────────────────────── */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {T['border']};
}}

/* ── Dialog ───────────────────────────────────────────────── */
#DialogHeader {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
        stop:0 {T['accent']}, stop:1 {T['purple']});
}}
#DialogHeaderTitle {{
    font-size: 15px; font-weight: 700; color: #FFF;
    padding: 16px 24px 2px; background: transparent;
}}
#DialogHeaderSub {{
    font-size: 11px; color: rgba(255,255,255,0.7);
    padding: 0 24px 16px; background: transparent;
}}
#DialogBody {{ background: {T['bg_surface']}; }}
#DialogFooter {{
    background-color: {T['bg_elevated']};
    border-top: 1px solid {T['border']};
}}

/* ── MessageBox ───────────────────────────────────────────── */
QMessageBox {{
    background-color: {T['bg_surface']};
}}
QMessageBox QLabel {{ color: {T['text_primary']}; }}
QMessageBox QPushButton {{ min-width: 80px; }}

/* ── GroupBox ─────────────────────────────────────────────── */
QGroupBox {{
    border: 1px solid {T['border']};
    border-radius: 12px; margin-top: 14px; padding-top: 8px;
    font-weight: 700; font-size: 11px; color: {T['text_muted']};
}}
QGroupBox::title {{
    subcontrol-origin: margin; subcontrol-position: top left;
    padding: 0 10px; left: 14px; color: {T['text_muted']};
}}

/* ── CheckBox ─────────────────────────────────────────────── */
QCheckBox {{ spacing: 8px; color: {T['text_primary']}; }}
QCheckBox::indicator {{
    width: 17px; height: 17px;
    border: 1.5px solid {T['border_strong']};
    border-radius: 5px; background: {T['bg_input']};
}}
QCheckBox::indicator:checked {{
    background-color: {a}; border-color: {a};
}}
QCheckBox::indicator:hover {{ border-color: {a}; }}

/* ── Toast/Notification ───────────────────────────────────────── */
#Toast {{
    background-color: {T['bg_elevated']};
    border: 1px solid {T['border_strong']};
    border-radius: 10px;
    padding: 12px 16px;
}}
#ToastInfo {{
    background-color: {'#1E3A5F' if dk else '#DBEAFE'};
    border: 1px solid {'#3B82F6' if dk else '#93C5FD'};
    border-radius: 10px;
}}
#ToastSuccess {{
    background-color: {'#064E3B' if dk else '#D1FAE5'};
    border: 1px solid {'#10B981' if dk else '#6EE7B7'};
    border-radius: 10px;
}}
#ToastWarning {{
    background-color: {'#78350F' if dk else '#FEF3C7'};
    border: 1px solid {'#F59E0B' if dk else '#FCD34D'};
    border-radius: 10px;
}}
#ToastError {{
    background-color: {'#7F1D1D' if dk else '#FEE2E2'};
    border: 1px solid {'#EF4444' if dk else '#FCA5A5'};
    border-radius: 10px;
}}

/* ── Status Bar ────────────────────────────────────────────── */
QStatusBar {{
    background-color: {T['bg_surface']};
    border-top: 1px solid {T['border']};
    color: {T['text_muted']}; font-size: 11px; padding: 3px 12px;
}}

/* ── ToolTip ──────────────────────────────────────────────── */
QToolTip {{
    background-color: {T['bg_elevated']};
    border: 1px solid {T['border_strong']};
    color: {T['text_primary']};
    padding: 6px 10px; border-radius: 8px; font-size: 12px;
}}

/* ── SearchBar ────────────────────────────────────────────── */
QLineEdit#SearchBar {{
    background-color: {T['bg_elevated']};
    border: 1.5px solid {T['border']};
    border-radius: 20px; padding: 8px 16px;
    color: {T['text_primary']};
}}
QLineEdit#SearchBar:focus {{ border-color: {a}; }}

/* ── InputLabel ───────────────────────────────────────────── */
#InputLabel {{
    font-size: 11px; font-weight: 700;
    color: {T['text_secondary']}; background: transparent;
    margin-bottom: 2px;
}}

/* ── Splitter ─────────────────────────────────────────────── */
QSplitter::handle {{ background-color: {T['border']}; }}

/* ── Progress Bar ─────────────────────────────────────────── */
QProgressBar {{
    background-color: {T['bg_elevated']};
    border: none; border-radius: 6px; height: 8px;
    text-align: center; color: transparent;
}}
QProgressBar::chunk {{
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
        stop:0 {a}, stop:1 {ah});
    border-radius: 6px;
}}

/* ── Wizard ───────────────────────────────────────────────── */
#WizardCard {{
    background-color: {T['bg_surface']};
    border: 1px solid {T['border']};
    border-radius: 20px;
}}
#WizardStep {{
    background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
        stop:0 {'#0D1B2A' if dk else '#F0F4F8'},
        stop:1 {'#1B2838' if dk else '#FFFFFF'});
    border-right: 1px solid {T['border']};
    border-radius: 20px 0 0 20px;
}}
#StepIndicatorActive {{
    background-color: {a}; color: #FFF;
    border-radius: 16px; font-weight: 800; font-size: 12px;
}}
#StepIndicatorDone {{
    background-color: {T['success']}; color: #FFF;
    border-radius: 16px; font-weight: 800; font-size: 12px;
}}
#StepIndicatorPending {{
    background-color: {T['bg_elevated']}; color: {T['text_muted']};
    border: 1.5px solid {T['border_strong']};
    border-radius: 16px; font-weight: 700; font-size: 12px;
}}
#StepLabel {{
    font-size: 12px; color: {T['text_secondary']}; background: transparent;
}}
#StepLabelActive {{
    font-size: 12px; font-weight: 700;
    color: {T['text_primary']}; background: transparent;
}}
"""
