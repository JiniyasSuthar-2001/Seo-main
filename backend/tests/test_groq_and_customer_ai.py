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
from app.models.external_connection import ExternalConnection
from app.config.auth import create_access_token
from app.config.settings import settings
from app.llm.llm_provider import get_llm_provider_for_user, GroqProviderAdapter, OpenAIProviderAdapter

class TestGroqAndCustomerAI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_a_email = f"groq_user_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"groq_user_b_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="Groq User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="Groq User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)
        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(cls.user_b.id)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_groq_status_endpoint(self):
        res = self.client.get("/api/ai/groq/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["provider"], "groq")
        self.assertIn("configured", data)
        self.assertNotIn("api_key", res.text.lower())

    def test_02_groq_test_connection_mock(self):
        with patch.object(settings, "GROQ_API_KEY", "gsk-mock-key-12345"):
            with patch("app.llm.llm_provider.GroqProviderAdapter.test_connection") as mock_test:
                mock_test.return_value = {
                    "status": "connected",
                    "provider": "groq",
                    "model": "llama-3.3-70b-versatile",
                    "message": "Groq connection successful."
                }
                res = self.client.post("/api/ai/groq/test", headers=self.headers_a)
                self.assertEqual(res.status_code, 200)
                data = res.json()
                self.assertEqual(data["status"], "connected")
                self.assertEqual(data["provider"], "groq")

    def test_03_customer_submit_invalid_api_key_fails(self):
        with patch("app.llm.llm_provider.OpenAIProviderAdapter.test_connection") as mock_test:
            from app.llm.llm_provider import AIProviderException
            mock_test.side_effect = AIProviderException("Invalid key", status_code=401)
            res = self.client.post(
                "/api/integrations/openai/key",
                json={"api_key": "sk-invalid-key"},
                headers=self.headers_a
            )
            self.assertEqual(res.status_code, 400)
            self.assertIn("Unable to verify", res.json()["detail"])

    def test_04_customer_submit_valid_api_key_encrypts_and_masks(self):
        with patch("app.llm.llm_provider.OpenAIProviderAdapter.test_connection") as mock_test:
            mock_test.return_value = {"status": "connected", "provider": "openai", "model": "gpt-4o-mini"}
            res = self.client.post(
                "/api/integrations/openai/key",
                json={"api_key": "sk-proj-test1234567890abcdef"},
                headers=self.headers_a
            )
            self.assertEqual(res.status_code, 200)
            data = res.json()
            self.assertEqual(data["status"], "success")
            self.assertIn("masked_key", data["connection"])
            self.assertTrue(data["connection"]["masked_key"].endswith("cdef"))

            # Verify GET /api/integrations returns masked key without raw secrets
            get_res = self.client.get("/api/integrations", headers=self.headers_a)
            self.assertEqual(get_res.status_code, 200)
            get_data = get_res.json()
            self.assertIn("customer_ai", get_data)
            self.assertNotIn("sk-proj-test1234567890abcdef", get_res.text)

    def test_05_customer_key_toggle_and_groq_fallback(self):
        with patch("app.llm.llm_provider.OpenAIProviderAdapter.test_connection") as mock_test:
            mock_test.return_value = {"status": "connected", "provider": "openai", "model": "gpt-4o-mini"}
            self.client.post(
                "/api/integrations/openai/key",
                json={"api_key": "sk-proj-test1234567890abcdef"},
                headers=self.headers_a
            )
        provider = get_llm_provider_for_user(self.user_a.id, self.db)
        self.assertIsInstance(provider, OpenAIProviderAdapter)

        # Toggle customer key to DISABLED
        res_toggle = self.client.post("/api/integrations/openai/toggle", headers=self.headers_a)
        self.assertEqual(res_toggle.status_code, 200)
        self.assertEqual(res_toggle.json()["new_status"], "DISABLED")

        # After disabling, resolution falls back to GroqProviderAdapter when GROQ_API_KEY is present
        with patch.object(settings, "GROQ_API_KEY", "gsk-mock-key-999"):
            fallback_provider = get_llm_provider_for_user(self.user_a.id, self.db)
            self.assertIsInstance(fallback_provider, GroqProviderAdapter)

    def test_06_tenant_isolation_customer_keys(self):
        # User B should NOT see or access User A's custom API key
        res_b = self.client.get("/api/integrations", headers=self.headers_b)
        self.assertEqual(res_b.status_code, 200)
        customer_ai_b = res_b.json().get("customer_ai", [])
        openai_b = next((c for c in customer_ai_b if c["provider"] == "openai"), None)
        self.assertIsNotNone(openai_b)
        self.assertFalse(openai_b["connected"])

if __name__ == '__main__':
    unittest.main()
