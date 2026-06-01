import bcrypt
from datetime import datetime
from db.manager import get_db
from db.models import User


class AuthSession:
    _user: User = None

    @classmethod
    def login(cls, username: str, password: str) -> tuple[bool, str]:
        session = get_db()
        try:
            user = session.query(User).filter_by(username=username, is_active=True).first()
            if not user:
                return False, "Invalid username or account is disabled."

            if not bcrypt.checkpw(password.encode(), user.password_hash.encode()):
                return False, "Incorrect password."

            user.last_login = datetime.now()
            session.commit()

            _ = (user.id, user.username, user.password_hash,
                 user.full_name, user.role, user.is_active, user.last_login)

            from sqlalchemy.orm.session import make_transient
            session.expunge(user)
            make_transient(user)

            cls._user = user
            return True, "Login successful."
        except Exception as e:
            return False, f"Login error: {e}"
        finally:
            session.close()

    @classmethod
    def logout(cls):
        cls._user = None

    @classmethod
    def current_user(cls) -> User | None:
        return cls._user

    @classmethod
    def is_logged_in(cls) -> bool:
        return cls._user is not None

    @classmethod
    def has_role(cls, *roles: str) -> bool:
        if cls._user is None:
            return False
        return cls._user.role in roles

    @classmethod
    def is_developer(cls) -> bool:
        return cls.has_role("developer")

    @classmethod
    def is_admin_or_above(cls) -> bool:
        return cls.has_role("developer", "admin")

    @classmethod
    def is_staff_or_above(cls) -> bool:
        return cls.has_role("developer", "admin", "staff")