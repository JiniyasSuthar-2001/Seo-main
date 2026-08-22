import os
import sys
import unittest

# Ensure backend path is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config.settings import settings, build_frontend_redirect, validate_startup_config
from app.config.crypto import encrypt_secret, decrypt_secret, reset_fernet_cache, get_encryption_key
from app.services.oauth_provider_service import generate_oauth_state, validate_oauth_state

class TestOAuthRedirectAndCrypto(unittest.TestCase):

    def test_1_build_frontend_redirect_url(self):
        """Verify build_frontend_redirect constructs absolute Frontend Port 8030 URL."""
        redirect_url = build_frontend_redirect("/settings", {"integration": "success", "provider": "google"})
        self.assertTrue(redirect_url.startswith("http://127.0.0.1:8030/settings"))
        self.assertIn("integration=success", redirect_url)
        self.assertIn("provider=google", redirect_url)

    def test_2_oauth_state_generation_and_validation(self):
        """Verify OAuth state generation and CSRF verification."""
        user_id = "test_user_99"
        provider = "google"
        state = generate_oauth_state(user_id, provider)
        
        self.assertTrue(isinstance(state, str))
        self.assertGreater(len(state), 20)

        validated = validate_oauth_state(state)
        self.assertEqual(validated["user_id"], user_id)
        self.assertEqual(validated["provider"], provider)

    def test_3_encryption_key_storage_and_decryption(self):
        """Verify token encryption and decryption using ENCRYPTION_KEY."""
        original_token = "ya29.a0AfH6SMA8912379128371928"
        ciphertext = encrypt_secret(original_token)
        self.assertNotEqual(original_token, ciphertext)
        
        decrypted = decrypt_secret(ciphertext)
        self.assertEqual(original_token, decrypted)

    def test_4_missing_encryption_key_raises(self):
        """Verify missing ENCRYPTION_KEY fails configuration validation cleanly."""
        old_env = os.environ.get("ENCRYPTION_KEY")
        try:
            if "ENCRYPTION_KEY" in os.environ:
                del os.environ["ENCRYPTION_KEY"]
            reset_fernet_cache()
            with self.assertRaises(RuntimeError):
                get_encryption_key()
        finally:
            if old_env:
                os.environ["ENCRYPTION_KEY"] = old_env
            reset_fernet_cache()

if __name__ == "__main__":
    unittest.main()
