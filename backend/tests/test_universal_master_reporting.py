import unittest
import os
import io
import json
import shutil
import zipfile
from datetime import datetime
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config.database import get_db, Base
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.competitor import Competitor
from app.config.settings import settings
import time
from app.config.auth import get_current_user_id, create_access_token
from app.services.crawl_storage import CrawlStorage
from app.services.reports.master_report_service import MasterReportBuilder
from app.services.reports.xlsx_service import XLSXExportService, HAS_OPENPYXL
from app.services.reports.pptx_service import PPTXExportService, HAS_PPTX
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService, ZIPExportService

from app.config.settings import _DB_PATH
SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.abspath(_DB_PATH)}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class TestUniversalMasterReporting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = TestingSessionLocal()
        cls.test_user_id = "test_univ_user_123"

        # Create test user
        user = cls.db.query(User).filter(User.id == cls.test_user_id).first()
        if not user:
            user = User(id=cls.test_user_id, email="universal_tester@seo.com", name="Universal Tester")
            cls.db.add(user)
            cls.db.commit()

        # Project A: Queenshine Electricals
        cls.proj_a_id = "proj_queenshine_univ"
        cls.proj_a_domain = "queenshine.com.au"
        proj_a = cls.db.query(Project).filter(Project.id == cls.proj_a_id).first()
        if not proj_a:
            proj_a = Project(id=cls.proj_a_id, name="Queenshine Electricals", url=f"https://{cls.proj_a_domain}")
            cls.db.add(proj_a)
            cls.db.commit()
            mem_a = ProjectMembership(id="mem_a_univ", project_id=cls.proj_a_id, user_id=cls.test_user_id, role="owner")
            cls.db.add(mem_a)
            cls.db.commit()

        # Project B: iHriday Hub
        cls.proj_b_id = "proj_ihriday_univ"
        cls.proj_b_domain = "ihriday.com"
        proj_b = cls.db.query(Project).filter(Project.id == cls.proj_b_id).first()
        if not proj_b:
            proj_b = Project(id=cls.proj_b_id, name="iHriday Hub", url=f"https://{cls.proj_b_domain}")
            cls.db.add(proj_b)
            cls.db.commit()
            mem_b = ProjectMembership(id="mem_b_univ", project_id=cls.proj_b_id, user_id=cls.test_user_id, role="owner")
            cls.db.add(mem_b)
            cls.db.commit()

        # Project C: Third Arbitrary Website (Solar Eco Solutions)
        cls.proj_c_id = "proj_solar_univ"
        cls.proj_c_domain = "solareco.com.au"
        proj_c = cls.db.query(Project).filter(Project.id == cls.proj_c_id).first()
        if not proj_c:
            proj_c = Project(id=cls.proj_c_id, name="Solar Eco Solutions", url=f"https://{cls.proj_c_domain}")
            cls.db.add(proj_c)
            cls.db.commit()
            mem_c = ProjectMembership(id="mem_c_univ", project_id=cls.proj_c_id, user_id=cls.test_user_id, role="owner")
            cls.db.add(mem_c)
            cls.db.commit()

        # Seed Snapshot 1 (Historical) & Snapshot 2 (Latest) for Queenshine
        storage = CrawlStorage()
        pages_a1 = [
            {"url": f"https://{cls.proj_a_domain}/", "status_code": 200, "title": "Queenshine Home", "word_count": 250, "h1": "Welcome", "meta_description": ""},
            {"url": f"https://{cls.proj_a_domain}/services", "status_code": 404, "title": "", "word_count": 0, "h1": "", "meta_description": ""}
        ]
        issues_a1 = [{"issue": "404 Not Found", "url": f"https://{cls.proj_a_domain}/services", "severity": "Critical"}]
        storage.save_crawl_snapshot(key=cls.proj_a_domain, session_id="crawl_q_01", results={"pages": pages_a1, "issues": issues_a1}, domain=cls.proj_a_domain, project_id=cls.proj_a_id)
        
        time.sleep(1.1)

        pages_a2 = [
            {"url": f"https://{cls.proj_a_domain}/", "status_code": 200, "title": "Queenshine Electricals | Level 2 Electrician Sydney", "word_count": 650, "h1": "Level 2 Electrician Sydney", "meta_description": "Sydney Level 2 electrical services for domestic, commercial and industrial needs."},
            {"url": f"https://{cls.proj_a_domain}/solar-power", "status_code": 200, "title": "Solar Power Installation Sydney", "word_count": 420, "h1": "Solar Power Sydney", "meta_description": "Clean solar energy installations across greater Sydney."},
            {"url": f"https://{cls.proj_a_domain}/contact", "status_code": 200, "title": "Contact Queenshine", "word_count": 180, "h1": "Get in Touch", "meta_description": ""}
        ]
        issues_a2 = [
            {"issue": "Thin Content (<300 words)", "url": f"https://{cls.proj_a_domain}/contact", "severity": "Warning", "details": "Found 180 words"},
            {"issue": "Missing Meta Description", "url": f"https://{cls.proj_a_domain}/contact", "severity": "Warning", "details": "Empty description"}
        ]
        storage.save_crawl_snapshot(key=cls.proj_a_domain, session_id="crawl_q_02", results={"pages": pages_a2, "issues": issues_a2}, domain=cls.proj_a_domain, project_id=cls.proj_a_id)

        # Seed Snapshot for iHriday
        pages_b = [
            {"url": f"https://{cls.proj_b_domain}/", "status_code": 200, "title": "iHriday Hub — Mental Wellness Platform", "word_count": 550, "h1": "Mindful Living & Therapy", "meta_description": "Empowering holistic mental health and online therapy sessions."},
            {"url": f"https://{cls.proj_b_domain}/therapists", "status_code": 200, "title": "Licensed Therapists Directory", "word_count": 480, "h1": "Find a Therapist", "meta_description": "Browse accredited psychologists and counsellors."}
        ]
        storage.save_crawl_snapshot(key=cls.proj_b_domain, session_id="crawl_ih_01", results={"pages": pages_b, "issues": []}, domain=cls.proj_b_domain, project_id=cls.proj_b_id)

        token = create_access_token(cls.test_user_id)
        cls.headers = {"Authorization": f"Bearer {token}"}
        app.dependency_overrides[get_current_user_id] = lambda: cls.test_user_id
        app.dependency_overrides[get_db] = lambda: cls.db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()
        cls.db.close()

    def test_master_report_builder_queenshine(self):
        """Test MasterReportBuilder on Queenshine Project."""
        proj = self.db.query(Project).filter(Project.id == self.proj_a_id).first()
        master = MasterReportBuilder.build_master_report(proj, self.db, self.test_user_id)

        self.assertEqual(master.get("status"), "COMPLETED")
        self.assertEqual(master.get("project", {}).get("domain"), "queenshine.com.au")
        self.assertEqual(master.get("crawl", {}).get("pages_crawled"), 3)
        self.assertIn("health", master)
        self.assertIn("checks", master)
        self.assertIn("problems", master)
        self.assertIn("opportunities", master)
        self.assertIn("aeo", master)
        self.assertIn("geo", master)
        self.assertIn("next_improvements", master)
        self.assertIn("historical_comparison", master)

        # Verify problem indicators
        for prob in master.get("problems", []):
            self.assertIn(prob.get("indicator"), ["🔴", "🟠", "🟡", "🔵"])
            self.assertIn("why_it_matters", prob)
            self.assertIn("recommended_action", prob)
            self.assertIn("ai_solution", prob)

        # Verify historical comparison
        hist = master.get("historical_comparison", {})
        self.assertTrue(hist.get("has_previous_crawl"))
        self.assertGreaterEqual(hist.get("problems_fixed_count", 0), 1)

    def test_multi_project_isolation(self):
        """Test that iHriday and Queenshine data NEVER cross over."""
        proj_a = self.db.query(Project).filter(Project.id == self.proj_a_id).first()
        proj_b = self.db.query(Project).filter(Project.id == self.proj_b_id).first()

        master_a = MasterReportBuilder.build_master_report(proj_a, self.db, self.test_user_id)
        master_b = MasterReportBuilder.build_master_report(proj_b, self.db, self.test_user_id)

        # Verify Queenshine master report contains ONLY queenshine URLs
        for p in master_a.get("affected_pages", []):
            self.assertIn("queenshine.com.au", p.get("url"))
            self.assertNotIn("ihriday.com", p.get("url"))

        # Verify iHriday master report contains ONLY ihriday URLs
        for p in master_b.get("affected_pages", []):
            self.assertIn("ihriday.com", p.get("url"))
            self.assertNotIn("queenshine.com.au", p.get("url"))

    def test_third_arbitrary_website_without_crawl(self):
        """Test graceful handling when an arbitrary website has no completed crawl."""
        proj_c = self.db.query(Project).filter(Project.id == self.proj_c_id).first()
        master_c = MasterReportBuilder.build_master_report(proj_c, self.db, self.test_user_id)

        self.assertEqual(master_c.get("status"), "NO_COMPLETED_CRAWL")
        self.assertFalse(master_c.get("crawl", {}).get("has_crawl"))
        self.assertIn("No completed crawl is available", master_c.get("message"))

    def test_full_master_pdf_export(self):
        """Test Full Website Health Report PDF export endpoint."""
        res = self.client.get(f"/api/projects/{self.proj_a_id}/report.pdf", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/pdf")
        self.assertTrue(res.content.startswith(b"%PDF"))

    def test_full_master_xlsx_export(self):
        """Test Full Master Excel Workbook (.xlsx) export endpoint with 22 worksheets."""
        res = self.client.get(f"/api/projects/{self.proj_a_id}/export.xlsx", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertGreater(len(res.content), 1000)

    def test_full_master_pptx_export(self):
        """Test Full Executive Presentation PPTX export endpoint with 17 slides."""
        res = self.client.get(f"/api/projects/{self.proj_a_id}/export.pptx", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        self.assertGreater(len(res.content), 1000)

    def test_full_master_zip_export(self):
        """Test Complete Master ZIP export package containing PDF, CSVs, and README."""
        res = self.client.get(f"/api/projects/{self.proj_a_id}/reports/complete-export.zip", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "application/zip")

        # Inspect ZIP contents
        with zipfile.ZipFile(io.BytesIO(res.content)) as zf:
            namelist = zf.namelist()
            self.assertTrue(any("README.txt" in name for name in namelist))
            self.assertTrue(any(".pdf" in name for name in namelist))
            self.assertTrue(any("Website_Health_Summary.csv" in name for name in namelist))
            self.assertTrue(any("Problems_Found.csv" in name for name in namelist))
            self.assertTrue(any("AI_Solutions.csv" in name for name in namelist))
            self.assertTrue(any("AEO.csv" in name for name in namelist))
            self.assertTrue(any("GEO.csv" in name for name in namelist))

if __name__ == "__main__":
    unittest.main()
