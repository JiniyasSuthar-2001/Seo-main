import os
import sys
import uuid
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
from app.models.crawl_session import CrawlSession
from app.config.auth import create_access_token
from app.crawler.crawler import SEOCrawler

class TestCrawlCancellationAndAISolution(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user_email = "user_cancel_ai@example.com"

        user = self.db.query(User).filter(User.email == self.user_email).first()
        if not user:
            user = User(id="usr_cancel_ai", email=self.user_email, name="Cancel AI User")
            self.db.add(user)
            self.db.commit()

        self.proj_id = "proj_cancel_ai_999"
        proj = self.db.query(Project).filter(Project.id == self.proj_id).first()
        if not proj:
            proj = Project(id=self.proj_id, name="Cancel AI Project", url="https://cancelaiexample.com")
            self.db.add(proj)
            self.db.commit()

        mem = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_email,
            ProjectMembership.project_id == self.proj_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_cancel_ai", user_id=self.user_email, project_id=self.proj_id, role="OWNER", status="ACTIVE")
            self.db.add(mem)
            self.db.commit()

        token = create_access_token(user_id=self.user_email)
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.db.close()

    def test_1_cancel_crawl_session_endpoint(self):
        """Test POST /api/projects/{project_id}/crawl/{session_id}/cancel sets session status to cancelling."""
        sess_id = f"sess_cancel_test_{uuid.uuid4().hex[:8]}"
        session = CrawlSession(
            id=sess_id,
            project_id=self.proj_id,
            status="running",
            pages_crawled=5,
            pages_discovered=20
        )
        self.db.add(session)
        self.db.commit()

        res = self.client.post(f"/api/projects/{self.proj_id}/crawl/{sess_id}/cancel", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "cancelling")

        db_sess = self.db.query(CrawlSession).filter(CrawlSession.id == sess_id).first()
        self.assertEqual(db_sess.status, "cancelling")

    def test_2_seo_crawler_cancellation_check(self):
        """Test SEOCrawler loop halts when cancellation_checker returns True."""
        cancelled = False
        def check_cancelled():
            nonlocal cancelled
            return cancelled

        crawler = SEOCrawler(
            start_url="https://cancelaiexample.com",
            max_pages=50,
            cancellation_checker=check_cancelled
        )
        
        # Simulate cancellation active
        cancelled = True
        results = asyncio.run(crawler.start())

        self.assertEqual(results["status"], "cancelled")
        self.assertTrue(crawler.is_cancelled)

    def test_3_ai_problem_solution_endpoint(self):
        """Test POST /api/projects/{project_id}/ai/problem-solution returns structured evidence solution."""
        payload = {
            "rule_id": "LINK_002",
            "title": "HTTP 4xx / 5xx Broken Pages",
            "category": "Crawlability",
            "severity": "critical",
            "description": "1 audited page returned HTTP 404",
            "recommendation": "Fix broken page URLs or implement 301 redirects.",
            "affected_urls": ["https://cancelaiexample.com/broken-link"]
        }

        res = self.client.post(f"/api/projects/{self.proj_id}/ai/problem-solution", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("page_solutions", data)
        self.assertIn("https://cancelaiexample.com/broken-link", data["page_solutions"])
        self.assertIsNotNone(data.get("default_solution"))

if __name__ == "__main__":
    unittest.main()
