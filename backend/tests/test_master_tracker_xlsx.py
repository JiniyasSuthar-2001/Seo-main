import io
import os
import sys
import unittest
import uuid
import openpyxl
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.services.reports.xlsx_service import XLSXExportService


class TestMasterTrackerXLSX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_email = f"lead_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="Master SEO Lead")
        cls.db.add(cls.user)

        # 1. Project with simulated crawl & business context
        cls.proj_a = Project(
            id=str(uuid.uuid4()),
            name="iHriday Hub Solar",
            domain="ihriday.com",
            url="https://ihriday.com",
            description="Commercial & Residential Solar Energy Contractor",
            industry="Solar & Electrical Engineering",
            services="Commercial Solar, Battery Storage, EV Charging",
            service_areas="Sydney, Newcastle, Central Coast, Wollongong"
        )
        cls.db.add(cls.proj_a)

        cls.mem_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_email,
            project_id=cls.proj_a.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_a)

        # 2. Uncrawled Project
        cls.proj_uncrawled = Project(
            id=str(uuid.uuid4()),
            name="Fresh Brand Inc",
            domain="freshbrand.com",
            url="https://freshbrand.com",
            description="Brand New Uncrawled Website"
        )
        cls.db.add(cls.proj_uncrawled)

        cls.mem_un = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_email,
            project_id=cls.proj_uncrawled.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_un)

        cls.db.commit()

        cls.token = create_access_token(user_id=cls.user_email)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.user_id == cls.user_email).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id.in_([cls.proj_a.id, cls.proj_uncrawled.id])).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id == cls.user_email).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_master_xlsx_structure_and_sheet_order(self):
        """Verify Master XLSX contains all 11 required sheets in exact specified order."""
        sample_pages = [
            {"url": "https://ihriday.com/", "title": "iHriday Solar | Commercial & Residential Solar", "status_code": 200, "word_count": 850, "meta_description": "Premier solar installation and battery storage.", "h1": "Solar Energy Solutions", "internal_links": ["https://ihriday.com/services/solar"]},
            {"url": "https://ihriday.com/services/solar", "title": "Commercial Solar Power Systems", "status_code": 200, "word_count": 1200, "meta_description": "High-efficiency commercial solar panels.", "h1": "Commercial Solar Power", "internal_links": ["https://ihriday.com/locations/sydney"]},
            {"url": "https://ihriday.com/locations/sydney", "title": "Sydney Solar Installers", "status_code": 200, "word_count": 950, "meta_description": "Certified solar panel installers across Sydney NSW.", "h1": "Solar Installers Sydney", "internal_links": []},
            {"url": "https://ihriday.com/broken-page", "title": "404 Not Found", "status_code": 404, "word_count": 50, "meta_description": "", "h1": "Page Not Found", "internal_links": []}
        ]
        sample_issues = [
            {"problem": "Broken Link 404", "severity": "Critical", "category": "Technical", "affected_url": "https://ihriday.com/broken-page", "what_was_found": "HTTP 404 response", "ai_solution": "Restore valid page content or implement 301 redirect."},
            {"problem": "Missing Meta Description", "severity": "High", "category": "On-Page", "affected_url": "https://ihriday.com/broken-page", "what_was_found": "Missing meta description", "ai_solution": "Add unique description tailored to page topic."}
        ]
        sample_keywords = [
            {"keyword": "commercial solar sydney", "target_url": "https://ihriday.com/services/solar", "frequency": 8},
            {"keyword": "battery storage systems", "target_url": "https://ihriday.com/services/solar", "frequency": 5}
        ]

        xlsx_bytes = XLSXExportService.generate_full_project_xlsx(
            project_name="iHriday Hub Solar",
            project_url="https://ihriday.com",
            pages=sample_pages,
            issues=sample_issues,
            keywords=sample_keywords,
            ai_insights={"health_score": 85}
        )

        self.assertIsInstance(xlsx_bytes, bytes)
        self.assertGreater(len(xlsx_bytes), 1000)

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
        sheet_names = wb.sheetnames

        expected_sheets = [
            "📊 Dashboard",
            "🔧 Technical SEO",
            "📝 On-Page SEO",
            "📍 Local SEO",
            "🔗 Content & Links",
            "📈 Keywords",
            "🤖 AEO",
            "🌐 GEO",
            "🔍 AI Citations",
            "📈 Keyword Research",
            "📅 Monthly Review"
        ]

        self.assertEqual(sheet_names, expected_sheets)

    def test_02_dashboard_formulas_and_kpis(self):
        """Verify dashboard formulas reference corresponding sheets without broken refs."""
        xlsx_bytes = XLSXExportService.generate_full_project_xlsx(
            project_name="iHriday Hub Solar",
            project_url="https://ihriday.com",
            pages=[{"url": "https://ihriday.com", "title": "Home", "status_code": 200}],
            issues=[],
            keywords=[{"keyword": "solar energy", "target_url": "https://ihriday.com"}],
            ai_insights={"health_score": 92}
        )

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        ws_dash = wb["📊 Dashboard"]

        # Verify Title Banner
        self.assertIn("iHriday Hub Solar", str(ws_dash["A1"].value))
        self.assertEqual(ws_dash["A1"].font.name, "Arial")

        # Verify formulas in KPI Summary rows
        cell_c13 = str(ws_dash["C13"].value) # Tech SEO Done
        self.assertIn("COUNTIF", cell_c13)
        self.assertIn("🔧 Technical SEO", cell_c13)

        cell_c14 = str(ws_dash["C14"].value) # On-Page SEO Done
        self.assertIn("COUNTIF", cell_c14)
        self.assertIn("📝 On-Page SEO", cell_c14)

        cell_c15 = str(ws_dash["C15"].value) # Local SEO Done
        self.assertIn("COUNTIF", cell_c15)
        self.assertIn("📍 Local SEO", cell_c15)

        cell_c16 = str(ws_dash["C16"].value) # Content & Links Done
        self.assertIn("COUNTIF", cell_c16)
        self.assertIn("🔗 Content & Links", cell_c16)

    def test_03_uncrawled_health_score_not_yet_scored(self):
        """Verify uncrawled project displays 'Not yet scored' and NEVER 0 or 100 fake score."""
        xlsx_bytes = XLSXExportService.generate_full_project_xlsx(
            project_name="Fresh Brand Inc",
            project_url="https://freshbrand.com",
            pages=[],
            issues=[],
            keywords=[],
            ai_insights={}
        )

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        ws_dash = wb["📊 Dashboard"]

        # Health score cell is E9
        health_val = str(ws_dash["E9"].value)
        self.assertEqual(health_val, "Not yet scored")

    def test_04_data_validations_and_dropdowns(self):
        """Verify DataValidation dropdowns exist on status and priority columns."""
        xlsx_bytes = XLSXExportService.generate_full_project_xlsx(
            project_name="iHriday Hub Solar",
            project_url="https://ihriday.com",
            pages=[{"url": "https://ihriday.com", "title": "Home", "status_code": 200}],
            issues=[{"problem": "Sample", "severity": "High", "category": "Technical", "affected_url": "https://ihriday.com"}],
            keywords=[{"keyword": "solar", "target_url": "https://ihriday.com"}]
        )

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes))
        ws_tech = wb["🔧 Technical SEO"]
        self.assertGreater(len(ws_tech.data_validations.dataValidation), 0)

        ws_onpage = wb["📝 On-Page SEO"]
        self.assertGreater(len(ws_onpage.data_validations.dataValidation), 0)

        ws_local = wb["📍 Local SEO"]
        self.assertGreater(len(ws_local.data_validations.dataValidation), 0)

    def test_05_monthly_review_growth_formulas(self):
        """Verify Monthly Review sheet has 12 prepopulated months and valid growth formulas."""
        xlsx_bytes = XLSXExportService.generate_full_project_xlsx(
            project_name="iHriday Hub Solar",
            project_url="https://ihriday.com",
            pages=[{"url": "https://ihriday.com", "title": "Home", "status_code": 200}]
        )

        wb = openpyxl.load_workbook(io.BytesIO(xlsx_bytes), data_only=False)
        ws_month = wb["📅 Monthly Review"]

        # Check Month 1 baseline vs Month 2 formula
        self.assertEqual(ws_month["C3"].value, "Baseline")
        self.assertIn("ISNUMBER", str(ws_month["C4"].value))
        self.assertIn("(B4-B3)/B3", str(ws_month["C4"].value))

    def test_06_page_specific_exports_contain_only_specific_data(self):
        """Verify page-specific XLSX generators produce single-sheet dedicated files."""
        # 1. Pages XLSX
        p_bytes = XLSXExportService.generate_pages_xlsx(pages=[{"url": "https://ihriday.com", "status_code": 200, "title": "Home"}])
        wb_p = openpyxl.load_workbook(io.BytesIO(p_bytes))
        self.assertEqual(len(wb_p.sheetnames), 1)
        self.assertEqual(wb_p.sheetnames[0], "Pages Inventory")

        # 2. Keywords XLSX
        k_bytes = XLSXExportService.generate_keywords_xlsx(keywords=[{"keyword": "solar energy", "frequency": 4}])
        wb_k = openpyxl.load_workbook(io.BytesIO(k_bytes))
        self.assertEqual(len(wb_k.sheetnames), 1)
        self.assertEqual(wb_k.sheetnames[0], "Keywords Dataset")

        # 3. Technical XLSX
        t_bytes = XLSXExportService.generate_technical_xlsx(issues=[{"problem": "404 Error", "severity": "Critical", "affected_url": "https://ihriday.com/404"}])
        wb_t = openpyxl.load_workbook(io.BytesIO(t_bytes))
        self.assertEqual(len(wb_t.sheetnames), 1)
        self.assertEqual(wb_t.sheetnames[0], "Technical Issues")

        # 4. Backlinks XLSX
        b_bytes = XLSXExportService.generate_backlinks_xlsx(backlinks=[{"source_url": "https://blog.com", "target_url": "https://ihriday.com", "anchor_text": "Solar Company"}])
        wb_b = openpyxl.load_workbook(io.BytesIO(b_bytes))
        self.assertEqual(len(wb_b.sheetnames), 1)
        self.assertEqual(wb_b.sheetnames[0], "Backlinks Dataset")

    def test_07_endpoint_export_xlsx(self):
        """Verify API GET /api/projects/{project_id}/export.xlsx returns valid master XLSX."""
        res = self.client.get(f"/api/projects/{self.proj_a.id}/export.xlsx", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        self.assertIn("attachment; filename=", res.headers["content-disposition"])

        wb = openpyxl.load_workbook(io.BytesIO(res.content))
        self.assertEqual(len(wb.sheetnames), 11)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id.in_([cls.proj_a.id, cls.proj_b.id])).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id.in_([cls.proj_a.id, cls.proj_b.id])).delete(synchronize_session=False)
            cls.db.query(User).filter((User.id == cls.user_email) | (User.email == cls.user_email)).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

if __name__ == '__main__':
    unittest.main()
