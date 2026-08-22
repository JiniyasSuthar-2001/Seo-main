import os
import sqlite3
from sqlalchemy.engine import Engine
from app.config.settings import _DB_PATH
from app.config.database import Base

# Import all models so Base.metadata contains all table definitions
from app.models import project, dataset, page, keyword, keyword_group, crawl_session, competitor, external_connection, audit_issue, action_opportunity

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
    Targeting strictly the authoritative database file path from application configuration.
    """
    db_file = os.path.abspath(_DB_PATH)
    print(f"[MIGRATION] Target database file: '{db_file}'", flush=True)
    _migrate_single_file(db_file)


def _migrate_single_file(db_file: str):
    expected_tables = {
        "schema_migrations": {
            "version": "TEXT",
            "applied_at": "DATETIME"
        },
        "projects": {

            "id": "TEXT",
            "name": "TEXT",
            "url": "TEXT",
            "description": "TEXT",
            "industry": "TEXT",
            "notes": "TEXT",
            "target_type": "TEXT",
            "search_engine": "TEXT",
            "target_country": "TEXT",
            "target_language": "TEXT",
            "target_device": "TEXT",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        },
        "crawl_sessions": {
            "id": "TEXT",
            "project_id": "TEXT",
            "status": "TEXT",
            "crawler_status": "TEXT",
            "crawl_scope": "TEXT",
            "pages_discovered": "INTEGER",
            "pages_crawled": "INTEGER",
            "blocked_pages_count": "INTEGER",
            "assets_crawled_count": "INTEGER",
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
            "group_id": "TEXT",
            "keyword": "TEXT",
            "target_url": "TEXT",
            "search_volume": "INTEGER",
            "difficulty": "REAL",
            "intent": "TEXT",
            "position": "INTEGER",
            "country": "TEXT",
            "device": "TEXT",
            "cpc": "REAL",
            "serp_features": "TEXT",
            "source": "TEXT"
        },
        "keyword_groups": {
            "id": "TEXT",
            "project_id": "TEXT",
            "name": "TEXT",
            "description": "TEXT",
            "created_at": "DATETIME"
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
        },
        "audit_issues": {
            "id": "TEXT",
            "project_id": "TEXT",
            "session_id": "TEXT",
            "rule_id": "TEXT",
            "category": "TEXT",
            "severity": "TEXT",
            "title": "TEXT",
            "description": "TEXT",
            "evidence_json": "TEXT",
            "affected_urls_json": "TEXT",
            "affected_pages_count": "INTEGER",
            "recommendation": "TEXT",
            "status": "TEXT",
            "first_detected": "DATETIME",
            "last_detected": "DATETIME",
            "created_at": "DATETIME"
        },
        "action_opportunities": {
            "id": "TEXT",
            "project_id": "TEXT",
            "title": "TEXT",
            "category": "TEXT",
            "priority_score": "REAL",
            "priority_level": "TEXT",
            "impact": "TEXT",
            "evidence": "TEXT",
            "affected_urls_json": "TEXT",
            "affected_count": "INTEGER",
            "recommendation": "TEXT",
            "status": "TEXT",
            "created_at": "DATETIME",
            "updated_at": "DATETIME"
        }
    }

    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]

        # 1. Create missing tables if needed
        for table_name, cols in expected_tables.items():
            if table_name not in existing_tables:
                print(f"[MIGRATION] Creating table '{table_name}'...", flush=True)
                col_defs = []
                for cname, ctype in cols.items():
                    col_str = f"{cname} {ctype}"
                    if cname == "id":
                        col_str += " PRIMARY KEY"
                    col_defs.append(col_str)
                cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(col_defs)});")
                conn.commit()
                existing_tables.append(table_name)

        # 2. Check each table for missing columns
        for table_name, cols in expected_tables.items():
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            col_info = cursor.fetchall()
            existing_col_names = {row[1].lower(): row for row in col_info}

            for col_name, col_type in cols.items():
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
