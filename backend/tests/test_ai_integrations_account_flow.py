import os
import sys
import unittest
from fastapi.testclient import TestClient

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.services.oauth_provider_service import OAuthProviderConfig, build_authorization_url
from app.routers.auth import create_access_token

client = TestClient(app)

class TestAIIntegrationsAccountFlow(unittest.TestCase):

    def setUp(self):
        self.token = create_access_token({"sub": "user_ai_test_99", "email": "test@example.com"})
        self.auth_headers = {"Authorization": f"Bearer {self.token}"}

    def test_1_gemini_oauth_provider_configuration(self):
        """Verify Gemini resolves Google OAuth auth_url and Generative Language scope."""
        details = OAuthProviderConfig.get_provider_details("gemini")
        self.assertEqual(details["auth_url"], "https://accounts.google.com/o/oauth2/v2/auth")
        self.assertIn("webmasters.readonly", details["scopes"])

        self.assertIn("/api/integrations/google/callback", details["redirect_uri"])

    def test_2_api_key_submission_deprecated(self):
        """Verify posting raw API keys returns 400 Bad Request error."""
        response = client.post(
            "/api/integrations/openai/key",
            json={"api_key": "sk-proj-test123"},
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Pasting raw API keys is deprecated", response.json()["detail"])

    def test_3_unauthenticated_disconnect_rejected(self):
        """Verify unauthenticated disconnect requests return HTTP 401 Unauthorized."""
        response = client.post("/api/integrations/fake-conn-id/disconnect")
        self.assertEqual(response.status_code, 401)

    def test_4_disconnect_nonexistent_connection(self):
        """Verify disconnecting invalid ID returns 404 Not Found."""
        response = client.post(
            "/api/integrations/nonexistent-conn-id/disconnect",
            headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
