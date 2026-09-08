import unittest
import uuid
import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.config.settings import settings
from app.services.crawl_storage import CrawlStorage


class TestInternalLinksCSVSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_email = f"csv_sec_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="CSV Section Tester")
        cls.db.add(cls.user)
        cls.db.commit()

        cls.token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        # Project 1: Populated crawl data
        cls.project = Project(
            id=str(uuid.uuid4()),
            name="Section CSV Test Project",
            url="https://csv-section-test.com",
            domain="csv-section-test.com"
        )
        cls.db.add(cls.project)
        cls.db.commit()

        cls.membership = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user.id,
            project_id=cls.project.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

        # Project 2: Empty crawl data
        cls.empty_project = Project(
            id=str(uuid.uuid4()),
            name="Empty CSV Project",
            url="https://empty-csv-test.com",
            domain="empty-csv-test.com"
        )
        cls.db.add(cls.empty_project)
        cls.db.commit()

        cls.empty_membership = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user.id,
            project_id=cls.empty_project.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.empty_membership)
        cls.db.commit()

        # Save snapshot with pages, internal links, external links, broken links
        storage = CrawlStorage()
        mock_results = {
            "status": "completed",
            "max_pages": 5000,
            "successful_pages_count": 3,
            "failed_pages_count": 0,
            "pages": [
                {"url": f"https://{cls.project.domain}/", "status_code": 200, "is_success": True, "title": "Home Page", "h1": "Welcome"},
                {"url": f"https://{cls.project.domain}/about", "status_code": 200, "is_success": True, "title": "About Us", "h1": "About"},
                {"url": f"https://{cls.project.domain}/orphan", "status_code": 200, "is_success": True, "title": "Orphan Page", "h1": "Orphan"}
            ],
            "issues": [],
            "internal_links": [
                {"source": f"https://{cls.project.domain}/", "target": f"https://{cls.project.domain}/about", "anchor_text": "Read About Us", "rel": ""},
                {"source": f"https://{cls.project.domain}/", "target": f"https://{cls.project.domain}/about", "anchor_text": "About Link 2", "rel": ""}
            ],
            "external_links": [
                {"source": f"https://{cls.project.domain}/", "target": "https://external.com/dead", "anchor_text": "Dead Outbound", "rel": ""}
            ],
            "broken_links": [
                {
                    "source": f"https://{cls.project.domain}/",
                    "target": f"https://{cls.project.domain}/missing-page",
                    "anchor_text": "Missing Link",
                    "link_type": "internal",
                    "status_code": 404,
                    "is_broken": True,
                    "error": "HTTP 404 Not Found"
                },
                {
                    "source": f"https://{cls.project.domain}/",
                    "target": "https://external.com/dead",
                    "anchor_text": "Dead Outbound",
                    "link_type": "external",
                    "status_code": 500,
                    "is_broken": True,
                    "error": "HTTP 500 Internal Server Error"
                }
            ]
        }

        storage.save_crawl_snapshot(
            key=cls.project.domain,
            session_id="csv_test_sess_1",
            results=mock_results,
            domain=cls.project.domain,
            project_id=cls.project.id
        )

        # Empty snapshot for empty_project
        storage.save_crawl_snapshot(
            key=cls.empty_project.domain,
            session_id="csv_empty_sess_1",
            results={
                "status": "completed",
                "max_pages": 5000,
                "pages": [],
                "issues": [],
                "internal_links": [],
                "external_links": [],
                "broken_links": []
            },
            domain=cls.empty_project.domain,
            project_id=cls.empty_project.id
        )

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_default_export_returns_graph_csv_backward_compatibility(self):
        """GET /export.csv without section query defaults to graph/internal-links CSV."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("content-type"), "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", res.headers.get("content-disposition", ""))
        self.assertIn("internal-links", res.headers.get("content-disposition", ""))
        self.assertIn("Source Page URL,Destination Page URL,Anchor Text,HTTP Status Code,Where This Data Came From", res.text)
        self.assertIn("Read About Us", res.text)

    def test_02_explicit_graph_section_export(self):
        """GET /export.csv?section=graph returns internal links graph CSV."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv?section=graph", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("internal-links", res.headers.get("content-disposition", ""))
        self.assertIn("Source Page URL,Destination Page URL,Anchor Text,HTTP Status Code", res.text)
        self.assertIn("Read About Us", res.text)

    def test_03_orphans_section_export(self):
        """GET /export.csv?section=orphans returns orphan pages CSV."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv?section=orphans", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("orphan-pages", res.headers.get("content-disposition", ""))
        self.assertIn("Page URL,Link Status,Recommended Action", res.text)
        self.assertIn(f"https://{self.project.domain}/orphan", res.text)
        self.assertIn("0 Links Pointing to This Page", res.text)

    def test_04_anchors_section_export(self):
        """GET /export.csv?section=anchors returns link text frequency CSV."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv?section=anchors", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("link-text", res.headers.get("content-disposition", ""))
        self.assertIn("Link Text,Times Used", res.text)
        self.assertIn("Read About Us", res.text)

    def test_05_opportunities_section_export(self):
        """GET /export.csv?section=opportunities returns link opportunities CSV."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv?section=opportunities", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("suggested-links", res.headers.get("content-disposition", ""))
        self.assertIn("Source Page,Target Page,Suggested Link Text,Reason,Priority", res.text)
        self.assertIn(f"https://{self.project.domain}/orphan", res.text)

    def test_06_broken_section_export(self):
        """GET /export.csv?section=broken returns broken links CSV."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv?section=broken", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertIn("broken-links", res.headers.get("content-disposition", ""))
        self.assertIn("Source Page,Broken URL,Link Type,Status Code,Link Text,Error", res.text)
        self.assertIn("https://external.com/dead", res.text)
        self.assertIn(f"https://{self.project.domain}/missing-page", res.text)

    def test_07_invalid_section_returns_400_bad_request(self):
        """GET /export.csv?section=invalid_section returns 400 Bad Request."""
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/export.csv?section=invalid_section", headers=self.headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid section", res.json().get("detail", ""))

    def test_08_empty_datasets_return_headers_without_error(self):
        """All sections must safely export valid CSV with headers when dataset is empty (no 500 error)."""
        sections = ["graph", "orphans", "anchors", "opportunities", "broken"]
        expected_headers = {
            "graph": "Source Page URL,Destination Page URL,Anchor Text",
            "orphans": "Page URL,Link Status,Recommended Action",
            "anchors": "Link Text,Times Used",
            "opportunities": "Source Page,Target Page,Suggested Link Text",
            "broken": "Source Page,Broken URL,Link Type,Status Code"
        }

        for sec in sections:
            res = self.client.get(f"/api/projects/{self.empty_project.id}/internal-links/export.csv?section={sec}", headers=self.headers)
            self.assertEqual(res.status_code, 200, f"Section {sec} failed on empty dataset")
            self.assertIn(expected_headers[sec], res.text, f"Header mismatch on empty section {sec}")


if __name__ == '__main__':
    unittest.main()
