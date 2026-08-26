import os
import sys
import unittest
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from unittest.mock import patch
from app.config.settings import settings
from app.llm.llm_provider import get_llm_provider_for_user, OpenAIProviderAdapter
from app.llm.seo_analyst import SEOAnalystAgent

class TestAIProviderArchitecture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_a_email = f"ai_usera_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"ai_userb_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="AI User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="AI User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)
        cls.db.commit()

        cls.token_a = create_access_token(cls.user_a.id)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(cls.user_b.id)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

        cls.proj_a = Project(
            id=str(uuid.uuid4()),
            name="AI Project A",
            url="https://ai-proj-a.com",
            domain="ai-proj-a.com"
        )
        cls.db.add(cls.proj_a)
        cls.db.commit()

        cls.mem_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_a.id,
            project_id=cls.proj_a.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_a)
        cls.db.commit()

        # Create mock crawl storage for proj_a
        from app.config.settings import settings
        proj_dir = os.path.join(settings.CRAWL_DATA_DIR, cls.proj_a.id)
        os.makedirs(proj_dir, exist_ok=True)
        with open(os.path.join(proj_dir, "latest.json"), "w") as f:
            import json
            json.dump({"path": proj_dir, "crawl_id": "test_crawl_123"}, f)
        with open(os.path.join(proj_dir, "pages.json"), "w") as f:
            import json
            json.dump([{"url": "https://ai-proj-a.com/", "status_code": 200, "title": "Home", "word_count": 500}], f)
        with open(os.path.join(proj_dir, "metadata.json"), "w") as f:
            import json
            json.dump({"crawl_id": "test_crawl_123", "timestamp": "2026-08-25T12:00:00Z"}, f)

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_platform_provider_resolution(self):
        old_openai = os.environ.get("OPENAI_API_KEY")
        old_groq = os.environ.get("GROQ_API_KEY")
        with patch.object(settings, "AI_PROVIDER", "openai"), \
             patch.object(settings, "GROQ_API_KEY", None):
            try:
                os.environ["OPENAI_API_KEY"] = "sk-test-platform-fake-key-12345"
                os.environ.pop("GROQ_API_KEY", None)
                provider = get_llm_provider_for_user(self.user_a.id, self.db)
                self.assertIsNotNone(provider)
                self.assertIsInstance(provider, OpenAIProviderAdapter)
                self.assertEqual(provider.api_key, "sk-test-platform-fake-key-12345")
            finally:
                if old_openai:
                    os.environ["OPENAI_API_KEY"] = old_openai
                else:
                    os.environ.pop("OPENAI_API_KEY", None)
                if old_groq:
                    os.environ["GROQ_API_KEY"] = old_groq

    def test_02_unavailable_state_when_no_api_key(self):
        old_groq = os.environ.get("GROQ_API_KEY")
        try:
            os.environ.pop("GROQ_API_KEY", None)
            with patch.object(settings, "GROQ_API_KEY", None), \
                 patch.object(settings, "GEMINI_API_KEY", None), \
                 patch.object(settings, "AI_API_KEY", None), \
                 patch.object(settings, "OPENAI_API_KEY", None), \
                 patch.object(settings, "ANTHROPIC_API_KEY", None):
                agent = SEOAnalystAgent()
                res = agent.analyze_project(self.proj_a.id, domain=self.proj_a.domain, user_id=self.user_a.id, db=self.db)
                self.assertEqual(res.get("status"), "AI_TEMPORARILY_UNAVAILABLE")
                self.assertIn("temporarily unavailable", res.get("message", "").lower())
                self.assertFalse(res.get("is_llm_generated"))
                self.assertEqual(len(res.get("insights", [])), 0)
        finally:
            if old_groq:
                os.environ["GROQ_API_KEY"] = old_groq

    def test_03_tenant_isolation_ai_endpoints(self):
        res_analyze = self.client.post(f"/api/projects/{self.proj_a.id}/ai/analyze", headers=self.headers_b)
        self.assertEqual(res_analyze.status_code, 403)

        res_chat = self.client.post(
            f"/api/projects/{self.proj_a.id}/ai/chat",
            json={"query": "What are the biggest SEO problems?"},
            headers=self.headers_b
        )
        self.assertEqual(res_chat.status_code, 403)

        old_groq = os.environ.get("GROQ_API_KEY")
        try:
            os.environ.pop("GROQ_API_KEY", None)
            with patch.object(settings, "GROQ_API_KEY", None), \
                 patch.object(settings, "GEMINI_API_KEY", None), \
                 patch.object(settings, "AI_API_KEY", None):
                res_user_a = self.client.get(f"/api/projects/{self.proj_a.id}/ai/insights", headers=self.headers_a)
                self.assertEqual(res_user_a.status_code, 200)
        finally:
            if old_groq:
                os.environ["GROQ_API_KEY"] = old_groq

if __name__ == '__main__':
    unittest.main()
