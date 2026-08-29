import os
import sys
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

class TestAIProblemSolutionFix(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user_email = "user_ai_sol_test@example.com"

        user = self.db.query(User).filter(User.email == self.user_email).first()
        if not user:
            user = User(id="usr_ai_sol_test", email=self.user_email, name="AI Sol User")
            self.db.add(user)
            self.db.commit()

        self.proj_id = "proj_ai_sol_test_123"
        proj = self.db.query(Project).filter(Project.id == self.proj_id).first()
        if not proj:
            proj = Project(id=self.proj_id, name="AI Solution Test Site", url="https://aisolutiontest.com")
            self.db.add(proj)
            self.db.commit()

        mem = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_email,
            ProjectMembership.project_id == self.proj_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_ai_sol_test", user_id=self.user_email, project_id=self.proj_id, role="OWNER", status="ACTIVE")
            self.db.add(mem)
            self.db.commit()

        token = create_access_token(user_id=self.user_email)
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.db.close()

    def test_1_problem_solution_endpoint_returns_grounded_solution(self):
        """Test POST /api/projects/{project_id}/ai/problem-solution returns structured solution data."""
        payload = {
            "rule_id": "MISSING_META_DESC",
            "title": "Pages Missing Meta Descriptions",
            "category": "Website Scan",
            "severity": "warning",
            "description": "3 pages are missing meta descriptions for search snippet optimization.",
            "recommendation": "Write compelling 140-160 character meta descriptions summarizing page topic.",
            "affected_urls": ["https://aisolutiontest.com/about", "https://aisolutiontest.com/contact"],
            "evidence_text": "Meta description tag is missing from HTML head"
        }
        res = self.client.post(f"/api/projects/{self.proj_id}/ai/problem-solution", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("status", data)
        
        if data["status"] == "success":
            self.assertIn("page_solutions", data)
            page_sols = data["page_solutions"]
            self.assertIsInstance(page_sols, dict)
            self.assertIn("https://aisolutiontest.com/about", page_sols)
            self.assertIn("https://aisolutiontest.com/contact", page_sols)
            self.assertIsNotNone(data.get("default_solution"))

    def test_2_problem_solution_caching(self):
        """Test repeated requests for the same finding return cached solution instantly."""
        payload = {
            "rule_id": "HTTP_404_PAGE",
            "title": "HTTP 404 Broken Pages Detected",
            "category": "Technical HTTP",
            "severity": "critical",
            "description": "Pages return HTTP 404 response.",
            "recommendation": "Implement 301 permanent redirects.",
            "affected_urls": ["https://aisolutiontest.com/old-page"],
            "evidence_text": "HTTP status 404"
        }
        res1 = self.client.post(f"/api/projects/{self.proj_id}/ai/problem-solution", json=payload, headers=self.headers)
        self.assertEqual(res1.status_code, 200)

        res2 = self.client.post(f"/api/projects/{self.proj_id}/ai/problem-solution", json=payload, headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res1.json(), res2.json())

if __name__ == "__main__":
    unittest.main()
