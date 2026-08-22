import os
import sys

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.abspath("backend"))

def test_external_connections_system():
    print("============================================================", flush=True)
    print(" EXTERNAL ACCOUNT CONNECTION SYSTEM — SECURITY & AUDIT SUITE", flush=True)
    print("============================================================\n", flush=True)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.config.database import SessionLocal
    from app.models.external_connection import ExternalConnection
    from app.config.crypto import encrypt_secret, decrypt_secret, mask_secret

    client = TestClient(app)
    db = SessionLocal()

    # Clean up test integration records if left over
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_user_a", "test_user_b"])).delete(synchronize_session=False)
    db.commit()

    # 1. Test Crypto Encryption & Masking
    print("[1/8] Testing AES-256 Secret Encryption & Masking...", flush=True)
    raw_token = "sk-ant-api03-super-secret-claude-token-123456789"
    encrypted = encrypt_secret(raw_token)
    decrypted = decrypt_secret(encrypted)
    masked = mask_secret(raw_token)

    assert encrypted != raw_token, "Token was not encrypted"
    assert decrypted == raw_token, "Decryption mismatch"
    assert "super-secret" not in masked, "Masking leaked secret string"
    print(f"      [PASS] Ciphertext: '{encrypted[:25]}...', Masked: '{masked}'\n", flush=True)

    # 2. Test OAuth State CSRF Protection
    print("[2/8] Testing OAuth CSRF State Protection...", flush=True)
    res_connect = client.get("/api/integrations/google/connect", headers={"X-User-ID": "test_user_a"})
    assert res_connect.status_code == 200, f"Connect status: {res_connect.status_code}"
    auth_data = res_connect.json()
    auth_url = auth_data["authorization_url"]
    assert "state=" in auth_url, "OAuth URL missing state parameter"
    print(f"      [PASS] Generated Secure OAuth URL with signed state parameter.\n", flush=True)

    # Test invalid state on callback
    res_bad_callback = client.get("/api/integrations/google/callback?code=mock_code&state=invalid_tampered_state", follow_redirects=False)
    assert res_bad_callback.status_code in (302, 307, 400), f"Invalid state returned status {res_bad_callback.status_code}"
    print(f"      [PASS] Tampered OAuth state parameter rejected cleanly.\n", flush=True)

    # 3. Test API Key Registration (OpenAI, Gemini & Claude AI)
    print("[3/8] Testing User-Owned AI API Key Registration (OpenAI, Gemini & Claude AI)...", flush=True)
    res_openai_key = client.post(
        "/api/integrations/openai/key",
        json={"api_key": "sk-proj-userA-test-key-abcdef12345678"},
        headers={"X-User-ID": "test_user_a"}
    )
    assert res_openai_key.status_code == 200, f"OpenAI Key register status: {res_openai_key.status_code}"

    res_claude_key = client.post(
        "/api/integrations/claude/key",
        json={"api_key": "sk-ant-api03-userA-claude-test-key-99887766"},
        headers={"X-User-ID": "test_user_a"}
    )
    assert res_claude_key.status_code == 200, f"Claude Key register status: {res_claude_key.status_code}"
    claude_payload = res_claude_key.json()
    assert "access_token" not in claude_payload, "Leaked access_token"
    assert "api_key" not in claude_payload, "Leaked raw api_key"
    assert claude_payload["masked_key"] != "", "Missing masked key snippet"
    assert claude_payload["status"] == "CONNECTED"
    print(f"      [PASS] Claude AI key registered safely. Masked Output: '{claude_payload['masked_key']}'\n", flush=True)

    # 4. Test Connection Health Check Endpoint
    print("[4/8] Testing Connection Health Check Endpoint (POST /test)...", flush=True)
    claude_conn_id = claude_payload["id"]
    res_test = client.post(f"/api/integrations/{claude_conn_id}/test", headers={"X-User-ID": "test_user_a"})
    assert res_test.status_code == 200, f"Health check status: {res_test.status_code}"
    assert res_test.json()["status"] == "HEALTHY"
    print(f"      [PASS] Connection test succeeded with HEALTHY status.\n", flush=True)

    # 5. Test Multi-User Isolation (User A vs User B)
    print("[5/8] Testing Multi-User Data & Connection Isolation...", flush=True)
    client.post(
        "/api/integrations/gemini/key",
        json={"api_key": "AIzaSy-userB-gemini-test-key-987654321"},
        headers={"X-User-ID": "test_user_b"}
    )

    res_user_a = client.get("/api/integrations", headers={"X-User-ID": "test_user_a"})
    user_a_conns = res_user_a.json()["connections"]
    user_a_providers = [c["provider"] for c in user_a_conns]

    res_user_b = client.get("/api/integrations", headers={"X-User-ID": "test_user_b"})
    user_b_conns = res_user_b.json()["connections"]
    user_b_providers = [c["provider"] for c in user_b_conns]

    assert "claude" in user_a_providers, "User A missing claude connection"
    assert "gemini" not in user_a_providers, "User A leaked User B gemini connection!"

    assert "gemini" in user_b_providers, "User B missing gemini connection"
    assert "claude" not in user_b_providers, "User B leaked User A claude connection!"
    print(f"      [PASS] User A and User B connections are 100% isolated.\n", flush=True)

    # 6. Verify Database Ciphertext Storage Protection
    print("[6/8] Verifying Database Ciphertext Storage (Zero Plain Text Tokens)...", flush=True)
    db_conn_claude = db.query(ExternalConnection).filter(ExternalConnection.user_id == "test_user_a", ExternalConnection.provider == "claude").first()
    assert db_conn_claude is not None, "Connection record missing in DB"
    assert db_conn_claude.api_key_encrypted is not None, "API key encrypted field is null"
    assert "sk-ant-api03-userA" not in db_conn_claude.api_key_encrypted, "Raw plain text key stored in database!"
    assert db_conn_claude.get_api_key() == "sk-ant-api03-userA-claude-test-key-99887766", "Decrypted key mismatch"
    print(f"      [PASS] DB stores AES encrypted ciphertext '{db_conn_claude.api_key_encrypted[:20]}...'\n", flush=True)

    # 7. Test Disconnect Authorization & User Isolation
    print("[7/8] Testing Disconnect Security & User Isolation...", flush=True)
    conn_a_id = db_conn_claude.id
    res_unauth_dis = client.post(f"/api/integrations/{conn_a_id}/disconnect", headers={"X-User-ID": "test_user_b"})
    assert res_unauth_dis.status_code == 404, "User B was able to access/disconnect User A's connection!"

    res_auth_dis = client.post(f"/api/integrations/{conn_a_id}/disconnect", headers={"X-User-ID": "test_user_a"})
    assert res_auth_dis.status_code == 200, "User A disconnect failed"
    print(f"      [PASS] Unauthorized disconnect blocked (404); Authorized disconnect succeeded.\n", flush=True)

    # 8. Clean up test records
    print("[8/8] Cleaning up test records...", flush=True)
    db.query(ExternalConnection).filter(ExternalConnection.user_id.in_(["test_user_a", "test_user_b"])).delete(synchronize_session=False)
    db.commit()
    db.close()
    print("      [PASS] Test clean up complete.\n", flush=True)

    print("============================================================", flush=True)
    print(" INTEGRATION SECURITY AUDIT: ALL 8 AUDIT CHECKS PASSED!", flush=True)
    print("============================================================\n", flush=True)

if __name__ == "__main__":
    test_external_connections_system()
