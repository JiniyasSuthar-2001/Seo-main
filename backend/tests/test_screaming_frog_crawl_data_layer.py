import pytest
import os
import io
import json
import zipfile
import openpyxl
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.config.database import Base, get_db
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.crawl_session import CrawlSession
from app.services.crawl_storage import CrawlStorage
from app.services.crawl_data.crawl_dataset_service import CrawlDatasetService
from app.services.crawl_data.crawl_tab_export_service import CrawlTabExportService
from app.services.reports.export_service import ZIPExportService
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"

@pytest.fixture
def db_session():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def setup_test_project_and_crawl(db_session):
    proj_domain = "screamingfrog-test-domain.com"
    proj = Project(
        name="Screaming Frog Layer Test Site",
        url=f"https://{proj_domain}",
        industry="Technology",
        services="SEO Auditing, Crawling",
        service_areas="Global",
        notes="Automated unit test site for crawl data layer"
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)

    # Add authorized user
    membership = ProjectMembership(
        user_id="frog_tester@example.com",
        project_id=proj.id,
        role="OWNER",
        status="ACTIVE"
    )
    db_session.add(membership)
    db_session.commit()

    # Create mock crawl pages & artifacts
    pages = [
        {
            "url": f"https://{proj_domain}/",
            "final_url": f"https://{proj_domain}/",
            "status_code": 200,
            "response_time_ms": 145,
            "title": "Home Page — Screaming Frog SEO Audit Engine",  # length 45 (good)
            "meta_description": "Comprehensive enterprise SEO intelligence platform with deterministic crawling and reporting.",  # 96 (good)
            "h1": "Master SEO Platform",
            "h1_count": 1,
            "h2_count": 4,
            "h3_count": 2,
            "word_count": 1200,
            "canonical": f"https://{proj_domain}/",
            "robots_meta": "index, follow",
            "html_lang": "en",
            "viewport": "width=device-width, initial-scale=1.0",
            "images_count": 8,
            "images_missing_alt": 2,
            "internal_links_count": 5,
            "structured_data": [
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Screaming Frog Tester"
                },
                {
                    "@context": "https://schema.org",
                    "@graph": [
                        {"@type": "WebSite", "url": f"https://{proj_domain}/"},
                        {"@type": ["BreadcrumbList", "ItemList"]}
                    ]
                }
            ],
            "hreflangs": [
                {"lang": "en-US", "href": f"https://{proj_domain}/"},
                {"lang": "en-GB", "href": f"https://{proj_domain}/en-gb/"}
            ]
        },
        {
            "url": f"https://{proj_domain}/short-title",
            "final_url": f"https://{proj_domain}/short-title",
            "status_code": 200,
            "response_time_ms": 120,
            "title": "Short",  # <30 chars -> Too Short
            "meta_description": "",  # Missing
            "h1": "",
            "h1_count": 0,
            "h2_count": 0,
            "h3_count": 0,
            "word_count": 150,
            "canonical": f"https://{proj_domain}/other-canonical",  # Internal / non-self
            "robots_meta": "noindex, follow",
            "html_lang": "en",
            "images_count": 3,
            "images_missing_alt": 0,
            "internal_links_count": 2,
            "structured_data": None
        },
        {
            "url": f"https://{proj_domain}/duplicate-page-1",
            "final_url": f"https://{proj_domain}/duplicate-page-1",
            "status_code": 200,
            "response_time_ms": 190,
            "title": "Duplicate Shared Title Across Two Different Pages in Test",  # Duplicate
            "meta_description": "Duplicate meta description shared across multiple pages in our unit test environment.",  # Duplicate
            "h1": "Duplicate Header",
            "h1_count": 2,  # Multiple H1
            "h2_count": 3,
            "word_count": 450,
            "canonical": f"https://{proj_domain}/duplicate-page-1",
            "robots_meta": "index, nofollow",
            "images_count": 5,
            "images_missing_alt": 5,
            "internal_links_count": 3
        },
        {
            "url": f"https://{proj_domain}/duplicate-page-2",
            "final_url": f"https://{proj_domain}/duplicate-page-2",
            "status_code": 200,
            "response_time_ms": 210,
            "title": "Duplicate Shared Title Across Two Different Pages in Test",  # Duplicate
            "meta_description": "Duplicate meta description shared across multiple pages in our unit test environment.",  # Duplicate
            "h1": "Duplicate Header 2",
            "h1_count": 1,
            "h2_count": 1,
            "word_count": 500,
            "canonical": f"https://external-domain.com/original-article",  # Cross-domain
            "robots_meta": "",
            "images_count": 0,
            "images_missing_alt": 0,
            "internal_links_count": 1
        },
        {
            "url": f"https://{proj_domain}/redirect-source",
            "final_url": f"https://{proj_domain}/redirect-destination",
            "status_code": 301,
            "response_time_ms": 85,
            "redirect_history": [
                {"status_code": 301, "url": f"https://{proj_domain}/redirect-source"}
            ],
            "title": "",
            "meta_description": "",
            "h1": "",
            "h1_count": 0,
            "h2_count": 0,
            "word_count": 0,
            "images_count": 0,
            "images_missing_alt": 0,
            "internal_links_count": 0
        },
        {
            "url": f"https://{proj_domain}/broken-404",
            "final_url": f"https://{proj_domain}/broken-404",
            "status_code": 404,
            "response_time_ms": 95,
            "title": "Page Not Found",
            "meta_description": "",
            "h1": "404 Not Found",
            "h1_count": 1,
            "h2_count": 0,
            "word_count": 50,
            "images_count": 0,
            "images_missing_alt": 0,
            "internal_links_count": 0
        }
    ]

    internal_links = [
        {
            "source_url": f"https://{proj_domain}/",
            "target_url": f"https://{proj_domain}/short-title",
            "anchor_text": "Short Title Article",
            "rel": "follow",
            "status_code": 200
        },
        {
            "source_url": f"https://{proj_domain}/",
            "target_url": f"https://{proj_domain}/broken-404",
            "anchor_text": "Dead Link Example",
            "rel": "nofollow",
            "status_code": 404
        }
    ]

    external_links = [
        {
            "source_url": f"https://{proj_domain}/",
            "target_url": "https://www.w3.org/Protocols/rfc2616/",
            "anchor_text": "HTTP Specification",
            "rel": "noopener",
            "status_code": 200
        }
    ]

    broken_links = [
        {
            "source_url": f"https://{proj_domain}/",
            "target_url": f"https://{proj_domain}/broken-404",
            "link_type": "internal",
            "status_code": 404,
            "anchor_text": "Dead Link Example",
            "error": "HTTP 404 Not Found"
        }
    ]

    issues = [
        {
            "issue_type": "missing_h1",
            "category": "On-Page SEO",
            "severity": "HIGH",
            "affected_url": f"https://{proj_domain}/short-title",
            "evidence": "<h1> tag not found in page HTML",
            "current_value": "None",
            "expected_value": "Single descriptive <h1> header",
            "why_it_matters": "Search engines use H1 to understand core topic.",
            "recommended_action": "Add an H1 tag that matches primary keyword intent.",
            "ai_solution": ""
        }
    ]

    storage = CrawlStorage()
    results_payload = {
        "pages": pages,
        "internal_links": internal_links,
        "external_links": external_links,
        "broken_links": broken_links,
        "issues": issues,
        "status": "completed"
    }
    crawl_folder_path = storage.save_crawl_snapshot(
        key=str(proj.id),
        session_id="crawl-test-snap-001",
        results=results_payload,
        domain=proj_domain,
        project_id=str(proj.id)
    )

    return {
        "project": proj,
        "domain": proj_domain,
        "crawl_id": "crawl-test-snap-001",
        "pages_count": len(pages),
        "internal_links_count": len(internal_links),
        "external_links_count": len(external_links),
        "broken_links_count": len(broken_links),
        "issues_count": len(issues)
    }


def test_normalized_crawl_dataset_all_16_tabs(setup_test_project_and_crawl):
    """Verify all 16 tabs are generated with accurate deterministic data and no fabricated rows."""
    info = setup_test_project_and_crawl
    proj_id = str(info["project"].id)
    domain = info["domain"]
    crawl_id = info["crawl_id"]

    # 1. Internal Tab
    res_internal = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, limit=50)
    assert res_internal["total_rows"] == info["pages_count"]
    first_page = res_internal["rows"][0]
    assert first_page["url"] == f"https://{domain}/"
    assert first_page["status_code"] == 200
    assert first_page["h2_count"] == 4
    assert first_page["canonical_type"] in ["Self", "Self-Referencing"]
    assert "Organization" in first_page["schema_types"]
    assert "WebSite" in first_page["schema_types"]

    # 2. Response Codes
    res_codes = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "response-codes", crawl_id)
    assert res_codes["total_rows"] == info["pages_count"]
    status_classes = {r["status_class"] for r in res_codes["rows"]}
    assert "2xx" in status_classes
    assert "3xx" in status_classes
    assert "4xx" in status_classes

    # 3. Page Titles
    res_titles = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "titles", crawl_id)
    assert res_titles["total_rows"] == info["pages_count"]
    short_title_row = next(r for r in res_titles["rows"] if r["url"].endswith("/short-title"))
    assert short_title_row["too_short"] == "Yes"
    dup_title_row = next(r for r in res_titles["rows"] if r["url"].endswith("/duplicate-page-1"))
    assert dup_title_row["duplicate"] == "Yes"

    # 4. Meta Descriptions
    res_meta = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "meta-descriptions", crawl_id)
    assert res_meta["total_rows"] == info["pages_count"]
    missing_meta_row = next(r for r in res_meta["rows"] if r["url"].endswith("/short-title"))
    assert missing_meta_row["missing"] == "Yes"
    dup_meta_row = next(r for r in res_meta["rows"] if r["url"].endswith("/duplicate-page-1"))
    assert dup_meta_row["duplicate"] == "Yes"

    # 5. H1
    res_h1 = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "h1", crawl_id)
    assert res_h1["total_rows"] == info["pages_count"]
    missing_h1_row = next(r for r in res_h1["rows"] if r["url"].endswith("/short-title"))
    assert missing_h1_row["missing"] == "Yes"
    multi_h1_row = next(r for r in res_h1["rows"] if r["url"].endswith("/duplicate-page-1"))
    assert multi_h1_row["multiple_h1"] == "Yes"

    # 6. H2
    res_h2 = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "h2", crawl_id)
    assert res_h2["total_rows"] == info["pages_count"]
    home_h2 = next(r for r in res_h2["rows"] if r["url"] == f"https://{domain}/")
    assert home_h2["h2_count"] == 4

    # 7. Images
    res_images = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "images", crawl_id)
    assert res_images["total_rows"] == info["pages_count"]
    home_images = next(r for r in res_images["rows"] if r["url"] == f"https://{domain}/")
    assert home_images["images_count"] == 8
    assert home_images["images_missing_alt"] == 2
    assert home_images["missing_alt_percentage"] == "25.0%"

    # 8. Canonicals
    res_canon = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "canonicals", crawl_id)
    assert res_canon["total_rows"] == info["pages_count"]
    home_canon = next(r for r in res_canon["rows"] if r["url"] == f"https://{domain}/")
    assert home_canon["canonical_type"] in ["Self", "Self-Referencing"]
    cross_canon = next(r for r in res_canon["rows"] if r["url"].endswith("/duplicate-page-2"))
    assert cross_canon["canonical_type"] == "Cross-Domain"

    # 9. Directives
    res_dir = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "directives", crawl_id)
    assert res_dir["total_rows"] == info["pages_count"]
    noindex_row = next(r for r in res_dir["rows"] if r["url"].endswith("/short-title"))
    assert noindex_row["noindex"] == "Yes"
    assert noindex_row["follow_directive"].lower() == "follow"

    # 10. Hreflang
    res_href = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "hreflang", crawl_id)
    assert res_href["total_rows"] == 2
    assert res_href["rows"][0]["language"] in ["en-US", "en-GB"]

    # 11. Structured Data
    res_sd = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "structured-data", crawl_id)
    assert res_sd["total_rows"] == info["pages_count"]
    home_sd = next(r for r in res_sd["rows"] if r["url"] == f"https://{domain}/")
    assert home_sd["structured_data_present"] == "Yes"
    assert "Organization" in home_sd["schema_types"]
    assert "WebSite" in home_sd["schema_types"]
    assert "BreadcrumbList" in home_sd["schema_types"]
    assert "ItemList" in home_sd["schema_types"]

    # 12. Redirects
    res_redir = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "redirects", crawl_id)
    assert res_redir["total_rows"] == 1
    assert res_redir["rows"][0]["original_url"].endswith("/redirect-source")
    assert "Redirected" in str(res_redir["rows"][0]["redirect_status"]) or res_redir["rows"][0]["redirect_status"] == 301

    # 13. Internal Links
    res_il = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal-links", crawl_id)
    assert res_il["total_rows"] == info["internal_links_count"]
    assert res_il["rows"][0]["anchor_text"] in ["Short Title Article", "Dead Link Example"]

    # 14. External Links
    res_el = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "external-links", crawl_id)
    assert res_el["total_rows"] == info["external_links_count"]
    assert res_el["rows"][0]["destination_url"] == "https://www.w3.org/Protocols/rfc2616/"

    # 15. Broken Links
    res_bl = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "broken-links", crawl_id)
    assert res_bl["total_rows"] == info["broken_links_count"]
    assert res_bl["rows"][0]["status_code"] == 404

    # 16. Issues
    res_iss = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "issues", crawl_id)
    assert res_iss["total_rows"] == info["issues_count"]
    assert res_iss["rows"][0]["issue_type"] == "missing_h1"


def test_pagination_search_and_sorting(setup_test_project_and_crawl):
    """Verify 20-row pagination ceiling, filtering and sorting work server-side."""
    info = setup_test_project_and_crawl
    proj_id = str(info["project"].id)
    domain = info["domain"]
    crawl_id = info["crawl_id"]

    # Test limit and offset
    page_1 = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, limit=2, offset=0)
    assert len(page_1["rows"]) == 2
    assert page_1["limit"] == 2
    assert page_1["offset"] == 0

    page_2 = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, limit=2, offset=2)
    assert len(page_2["rows"]) == 2
    assert page_2["rows"][0]["url"] != page_1["rows"][0]["url"]

    # Test search filter
    search_res = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, search="short-title")
    assert search_res["total_rows"] == 1
    assert "short-title" in search_res["rows"][0]["url"]

    # Test filter by status_code
    status_404_res = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, filter_field="status_code", filter_value="404")
    assert status_404_res["total_rows"] == 1
    assert status_404_res["rows"][0]["status_code"] == 404

    # Test sorting
    sorted_asc = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, sort_by="status_code", sort_dir="asc")
    assert sorted_asc["rows"][0]["status_code"] <= sorted_asc["rows"][-1]["status_code"]

    sorted_desc = CrawlDatasetService.get_paginated_tab_data(proj_id, domain, "internal", crawl_id, sort_by="status_code", sort_dir="desc")
    assert sorted_desc["rows"][0]["status_code"] >= sorted_desc["rows"][-1]["status_code"]


def test_csv_export_and_injection_defense(setup_test_project_and_crawl):
    """Verify complete CSV export and CSV formula injection protection."""
    info = setup_test_project_and_crawl
    proj_id = str(info["project"].id)
    domain = info["domain"]
    crawl_id = info["crawl_id"]

    csv_data = CrawlTabExportService.export_tab_csv(proj_id, domain, "internal", crawl_id)
    assert isinstance(csv_data, str)
    lines = [l for l in csv_data.strip().split("\n") if l]
    # Header + 6 pages = 7 lines
    assert len(lines) == info["pages_count"] + 1

    # Verify CSV sanitization with dangerous formula symbols
    danger_page = {
        "url": "=cmd|' /C calc'!A0",
        "final_url": "+calc.exe",
        "status_code": 200,
        "title": "@SUM(1,2)",
        "meta_description": "-HYPERLINK('http://evil.com')",
        "canonical": f"https://{domain}/"
    }
    storage = CrawlStorage()
    storage.save_crawl_snapshot(
        key="danger-proj",
        session_id="danger-snap-001",
        results={"pages": [danger_page]},
        domain="danger.com",
        project_id="danger-proj"
    )
    danger_internal_csv = CrawlTabExportService.export_tab_csv("danger-proj", "danger.com", "internal", "danger-snap-001")
    assert "'=cmd" in danger_internal_csv
    assert "'@SUM" in danger_internal_csv
    assert "'-HYPERLINK" in danger_internal_csv

    danger_codes_csv = CrawlTabExportService.export_tab_csv("danger-proj", "danger.com", "response-codes", "danger-snap-001")
    assert "'+calc" in danger_codes_csv


def test_xlsx_crawl_data_export(setup_test_project_and_crawl):
    """Verify multi-sheet XLSX export containing all 16 sheets."""
    info = setup_test_project_and_crawl
    proj_id = str(info["project"].id)
    domain = info["domain"]
    crawl_id = info["crawl_id"]

    xlsx_bytes = CrawlTabExportService.export_crawl_data_xlsx(proj_id, domain, crawl_id)
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))

    expected_sheets = [
        "Internal", "Response Codes", "Page Titles", "Meta Descriptions",
        "H1", "H2", "Images", "Canonicals", "Directives", "Hreflang",
        "Structured Data", "Redirects", "Internal Links", "External Links",
        "Broken Links", "Issues"
    ]
    for sheet in expected_sheets:
        assert sheet in wb.sheetnames

    # Check Internal sheet content
    ws_internal = wb["Internal"]
    assert ws_internal.max_row == info["pages_count"] + 1  # 1 header + 6 data rows


def test_zip_export_includes_crawl_data_package(setup_test_project_and_crawl, db_session):
    """Verify complete-export.zip bundles crawl-data/ CSVs and SEO_Crawl_Data.xlsx."""
    info = setup_test_project_and_crawl
    proj = info["project"]
    domain = info["domain"]

    # Register crawl session in DB
    session = CrawlSession(
        project_id=proj.id,
        status="completed",
        pages_crawled=info["pages_count"],
        pages_discovered=info["pages_count"]
    )
    db_session.add(session)
    db_session.commit()

    zip_bytes = ZIPExportService.generate_complete_zip_export(
        project_name=proj.name,
        domain=proj.domain,
        url=proj.url,
        project_id=str(proj.id),
        metadata={"crawl_id": info["crawl_id"], "timestamp": "2026-09-09 12:00:00"},
        pages=[{"url": f"https://{domain}/", "status_code": 200, "title": "Home", "word_count": 500}],
        issues=[],
        opportunities=[]
    )

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        namelist = zf.namelist()
        # Verify existing exports are preserved
        assert any(n.endswith("Full_Website_Health_Report.xlsx") for n in namelist)
        assert any(n.endswith("README.txt") for n in namelist)
        assert any(n.endswith("Website_Health_Summary.csv") for n in namelist)
        
        # Verify new crawl-data/ directory files
        assert any(n.endswith("crawl-data/internal.csv") for n in namelist)
        assert any(n.endswith("crawl-data/response-codes.csv") for n in namelist)
        assert any(n.endswith("crawl-data/titles.csv") for n in namelist)
        assert any(n.endswith("crawl-data/meta-descriptions.csv") for n in namelist)
        assert any(n.endswith("crawl-data/h1.csv") for n in namelist)
        assert any(n.endswith("crawl-data/h2.csv") for n in namelist)
        assert any(n.endswith("crawl-data/images.csv") for n in namelist)
        assert any(n.endswith("crawl-data/canonicals.csv") for n in namelist)
        assert any(n.endswith("crawl-data/directives.csv") for n in namelist)
        assert any(n.endswith("crawl-data/hreflang.csv") for n in namelist)
        assert any(n.endswith("crawl-data/structured-data.csv") for n in namelist)
        assert any(n.endswith("crawl-data/redirects.csv") for n in namelist)
        assert any(n.endswith("crawl-data/internal-links.csv") for n in namelist)
        assert any(n.endswith("crawl-data/external-links.csv") for n in namelist)
        assert any(n.endswith("crawl-data/broken-links.csv") for n in namelist)
        assert any(n.endswith("crawl-data/issues.csv") for n in namelist)
        assert any(n.endswith("crawl-data/SEO_Crawl_Data.xlsx") for n in namelist)


def test_api_crawl_data_endpoints_authorization(client, setup_test_project_and_crawl):
    """Verify API endpoints require valid authorization and project membership."""
    info = setup_test_project_and_crawl
    proj = info["project"]

    # 1. Authorized user access
    auth_headers = {"X-User-ID": "frog_tester@example.com"}
    res = client.get(f"/api/projects/{proj.id}/crawl-data/internal", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["tab"] == "internal"
    assert data["total_rows"] == info["pages_count"]

    # 2. Unauthorized user access (not a project member)
    unauth_headers = {"X-User-ID": "intruder@example.com"}
    res_unauth = client.get(f"/api/projects/{proj.id}/crawl-data/internal", headers=unauth_headers)
    assert res_unauth.status_code in [401, 403, 404]

    # 3. CSV download endpoint
    csv_res = client.get(f"/api/projects/{proj.id}/crawl-data/internal/export.csv", headers=auth_headers)
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers.get("content-type", "")

    # 4. XLSX download endpoint
    xlsx_res = client.get(f"/api/projects/{proj.id}/crawl-data/export.xlsx", headers=auth_headers)
    assert xlsx_res.status_code == 200
    assert "spreadsheetml" in xlsx_res.headers.get("content-type", "")
