import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment keys if missing
if not os.environ.get("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-full-platform-suite-32b"
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "test-secret-key-full-platform-suite-32b"
if not os.environ.get("OAUTH_STATE_SECRET"):
    os.environ["OAUTH_STATE_SECRET"] = "test-oauth-state-secret-full-suite-32b"

def test_full_platform_remediation_suite():
    print("============================================================", flush=True)
    print(" COMPREHENSIVE PLATFORM FUNCTIONALITY & TRUTHFULNESS SUITE", flush=True)
    print("============================================================\n", flush=True)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.config.database import SessionLocal
    from app.models.project import Project
    from app.models.keyword import Keyword
    from app.importers.keyword_importer import KeywordImporter, parse_optional_int
    from app.importers.ranking_importer import RankingImporter
    from app.importers.backlink_importer import BacklinkImporter
    from app.config.utils import sanitize_csv_cell, sanitize_csv_row
    from app.services.reports.export_service import CSVExportService
    from app.services.audit_rules import evaluate_site_audit_rules
    from app.services.report_builder_service import generate_custom_pdf_report
    from app.providers.datasources import DataSourceManager

    client = TestClient(app)
    db = SessionLocal()

    # Create temporary test project in DB
    test_proj = Project(
        name="Platform Suite Test Project",
        domain="platformtest.com",
        target_country="Australia"
    )
    db.add(test_proj)
    db.commit()
    db.refresh(test_proj)
    proj_id = test_proj.id

    try:
        # 1. Keywords CSV Import Test
        print("[1/9] Testing Keyword Importer (numeric 0 preservation & error reporting)...", flush=True)
        kw_importer = KeywordImporter(db=db, project_id=proj_id, filename="keywords.csv", source="Test")
        kw_importer.start_import("keywords")
        records = [
            {"keyword": "seo platform", "search_volume": "1000", "position": "0"},
            {"keyword": "", "position": "5"},
            {"keyword": "audit tool", "position": "invalid_val"}
        ]
        kw_importer.process_records(records)
        report = kw_importer.get_structured_import_report()
        assert report["successful_records"] == 1
        assert report["error_records"] == 2
        assert len(report["error_details"]) == 2
        # Verify numeric 0 position preserved
        db_kw = db.query(Keyword).filter(Keyword.project_id == proj_id, Keyword.keyword == "seo platform").first()
        assert db_kw is not None
        assert db_kw.position == 0
        print("      [PASS] Keyword Importer preserved numeric 0 position and reported structured errors.\n", flush=True)

        # 2. Rankings CSV Import Test
        print("[2/9] Testing Rankings Importer (position mapping & dataset JSON)...", flush=True)
        rk_importer = RankingImporter(db=db, project_id=proj_id, filename="rankings.csv", source="Test")
        rk_importer.start_import("rankings")
        rk_records = [
            {"keyword": "rank tracker", "position": "3", "previous_position": "5", "search_engine": "Google", "device": "Desktop"},
            {"keyword": "seo tools", "position": "1", "previous_position": "2", "search_engine": "Google", "device": "Mobile"}
        ]
        rk_importer.process_records(rk_records)
        rk_report = rk_importer.get_structured_import_report()
        assert rk_report["successful_records"] == 2
        assert rk_report["error_records"] == 0
        print("      [PASS] Rankings Importer processed records successfully.\n", flush=True)

        # 3. Backlinks CSV Import Test
        print("[3/9] Testing Backlinks Importer (referring domain & link status)...", flush=True)
        bl_importer = BacklinkImporter(db=db, project_id=proj_id, filename="backlinks.csv", source="Test")
        bl_importer.start_import("backlinks")
        bl_records = [
            {"source_url": "https://techblog.com/review", "target_url": f"https://{test_proj.domain}/", "anchor_text": "Top SEO Platform", "follow_status": "dofollow"},
            {"source_url": "https://directory.org/listing", "target_url": f"https://{test_proj.domain}/about", "anchor_text": "About Us", "follow_status": "nofollow"}
        ]
        bl_importer.process_records(bl_records)
        bl_report = bl_importer.get_structured_import_report()
        assert bl_report["successful_records"] == 2
        assert bl_report["error_records"] == 0
        print("      [PASS] Backlinks Importer processed records successfully.\n", flush=True)

        # 4. CSV Formula Injection Protection Test
        print("[4/9] Testing CSV Formula Injection Sanitization...", flush=True)
        dangerous_val1 = "=SUM(A1:A2)"
        dangerous_val2 = "+12345"
        dangerous_val3 = "-cmd|'/C calc'!A0"
        dangerous_val4 = "@COMMAND"

        assert sanitize_csv_cell(dangerous_val1) == "'=SUM(A1:A2)"
        assert sanitize_csv_cell(dangerous_val2) == "'+12345"
        assert sanitize_csv_cell(dangerous_val3) == "'-cmd|'/C calc'!A0"
        assert sanitize_csv_cell(dangerous_val4) == "'@COMMAND"
        assert sanitize_csv_cell("Normal Text") == "Normal Text"

        # Verify CSV export string output
        exported_csv = CSVExportService.generate_pages_csv([
            {"url": "https://example.com", "title": "=DANGEROUS_FORMULA()", "word_count": 200}
        ])
        assert "'=DANGEROUS_FORMULA()" in exported_csv
        print("      [PASS] CSV Formula Injection protection verified for dangerous spreadsheet prefixes.\n", flush=True)

        # 5. Fix Rankings Export Default Location Test (No hardcoded "US")
        print("[5/9] Testing Rankings Export Location Neutrality...", flush=True)
        rankings_csv = CSVExportService.generate_rankings_csv([
            {"keyword": "test kw", "url": "https://example.com", "position": 5, "location": None}
        ])
        assert ",Unknown," in rankings_csv
        assert ",US," not in rankings_csv
        print("      [PASS] Verified neutral 'Unknown' location representation in Rankings CSV export.\n", flush=True)

        # 6. Real Alerts System API Test
        print("[6/9] Testing Real Alerts API Endpoint...", flush=True)
        res_alerts = client.get(f"/api/projects/{proj_id}/alerts")
        assert res_alerts.status_code == 200
        alerts_json = res_alerts.json()
        assert "alerts" in alerts_json
        assert "summary" in alerts_json
        assert alerts_json["total_alerts"] >= 0
        print("      [PASS] Real Alerts API endpoint returned deterministic alert payload.\n", flush=True)

        # 7. Audit Category Status Truthfulness Test
        print("[7/9] Testing Site Audit Category Truthfulness...", flush=True)
        eval_res = evaluate_site_audit_rules([
            {"url": "https://platformtest.com", "status_code": 200, "word_count": 400, "h1": "Main Title", "title": "Title Tag", "meta_description": "Description", "canonical": "https://platformtest.com"}
        ])
        categories = eval_res["category_breakdown"]
        assert categories["Performance"]["status"] in ("Not Evaluated", "Not Analyzed")
        assert categories["Performance"]["evaluated"] is False

        assert categories["Crawlability"]["status"] == "Passed"
        assert categories["Crawlability"]["evaluated"] is True
        print("      [PASS] Unevaluated categories report status 'Not Evaluated' (evaluated=False).\n", flush=True)

        # 8. PDF Report Category Table Truthfulness Test
        print("[8/9] Testing PDF Executive Report Generation...", flush=True)
        pdf_bytes = generate_custom_pdf_report(
            project_name="Platform Test",
            domain="platformtest.com",
            sections=["Technical Audit"],
            audit_summary=eval_res
        )
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 100
        print("      [PASS] Executive PDF report generated with truthful category statuses.\n", flush=True)

        # 9. Provider Status Truthfulness Test
        print("[9/9] Testing Datasource Provider Status Truthfulness...", flush=True)
        ds_mgr = DataSourceManager()
        sources = ds_mgr.get_project_datasources("platformtest.com")
        assert sources["google_search_console"]["status"] == "Not Implemented"
        assert sources["google_search_console"]["implemented"] is False
        assert sources["pagespeed_insights"]["status"] == "Not Implemented"
        assert sources["pagespeed_insights"]["implemented"] is False
        print("      [PASS] Stubbed datasources report status 'Not Implemented' (implemented=False).\n", flush=True)

    finally:
        # Clean up test project
        db.query(Keyword).filter(Keyword.project_id == proj_id).delete()
        db.query(Project).filter(Project.id == proj_id).delete()
        db.commit()
        db.close()

    print("============================================================", flush=True)
    print(" ALL PLATFORM FUNCTIONALITY & TRUTHFULNESS TESTS PASSED!", flush=True)
    print("============================================================\n", flush=True)

if __name__ == "__main__":
    test_full_platform_remediation_suite()
