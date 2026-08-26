import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership

class TestExportSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.client = TestClient(app)

        cls.user = cls.db.query(User).filter(User.email == "export_test@example.com").first()
        if not cls.user:
            cls.user = User(
                id="test_export_user_id",
                email="export_test@example.com",
                name="Export Tester"
            )
            cls.db.add(cls.user)
            cls.db.commit()

        cls.project = cls.db.query(Project).filter((Project.id == "test_export_project_id") | (Project.domain == "queenshine.com.au")).first()
        if not cls.project:
            cls.project = Project(
                id="test_export_project_id",
                name="Queenshine Electrical",
                domain="queenshine.com.au"
            )
            cls.db.add(cls.project)
            cls.db.commit()

        cls.membership = cls.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == cls.project.id,
            ProjectMembership.user_id == cls.user.id
        ).first()
        if not cls.membership:
            cls.membership = ProjectMembership(
                id="test_export_membership_id",
                project_id=cls.project.id,
                user_id=cls.user.id,
                role="Owner"
            )
            cls.db.add(cls.membership)
            cls.db.commit()

        cls.headers = {"X-User-ID": cls.user.id}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_pages_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/pages/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("queenshine_com_au_pages_", disp)
        self.assertIn(".csv", disp)

    def test_02_pages_pdf_report(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/reports/pages", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/pdf", resp.headers.get("content-type"))
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("queenshine_com_au_pages_", disp)
        self.assertIn(".pdf", disp)

    def test_03_keywords_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/keywords/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("queenshine_com_au_keywords_", disp)

    def test_04_technical_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/technical/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("queenshine_com_au_technical-seo_", disp)

    def test_05_backlinks_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/backlinks/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("queenshine_com_au_outbound-links_", disp)

    def test_06_internal_links_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))

    def test_07_competitors_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/competitors/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))

    def test_08_opportunities_csv_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/opportunities/export.csv", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/csv", resp.headers.get("content-type"))

    def test_09_complete_zip_export(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/reports/complete-export.zip", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/zip", resp.headers.get("content-type"))
        disp = resp.headers.get("content-disposition", "")
        self.assertIn("queenshine_com_au_complete-seo-export_", disp)
        self.assertIn(".zip", disp)

    def test_10_report_history_logging(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/reports/history", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        history = resp.json()
        self.assertIsInstance(history, list)
        self.assertGreater(len(history), 0)
        self.assertIn("filename", history[0])
        self.assertIn("queenshine_com_au_", history[0]["filename"])

    def test_11_crawl_comparison(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/crawl/compare", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("comparison", data)
        self.assertEqual(data["domain"], "queenshine.com.au")

if __name__ == "__main__":
    unittest.main()
