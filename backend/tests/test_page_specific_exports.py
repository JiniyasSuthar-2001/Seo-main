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

import app.models as _models_registry

from app.config.database import get_db, Base, engine, SessionLocal

class TestPageSpecificExports(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.client = TestClient(app)

        import uuid
        uid = uuid.uuid4().hex[:6]
        user_email = f"page_export_{uid}@example.com"
        cls.user = User(id=user_email, email=user_email, name="Page Export Tester")
        cls.db.add(cls.user)
        cls.db.commit()

        cls.project = Project(
            id=f"proj_page_export_{uid}",
            name="Queenshine Electricals",
            domain=f"queenshine_{uid}.com.au",
            url=f"https://queenshine_{uid}.com.au"
        )
        cls.db.add(cls.project)
        cls.db.commit()

        cls.membership = ProjectMembership(
            id=f"tm_page_export_{uid}",
            user_id=cls.user.id,
            project_id=cls.project.id,
            role="owner"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

        from app.services.crawl_storage import CrawlStorage
        storage = CrawlStorage()
        results = {"pages": [{"url": f"https://queenshine_{uid}.com.au", "status_code": 200, "title": "Home", "word_count": 300}], "issues": [], "internal_links": [], "external_links": []}
        storage.save_crawl_snapshot(key=f"queenshine_{uid}.com.au", session_id=f"sess_export_{uid}", results=results, domain=f"queenshine_{uid}.com.au", project_id=cls.project.id)

        token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {token}"}

    def test_01_keywords_export_contains_only_keywords(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/keywords/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.text

        # Must contain keyword headers
        self.assertIn("Search Term / Keyword", csv_text)
        self.assertIn("Where This Data Came From", csv_text)

        # Must NOT contain technical audit headers
        self.assertNotIn("SEO Problems Found", csv_text)
        self.assertNotIn("Inbound Backlinks", csv_text)
        self.assertNotIn("Competitor Name", csv_text)

    def test_02_pages_export_contains_only_pages(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/pages/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.text

        # Must contain page inventory headers
        self.assertIn("URL,Status Code", csv_text)
        self.assertIn("Can Search Engines Find This Page?", csv_text)

        # Must NOT contain competitor or ranking headers
        self.assertNotIn("Competitor Name", csv_text)
        self.assertNotIn("Google Position", csv_text)

    def test_03_technical_export_contains_only_technical_findings(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/technical/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        csv_text = resp.text

        # Must contain technical audit headers
        self.assertIn("SEO Problems Found", csv_text)
        self.assertIn("What Was Found / Evidence", csv_text)

        # Must NOT contain keyword rankings headers
        self.assertNotIn("Content Frequency", csv_text)
        self.assertNotIn("Competitor Name", csv_text)

    def test_04_master_report_combines_all_applicable_datasets(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/report.pdf", headers=self.headers)
        self.assertEqual(resp.status_code, 200, f"Failed with response: {resp.text}")
        self.assertEqual(resp.headers.get("content-type"), "application/pdf")
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("Full_Website_Health_Report", disp)

    def test_05_master_xlsx_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/export.xlsx", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("SEO_Master_Export", disp)

    def test_06_master_pptx_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/export.pptx", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.presentationml.presentation")
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("SEO_Executive_Presentation", disp)

    def test_07_page_specific_xlsx_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/pages/export.xlsx", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.headers.get("content-type"), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.project.id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.project.id).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id == cls.user.id).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

if __name__ == "__main__":
    unittest.main()
