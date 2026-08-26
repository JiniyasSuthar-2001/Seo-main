import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.services.anchor_suggestion_service import AnchorSuggestionService

class TestAnchorSuggestions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.client = TestClient(app)

        cls.user = cls.db.query(User).filter(User.email == "anchor_test@example.com").first()
        if not cls.user:
            cls.user = User(
                id="test_anchor_user_id",
                email="anchor_test@example.com",
                name="Anchor Tester"
            )
            cls.db.add(cls.user)
            cls.db.commit()

        cls.project = cls.db.query(Project).filter((Project.id == "test_anchor_project_id") | (Project.domain == "queenshine.com.au")).first()
        if not cls.project:
            cls.project = Project(
                id="test_anchor_project_id",
                name="Queenshine Electrical",
                domain="queenshine.com.au"
            )
            cls.db.add(cls.project)
            cls.db.commit()

        cls.membership = cls.db.query(ProjectMembership).filter(
            ProjectMembership.project_id == cls.project.id,
            ProjectMembership.user_id == cls.user.id
        ).first()
        if not cls.membership:
            cls.membership = ProjectMembership(
                id="test_anchor_membership_id",
                project_id=cls.project.id,
                user_id=cls.user.id,
                role="Owner"
            )
            cls.db.add(cls.membership)
            cls.db.commit()

        cls.headers = {"X-User-ID": cls.user.id}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_anchor_suggestions_endpoint(self):
        resp = self.client.post(
            f"/api/projects/{self.project.id}/internal-links/anchor-suggestions",
            headers=self.headers,
            json={
                "source_url": f"https://{self.project.domain}/",
                "target_url": f"https://{self.project.domain}/services",
                "refresh": True
            }
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("status", data)
        self.assertIn("suggestions", data)
        self.assertIn("evidence", data)
        self.assertIsInstance(data["suggestions"], list)

        # Ensure NO Learn More hardcoded fallback in suggestions
        for s in data["suggestions"]:
            self.assertNotIn("learn more", s["anchor"].lower())

    def test_02_opportunities_endpoint_no_learn_more(self):
        resp = self.client.get(f"/api/projects/{self.project.id}/internal-links/opportunities", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        opps = data.get("opportunities", [])
        for o in opps:
            self.assertNotEqual(o.get("suggested_anchor"), "Learn More")

    def test_03_service_insufficient_evidence(self):
        # Service call for non-existent target page
        res = AnchorSuggestionService.get_suggestions(
            project_id=self.project.id,
            domain=self.project.domain,
            source_url="https://example.com/source",
            target_url="https://example.com/nonexistent",
            refresh=True
        )
        self.assertEqual(res["status"], "insufficient_evidence")
        self.assertEqual(len(res["suggestions"]), 0)
        self.assertIn("Not enough evidence", res["message"])

if __name__ == "__main__":
    unittest.main()
