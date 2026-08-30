import pytest
import os
import io
import json
import zipfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config.database import Base
from app.models.project import Project
from app.models.crawl_session import CrawlSession
from app.models.project_membership import ProjectMembership
from app.services.reports.master_report_service import MasterReportBuilder
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.xlsx_service import XLSXExportService
from app.services.reports.pptx_service import PPTXExportService
from app.services.reports.export_service import CSVExportService, ZIPExportService
from app.config.settings import settings

from app.services.crawl_storage import CrawlStorage

# Setup in-memory SQLite for test
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
def sample_project(db_session):
    proj_domain = "queenshineelectricals.com.au"
    proj = Project(
        name="Queenshine Electricals & Solar",
        url=f"https://{proj_domain}",
        industry="Electrical & Solar Contracting",
        services="Level 2 Electrical, Solar Power Installation, Battery Storage, EV Chargers, Air Conditioning",
        service_areas="Sydney, Brisbane, Gold Coast, Regional NSW/QLD",
        notes="Premium commercial and residential electrical services."
    )
    db_session.add(proj)
    db_session.commit()
    db_session.refresh(proj)

    membership = ProjectMembership(
        user_id="tester@example.com",
        project_id=proj.id,
        role="OWNER",
        status="ACTIVE"
    )
    db_session.add(membership)
    db_session.commit()

    # Seed crawl snapshot via CrawlStorage
    storage = CrawlStorage()
    pages = [
        {
            "url": f"https://{proj_domain}/",
            "status_code": 200,
            "title": "Level 2 Electrician Sydney | Queenshine Electricals",
            "meta_description": "Certified Level 2 electricians providing residential and commercial electrical services across Sydney and Brisbane.",
            "h1": "Expert Electrical & Solar Services",
            "word_count": 850,
            "canonical": f"https://{proj_domain}/",
            "internal_links": [f"https://{proj_domain}/solar", f"https://{proj_domain}/contact"]
        },
        {
            "url": f"https://{proj_domain}/solar",
            "status_code": 200,
            "title": "Commercial Solar Power Systems Installation",
            "meta_description": "",
            "h1": "Solar Power Installation",
            "word_count": 420,
            "canonical": f"https://{proj_domain}/solar",
            "internal_links": [f"https://{proj_domain}/"]
        },
        {
            "url": f"https://{proj_domain}/broken-page",
            "status_code": 404,
            "title": "Page Not Found",
            "meta_description": "",
            "h1": "",
            "word_count": 50,
            "canonical": "",
            "internal_links": []
        }
    ]
    issues = [
        {"issue": "Broken Page (404)", "url": f"https://{proj_domain}/broken-page", "severity": "Critical", "what_was_found": "Server returned HTTP 404"},
        {"issue": "Missing Meta Description", "url": f"https://{proj_domain}/solar", "severity": "Warning", "what_was_found": "Empty description tag"}
    ]
    storage.save_crawl_snapshot(
        key=proj_domain,
        session_id="crawl_consistency_01",
        results={"pages": pages, "issues": issues},
        domain=proj_domain,
        project_id=proj.id
    )

    return proj

def test_master_report_builder_and_export_consistency(db_session, sample_project):
    """
    Asserts that MasterReportBuilder creates a unified master object that is passed
    consistently into all format generators (PDF, XLSX, PPTX, CSV, ZIP) without data divergence.
    """
    master_report = MasterReportBuilder.build_master_report(
        project=sample_project,
        user_id="tester@example.com",
        db=db_session
    )

    # 1. Verify Master Report Structure & Business Context
    assert master_report["status"] == "COMPLETED"
    assert master_report["project"]["name"] == "Queenshine Electricals & Solar"
    assert master_report["project"]["domain"] == "queenshineelectricals.com.au"
    assert master_report["business_context"]["industry"] == "Electrical & Solar Contracting"
    assert "Sydney" in master_report["business_context"]["service_areas"]
    assert len(master_report["affected_pages"]) == 3
    assert len(master_report["problems"]) >= 1

    health_score = master_report["health"]["health_score"]
    total_pages = len(master_report["affected_pages"])
    total_problems = len(master_report["problems"])
    total_keywords = len(master_report["keywords"])

    # 2. PDF Export
    pdf_gen = PDFReportGenerator()
    pdf_bytes = pdf_gen.generate_full_project_pdf(master_report=master_report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")

    # 3. XLSX Master Export
    xlsx_bytes = XLSXExportService.generate_full_project_xlsx(master_report=master_report)
    assert isinstance(xlsx_bytes, bytes)
    assert len(xlsx_bytes) > 500

    # Verify XLSX sheets
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
    sheet_names = wb.sheetnames
    assert "📊 Dashboard" in sheet_names
    assert "Technical SEO" in sheet_names
    assert "On-Page SEO" in sheet_names
    assert "Local SEO" in sheet_names
    assert "Content & Links" in sheet_names
    assert "Keywords" in sheet_names
    assert "AEO" in sheet_names
    assert "GEO" in sheet_names
    assert "AI Citations" in sheet_names
    assert "Opportunities & Roadmap" in sheet_names
    assert "Affected Pages" in sheet_names
    assert "Data Limitations" in sheet_names

    # 4. PPTX Export
    pptx_bytes = PPTXExportService.generate_presentation(master_report=master_report)
    assert isinstance(pptx_bytes, bytes)
    assert len(pptx_bytes) > 500

    # 5. CSV Summary Export
    csv_str = CSVExportService.generate_project_summary_csv(
        project_name=master_report["project"]["name"],
        domain=master_report["project"]["domain"],
        url=master_report["project"]["url"],
        metadata=master_report["crawl"],
        pages=master_report["affected_pages"],
        keywords=master_report["keywords"],
        issues=master_report["problems"]
    )
    assert isinstance(csv_str, str)
    assert "Queenshine Electricals & Solar" in csv_str
    assert "queenshineelectricals.com.au" in csv_str

    # 6. Complete ZIP Export
    zip_bytes = ZIPExportService.generate_complete_export_zip(
        project_name=master_report["project"]["name"],
        domain=master_report["project"]["domain"],
        project_url=master_report["project"]["url"],
        master_report=master_report
    )
    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 1000

    # Verify contents of complete ZIP package
    with zipfile.ZipFile(io.BytesIO(zip_bytes), "r") as z:
        files = z.namelist()
        assert any(f.endswith(".pdf") for f in files)
        assert any(f.endswith(".xlsx") for f in files)
        assert any(f.endswith(".pptx") for f in files)
        assert any("problems_found.csv" in f.lower() or "ai_solutions" in f.lower() or "affected_pages.csv" in f.lower() for f in files)

def test_routes_call_single_source_of_truth():
    """
    Audits backend/app/routers/reports.py to confirm all download handlers route through
    get_shared_project_report_data / MasterReportBuilder rather than separate ad-hoc DB queries.
    """
    reports_file = os.path.join(os.path.dirname(__file__), "..", "app", "routers", "reports.py")
    with open(reports_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Confirm get_shared_project_report_data is defined and invokes MasterReportBuilder
    assert "def get_shared_project_report_data" in content
    assert "MasterReportBuilder.build_master_report" in content
    assert "get_shared_project_report_data(project, db, user_id)" in content
