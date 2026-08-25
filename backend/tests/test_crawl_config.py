import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token


class TestCrawlConfigAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_a_email = f"user_cfg_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"user_cfg_b_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="Config User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="Config User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)

        cls.proj_a = Project(
            id=str(uuid.uuid4()),
            name="Config Project A",
            url="https://cfg-test-a.com"
        )
        cls.db.add(cls.proj_a)

        cls.mem_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_a_email,
            project_id=cls.proj_a.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_a)
        cls.db.commit()

        cls.token_a = create_access_token(user_id=cls.user_a_email)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(user_id=cls.user_b_email)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(
                ProjectMembership.user_id.in_([cls.user_a_email, cls.user_b_email])
            ).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.proj_a.id).delete(synchronize_session=False)
            cls.db.query(User).filter(
                User.email.in_([cls.user_a_email, cls.user_b_email])
            ).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_get_default_crawl_config(self):
        """Verify GET returns default crawl configuration."""
        res = self.client.get(f"/api/projects/{self.proj_a.id}/crawl-config", headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "success")
        cfg = data["config"]
        self.assertTrue(cfg["ignore_tracking_parameters"])
        self.assertTrue(cfg["audit_modules"]["technical_http"])
        self.assertTrue(cfg["audit_modules"]["metadata"])

    def test_02_patch_partial_crawl_config(self):
        """Verify PATCH allows partial updates to crawl configuration."""
        payload = {
            "ignore_tracking_parameters": False,
            "audit_modules": {
                "metadata": False
            }
        }
        res = self.client.patch(f"/api/projects/{self.proj_a.id}/crawl-config", json=payload, headers=self.headers_a)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        cfg = data["config"]
        self.assertFalse(cfg["ignore_tracking_parameters"])
        self.assertFalse(cfg["audit_modules"]["metadata"])
        self.assertTrue(cfg["audit_modules"]["technical_http"])  # Preserved other modules

    def test_03_cross_tenant_access_denied(self):
        """Verify User B cannot view or modify User A's crawl config."""
        res_get = self.client.get(f"/api/projects/{self.proj_a.id}/crawl-config", headers=self.headers_b)
        self.assertEqual(res_get.status_code, 403)

        res_patch = self.client.patch(f"/api/projects/{self.proj_a.id}/crawl-config", json={"max_pages": 100}, headers=self.headers_b)
        self.assertEqual(res_patch.status_code, 403)


if __name__ == "__main__":
    unittest.main()
