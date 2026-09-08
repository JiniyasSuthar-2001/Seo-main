import unittest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token

class TestTechnicalAuditAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_email = f"tech_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.other_email = f"tech_other_{uuid.uuid4().hex[:6]}@example.com"

        cls.user = User(id=cls.user_email, email=cls.user_email, name="Tech Owner")
        cls.other = User(id=cls.other_email, email=cls.other_email, name="Tech Other")

        cls.db.add(cls.user)
        cls.db.add(cls.other)
        cls.db.commit()

        cls.token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        cls.other_token = create_access_token(cls.other.id)
        cls.other_headers = {"Authorization": f"Bearer {cls.other_token}"}

        cls.project = Project(
            id=str(uuid.uuid4()),
            name="Tech Audit Test Project",
            url="https://tech-audit-test.com",
            domain="tech-audit-test.com"
        )
        cls.db.add(cls.project)
        cls.db.commit()

        cls.membership = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user.id,
            project_id=cls.project.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.project.id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.project.id).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id.in_([cls.user.id, cls.other.id])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

    def test_01_get_technical_audit_success(self):
        res = self.client.get(f"/api/projects/{self.project.id}/technical", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("project_id"), self.project.id)
        self.assertEqual(data.get("domain"), self.project.domain)
        self.assertIn("health_score", data)
        self.assertIn("category_breakdown", data)
        self.assertIn("summary", data)
        self.assertIn("issues", data)

        categories = data.get("category_breakdown", {})
        self.assertIn("Crawlability", categories)
        self.assertIn("Performance", categories)
        self.assertFalse(categories["Performance"]["evaluated"])

    def test_02_get_technical_audit_forbidden(self):
        res = self.client.get(f"/api/projects/{self.project.id}/technical", headers=self.other_headers)
        self.assertEqual(res.status_code, 403)

    def test_03_get_technical_audit_not_found(self):
        fake_id = str(uuid.uuid4())
        res = self.client.get(f"/api/projects/{fake_id}/technical", headers=self.headers)
        self.assertEqual(res.status_code, 404)

if __name__ == '__main__':
    unittest.main()
