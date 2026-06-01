import bcrypt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QCheckBox, QDialog, QMessageBox,
    QFrame, QScrollArea
)

from ui.components.data_table import DataTable
from ui.components.form_dialog import FormDialog, ValidationError
from db.manager import get_db
from db.models import User
from core.auth import AuthSession

class AddEditUserDialog(FormDialog):
    def __init__(self, user: User = None, parent=None):
        mode = "Edit User" if user else "Add New User"
        super().__init__(mode, width=440, parent=parent)
        self._user = user
        self._build_fields()
        if user:
            self._populate(user)
        self.finalize()

    def _build_fields(self):
        self.full_name_edit = QLineEdit(); self.full_name_edit.setPlaceholderText("Full Name *")
        self.add_field("Full Name *", self.full_name_edit)

        self.username_edit = QLineEdit(); self.username_edit.setPlaceholderText("Username *")
        self.add_field("Username *", self.username_edit)

        self.password_edit = QLineEdit(); self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        hint = "Leave blank to keep existing password" if self._user else ""
        self.password_edit.setPlaceholderText("Password *" if not self._user else "New password (optional)")
        self.add_field("Password", self.password_edit, hint=hint)

        self.role_combo = QComboBox()
        current = AuthSession.current_user()
        if current and current.role == "developer":
            self.role_combo.addItems(["staff", "admin", "developer"])
        else:
            self.role_combo.addItems(["staff", "admin"])
        self.add_field("Role", self.role_combo)

        self.active_check = QCheckBox("Account Active")
        self.active_check.setChecked(True)
        self.body_layout.addWidget(self.active_check)

    def _populate(self, u: User):
        self.full_name_edit.setText(u.full_name or "")
        self.username_edit.setText(u.username or "")
        self.username_edit.setReadOnly(True)
        idx = self.role_combo.findText(u.role)
        if idx >= 0: self.role_combo.setCurrentIndex(idx)
        self.active_check.setChecked(u.is_active)

    def _collect(self):
        full_name = self.full_name_edit.text().strip()
        username = self.username_edit.text().strip()
        password = self.password_edit.text()

        if not full_name: raise ValidationError("Full name is required.")
        if not username: raise ValidationError("Username is required.")
        if not self._user and not password:
            raise ValidationError("Password is required for new users.")
        if password and len(password) < 6:
            raise ValidationError("Password must be at least 6 characters.")

        data = {
            "full_name": full_name, "username": username,
            "role": self.role_combo.currentText(),
            "is_active": self.active_check.isChecked(),
        }
        if password:
            data["password_hash"] = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        return data

class UserMgmtPage(QWidget):
    def __init__(self):
        super().__init__()
        self._users: list[User] = []
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

        title = QLabel("User Management")
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        if not AuthSession.is_admin_or_above():
            lbl = QLabel("🔒  You do not have permission to access this page.")
            lbl.setStyleSheet("color: #f87171; font-size: 16px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
            return

        self.table = DataTable(
            columns=["Username", "Full Name", "Role", "Status", "Last Login"],
            searchable=True,
            actions=[
                ("➕  Add User", self._add_user),
                ("✏️  Edit",      self._edit_user),
            ],
        )
        layout.addWidget(self.table)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

    def refresh(self):
        if not AuthSession.is_admin_or_above():
            return
        session = get_db()
        try:
            self._users = session.query(User).order_by(User.username).all()
            rows = []
            for u in self._users:
                status = "Active" if u.is_active else "Inactive"
                last = u.last_login.strftime("%d %b %Y %H:%M") if u.last_login else "Never"
                rows.append([u.username, u.full_name, u.role.capitalize(), status, last])
            self.table.set_data(rows)
        finally:
            session.close()

    def _add_user(self):
        dlg = AddEditUserDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            data = dlg.get_data()
            session = get_db()
            try:
                if session.query(User).filter_by(username=data["username"]).first():
                    QMessageBox.warning(self, "Duplicate", "Username already exists.")
                    return
                u = User(**data)
                session.add(u); session.commit()
                self.refresh()
                QMessageBox.information(self, "Success", "User created.")
            except Exception as e:
                session.rollback()
                QMessageBox.critical(self, "Error", str(e))
            finally:
                session.close()

    def _edit_user(self):
        orig = self.table.get_selected_original_index()
        if orig is None:
            QMessageBox.information(self, "Select User", "Please select a user.")
            return
        user = self._users[orig]
        if user.role == "developer" and not AuthSession.is_developer():
            QMessageBox.warning(self, "Permission Denied", "Cannot edit developer account.")
            return
        session = get_db()
        try:
            u = session.query(User).get(user.id)
            dlg = AddEditUserDialog(user=u, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                data = dlg.get_data()
                for k, v in data.items():
                    if k != "username":
                        setattr(u, k, v)
                session.commit()
                self.refresh()
                QMessageBox.information(self, "Done", "User updated.")
        except Exception as e:
            session.rollback()
            QMessageBox.critical(self, "Error", str(e))
        finally:
            session.close()
