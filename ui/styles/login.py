# In your login.py
from theme import ThemeManager  # Adjust this import based on your project structure


def get_login_stylesheet() -> str:
    """
    Dynamically generates the stylesheet for the login window
    based on the current active theme in ThemeManager.
    """
    # Grab the current theme tokens (Light or Dark)
    T = ThemeManager.tokens()

    # We use double braces {{ }} in f-strings to output actual CSS curly braces
    return f"""
        QDialog {{
            /* Using bg_base here gives the window a slightly recessed look, 
               making input fields (bg_input) pop out more */
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
            /* bg_input ensures high contrast against bg_base */
            background-color: {T['bg_input']}; 
            color: {T['text_primary']};
        }}

        QLineEdit:focus {{
            border: 2px solid {T['accent']};
        }}

        QPushButton#loginBtn {{
            background-color: {T['accent']};
            color: #FFFFFF; /* Buttons with accent color always use white text */
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