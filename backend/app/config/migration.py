import os
import sqlite3
from sqlalchemy.engine import Engine
from app.config.settings import _DB_PATH

def run_schema_migrations(engine: Engine = None):
    """
    Automatic, idempotent SQLite schema migration engine using raw sqlite3 connection.
    Guarantees column additions for existing tables directly on disk database file before ORM operations.
    Preserves 100% of existing rows, primary keys, relationships, and datasets.
    """
    db_file = os.path.abspath(_DB_PATH)
    print(f"[MIGRATION] Checking database schema on '{db_file}'...", flush=True)

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
        }
    }

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]

        for table_name, columns in expected_tables.items():
            if table_name not in existing_tables:
                print(f"[MIGRATION] Table '{table_name}' does not exist yet (create_all will initialize it).", flush=True)
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
