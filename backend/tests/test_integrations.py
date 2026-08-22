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
    from app.config.crypto import encrypt_secret, decrypt_secret, mask_secret
    from app.config.auth import create_access_token

    client = TestClient(app)
    db = SessionLocal()

    # Clean up test integration records if left over
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_user_a", "test_user_b"])).delete(synchronize_session=False)
    db.commit()

    # 1. Test Unauthenticated 401 Protection
    print("[1/5] Testing 401 Unauthorized rejection for unauthenticated requests...", flush=True)
    res_unauth = client.get("/api/integrations")
    assert res_unauth.status_code == 401, f"Expected 401 Unauthenticated, got {res_unauth.status_code}"
    print("      [PASS] Unauthenticated access blocked with HTTP 401.\n", flush=True)

    # 2. Test JWT Authentication & Token Extraction
    print("[2/5] Testing JWT Access Token Authentication...", flush=True)
    jwt_token = create_access_token("test_user_a")
    res_auth = client.get("/api/integrations", headers={"Authorization": f"Bearer {jwt_token}"})
    assert res_auth.status_code == 200, f"Expected 200 OK with valid JWT, got {res_auth.status_code}"
    assert res_auth.json()["user_id"] == "test_user_a"
    print("      [PASS] Verified identity 'test_user_a' from signed JWT token.\n", flush=True)

    # 3. Test Crypto Encryption & Masking
    print("[3/5] Testing AES-256 Secret Encryption & Masking...", flush=True)
    raw_token = "sk-ant-api03-super-secret-claude-token-123456789"
    encrypted = encrypt_secret(raw_token)
    decrypted = decrypt_secret(encrypted)
    masked = mask_secret(raw_token)

    assert encrypted != raw_token, "Token was not encrypted"
    assert decrypted == raw_token, "Decryption mismatch"
    assert "super-secret" not in masked, "Masking leaked secret string"
    print(f"      [PASS] Ciphertext: '{encrypted[:25]}...', Masked: '{masked}'\n", flush=True)

    # 4. Test Direct Provider Key Validation Flow (No Bypass)
    print("[4/5] Testing Provider Key Validation Flow...", flush=True)
    res_bad_key = client.post(
        "/api/integrations/openai/key",
        json={"api_key": "sk-invalid-test-key-123456789"},
        headers={"Authorization": f"Bearer {jwt_token}"}
    )
    assert res_bad_key.status_code == 400
    print("      [PASS] Invalid test key rejected by provider verification.\n", flush=True)

    # 5. Clean up test records
    print("[5/5] Cleaning up test records...", flush=True)
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_user_a", "test_user_b"])).delete(synchronize_session=False)
    db.commit()
    db.close()
    print("      [PASS] Test clean up complete.\n", flush=True)

if __name__ == "__main__":
    test_external_connections_system()
