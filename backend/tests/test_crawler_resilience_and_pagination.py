import unittest
import uuid
import os
import json
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.config.settings import settings
from app.crawler.crawler import SEOCrawler

class TestCrawlerResilienceAndPagination(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_a_email = f"resil_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"resil_b_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="Resil User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="Resil User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)
        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(cls.user_b.id)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        cls.project = Project(
            id=str(uuid.uuid4()),
            name="Resilience Test Project",
            url="https://resilience-test.com",
            domain="resilience-test.com"
        )
        cls.db.add(cls.project)
        cls.db.commit()

        cls.membership = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_a.id,
            project_id=cls.project.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

        # Create mock dataset with 45 pages (35 crawled, 10 failed)
        cls.proj_dir = os.path.join(settings.CRAWL_DATA_DIR, cls.project.id)
        os.makedirs(cls.proj_dir, exist_ok=True)
        with open(os.path.join(cls.proj_dir, "latest.json"), "w") as f:
            json.dump({"path": cls.proj_dir, "crawl_id": "crawl_resil_1"}, f)

        mock_pages = []
        for i in range(1, 36):
            mock_pages.append({
                "url": f"https://resilience-test.com/page-{i}",
                "status_code": 200,
                "is_success": True,
                "fetch_status": "CRAWLED",
                "title": f"Page {i}",
                "word_count": 300
            })
        for i in range(36, 46):
            mock_pages.append({
                "url": f"https://resilience-test.com/broken-page-{i}",
                "status_code": 404,
                "is_success": False,
                "fetch_status": "FAILED",
                "error": "HTTP 404 Error",
                "word_count": 0
            })

        with open(os.path.join(cls.proj_dir, "pages.json"), "w") as f:
            json.dump(mock_pages, f)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_crawler_internal_broken_link_evaluation(self):
        crawler = SEOCrawler(start_url="https://resilience-test.com/")
        crawler.internal_links.append({
            "source": "https://resilience-test.com/services",
            "target": "https://resilience-test.com/dead-link",
            "anchor_text": "Dead Link"
        })

        # Evaluate failed internal page
        failed_record = {
            "url": "https://resilience-test.com/dead-link",
            "status_code": 404,
            "is_success": False,
            "fetch_status": "FAILED",
            "error": "HTTP 404 Not Found"
        }
        crawler.evaluate_page_issues(failed_record)

        broken_link_issues = [i for i in crawler.issues if i.get("issue_type") == "Internal Broken Link"]
        self.assertGreater(len(broken_link_issues), 0)
        self.assertEqual(broken_link_issues[0]["affected_url"], "https://resilience-test.com/dead-link")
        self.assertEqual(broken_link_issues[0]["source_url"], "https://resilience-test.com/services")

    def test_02_server_side_pagination_api(self):
        # Fetch Page 1 (limit 20, offset 0)
        res1 = self.client.get(f"/api/projects/{self.project.id}/pages?limit=20&offset=0", headers=self.headers_a)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertEqual(len(data1.get("items", [])), 20)
        self.assertEqual(data1.get("total"), 45)
        self.assertEqual(data1.get("pages_crawled"), 35)
        self.assertEqual(data1.get("pages_failed"), 10)

        # Fetch Page 2 (limit 20, offset 20)
        res2 = self.client.get(f"/api/projects/{self.project.id}/pages?limit=20&offset=20", headers=self.headers_a)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertEqual(len(data2.get("items", [])), 20)

        # Filter by status=failed
        res_failed = self.client.get(f"/api/projects/{self.project.id}/pages?limit=20&offset=0&status=failed", headers=self.headers_a)
        self.assertEqual(res_failed.status_code, 200)
        data_failed = res_failed.json()
        self.assertEqual(data_failed.get("total"), 10)
        self.assertEqual(len(data_failed.get("items", [])), 10)

    def test_03_tenant_isolation(self):
        # User B should be rejected (403 Forbidden)
        res = self.client.get(f"/api/projects/{self.project.id}/pages", headers=self.headers_b)
        self.assertEqual(res.status_code, 403)

if __name__ == '__main__':
    unittest.main()
