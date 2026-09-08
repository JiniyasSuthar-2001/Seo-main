import os
import sys
import pytest

# Ensure backend directory is in sys.path
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Set critical test environment variables
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ALLOW_DEV_USER_HEADER", "true")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-for-unit-audit-suite-32b")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-signing-session-32b")
os.environ.setdefault("OAUTH_STATE_SECRET", "test-oauth-state-secret-signing-32b")

from app.config.database import SessionLocal, engine

@pytest.fixture(autouse=True)
def clean_db_session():
    """Autouse fixture to ensure database transactions are cleanly managed per test."""
    db = SessionLocal()
    try:
        yield db
    finally:
        try:
            db.rollback()
        except Exception:
            pass
        db.close()
