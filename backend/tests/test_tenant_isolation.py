import unittest
import os
import sys
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token


class TestTenantIsolation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Create test users
        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)

        # Create project for User A
        cls.proj_a = Project(
            id=str(uuid.uuid4()),
            name="User A Website",
            url="https://usera-domain.com",
            description="Project owned by User A"
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

        # Create project for User B
        cls.proj_b = Project(
            id=str(uuid.uuid4()),
            name="User B Website",
            url="https://userb-domain.com",
            description="Project owned by User B"
        )
        cls.db.add(cls.proj_b)

        cls.mem_b = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_b_email,
            project_id=cls.proj_b.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_b)

        cls.db.commit()

        # Generate JWT tokens
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
            cls.db.query(Project).filter(
                Project.id.in_([cls.proj_a.id, cls.proj_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(User).filter(
                User.email.in_([cls.user_a_email, cls.user_b_email])
            ).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_user_projects_isolation(self):
        """Verify GET /api/projects returns strictly projects owned by the calling user."""
        res_a = self.client.get("/api/projects", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        proj_ids_a = [p["id"] for p in res_a.json()]
        self.assertIn(self.proj_a.id, proj_ids_a)
        self.assertNotIn(self.proj_b.id, proj_ids_a)

        res_b = self.client.get("/api/projects", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        proj_ids_b = [p["id"] for p in res_b.json()]
        self.assertIn(self.proj_b.id, proj_ids_b)
        self.assertNotIn(self.proj_a.id, proj_ids_b)

    def test_02_cross_tenant_project_access_denied(self):
        """Verify User B cannot access User A's project metrics or audit details."""
        # Technical audit
        res_tech = self.client.get(f"/api/projects/{self.proj_a.id}/technical", headers=self.headers_b)
        self.assertEqual(res_tech.status_code, 403)

        # Keywords
        res_kw = self.client.get(f"/api/projects/{self.proj_a.id}/keywords", headers=self.headers_b)
        self.assertEqual(res_kw.status_code, 403)

        # Rankings
        res_rank = self.client.get(f"/api/projects/{self.proj_a.id}/rankings", headers=self.headers_b)
        self.assertEqual(res_rank.status_code, 403)

        # Backlinks
        res_bl = self.client.get(f"/api/projects/{self.proj_a.id}/backlinks", headers=self.headers_b)
        self.assertEqual(res_bl.status_code, 403)

        # Competitors
        res_comp = self.client.get(f"/api/projects/{self.proj_a.id}/competitors", headers=self.headers_b)
        self.assertEqual(res_comp.status_code, 403)

        # Crawl History
        res_crawl = self.client.get(f"/api/projects/{self.proj_a.id}/crawl-history", headers=self.headers_b)
        self.assertEqual(res_crawl.status_code, 403)

    def test_03_workspace_overview_isolation(self):
        """Verify GET /api/workspace/overview aggregates ONLY the caller's projects."""
        res_a = self.client.get("/api/workspace/overview", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        data_a = res_a.json()
        projects_a = [p["id"] for p in data_a.get("projects", [])]
        self.assertIn(self.proj_a.id, projects_a)
        self.assertNotIn(self.proj_b.id, projects_a)

        res_b = self.client.get("/api/workspace/overview", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        data_b = res_b.json()
        projects_b = [p["id"] for p in data_b.get("projects", [])]
        self.assertIn(self.proj_b.id, projects_b)
        self.assertNotIn(self.proj_a.id, projects_b)

    def test_04_unauthenticated_access_rejected(self):
        """Verify requests without valid JWT authorization receive HTTP 401 Unauthorized."""
        res = self.client.get("/api/projects")
        self.assertEqual(res.status_code, 401)

    def test_05_same_domain_different_users_are_isolated(self):
        """Verify two different users auditing the exact same domain maintain completely separate datasets."""
        same_domain_url = "https://same-domain-test.com"

        # User A creates project for same_domain
        res_create_a = self.client.post("/api/projects", json={"name": "Domain Test A", "url": same_domain_url}, headers=self.headers_a)
        self.assertEqual(res_create_a.status_code, 200)
        proj_a_id = res_create_a.json()["project"]["id"]

        # User B creates project for exact same_domain
        res_create_b = self.client.post("/api/projects", json={"name": "Domain Test B", "url": same_domain_url}, headers=self.headers_b)
        self.assertEqual(res_create_b.status_code, 200)
        proj_b_id = res_create_b.json()["project"]["id"]

        # Project IDs MUST be distinct
        self.assertNotEqual(proj_a_id, proj_b_id)

        # User B cannot access User A's project ID
        res_cross = self.client.get(f"/api/projects/{proj_a_id}/technical", headers=self.headers_b)
        self.assertEqual(res_cross.status_code, 403)

        # User A cannot access User B's project ID
        res_cross_rev = self.client.get(f"/api/projects/{proj_b_id}/technical", headers=self.headers_a)
        self.assertEqual(res_cross_rev.status_code, 403)

    def test_06_integrations_are_user_scoped(self):
        """Verify external connection integrations are isolated per authenticated user."""
        res_a = self.client.get("/api/integrations", headers=self.headers_a)
        self.assertEqual(res_a.status_code, 200)
        self.assertEqual(res_a.json()["user_id"], self.user_a_email)

        res_b = self.client.get("/api/integrations", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        self.assertEqual(res_b.json()["user_id"], self.user_b_email)

    def test_07_reports_are_user_scoped(self):
        """Verify report generation URLs reject cross-tenant project IDs."""
        res_report = self.client.get(f"/api/projects/{self.proj_a.id}/report.pdf", headers=self.headers_b)
        self.assertEqual(res_report.status_code, 403)


if __name__ == "__main__":
    unittest.main()
