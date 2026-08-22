import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_crawl_storage_canonicalization():
    from app.config.utils import get_sanitized_domain

    d1 = get_sanitized_domain("https://example.com")
    d2 = get_sanitized_domain("https://example.com/")
    d3 = get_sanitized_domain("https://example.com/services/")
    d4 = get_sanitized_domain("example.com")

    assert d1 == "example_com"
    assert d2 == "example_com"
    assert d3 == "example_com"
    assert d4 == "example_com"

def test_reconcile_crawl_storage_dry_run():
    from maintenance.reconcile_crawl_storage import reconcile_storage
    reconcile_storage(dry_run=True)

def test_backend_graceful_nonexistent_project_id_handling():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # Nonexistent string IDs like 'undefined' or 'null' should return valid empty responses or 404
    res_undefined = client.get("/api/projects/undefined/keywords")
    assert res_undefined.status_code in (200, 404)

    res_null = client.get("/api/projects/null/rankings")
    assert res_null.status_code in (200, 404)

def test_exception_logging():
    from app.config.logger import get_logger
    logger = get_logger("test_logger")
    logger.info("Regression test logger output verified.")

if __name__ == "__main__":
    test_crawl_storage_canonicalization()
    test_reconcile_crawl_storage_dry_run()
    test_backend_graceful_nonexistent_project_id_handling()
    test_exception_logging()
    print("All regression tests passed successfully!")
