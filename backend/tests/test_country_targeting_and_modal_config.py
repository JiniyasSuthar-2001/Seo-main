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

class TestCountryTargetingAndModalConfig(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user_a_email = "user_a_country@example.com"
        self.user_b_email = "user_b_country@example.com"

        # Create User A
        user_a = self.db.query(User).filter(User.email == self.user_a_email).first()
        if not user_a:
            user_a = User(id="usr_cntry_a", email=self.user_a_email, name="User A")
            self.db.add(user_a)

        # Create User B
        user_b = self.db.query(User).filter(User.email == self.user_b_email).first()
        if not user_b:
            user_b = User(id="usr_cntry_b", email=self.user_b_email, name="User B")
            self.db.add(user_b)
            
        self.db.commit()

        # Create Project A for User A
        self.proj_a_id = "proj_cntry_a_999"
        proj_a = self.db.query(Project).filter(Project.id == self.proj_a_id).first()
        if not proj_a:
            proj_a = Project(id=self.proj_a_id, name="Project A Site", url="https://site-a.com")
            self.db.add(proj_a)
            self.db.commit()

        mem_a = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_a_email,
            ProjectMembership.project_id == self.proj_a_id
        ).first()
        if not mem_a:
            mem_a = ProjectMembership(id="mem_cntry_a", user_id=self.user_a_email, project_id=self.proj_a_id, role="OWNER", status="ACTIVE")
            self.db.add(mem_a)
            self.db.commit()

        # Create Project B for User B
        self.proj_b_id = "proj_cntry_b_888"
        proj_b = self.db.query(Project).filter(Project.id == self.proj_b_id).first()
        if not proj_b:
            proj_b = Project(id=self.proj_b_id, name="Project B Site", url="https://site-b.com")
            self.db.add(proj_b)
            self.db.commit()

        mem_b = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_b_email,
            ProjectMembership.project_id == self.proj_b_id
        ).first()
        if not mem_b:
            mem_b = ProjectMembership(id="mem_cntry_b", user_id=self.user_b_email, project_id=self.proj_b_id, role="OWNER", status="ACTIVE")
            self.db.add(mem_b)
            self.db.commit()

        token_a = create_access_token(user_id=self.user_a_email)
        self.headers_a = {"Authorization": f"Bearer {token_a}"}

        token_b = create_access_token(user_id=self.user_b_email)
        self.headers_b = {"Authorization": f"Bearer {token_b}"}

    def tearDown(self):
        self.db.close()

    def test_1_default_crawl_config_includes_target_countries(self):
        """Verify GET /api/projects/{project_id}/crawl-config includes target_countries default array."""
        res = self.client.get(f"/api/projects/{self.proj_a_id}/crawl-config", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("config", data)
        self.assertIn("target_countries", data["config"])
        self.assertIsInstance(data["config"]["target_countries"], list)

    def test_2_patch_persists_target_countries(self):
        """Verify PATCH /api/projects/{project_id}/crawl-config persists selected countries."""
        payload = {
            "target_countries": ["IN", "AU", "US", "GB", "CA"]
        }
        res_patch = self.client.patch(f"/api/projects/{self.proj_a_id}/crawl-config", json=payload, headers=self.headers_a)
        self.assertEqual(res_patch.status_code, 200)
        data_patch = res_patch.json()
        self.assertEqual(data_patch["config"]["target_countries"], ["IN", "AU", "US", "GB", "CA"])

        # Fetch remote config to confirm persistence
        res_get = self.client.get(f"/api/projects/{self.proj_a_id}/crawl-config", headers=self.headers_a)
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["config"]["target_countries"], ["IN", "AU", "US", "GB", "CA"])

    def test_3_multi_tenant_country_isolation(self):
        """Verify Project A country settings do not bleed into Project B."""
        # Save Project A countries
        self.client.patch(f"/api/projects/{self.proj_a_id}/crawl-config", json={"target_countries": ["IN", "AU"]}, headers=self.headers_a)
        
        # Save Project B countries
        self.client.patch(f"/api/projects/{self.proj_b_id}/crawl-config", json={"target_countries": ["DE", "FR"]}, headers=self.headers_b)

        # Verify User A sees Project A settings
        res_a = self.client.get(f"/api/projects/{self.proj_a_id}/crawl-config", headers=self.headers_a)
        self.assertEqual(res_a.json()["config"]["target_countries"], ["IN", "AU"])

        # Verify User B sees Project B settings
        res_b = self.client.get(f"/api/projects/{self.proj_b_id}/crawl-config", headers=self.headers_b)
        self.assertEqual(res_b.json()["config"]["target_countries"], ["DE", "FR"])

        # Verify User B cannot access Project A settings
        res_forbidden = self.client.get(f"/api/projects/{self.proj_a_id}/crawl-config", headers=self.headers_b)
        self.assertIn(res_forbidden.status_code, [403, 404])

    def test_4_start_crawl_accepts_target_countries(self):
        """Verify POST /api/projects/{project_id}/crawl accepts target_countries payload."""
        crawl_payload = {
            "url": "https://site-a.com",
            "scope_type": "entire_domain",
            "max_pages": 100,
            "max_depth": 2,
            "target_countries": ["IN", "AU"]
        }
        res = self.client.post(f"/api/projects/{self.proj_a_id}/crawl", json=crawl_payload, headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("session_id", data)
        self.assertIn("message", data)

if __name__ == "__main__":
    unittest.main()
