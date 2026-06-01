"""
Progressive Enterprises – Automated SQLite MigrationSystem
Detects schema differences and auto-migrates the database.
"""

import sqlite3
from typing import Dict, List, Tuple, Set
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session
from db.models import Base


class MigrationSystem:
    """
    Automated migration system for SQLite.
    Compares SQLAlchemy models with actual database schema
    and performs necessary migrations.
    """
    
    def __init__(self, engine, session: Session = None):
        self.engine = engine
        self.session = session
        self.inspector = inspect(engine)
        
    def get_db_tables(self) -> Set[str]:
        """Get all table names from the actual database."""
        try:
            return set(self.inspector.get_table_names())
        except Exception:
            return set()
    
    def get_model_tables(self) -> Set[str]:
        """Get all table names from SQLAlchemy models."""
        return set(Base.metadata.tables.keys())
    
    def get_db_columns(self, table_name: str) -> Dict[str, dict]:
        """Get column info from actual database for a table."""
        try:
            columns = {}
            for col in self.inspector.get_columns(table_name):
                columns[col['name']] = {
                    'type': str(col['type']),
                    'nullable': col.get('nullable', True),
                    'default': col.get('default'),
                    'primary_key': col.get('primary_key', False),
                }
            return columns
        except Exception:
            return {}
    
    def get_model_columns(self, table_name: str) -> Dict[str, dict]:
        """Get column info from SQLAlchemy model for a table."""
        columns = {}
        if table_name not in Base.metadata.tables:
            return columns
        
        table = Base.metadata.tables[table_name]
        for col in table.columns:
            columns[col.name] = {
                'type': str(col.type),
                'nullable': col.nullable,
                'default': str(col.default) if col.default else None,
                'primary_key': col.primary_key,
            }
        return columns
    
    def sqlite_type_to_sqlalchemy(self, sqlite_type: str) -> str:
        """Map SQLite types to SQLAlchemy type strings for comparison."""
        sqlite_type = sqlite_type.upper()
        
        type_mappings = {
            'INTEGER': 'INTEGER',
            'INT': 'INTEGER',
            'BIGINT': 'BIGINT',
            'SMALLINT': 'SMALLINT',
            'TINYINT': 'SMALLINT',
            'REAL': 'FLOAT',
            'DOUBLE': 'FLOAT',
            'FLOAT': 'FLOAT',
            'NUMERIC': 'FLOAT',
            'DECIMAL': 'FLOAT',
            'TEXT': 'TEXT',
            'VARCHAR': 'VARCHAR',
            'CHAR': 'VARCHAR',
            'CLOB': 'TEXT',
            'BLOB': 'BLOB',
            'BOOLEAN': 'BOOLEAN',
            'BOOL': 'BOOLEAN',
            'DATE': 'DATE',
            'DATETIME': 'DATETIME',
            'TIMESTAMP': 'DATETIME',
            'TIME': 'TIME',
        }
        
        for key in type_mappings:
            if sqlite_type.startswith(key):
                return type_mappings[key]
        
        return sqlite_type
    
    def types_compatible(self, db_type: str, model_type: str) -> bool:
        """Check if database type is compatible with model type."""
        db_type_upper = db_type.upper()
        model_type_upper = model_type.upper()
        
        if db_type_upper == model_type_upper:
            return True
        
        compatible_groups = [
            {'INTEGER', 'BIGINT', 'SMALLINT', 'INT'},
            {'FLOAT', 'REAL', 'DOUBLE', 'NUMERIC', 'DECIMAL'},
            {'TEXT', 'VARCHAR', 'CHAR', 'CLOB'},
            {'DATE', 'DATETIME', 'TIMESTAMP'},
            {'BOOLEAN', 'BOOL'},
        ]
        
        for group in compatible_groups:
            if db_type_upper in group and model_type_upper in group:
                return True
        
        return False
    
    def detect_changes(self) -> Dict:
        """
        Detect all schema changes needed.
        Returns dict with:
        - new_tables: tables to create
        - new_columns: columns to add per table
        - modified_columns: columns that need attention (log warnings)
        """
        changes = {
            'new_tables': [],
            'new_columns': {},
            'modified_columns': {},
            'dropped_tables': [],
        }
        
        db_tables = self.get_db_tables()
        model_tables = self.get_model_tables()
        
        changes['new_tables'] = list(model_tables - db_tables)
        
        changes['dropped_tables'] = list(db_tables - model_tables)
        
        for table_name in model_tables & db_tables:
            db_cols = self.get_db_columns(table_name)
            model_cols = self.get_model_columns(table_name)
            
            db_col_names = set(db_cols.keys())
            model_col_names = set(model_cols.keys())
            
            new_cols = model_col_names - db_col_names
            if new_cols:
                changes['new_columns'][table_name] = [
                    (col, model_cols[col]) for col in new_cols
                ]
            
            common_cols = db_col_names & model_col_names
            modified = []
            for col_name in common_cols:
                db_col = db_cols[col_name]
                model_col = model_cols[col_name]
                
                if not self.types_compatible(db_col['type'], model_col['type']):
                    modified.append((col_name, db_col, model_col))
            
            if modified:
                changes['modified_columns'][table_name] = modified
        
        return changes
    
    def apply_migrations(self, verbose: bool = True) -> Tuple[bool, List[str]]:
        """
        Apply all detected migrations.
        Returns (success, messages).
        """
        messages = []
        
        try:
            changes = self.detect_changes()
            
            if not any([changes['new_tables'], changes['new_columns'], 
                       changes['modified_columns']]):
                if verbose:
                    print("[Migration] Database schema is up to date.")
                return True, ["Database schema is up to date."]
            
            for table_name in changes['new_tables']:
                if verbose:
                    print(f"[Migration] Creating new table: {table_name}")
                self._create_table(table_name)
                messages.append(f"Created table: {table_name}")
            
            for table_name, columns in changes['new_columns'].items():
                for col_name, col_info in columns:
                    if verbose:
                        print(f"[Migration] Adding column {col_name} to {table_name}")
                    self._add_column(table_name, col_name, col_info)
                    messages.append(f"Added column {col_name} to {table_name}")
            
            for table_name, columns in changes['modified_columns'].items():
                for col_name, db_col, model_col in columns:
                    msg = (f"[Migration] WARNING: Column {table_name}.{col_name} has type "
                           f"'{db_col['type']}' in DB but '{model_col['type']}' in model. "
                           f"SQLite does not support ALTER COLUMN. Consider recreating the table.")
                    if verbose:
                        print(msg)
                    messages.append(msg)
            
            return True, messages
            
        except Exception as e:
            error_msg = f"Migration failed: {str(e)}"
            if verbose:
                print(f"[Migration] ERROR: {error_msg}")
            return False, [error_msg]
    
    def _create_table(self, table_name: str):
        """Create a table from the SQLAlchemy model."""
        if table_name not in Base.metadata.tables:
            return
        
        table = Base.metadata.tables[table_name]
        
        conn = self.engine.connect()
        try:
            table.create(self.engine)
            conn.commit()
        finally:
            conn.close()
    
    def _add_column(self, table_name: str, column_name: str, column_info: dict):
        """Add a new column to an existing table."""
        conn = self.engine.connect()
        try:
            sql_type = self._get_sql_type(column_info)
            nullable = "" if column_info.get('nullable', True) else " NOT NULL"
            default = f" DEFAULT {column_info['default']}" if column_info.get('default') else ""
            
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {sql_type}{nullable}{default}"
            conn.execute(text(sql))
            conn.commit()
        finally:
            conn.close()
    
    def _get_sql_type(self, column_info: dict) -> str:
        """Convert SQLAlchemy type to SQLite type."""
        type_str = column_info['type'].upper()
        
        if 'VARCHAR' in type_str or 'CHAR' in type_str:
            return 'TEXT'
        elif 'INTEGER' in type_str or 'BIGINT' in type_str:
            return 'INTEGER'
        elif 'FLOAT' in type_str or 'DOUBLE' in type_str or 'NUMERIC' in type_str:
            return 'REAL'
        elif 'BOOLEAN' in type_str:
            return 'INTEGER'
        elif 'DATE' in type_str or 'TIME' in type_str:
            return 'TEXT'
        elif 'TEXT' in type_str:
            return 'TEXT'
        else:
            return 'TEXT'
    
    def get_migration_report(self) -> str:
        """Generate a human-readable migration report."""
        changes = self.detect_changes()
        lines = ["=" * 50, "Database Migration Report", "=" * 50, ""]
        
        lines.append(f"Model tables: {len(self.get_model_tables())}")
        lines.append(f"Database tables: {len(self.get_db_tables())}")
        lines.append("")
        
        if changes['new_tables']:
            lines.append("NEW TABLES TO CREATE:")
            for t in changes['new_tables']:
                lines.append(f"  - {t}")
            lines.append("")
        
        if changes['new_columns']:
            lines.append("NEW COLUMNS TO ADD:")
            for table, cols in changes['new_columns'].items():
                lines.append(f"  {table}:")
                for col_name, col_info in cols:
                    lines.append(f"    -{col_name} ({col_info['type']})")
            lines.append("")
        
        if changes['modified_columns']:
            lines.append("MODIFIED COLUMNS (requires manual migration or table recreation):")
            for table, cols in changes['modified_columns'].items():
                lines.append(f"  {table}:")
                for col_name, db_col, model_col in cols:
                    lines.append(f"    - {col_name}: {db_col['type']} -> {model_col['type']}")
            lines.append("")
        
        if changes['dropped_tables']:
            lines.append("ORPHANED TABLES (not in models):")
            for t in changes['dropped_tables']:
                lines.append(f"  - {t}")
            lines.append("")
        
        if not any([changes['new_tables'], changes['new_columns'], 
                   changes['modified_columns'], changes['dropped_tables']]):
            lines.append("Database is in sync with models.")
        
        return "\n".join(lines)


def run_migrations(engine, verbose: bool = True) -> Tuple[bool, List[str]]:
    """
    Convenience function to run migrations.
    Call this after DatabaseManager.init() but before seeding.
    """
    migrator = MigrationSystem(engine)
    return migrator.apply_migrations(verbose=verbose)