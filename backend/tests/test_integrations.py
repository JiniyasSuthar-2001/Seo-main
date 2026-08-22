import os
import sys

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment keys if missing
if not os.environ.get("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-unit-audit-suite-32b"
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "test-secret-key-for-signing-session-32b"
if not os.environ.get("OAUTH_STATE_SECRET"):
    os.environ["OAUTH_STATE_SECRET"] = "test-oauth-state-secret-signing-32b"

def test_external_connections_system():
    print("============================================================", flush=True)
    print(" EXTERNAL ACCOUNT CONNECTION SYSTEM — SECURITY & AUDIT SUITE", flush=True)
    print("============================================================\n", flush=True)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.config.database import SessionLocal
    from app.models.external_connection import ExternalConnection
    from app.config.crypto import encrypt_secret, decrypt_secret, mask_secret, get_encryption_key, reset_fernet_cache

    client = TestClient(app)
    db = SessionLocal()

    # Clean up test integration records if left over
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_user_a", "test_user_b"])).delete(synchronize_session=False)
    db.commit()

    # 1. Test Crypto Encryption & Masking
    raw_token = "sk-ant-api03-super-secret-claude-token-123456789"
    encrypted = encrypt_secret(raw_token)
    decrypted = decrypt_secret(encrypted)
    masked = mask_secret(raw_token)

    assert encrypted != raw_token, "Token was not encrypted"
    assert decrypted == raw_token, "Decryption mismatch"
    assert "super-secret" not in masked, "Masking leaked secret string"

    # 2. Test OAuth State CSRF Protection
    res_bad_callback = client.get("/api/integrations/google/callback?code=mock_code&state=invalid_tampered_state", follow_redirects=False)
    assert res_bad_callback.status_code in (302, 307, 400)

    # 3. Test Direct Provider Key Registration & Validation Flow
    res_bad_key = client.post(
        "/api/integrations/openai/key",
        json={"api_key": "sk-invalid-test-key-123456789"},
        headers={"X-User-ID": "test_user_a"}
    )
    assert res_bad_key.status_code == 400

    # 4. Clean up test records
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_user_a", "test_user_b"])).delete(synchronize_session=False)
    db.commit()
    db.close()

if __name__ == "__main__":
    test_external_connections_system()
