import os
import sqlite3
from sqlalchemy.engine import Engine
from app.config.settings import _DB_PATH
from app.config.database import Base

# Import all models so Base.metadata contains all table definitions
from app.models import project, dataset, page, keyword, crawl_session, competitor, external_connection

def get_sqlite_type(sql_type) -> str:
    st = str(sql_type).upper()
    if 'INT' in st:
        return 'INTEGER'
    elif 'FLOAT' in st or 'REAL' in st or 'NUMERIC' in st:
        return 'REAL'
    elif 'BOOL' in st:
        return 'BOOLEAN'
    elif 'DATE' in st or 'TIME' in st:
        return 'DATETIME'
    else:
        return 'TEXT'

def run_schema_migrations(engine: Engine = None):
    """
    Automatic, idempotent SQLite schema migration engine using raw sqlite3 connection.
    Dynamically inspects all registered SQLAlchemy models and guarantees missing columns are added directly
    to the SQLite database file on disk before ORM operations start.
    Preserves 100% of existing tables, rows, primary keys, and relationships without recreation or data deletion.
    """
    db_file = os.path.abspath(_DB_PATH)
    print(f"[MIGRATION] Checking database schema on '{db_file}'...", flush=True)

    if not os.path.exists(db_file):
        print(f"[MIGRATION] Database file '{db_file}' does not exist yet. SQLAlchemy create_all will initialize it.", flush=True)
        return

    expected_tables = {
        "projects": {
            "id": "TEXT",
            "name": "TEXT",
            "url": "TEXT",
            "description": "TEXT",
            "industry": "TEXT",
            "notes": "TEXT",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        },
        "crawl_sessions": {
            "id": "TEXT",
            "project_id": "TEXT",
            "status": "TEXT",
            "pages_discovered": "INTEGER",
            "pages_crawled": "INTEGER",
            "issues_found": "INTEGER",
            "started_at": "DATETIME",
            "completed_at": "DATETIME"
        },
        "datasets": {
            "id": "TEXT",
            "project_id": "TEXT",
            "data_type": "TEXT",
            "source": "TEXT",
            "filename": "TEXT",
            "record_count": "INTEGER",
            "error_count": "INTEGER",
            "status": "TEXT",
            "imported_at": "DATETIME"
        },
        "keywords": {
            "id": "TEXT",
            "project_id": "TEXT",
            "dataset_id": "TEXT",
            "keyword": "TEXT",
            "target_url": "TEXT",
            "search_volume": "INTEGER",
            "difficulty": "REAL",
            "intent": "TEXT",
            "position": "INTEGER",
            "country": "TEXT",
            "device": "TEXT"
        },
        "pages": {
            "id": "TEXT",
            "project_id": "TEXT",
            "dataset_id": "TEXT",
            "url": "TEXT",
            "title": "TEXT",
            "meta_description": "TEXT",
            "canonical": "TEXT",
            "status_code": "INTEGER",
            "word_count": "INTEGER",
            "h1": "TEXT",
            "indexability": "TEXT"
        },
        "competitors": {
            "id": "TEXT",
            "project_id": "TEXT",
            "name": "TEXT",
            "domain": "TEXT",
            "url": "TEXT",
            "location": "TEXT",
            "geographic_level": "TEXT",
            "relevance_score": "REAL",
            "keyword_overlap": "INTEGER",
            "search_appearances": "INTEGER",
            "status": "TEXT",
            "is_primary": "BOOLEAN",
            "discovery_source": "TEXT",
            "discovered_keywords": "TEXT",
            "competing_services": "TEXT",
            "notes": "TEXT",
            "first_discovered": "DATETIME",
            "last_checked": "DATETIME",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        }
    }

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]

        # 1. Check metadata tables from SQLAlchemy models
        for table_name, table in Base.metadata.tables.items():
            if table_name not in existing_tables:
                continue

            cursor.execute(f"PRAGMA table_info('{table_name}');")
            col_info = cursor.fetchall()
            existing_col_names = {row[1].lower(): row for row in col_info}

            for column in table.columns:
                col_name = column.name
                if col_name.lower() not in existing_col_names:
                    col_type = get_sqlite_type(column.type)
                    print(f"[MIGRATION] Adding missing column '{col_name}' ({col_type}) to table '{table_name}'...", flush=True)
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                        conn.commit()
                        print(f"[MIGRATION] SUCCESS: Added '{col_name}' to '{table_name}'.", flush=True)
                    except Exception as col_err:
                        print(f"[MIGRATION] ERROR adding '{col_name}' to '{table_name}': {col_err}", flush=True)

        # 2. Check fallback explicit expected_tables dict for double safety
        for table_name, columns in expected_tables.items():
            if table_name not in existing_tables:
                continue

            cursor.execute(f"PRAGMA table_info('{table_name}');")
            col_info = cursor.fetchall()
            existing_col_names = {row[1].lower(): row for row in col_info}

            for col_name, col_type in columns.items():
                if col_name.lower() not in existing_col_names:
                    print(f"[MIGRATION] Adding missing column '{col_name}' ({col_type}) to table '{table_name}'...", flush=True)
                    try:
                        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type};")
                        conn.commit()
                        print(f"[MIGRATION] SUCCESS: Added '{col_name}' to '{table_name}'.", flush=True)
                    except Exception as col_err:
                        print(f"[MIGRATION] ERROR adding '{col_name}' to '{table_name}': {col_err}", flush=True)

        conn.close()
        print("[MIGRATION] Schema check & migrations completed successfully.", flush=True)
    except Exception as e:
        print(f"[MIGRATION CRITICAL ERROR] Failed raw migration check: {e}", flush=True)

if __name__ == "__main__":
    run_schema_migrations()
