import os
import sys
import unittest
import asyncio
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.crawler.crawler import SEOCrawler
from app.services.crawl_storage import CrawlStorage

class TestMaxPagesCeiling5000Plus(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.user_email = "user_max_pages_5000@example.com"

        user = cls.db.query(User).filter(User.email == cls.user_email).first()
        if not user:
            user = User(id=cls.user_email, email=cls.user_email, name="Max Pages User")
            cls.db.add(user)
            cls.db.commit()

        cls.proj_id = "proj_max_pages_5000_plus"
        proj = cls.db.query(Project).filter(Project.id == cls.proj_id).first()
        if not proj:
            proj = Project(id=cls.proj_id, name="5000 Plus Test Site", url="https://maxpages5000plus.com")
            cls.db.add(proj)
            cls.db.commit()

        mem = cls.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == cls.user_email,
            ProjectMembership.project_id == cls.proj_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_max_pages_5000", user_id=cls.user_email, project_id=cls.proj_id, role="OWNER", status="ACTIVE")
            cls.db.add(mem)
            cls.db.commit()

        token = create_access_token(user_id=cls.user_email)
        cls.headers = {"Authorization": f"Bearer {token}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.proj_id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.proj_id).delete(synchronize_session=False)
            cls.db.query(User).filter((User.id == cls.user_email) | (User.email == cls.user_email)).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

    def test_1_numeric_max_pages_ceiling_stops_at_limit(self):
        """Test numeric max_pages (e.g. 3) enforces a hard stopping limit."""
        crawler = SEOCrawler(
            start_url="https://maxpages5000plus.com",
            max_pages=3
        )
        self.assertEqual(crawler.max_pages, 3)
        self.assertFalse(crawler.is_unlimited_scope)

        # Pre-populate queue with 10 dummy URLs
        crawler.to_visit = [f"https://maxpages5000plus.com/page{i}" for i in range(10)]
        crawler.visited = set([f"https://maxpages5000plus.com/page{i}" for i in range(3)])

        # Loop condition should evaluate False because len(visited) == 3 >= max_pages (3)
        should_continue = crawler.to_visit and (crawler.is_unlimited_scope or len(crawler.visited) < crawler.max_pages)
        self.assertFalse(should_continue)

    def test_2_5000_plus_mode_enters_unlimited_scope(self):
        """Test max_pages='5000+' or 0 sets is_unlimited_scope=True and bypasses numeric stopping ceiling."""
        crawler = SEOCrawler(
            start_url="https://maxpages5000plus.com",
            max_pages="5000+"
        )
        self.assertTrue(crawler.is_unlimited_scope)

        # Pre-populate queue with 10 dummy URLs and 5 visited URLs
        crawler.to_visit = [f"https://maxpages5000plus.com/page{i}" for i in range(10)]
        crawler.visited = set([f"https://maxpages5000plus.com/page{i}" for i in range(5)])

        # Loop condition should evaluate True even though visited (5) > 0 because is_unlimited_scope is True
        should_continue = crawler.to_visit and (crawler.is_unlimited_scope or len(crawler.visited) < crawler.max_pages)
        self.assertTrue(should_continue)

    def test_3_crawl_config_api_persists_5000_plus_mode(self):
        """Test PATCH /api/projects/{project_id}/crawl-config accepts and persists max_pages='5000+'."""
        payload = {"max_pages": "5000+"}
        res = self.client.patch(f"/api/projects/{self.proj_id}/crawl-config", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["config"]["max_pages"], "5000+")

        get_res = self.client.get(f"/api/projects/{self.proj_id}/crawl-config", headers=self.headers)
        self.assertEqual(get_res.status_code, 200)
        get_data = get_res.json()
        self.assertEqual(get_data["config"]["max_pages"], "5000+")

    def test_4_storage_metadata_preserves_5000_plus_ceiling(self):
        """Test CrawlStorage writes max_pages_ceiling='5000+' to metadata.json."""
        storage = CrawlStorage()
        results = {
            "status": "completed",
            "max_pages": "5000+",
            "successful_pages_count": 12,
            "failed_pages_count": 0,
            "pages": [{"url": f"https://maxpages5000plus.com/p{i}", "status_code": 200} for i in range(12)],
            "issues": [],
            "internal_links": [],
            "external_links": []
        }
        crawl_dir = storage.save_crawl_snapshot(self.proj_id, "sess_5000_plus_test", results, domain="maxpages5000plus.com", project_id=self.proj_id)
        self.assertTrue(os.path.exists(crawl_dir))

        meta_path = os.path.join(crawl_dir, "metadata.json")
        self.assertTrue(os.path.exists(meta_path))

        import json
        with open(meta_path, "r") as f:
            meta = json.load(f)

        self.assertEqual(meta["max_pages_ceiling"], "5000+")
        self.assertEqual(meta["pages_crawled"], 12)

if __name__ == "__main__":
    unittest.main()
