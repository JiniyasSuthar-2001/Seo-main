import unittest
import uuid
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.config.settings import settings

class TestGeminiAIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_a_email = f"gemini_user_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"gemini_user_b_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="Gemini User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="Gemini User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)
        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(cls.user_b.id)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        cls.project_a = Project(
            id=str(uuid.uuid4()),
            name="Gemini Project A",
            url="https://gemini-test-a.com",
            domain="gemini-test-a.com"
        )
        cls.db.add(cls.project_a)
        cls.db.commit()

        cls.membership_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_a.id,
            project_id=cls.project_a.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.membership_a)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_gemini_status_endpoint_never_exposes_secrets(self):
        res = self.client.get("/api/ai/gemini/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("provider", data)
        self.assertEqual(data["provider"], "gemini")
        self.assertIn("configured", data)
        self.assertIn("available", data)

        # Verify no sensitive key is returned
        body_text = res.text.lower()
        self.assertNotIn("api_key", body_text)
        self.assertNotIn("secret", body_text)

    def test_02_gemini_test_connection_unconfigured(self):
        with patch.object(settings, "GEMINI_API_KEY", None), patch.object(settings, "AI_API_KEY", None):
            res = self.client.post("/api/ai/gemini/test", headers=self.headers_a)
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "error")
            self.assertFalse(data["configured"])

    def test_03_gemini_test_connection_mock_success(self):
        with patch.object(settings, "GEMINI_API_KEY", "mock-gemini-key-12345"):
            with patch("app.llm.llm_provider.GeminiProviderAdapter.test_connection") as mock_test:
                mock_test.return_value = {
                    "status": "connected",
                    "provider": "gemini",
                    "model": "gemini-1.5-flash",
                    "message": "Gemini connection successful."
                }
                res = self.client.post("/api/ai/gemini/test", headers=self.headers_a)
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "connected")
                self.assertEqual(data["provider"], "gemini")

    def test_04_multi_account_isolation_for_ai_analysis(self):
        # User B should be rejected when requesting User A's project AI analysis (403 Forbidden)
        res = self.client.post(f"/api/projects/{self.project_a.id}/ai/analyze", headers=self.headers_b)
        self.assertEqual(res.status_code, 403)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.project_a.id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.project_a.id).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id.in_([cls.user_a.id, cls.user_b.id])).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

if __name__ == '__main__':
    unittest.main()
