import unittest
import uuid
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.external_connection import ExternalConnection
from app.config.auth import create_access_token
from app.config.settings import settings
from app.llm.ollama_adapter import OllamaProviderAdapter
from app.llm.ai_service import AIService
from app.llm.llm_provider import AIProviderException, GroqProviderAdapter

client = TestClient(app)


class TestOllamaAndAIService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.user_email = f"ollama_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="Ollama Test User")
        cls.db.add(cls.user)
        cls.db.commit()

        cls.token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_ollama_hardware_compatibility_evaluation(self):
        adapter = OllamaProviderAdapter()
        eval_3b = adapter.evaluate_hardware_fit("llama3.2:3b")
        self.assertEqual(eval_3b["fit"], "OPTIMAL")
        self.assertTrue(eval_3b["recommended"])
        self.assertIn("8GB RAM", eval_3b["detail"])

        eval_70b = adapter.evaluate_hardware_fit("llama3:70b")
        self.assertEqual(eval_70b["fit"], "WARNING")
        self.assertFalse(eval_70b["recommended"])
        self.assertIn("exceeds recommended", eval_70b["detail"])

    def test_02_ollama_test_connection_mock_success(self):
        adapter = OllamaProviderAdapter()
        with patch.object(adapter, "get_installed_models") as mock_models:
            mock_models.return_value = [
                {"name": "llama3.2:3b", "size_mb": 2000.0, "hardware_fit": "OPTIMAL", "hardware_badge": "Suitable", "recommended": True}
            ]
            res = adapter.test_connection(timeout=2.0)
            self.assertEqual(res["status"], "connected")
            self.assertEqual(res["provider"], "ollama")
            self.assertEqual(res["hardware_fit"], "OPTIMAL")

    def test_03_ollama_offline_returns_friendly_error(self):
        adapter = OllamaProviderAdapter(base_url="http://127.0.0.1:59999")
        with self.assertRaises(AIProviderException) as ctx:
            adapter.test_connection(timeout=1.0)
        self.assertEqual(ctx.exception.status_code, 503)
        self.assertIn("Ollama is not running on this device", ctx.exception.message)

    def test_04_ai_service_provider_status_matrix(self):
        matrix = AIService.get_provider_status_matrix(user_id=self.user.id, db=self.db)
        self.assertIn("active_provider", matrix)
        self.assertIn("providers", matrix)
        self.assertIn("ollama", matrix["providers"])
        self.assertIn("groq", matrix["providers"])
        self.assertIn("openai", matrix["providers"])
        self.assertIn("gemini", matrix["providers"])
        self.assertIn("claude", matrix["providers"])
        self.assertNotIn("api_key", str(matrix).lower())

    def test_05_ai_providers_api_endpoint(self):
        res = client.get("/api/ai/providers", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("providers", data)
        self.assertIn("ollama", data["providers"])

    def test_06_preferred_provider_fallback_to_groq(self):
        # Requesting unconfigured provider falls back to Groq if GROQ_API_KEY is present
        with patch.object(settings, "GROQ_API_KEY", "gsk-mock-key-777"):
            provider = AIService.get_provider(user_id=self.user.id, db=self.db, preferred_provider="claude")
            self.assertIsInstance(provider, GroqProviderAdapter)


if __name__ == '__main__':
    unittest.main()
