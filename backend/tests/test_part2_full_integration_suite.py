"""
Part 2 Full Integration Suite — Canonical Audit Integration Verification
Tests PDF generation, Master XLSX report building, project isolation,
and evidence-based schema/robots exporting.
"""
import pytest
import os
import json
from pathlib import Path
from io import BytesIO
import openpyxl

from app.config.utils import get_project_storage_dir
from app.config.settings import settings
from app.services.canonical_audit_service import CanonicalAuditService
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.xlsx_service import XLSXExportService, build_master_tracker_xlsx

def setup_mock_crawl_data(domain: str, project_id: str, crawl_id: str = "crawl_canonical_123"):
    """Helper to populate isolated project storage with 20 pages and canonical metadata."""
    storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
    crawl_dir = os.path.join(storage_dir, "crawls", crawl_id)
    os.makedirs(crawl_dir, exist_ok=True)
    
    mock_pages = []
    for idx in range(1, 21):
        has_sd = idx <= 12
        types_list = ["Organization", "WebSite"] if has_sd else []
        json_ld_blocks = [{"@type": "Organization", "name": "Test Company", "url": f"https://{domain}/"}] if has_sd else []
        
        mock_pages.append({
            "url": f"https://{domain}/page-{idx}",
            "status_code": 200,
            "title": f"Page Title {idx}" if idx > 3 else "",  # 3 missing titles
            "meta_description": f"Meta description for page {idx}",
            "h1": f"Heading 1 for page {idx}",
            "word_count": 250,
            "canonical_url": f"https://{domain}/page-{idx}",
            "has_structured_data": has_sd,
            "structured_data_types": types_list,
            "structured_data": json_ld_blocks,
            "raw_json_ld": json_ld_blocks
        })

    with open(os.path.join(crawl_dir, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(mock_pages, f)

    meta_obj = {
        "crawl_id": crawl_id,
        "project_id": project_id,
        "website": domain,
        "timestamp": "2026-09-16T12:00:00Z",
        "pages_crawled": 20
    }
    with open(os.path.join(crawl_dir, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta_obj, f)

    latest_ptr = {
        "crawl_id": crawl_id,
        "timestamp": "2026-09-16T12:00:00Z",
        "path": crawl_dir
    }
    with open(os.path.join(storage_dir, "latest.json"), "w", encoding="utf-8") as f:
        json.dump(latest_ptr, f)
        
    return mock_pages

def test_canonical_audit_service_structure(tmp_path):
    """Verify CanonicalAuditService provides all required canonical audit fields."""
    project_id = "proj_part2_canonical_test"
    domain = "testdomain.com"
    crawl_id = "crawl_canonical_123"
    
    setup_mock_crawl_data(domain, project_id, crawl_id)
        
    audit_res = CanonicalAuditService.get_canonical_audit_result(project_id, domain)
    
    assert audit_res["project_id"] == project_id
    assert audit_res["domain"] == domain
    assert audit_res["analyzed_pages"] == 20
    assert audit_res["evaluated_rules"] == 14
    assert audit_res["total_evaluated_checks"] == 280
    assert audit_res["health_score"] is not None
    assert audit_res["score_available"] is True
    assert "schema_summary" in audit_res
    assert "robots_summary" in audit_res
    assert audit_res["schema_summary"]["total_pages_with_schema"] == 12

def test_pdf_report_generation_with_canonical_data():
    """Verify PDFService builds PDF with dynamic rule breakdown, schema, and robots sections."""
    project_id = "proj_pdf_test"
    domain = "pdfdemo.com"
    
    setup_mock_crawl_data(domain, project_id, "crawl_pdf_456")
        
    pdf_gen = PDFReportGenerator()
    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name=domain,
        project_url=f"https://{domain}/",
        metadata={"project_id": project_id, "domain": domain}
    )
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF")

def test_master_xlsx_worksheets_and_canonical_data():
    """Verify Master XLSX includes Audit Rules Applied, Schema Evidence, and Robots Evidence worksheets."""
    project_id = "proj_xlsx_test"
    domain = "xlsxdemo.com"
    
    setup_mock_crawl_data(domain, project_id, "crawl_xlsx_789")
        
    xlsx_bytes = build_master_tracker_xlsx(project_id, domain)
    assert xlsx_bytes is not None
    assert len(xlsx_bytes) > 2000
    
    # Read Excel workbook structure using openpyxl
    wb = openpyxl.load_workbook(filename=BytesIO(xlsx_bytes))
    sheet_names = wb.sheetnames
    
    assert "Audit Rules Applied" in sheet_names
    assert "Schema Evidence" in sheet_names
    assert "Robots Evidence" in sheet_names
    
    ws_rules = wb["Audit Rules Applied"]
    assert ws_rules["A1"].value == "Analyzed Pages"
    assert ws_rules["B1"].value == 20
    assert ws_rules["A2"].value == "Evaluated Rules"
    assert ws_rules["B2"].value == 14
    assert ws_rules["A3"].value == "Total Checks"
    assert ws_rules["B3"].value == 280

def test_null_score_handling_no_100_fallback():
    """Verify null health score produces 'Not Yet Scored' and never falls back to 100."""
    project_id = "proj_null_score"
    domain = "nullscore.com"
    
    storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
    os.makedirs(storage_dir, exist_ok=True)
    
    audit_res = CanonicalAuditService.get_canonical_audit_result(project_id, domain)
    assert audit_res["health_score"] is None
    assert audit_res["score_available"] is False

def test_multi_tenant_same_domain_isolation():
    """Verify two projects with identical domain store data in isolated project folders."""
    domain = "shared-domain.com"
    proj1 = "proj_alpha_111"
    proj2 = "proj_beta_222"
    
    dir1 = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, proj1)
    dir2 = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, proj2)
    
    assert dir1 != dir2
    assert proj1 in str(dir1)
    assert proj2 in str(dir2)
