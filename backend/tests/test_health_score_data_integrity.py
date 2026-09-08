import os
import sys
import json
import unittest
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
from app.services.audit_rules import evaluate_site_audit_rules
from app.config.utils import get_project_storage_dir
from app.config.settings import settings

class TestHealthScoreDataIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()
        cls.user_email = "user_health_integrity@example.com"

        # Create User
        user = cls.db.query(User).filter(User.email == cls.user_email).first()
        if not user:
            user = User(id=cls.user_email, email=cls.user_email, name="Health User")
            cls.db.add(user)
            cls.db.commit()

        # Create Project
        cls.proj_id = "proj_health_int_777"
        cls.domain = "healthtestsite.com"
        proj = cls.db.query(Project).filter(Project.id == cls.proj_id).first()
        if not proj:
            proj = Project(id=cls.proj_id, name="Health Test Site", url=f"https://{cls.domain}", domain=cls.domain)
            cls.db.add(proj)
            cls.db.commit()

        mem = cls.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == cls.user_email,
            ProjectMembership.project_id == cls.proj_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_health_int", user_id=cls.user_email, project_id=cls.proj_id, role="OWNER", status="ACTIVE")
            cls.db.add(mem)
            cls.db.commit()

        token = create_access_token(user_id=cls.user_email)
        cls.headers = {"Authorization": f"Bearer {token}"}

        # Setup mock crawl dataset with 5 pages (4 HTML 200, 1 HTTP 404)
        cls.storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, cls.domain, cls.proj_id)
        os.makedirs(cls.storage_dir, exist_ok=True)
        cls.crawl_dir = os.path.join(cls.storage_dir, "crawls", "2026-08-29_120000")
        os.makedirs(cls.crawl_dir, exist_ok=True)

        cls.mock_pages = [
            {"url": f"https://{cls.domain}/", "status_code": 200, "is_success": True, "title": "Home", "meta_description": "Welcome", "h1": ["Home"], "canonical": f"https://{cls.domain}/", "word_count": 450},
            {"url": f"https://{cls.domain}/about", "status_code": 200, "is_success": True, "title": "", "meta_description": "", "h1": [], "canonical": "", "word_count": 200}, # Missing title, desc, h1, canon
            {"url": f"https://{cls.domain}/services", "status_code": 200, "is_success": True, "title": "Services", "meta_description": "Our services", "h1": ["Services"], "canonical": f"https://{cls.domain}/services", "word_count": 300},
            {"url": f"https://{cls.domain}/contact", "status_code": 200, "is_success": True, "title": "Contact", "meta_description": "Contact us", "h1": ["Contact"], "canonical": f"https://{cls.domain}/contact", "word_count": 180},
            {"url": f"https://{cls.domain}/broken-page", "status_code": 404, "is_success": False, "title": "", "meta_description": "", "h1": [], "canonical": "", "word_count": 0} # 404 Error page
        ]

        with open(os.path.join(cls.crawl_dir, "pages.json"), "w") as f:
            json.dump(cls.mock_pages, f)

        with open(os.path.join(cls.storage_dir, "latest.json"), "w") as f:
            json.dump({"path": cls.crawl_dir, "status": "completed"}, f)

    def tearDown(self):
        self.db.close()

    def test_1_canonical_audit_rules_engine(self):
        """Verify audit rules engine calculates health score and excludes HTTP 404 from HTML metadata checks."""
        res = evaluate_site_audit_rules(self.mock_pages)
        self.assertIn("health_score", res)
        self.assertEqual(res["total_audited_pages"], 5)
        self.assertEqual(res["successful_html_pages_count"], 4)
        self.assertEqual(res["error_pages_count"], 1)
        # HTTP 404 is captured in Crawlability issue
        crawlability_issues = [i for i in res["issues"] if i["category"] == "Crawlability"]
        self.assertEqual(len(crawlability_issues), 1)
        self.assertEqual(crawlability_issues[0]["affected_count"], 1)

    def test_2_technical_api_matches_workspace_overview_score(self):
        """Verify GET /technical health score matches GET /workspace/overview health score 100%."""
        tech_res = self.client.get(f"/api/projects/{self.proj_id}/technical", headers=self.headers)
        self.assertEqual(tech_res.status_code, 200)
        tech_data = tech_res.json()
        tech_health = tech_data["health_score"]

        work_res = self.client.get("/api/workspace/overview", headers=self.headers)
        self.assertEqual(work_res.status_code, 200)
        work_data = work_res.json()

        proj_summary = next((p for p in work_data["projects"] if p["id"] == self.proj_id), None)
        self.assertIsNotNone(proj_summary)
        self.assertEqual(proj_summary["health_score"], tech_health)

    def test_3_projects_metrics_matches_technical_score_and_issues(self):
        """Verify GET /api/projects card metrics match technical audit score and issues count."""
        proj_res = self.client.get("/api/projects", headers=self.headers)
        self.assertEqual(proj_res.status_code, 200)
        proj_list = proj_res.json()

        target_proj = next((p for p in proj_list if p["id"] == self.proj_id), None)
        self.assertIsNotNone(target_proj)

        tech_res = self.client.get(f"/api/projects/{self.proj_id}/technical", headers=self.headers)
        tech_data = tech_res.json()

        self.assertEqual(target_proj["health_score"], tech_data["health_score"])
        self.assertEqual(target_proj["issues_count"], tech_data["total_issues"])

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

if __name__ == "__main__":
    unittest.main()
