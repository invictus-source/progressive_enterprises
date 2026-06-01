"""
Progressive Enterprises – Database Manager
Singleton that owns the SQLAlchemy engine and session factory.
Call DatabaseManager.init() once at app startup.
"""

import os
import bcrypt
from datetime import datetime, date
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from db.models import Base, User, Category, FinanceProvider
import config


class DatabaseManager:
    _instance = None
    engine = None
    SessionLocal = None

    @classmethod
    def init(cls):
        """Create engine, tables, and seed first-run data."""
        db_path = config.DB_PATH

        cls.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(cls.engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        cls.SessionLocal = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)
        
        Base.metadata.create_all(cls.engine)
        
        from db.migrations import run_migrations
        success, messages = run_migrations(cls.engine, verbose=True)
        if not success:
            print("[DatabaseManager] Migration warnings:", messages)
        
        cls._seed_first_run()

    @classmethod
    def get_session(cls) -> Session:
        if cls.SessionLocal is None:
            raise RuntimeError("DatabaseManager not initialised. Call DatabaseManager.init() first.")
        return cls.SessionLocal()

    @classmethod
    def db_path(cls) -> str:
        return config.DB_PATH

    @classmethod
    def data_dir(cls) -> str:
        return config.DATA_DIR

    # ── First-run seeding ─────────────────────────────────────────────────────

    @classmethod
    def _seed_first_run(cls):
        session = cls.get_session()
        try:
            cls._seed_dev_user(session)
            cls._seed_admin_from_wizard(session)
            cls._seed_default_categories(session)
            cls._seed_finance_providers(session)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"[WARNING] Seed error: {e}")
        finally:
            session.close()

    @classmethod
    def _seed_dev_user(cls, session: Session):
        """Always ensure the developer account exists and is intact.
        
        This runs on every startup. If the account was deleted, deactivated,
        or its password was tampered with, it is recreated / restored.
        """
        hashed = bcrypt.hashpw(config.DEV_PASSWORD.encode(), bcrypt.gensalt()).decode()
        dev = session.query(User).filter_by(username=config.DEV_USERNAME).first()
        if dev:
            # Restore correct state even if someone tampered via raw SQL
            dev.password_hash = hashed
            dev.full_name = config.DEV_FULL_NAME
            dev.role = "developer"
            dev.is_active = True
        else:
            session.add(User(
                username=config.DEV_USERNAME,
                password_hash=hashed,
                full_name=config.DEV_FULL_NAME,
                role="developer",
                is_active=True,
            ))

    @classmethod
    def _seed_admin_from_wizard(cls, session: Session):
        """If the setup wizard saved an admin account, create it."""
        import json
        sf = config.SETTINGS_FILE
        if not os.path.exists(sf):
            return
        try:
            with open(sf, "r") as f:
                data = json.load(f)
            uname = data.get("_admin_username")
            pwd_hash = data.get("_admin_pwd_hash")
            if uname and pwd_hash and not session.query(User).filter_by(username=uname).first():
                session.add(User(
                    username=uname,
                    password_hash=pwd_hash,
                    full_name=data.get("company_name", "Admin"),
                    role="admin",
                    is_active=True,
                ))
        except Exception:
            pass

    @classmethod
    def _seed_default_categories(cls, session: Session):
        defaults = [
            "Mobile Phones", "Laptops & Computers", "Televisions",
            "Home Appliances", "Audio & Speakers", "Accessories",
            "Cameras", "Tablets", "Networking", "Other Electronics",
        ]
        for name in defaults:
            if not session.query(Category).filter_by(name=name).first():
                session.add(Category(name=name))

    @classmethod
    def _seed_finance_providers(cls, session: Session):
        providers = [
            "Bajaj Finance", "Home Credit", "HDB Financial Services",
            "HDFC Bank EMI", "ICICI Bank EMI", "SBI Card EMI",
            "Axis Bank EMI", "Kotak Mahindra", "TVS Credit",
        ]
        for name in providers:
            if not session.query(FinanceProvider).filter_by(name=name).first():
                session.add(FinanceProvider(name=name, is_active=True))


# ── Convenience helper ────────────────────────────────────────────────────────
def get_db() -> Session:
    return DatabaseManager.get_session()
