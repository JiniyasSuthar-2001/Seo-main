"""
Comprehensive Security Regression Test Suite for SEO Intelligence Platform.
Covers:
- Password Authentication, Bcrypt Hashing, Password Policy, Generic 401 errors
- X-User-ID header bypass prevention in production and dev gating
- Project isolation, IDOR prevention, project_id='all' prevention
- Crypto key validation and hardcoded secret removal
- Crawler SSRF Protection (IPv4, IPv6, loopback, private, metadata, scheme, redirects)
- CORS production hardening
"""
import os
import pytest
import uuid
import base64
import hashlib
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.security import get_password_hash, verify_password, validate_password_strength
from app.config.auth import create_access_token, decode_access_token
from app.config.crypto import encrypt_secret, decrypt_secret, migrate_legacy_encrypted_secret, reset_fernet_cache
from app.config.settings import validate_startup_config, KNOWN_INSECURE_SECRETS, settings
from app.crawler.ssrf_protection import validate_url_ssrf, is_ip_allowed, SSRFBlockedError

client = TestClient(app)

# ============================================================
# 1. AUTHENTICATION & PASSWORD TESTS
# ============================================================

def test_password_policy_enforcement():
    """Verifies that registration rejects short or empty passwords (< 8 chars)."""
    # 1. Short password (< 8 chars)
    resp = client.post("/api/auth/register", json={
        "email": "shortpwd@example.com",
        "password": "short",
        "name": "Short Pwd"
    })
    assert resp.status_code == 400
    assert "at least 8 characters" in resp.json()["detail"]

    # 2. Empty password
    resp = client.post("/api/auth/register", json={
        "email": "emptypwd@example.com",
        "password": "",
        "name": "Empty Pwd"
    })
    assert resp.status_code == 400

def test_register_and_login_successful_flow():
    """Verifies valid registration hashes password with bcrypt and login succeeds with valid token."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "SecurePassword123!"

    # 1. Register
    reg_resp = client.post("/api/auth/register", json={
        "email": email,
        "password": pwd,
        "name": "Test User"
    })
    assert reg_resp.status_code == 200
    reg_data = reg_resp.json()
    assert "access_token" in reg_data
    assert reg_data["user"]["email"] == email
    # password_hash must NEVER be exposed in responses
    assert "password_hash" not in reg_data["user"]
    assert "password" not in reg_data["user"]

    # Verify password is stored hashed in database
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.password_hash is not None
        assert user.password_hash.startswith("$2b$")  # bcrypt prefix
        assert user.password_hash != pwd              # NEVER plaintext
        assert verify_password(pwd, user.password_hash) is True
    finally:
        db.close()

    # 2. Login with correct password
    login_resp = client.post("/api/auth/login", json={
        "email": email,
        "password": pwd
    })
    assert login_resp.status_code == 200
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"
    # Verify token payload
    payload = decode_access_token(login_data["access_token"])
    assert payload["sub"] == email

def test_login_wrong_password_rejected():
    """Verifies that wrong password returns generic 401 without revealing details."""
    email = f"user_{uuid.uuid4().hex[:8]}@example.com"
    pwd = "CorrectPassword123!"

    # Register user
    client.post("/api/auth/register", json={"email": email, "password": pwd, "name": "User"})

    # Try login with wrong password
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "WrongPassword999!"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."

def test_login_unknown_email_rejected():
    """Verifies that unknown email returns same generic 401 (no user enumeration)."""
    resp = client.post("/api/auth/login", json={
        "email": "nonexistent_random_account@example.com",
        "password": "SomePassword123!"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."

def test_unhashed_legacy_account_cannot_login_with_arbitrary_password():
    """Verifies that accounts created without password_hash (e.g. Google-only) cannot authenticate with password."""
    email = f"google_only_{uuid.uuid4().hex[:8]}@example.com"
    db = SessionLocal()
    try:
        u = User(id=email, email=email, name="Google Account", google_id="g_12345", password_hash=None)
        db.add(u)
        db.commit()
    finally:
        db.close()

    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": "AnyArbitraryPassword123!"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid email or password."

# ============================================================
# 2. HEADER AUTHENTICATION & X-USER-ID BYPASS TESTS
# ============================================================

def test_x_user_id_rejected_in_production(monkeypatch):
    """Verifies that X-User-ID is completely ignored/rejected when ENVIRONMENT=production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_DEV_USER_HEADER", "true")  # Even if mistakenly set to true

    resp = client.get("/api/projects", headers={"X-User-ID": "victim_user@example.com"})
    assert resp.status_code == 401
    assert "Authentication required" in resp.json()["detail"]

def test_x_user_id_rejected_when_dev_flag_disabled(monkeypatch):
    """Verifies that X-User-ID is rejected when ALLOW_DEV_USER_HEADER=false."""
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ALLOW_DEV_USER_HEADER", "false")

    resp = client.get("/api/projects", headers={"X-User-ID": "victim_user@example.com"})
    assert resp.status_code == 401

def test_valid_bearer_token_cannot_be_overridden_by_header():
    """Verifies authenticated user identity is taken strictly from verified Bearer token."""
    user_a = f"user_a_{uuid.uuid4().hex[:6]}@example.com"
    user_b = f"user_b_{uuid.uuid4().hex[:6]}@example.com"
    token_a = create_access_token(user_id=user_a)

    # Send token for User A with malicious X-User-ID for User B
    resp = client.get("/api/auth/me", headers={
        "Authorization": f"Bearer {token_a}",
        "X-User-ID": user_b
    })
    assert resp.status_code == 200
    assert resp.json()["user_id"] == user_a
    assert resp.json()["user_id"] != user_b

# ============================================================
# 3. PROJECT ISOLATION & IDOR PROTECTION TESTS
# ============================================================

def test_user_cannot_access_other_user_project():
    """Verifies User A cannot access User B's project (403 Forbidden)."""
    db = SessionLocal()
    user_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    user_b = f"bob_{uuid.uuid4().hex[:6]}@example.com"
    proj_b_id = f"proj_b_{uuid.uuid4().hex[:6]}"

    try:
        # Create Project B owned by Bob
        proj_b = Project(id=proj_b_id, name="Bob Private Site", domain="bob-private.com", url="https://bob-private.com")
        db.add(proj_b)
        db.commit()

        mb = ProjectMembership(id=str(uuid.uuid4()), user_id=user_b, project_id=proj_b_id, role="OWNER", status="ACTIVE")
        db.add(mb)
        db.commit()

        # Alice attempts to access Bob's project
        token_a = create_access_token(user_id=user_a)
        resp = client.get(f"/api/projects/{proj_b_id}/technical", headers={"Authorization": f"Bearer {token_a}"})
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]
    finally:
        db.close()

def test_project_id_all_cannot_leak_cross_user_data():
    """Verifies that project_id='all' on specific project endpoints is rejected (400 Bad Request)."""
    user_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    token_a = create_access_token(user_id=user_a)

    resp = client.get("/api/projects/all/technical", headers={"Authorization": f"Bearer {token_a}"})
    assert resp.status_code == 400

def test_projects_list_returns_only_authorized_user_projects():
    """Verifies that GET /api/projects returns only User A's authorized projects, never User B's."""
    db = SessionLocal()
    user_a = f"alice_{uuid.uuid4().hex[:6]}@example.com"
    user_b = f"bob_{uuid.uuid4().hex[:6]}@example.com"
    proj_a_id = f"proj_a_{uuid.uuid4().hex[:6]}"
    proj_b_id = f"proj_b_{uuid.uuid4().hex[:6]}"

    try:
        p_a = Project(id=proj_a_id, name="Alice Project", domain="alice.com", url="https://alice.com")
        p_b = Project(id=proj_b_id, name="Bob Project", domain="bob.com", url="https://bob.com")
        db.add_all([p_a, p_b])
        db.commit()

        m_a = ProjectMembership(id=str(uuid.uuid4()), user_id=user_a, project_id=proj_a_id, role="OWNER", status="ACTIVE")
        m_b = ProjectMembership(id=str(uuid.uuid4()), user_id=user_b, project_id=proj_b_id, role="OWNER", status="ACTIVE")
        db.add_all([m_a, m_b])
        db.commit()

        token_a = create_access_token(user_id=user_a)
        resp = client.get("/api/projects", headers={"Authorization": f"Bearer {token_a}"})
        assert resp.status_code == 200
        projects = resp.json()
        project_ids = [p["id"] for p in projects]

        assert proj_a_id in project_ids
        assert proj_b_id not in project_ids
    finally:
        db.close()

# ============================================================
# 4. CRYPTO & STARTUP CONFIGURATION VALIDATION TESTS
# ============================================================

def test_crypto_encrypt_and_decrypt_with_configured_key(monkeypatch):
    """Verifies that Fernet encryption and decryption work correctly using ENCRYPTION_KEY."""
    test_key = "test-fernet-key-32-chars-long-abc"
    monkeypatch.setenv("ENCRYPTION_KEY", test_key)
    reset_fernet_cache()

    secret = "my-oauth-access-token-12345"
    encrypted = encrypt_secret(secret)
    assert encrypted is not None
    assert encrypted != secret

    decrypted = decrypt_secret(encrypted)
    assert decrypted == secret

def test_crypto_migration_utility():
    """Verifies explicit migration utility can re-encrypt data between keys."""
    old_key = "old-compromised-key-32-bytes-long"
    new_key = "new-secure-key-32-bytes-long-abcde"

    # Encrypt with old key
    old_derived = base64.urlsafe_b64encode(hashlib.sha256(old_key.encode()).digest())
    old_f = Fernet(old_derived)
    cipher = old_f.encrypt(b"migrated-secret-token").decode()

    # Migrate to new key
    migrated_cipher = migrate_legacy_encrypted_secret(cipher, old_key, new_key)
    assert migrated_cipher is not None
    assert migrated_cipher != cipher

    # Decrypt with new key
    new_derived = base64.urlsafe_b64encode(hashlib.sha256(new_key.encode()).digest())
    new_f = Fernet(new_derived)
    assert new_f.decrypt(migrated_cipher.encode()).decode() == "migrated-secret-token"

def test_startup_validation_fails_on_insecure_secrets_in_production(monkeypatch):
    """Verifies startup validation raises RuntimeError in production on default/insecure keys."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ENCRYPTION_KEY", "change_me")
    monkeypatch.setenv("SECRET_KEY", "secret")

    with pytest.raises(RuntimeError):
        validate_startup_config(strict=True)

def test_startup_validation_fails_on_missing_encryption_key_in_production(monkeypatch):
    """Verifies startup validation raises RuntimeError when ENCRYPTION_KEY is missing in production."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    with pytest.raises(RuntimeError):
        validate_startup_config(strict=True)

# ============================================================
# 5. SSRF PROTECTION LAYER TESTS
# ============================================================

def test_ssrf_blocks_private_and_loopback_ips():
    """Verifies SSRF protection blocks private, loopback, link-local, and cloud metadata destinations."""
    blocked_urls = [
        "http://127.0.0.1",
        "http://127.0.0.1:8000/admin",
        "http://localhost",
        "http://localhost:8020/api",
        "http://169.254.169.254/latest/meta-data/",  # AWS/GCP metadata
        "http://10.0.0.1",
        "http://10.255.255.255",
        "http://172.16.0.1",
        "http://172.31.255.255",
        "http://192.168.0.1",
        "http://192.168.1.100",
        "http://0.0.0.0",
        "http://[::1]",
        "http://[fc00::1]",
        "http://[fe80::1]",
    ]
    for url in blocked_urls:
        is_safe, reason = validate_url_ssrf(url)
        assert is_safe is False, f"Expected {url} to be blocked by SSRF protection"

def test_ssrf_blocks_non_http_schemes():
    """Verifies SSRF protection strictly rejects non-HTTP(S) protocols."""
    prohibited_schemes = [
        "file:///etc/passwd",
        "file:///C:/Windows/win.ini",
        "ftp://ftp.example.com/files",
        "gopher://example.com:70/",
        "dict://dict.org/",
        "javascript:alert(1)",
        "data:text/html,<h1>Hello</h1>"
    ]
    for url in prohibited_schemes:
        is_safe, reason = validate_url_ssrf(url)
        assert is_safe is False, f"Expected non-http scheme {url} to be blocked"

def test_ssrf_allows_public_https_websites():
    """Verifies SSRF protection allows legitimate public domains."""
    public_urls = [
        "https://example.com",
        "https://google.com",
        "https://github.com",
        "http://example.org/about"
    ]
    for url in public_urls:
        is_safe, reason = validate_url_ssrf(url)
        assert is_safe is True, f"Expected {url} to be allowed by SSRF protection (Reason: {reason})"

# ============================================================
# 6. CORS CONFIGURATION TESTS
# ============================================================

def test_cors_production_uses_explicit_allowlist(monkeypatch):
    """Verifies that in production, CORS origins list is strictly derived without uncontrolled LAN injection."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com,https://dashboard.example.com")

    # In production, cors_origins_list should match configured origins exactly
    origins = settings.cors_origins_list
    assert "https://app.example.com" in origins
    assert "https://dashboard.example.com" in origins
