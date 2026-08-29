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

class TestWebsiteHealthAndAPIFixes(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user_email = "health_test_user@example.com"
        
        # Ensure test user exists
        user = self.db.query(User).filter(User.email == self.user_email).first()
        if not user:
            user = User(id="usr_health_123", email=self.user_email, name="Health Tester")
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
        self.user = user

        # Create test project
        self.project_id = "proj_health_test_999"
        project = self.db.query(Project).filter(Project.id == self.project_id).first()
        if not project:
            project = Project(id=self.project_id, name="Health Test Site", domain="healthtest.org", url="https://healthtest.org")
            self.db.add(project)
            self.db.commit()
            self.db.refresh(project)
        self.project = project

        # Ensure project membership
        mem = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_email,
            ProjectMembership.project_id == self.project_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_health_123", user_id=self.user_email, project_id=self.project_id, role="OWNER", status="ACTIVE")
            self.db.add(mem)
            self.db.commit()

        # Generate auth header
        from app.config.auth import create_access_token
        token = create_access_token(user_id=self.user_email)
        self.headers = {"Authorization": f"Bearer {token}"}

    def tearDown(self):
        self.db.close()

    def test_1_keywords_endpoint_returns_200(self):
        """Verify GET /api/projects/{project_id}/keywords returns 200 OK without 500 NameError."""
        res = self.client.get(f"/api/projects/{self.project_id}/keywords", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("keywords", data)
        self.assertIsInstance(data["keywords"], list)

    def test_2_import_history_endpoints_return_200(self):
        """Verify both /import/history and /imports/history endpoints return 200 OK without 404."""
        res1 = self.client.get(f"/api/projects/{self.project_id}/imports/history", headers=self.headers)
        self.assertEqual(res1.status_code, 200)
        
        res2 = self.client.get(f"/api/projects/{self.project_id}/import/history", headers=self.headers)
        self.assertEqual(res2.status_code, 200)
        
        data = res2.json()
        self.assertIsInstance(data, list)

    def test_3_technical_audit_endpoint_returns_real_metrics(self):
        """Verify GET /api/projects/{project_id}/technical returns health score and evaluated checks structure."""
        res = self.client.get(f"/api/projects/{self.project_id}/technical", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("health_score", data)
        self.assertIn("total_audited_pages", data)
        self.assertIn("category_checks_table", data)
        self.assertIn("issues", data)

    def test_4_unauthorized_access_blocked(self):
        """Verify requests without valid authentication token are blocked (401)."""
        res = self.client.get(f"/api/projects/{self.project_id}/keywords")
        self.assertEqual(res.status_code, 401)

if __name__ == "__main__":
    unittest.main()
