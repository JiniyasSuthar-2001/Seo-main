import unittest
import io
import zipfile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config.database import get_db, Base
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService, ZIPExportService

class TestFullMasterHealthReport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)
        cls.db = TestingSessionLocal()

        # Create user
        cls.user = User(
            id="usr_master_report_test",
            email="master_report@example.com",
            name="Report Master Tester"
        )
        cls.db.add(cls.user)

        # Create project
        cls.project = Project(
            id="proj_master_report_123",
            name="Queenshine Electricals",
            url="https://queenshine.com.au"
        )
        cls.db.add(cls.project)

        cls.membership = ProjectMembership(
            id="tm_master_report_123",
            user_id=cls.user.id,
            project_id=cls.project.id,
            role="owner"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

        token = create_access_token({"sub": cls.user.id})
        cls.headers = {"Authorization": f"Bearer {token}"}

    def test_01_master_pdf_generation(self):
        pdf_gen = PDFReportGenerator()
        metadata = {
            "website": "queenshine.com.au",
            "health_score": 87,
            "timestamp": "2026-08-29 16:00:00",
            "evaluated_rules_count": 14
        }
        pages = [
            {"url": "https://queenshine.com.au/", "status_code": 200, "title": "Queenshine Electricals", "word_count": 450, "meta_description": "Leading electrician in Sydney."},
            {"url": "https://queenshine.com.au/services", "status_code": 200, "title": "Services", "word_count": 210, "meta_description": ""}
        ]
        issues = [
            {"title": "Missing Meta Descriptions", "severity": "Warning", "affected_urls": ["https://queenshine.com.au/services"], "description": "1 page missing description.", "recommendation": "Add meta description."}
        ]

        pdf_bytes = pdf_gen.generate_full_project_pdf(
            project_name=self.project.name,
            project_url=self.project.domain,
            metadata=metadata,
            pages=pages,
            keywords=[],
            rankings=[],
            backlinks=[],
            internal_links=[],
            competitors=[],
            issues=issues,
            crawls=[]
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(len(pdf_bytes) > 500)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))

    def test_02_master_zip_package_generation(self):
        metadata = {"website": "queenshine.com.au", "health_score": 87, "timestamp": "2026-08-29 16:00:00"}
        pages = [{"url": "https://queenshine.com.au/", "status_code": 200, "title": "Home", "word_count": 300}]
        issues = [{"title": "Thin Content", "severity": "Warning", "affected_url": "https://queenshine.com.au/service-a", "description": "Low word count"}]
        pdf_bytes = b"%PDF-1.4 Mock PDF Content"

        zip_bytes = ZIPExportService.generate_complete_zip_export(
            project_name=self.project.name,
            domain=self.project.domain,
            url=self.project.url,
            metadata=metadata,
            pages=pages,
            keywords=[],
            rankings=[],
            inbound_backlinks=[],
            outbound_links=[],
            internal_links=[],
            competitors=[],
            issues=issues,
            opportunities=[],
            crawls=[],
            audit_pdf_bytes=pdf_bytes
        )

        self.assertIsInstance(zip_bytes, bytes)
        zip_file = zipfile.ZipFile(io.BytesIO(zip_bytes))
        file_list = zip_file.namelist()

        # Verify files inside zip
        self.assertTrue(any("Full_Website_Health_Report" in f and f.endswith(".pdf") for f in file_list))
        self.assertTrue(any("Website_Health_Summary.csv" in f for f in file_list))
        self.assertTrue(any("Problems_Found.csv" in f for f in file_list))
        self.assertTrue(any("Affected_Pages.csv" in f for f in file_list))
        self.assertTrue(any("AI_Solutions.csv" in f for f in file_list))
        self.assertTrue(any("Future_SEO_Improvements.csv" in f for f in file_list))
        self.assertTrue(any("README.txt" in f for f in file_list))

        # Inspect README content
        readme_path = [f for f in file_list if f.endswith("README.txt")][0]
        readme_content = zip_file.read(readme_path).decode("utf-8")
        self.assertIn("queenshine.com.au", readme_content)
        self.assertIn("FULL WEBSITE HEALTH", readme_content.upper())

    def test_03_csv_human_readable_headers(self):
        pages = [{"url": "https://example.com", "status_code": 200, "title": "Test"}]
        csv_out = CSVExportService.generate_pages_csv(pages)
        self.assertIn("Where This Data Came From", csv_out)
        self.assertIn("Can Search Engines Find This Page?", csv_out)

        issues = [{"title": "Broken Link", "severity": "Critical", "affected_url": "https://example.com/broken"}]
        tech_csv = CSVExportService.generate_technical_issues_csv(issues)
        self.assertIn("Where This Data Came From", tech_csv)
        self.assertIn("SEO Problems Found", tech_csv)

if __name__ == "__main__":
    unittest.main()
