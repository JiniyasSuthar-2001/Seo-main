import uuid
import os
import json
import unittest
from unittest.mock import patch, MagicMock
import urllib.error
from fastapi.testclient import TestClient

from app.main import app
from app.config.settings import settings
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.config.auth import create_access_token
from app.llm.llm_provider import GroqProviderAdapter, AIProviderException

client = TestClient(app)


class TestGroqModelsDiscovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.user_email = f"groq_models_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="Groq Models User")
        cls.db.add(cls.user)
        cls.db.commit()

        cls.token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_fetch_available_models_filters_non_chat_models(self):
        adapter = GroqProviderAdapter(api_key="gsk_test_fake_key_12345")
        mock_response_data = {
            "data": [
                {"id": "openai/gpt-oss-120b", "active": True, "owned_by": "OpenAI"},
                {"id": "whisper-large-v3", "active": True, "owned_by": "OpenAI"},
                {"id": "meta-llama/llama-prompt-guard-2-22m", "active": True, "owned_by": "Meta"},
                {"id": "qwen/qwen3.6-27b", "active": True, "owned_by": "Alibaba Cloud"}
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_response_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp):
            models = adapter.fetch_available_models()
            model_ids = [m["id"] for m in models]
            self.assertIn("openai/gpt-oss-120b", model_ids)
            self.assertIn("qwen/qwen3.6-27b", model_ids)
            self.assertNotIn("whisper-large-v3", model_ids)
            self.assertNotIn("meta-llama/llama-prompt-guard-2-22m", model_ids)

    def test_02_groq_test_endpoint_returns_non_200_on_auth_failure(self):
        with patch.object(settings, "GROQ_API_KEY", "gsk_invalid_key_99999"):
            res = client.post("/api/ai/groq/test", json={"model": "non-existent-model"}, headers=self.headers)
            # Must return HTTP 401 or 404 or 502, NEVER HTTP 200
            self.assertNotEqual(res.status_code, 200)
            self.assertIn(res.status_code, (400, 401, 404, 502))
            data = res.json()
            self.assertIn("detail", data)

    def test_03_groq_test_endpoint_with_live_key(self):
        real_key = os.environ.get("GROQ_API_KEY")
        if not real_key:
            self.skipTest("GROQ_API_KEY not configured in environment")

        res = client.post("/api/ai/groq/test", json={}, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "connected")
        self.assertEqual(data["provider"], "groq")
        self.assertIsNotNone(data.get("model"))
        self.assertGreater(len(data.get("available_models", [])), 0)

    def test_04_no_raw_api_key_leaked_in_responses(self):
        real_key = os.environ.get("GROQ_API_KEY") or "gsk_secret_test_key_abc123"
        with patch.object(settings, "GROQ_API_KEY", real_key):
            res_status = client.get("/api/ai/providers", headers=self.headers)
            self.assertEqual(res_status.status_code, 200)
            text = res_status.text
            self.assertNotIn(real_key, text)

            res_integrations = client.get("/api/integrations", headers=self.headers)
            self.assertEqual(res_integrations.status_code, 200)
            self.assertNotIn(real_key, res_integrations.text)


if __name__ == "__main__":
    unittest.main()
