from theme import ThemeManager


def get_login_stylesheet() -> str:
    T = ThemeManager.tokens()

    return f"""
        QDialog {{
            background-color: {T['bg_base']};
        }}

        QLabel#companyTitle {{
            font-size: 24px;
            font-weight: bold;
            color: {T['text_primary']};
        }}

        QLabel#subTitle {{
            font-size: 14px;
            color: {T['text_muted']};
            margin-bottom: 20px;
        }}

        QLineEdit {{
            padding: 12px;
            border: 1px solid {T['border_strong']};
            border-radius: 6px;
            font-size: 14px;
            background-color: {T['bg_input']}; 
            color: {T['text_primary']};
        }}

        QLineEdit:focus {{
            border: 2px solid {T['accent']};
        }}

        QPushButton#loginBtn {{
            background-color: {T['accent']};
            color: #FFFFFF;
            padding: 12px;
            border-radius: 6px;
            font-size: 16px;
            font-weight: bold;
            margin-top: 15px;
        }}

        QPushButton#loginBtn:hover {{
            background-color: {T['accent_hover']};
        }}
    """