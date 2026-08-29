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

class TestAIButtonAndNavigation(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user_email = "user_ai_nav@example.com"

        user = self.db.query(User).filter(User.email == self.user_email).first()
        if not user:
            user = User(id="usr_ai_nav", email=self.user_email, name="AI Nav User")
            self.db.add(user)
            self.db.commit()

        self.proj_id = "proj_ai_nav_123"
        proj = self.db.query(Project).filter(Project.id == self.proj_id).first()
        if not proj:
            proj = Project(id=self.proj_id, name="AI Nav Test Site", url="https://ainavtest.com")
            self.db.add(proj)
            self.db.commit()

        mem = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_email,
            ProjectMembership.project_id == self.proj_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_ai_nav", user_id=self.user_email, project_id=self.proj_id, role="OWNER", status="ACTIVE")
            self.db.add(mem)
            self.db.commit()

        token = create_access_token(user_id=self.user_email)
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.db.close()

    def test_1_get_project_details_for_navigation(self):
        """Verify project details can be fetched for project navigation."""
        res = self.client.get("/api/projects", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(any(p["id"] == self.proj_id for p in data))

    def test_2_ai_chat_accepts_page_context(self):
        """Verify POST /api/projects/{project_id}/ai/chat accepts query and page context."""
        payload = {
            "query": "What crawl issues exist on this website?",
            "current_page": "/technical"
        }
        res = self.client.post(f"/api/projects/{self.proj_id}/ai/chat", json=payload, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("answer", data)
        self.assertIn("context_used", data)
        self.assertIn("ainavtest.com", data["context_used"]["domain"])

if __name__ == "__main__":
    unittest.main()
