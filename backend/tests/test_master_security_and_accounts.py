import os
import json
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.audit_log import AuditLog
from app.config.security import get_password_hash
from app.config.auth import create_access_token, ensure_root_super_master

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_test_master_environment():
    ensure_root_super_master()
    db = SessionLocal()
    try:
        # Create a standard customer user
        customer = db.query(User).filter(User.id == "customer_test_user@example.com").first()
        if not customer:
            customer = User(
                id="customer_test_user@example.com",
                email="customer_test_user@example.com",
                name="Regular Customer",
                password_hash=get_password_hash("CustomerPass123!"),
                platform_role="USER",
                status="ACTIVE",
                permissions_json="[]"
            )
            db.add(customer)
            db.commit()
    finally:
        db.close()

def test_root_super_master_login_success():
    """TEST 1: Correct root Master credentials authenticate successfully."""
    res = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "Uis001Digital"
    })
    assert res.status_code == 200, f"Expected 200, got {res.status_code}: {res.text}"
    data = res.json()
    assert data["status"] == "success"
    assert "access_token" in data
    assert data["user"]["platform_role"] == "SUPER_MASTER"
    assert "*" in data["user"]["permissions"]

def test_master_login_invalid_credentials():
    """TEST 2: Incorrect Master password returns 401 Unauthorized."""
    res = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "WrongPassword999!"
    })
    assert res.status_code == 401

def test_customer_cannot_login_to_master():
    """TEST 3: Standard Customer attempting Master login is rejected."""
    res = client.post("/api/master/login", json={
        "login_id": "customer_test_user@example.com",
        "password": "CustomerPass123!"
    })
    assert res.status_code == 403
    assert "Master Admin privileges" in res.json()["detail"]

def test_customer_token_blocked_on_master_api():
    """TEST 4: Customer JWT token receives 403 Forbidden on Master endpoints."""
    cust_token = create_access_token(user_id="customer_test_user@example.com")
    res = client.get("/api/master/dashboard", headers={"Authorization": f"Bearer {cust_token}"})
    assert res.status_code == 403

def test_unauthenticated_request_blocked():
    """TEST 5: Unauthenticated access to Master APIs returns 401."""
    res = client.get("/api/master/dashboard")
    assert res.status_code == 401

def test_super_master_creates_selective_master_admin():
    """TEST 6 & 10: Super Master creates Master Admin with selective permissions."""
    root_token = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "Uis001Digital"
    }).json()["access_token"]

    admin_login_id = "test_selective_admin_01"
    
    # Cleanup if exists
    db = SessionLocal()
    try:
        old = db.query(User).filter(User.id == admin_login_id).first()
        if old:
            db.delete(old)
            db.commit()
    finally:
        db.close()

    res = client.post("/api/master/accounts", headers={"Authorization": f"Bearer {root_token}"}, json={
        "login_id": admin_login_id,
        "name": "Selective Admin One",
        "password": "AdminPassword123!",
        "confirm_password": "AdminPassword123!",
        "role": "MASTER_ADMIN",
        "full_authority": False,
        "permissions": ["master.customers.view", "master.websites.view"]
    })
    assert res.status_code == 200, res.text
    account = res.json()["account"]
    assert account["id"] == admin_login_id
    assert account["role"] == "MASTER_ADMIN"
    assert "master.customers.view" in account["permissions"]
    assert "master.credits.view" not in account["permissions"]

    # Authenticate as the newly created selective Master Admin
    login_res = client.post("/api/master/login", json={
        "login_id": admin_login_id,
        "password": "AdminPassword123!"
    })
    assert login_res.status_code == 200
    admin_token = login_res.json()["access_token"]

    # 1. Permitted endpoint works (customers.view)
    cust_res = client.get("/api/master/customers", headers={"Authorization": f"Bearer {admin_token}"})
    assert cust_res.status_code == 200

    # 2. Restricted endpoint returns 403 (credits.view)
    cred_res = client.get("/api/master/credits", headers={"Authorization": f"Bearer {admin_token}"})
    assert cred_res.status_code == 403
    assert "PERMISSION_DENIED" in cred_res.json()["detail"]

def test_privilege_escalation_prevention():
    """TEST 7 & 8: Limited Master Admin cannot promote to Super Master or grant unheld permissions."""
    root_token = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "Uis001Digital"
    }).json()["access_token"]

    # 1. Admin without master.master_accounts.create is blocked at endpoint guard
    login_res = client.post("/api/master/login", json={
        "login_id": "test_selective_admin_01",
        "password": "AdminPassword123!"
    })
    admin_token = login_res.json()["access_token"]

    res_blocked = client.post("/api/master/accounts", headers={"Authorization": f"Bearer {admin_token}"}, json={
        "login_id": "blocked_attempt",
        "name": "Blocked",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "MASTER_ADMIN",
        "full_authority": False,
        "permissions": ["master.customers.view"]
    })
    assert res_blocked.status_code == 403
    assert "PERMISSION_DENIED" in res_blocked.json()["detail"]

    # 2. Create an admin WITH master.master_accounts.create, but WITHOUT master.credits.manage
    del_admin_id = "test_delegation_admin_02"
    db = SessionLocal()
    try:
        old = db.query(User).filter(User.id == del_admin_id).first()
        if old:
            db.delete(old)
            db.commit()
    finally:
        db.close()

    client.post("/api/master/accounts", headers={"Authorization": f"Bearer {root_token}"}, json={
        "login_id": del_admin_id,
        "name": "Delegator Admin",
        "password": "AdminPassword123!",
        "confirm_password": "AdminPassword123!",
        "role": "MASTER_ADMIN",
        "full_authority": False,
        "permissions": ["master.master_accounts.create", "master.customers.view"]
    })

    del_admin_token = client.post("/api/master/login", json={
        "login_id": del_admin_id,
        "password": "AdminPassword123!"
    }).json()["access_token"]

    # Attempt to promote someone to SUPER_MASTER
    res_super = client.post("/api/master/accounts", headers={"Authorization": f"Bearer {del_admin_token}"}, json={
        "login_id": "escalated_user",
        "name": "Escalated",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "SUPER_MASTER",
        "full_authority": True
    })
    assert res_super.status_code == 403
    assert "PRIVILEGE_ESCALATION_DENIED" in res_super.json()["detail"]

    # Attempt to delegate unheld permission (master.credits.manage)
    res_deleg = client.post("/api/master/accounts", headers={"Authorization": f"Bearer {del_admin_token}"}, json={
        "login_id": "unheld_perm_user",
        "name": "Unheld",
        "password": "Password123!",
        "confirm_password": "Password123!",
        "role": "MASTER_ADMIN",
        "full_authority": False,
        "permissions": ["master.credits.manage"]
    })
    assert res_deleg.status_code == 403
    assert "DELEGATION_DENIED" in res_deleg.json()["detail"]

def test_super_master_protection():
    """TEST 12 & 13: Super Master account cannot be disabled or deleted."""
    root_token = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "Uis001Digital"
    }).json()["access_token"]

    # Attempt to disable Super Master
    res_dis = client.post("/api/master/accounts/Kirito@420/disable", headers={"Authorization": f"Bearer {root_token}"})
    assert res_dis.status_code == 403
    assert "SUPER_MASTER_PROTECTED" in res_dis.json()["detail"]

    # Attempt to delete Super Master
    res_del = client.delete("/api/master/accounts/Kirito@420", headers={"Authorization": f"Bearer {root_token}"})
    assert res_del.status_code == 403
    assert "SUPER_MASTER_PROTECTED" in res_del.json()["detail"]

def test_account_disabling_and_session_revocation():
    """TEST 14 & 15: Disabling an account and revoking sessions immediately rejects requests."""
    root_token = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "Uis001Digital"
    }).json()["access_token"]

    # Create temporary admin
    temp_id = "test_temp_admin_revocation"
    db = SessionLocal()
    try:
        old = db.query(User).filter(User.id == temp_id).first()
        if old:
            db.delete(old)
            db.commit()
    finally:
        db.close()

    client.post("/api/master/accounts", headers={"Authorization": f"Bearer {root_token}"}, json={
        "login_id": temp_id,
        "name": "Temp Admin",
        "password": "TempPass123!",
        "confirm_password": "TempPass123!",
        "role": "MASTER_ADMIN",
        "full_authority": True
    })

    # Log in as temp admin
    temp_token = client.post("/api/master/login", json={
        "login_id": temp_id,
        "password": "TempPass123!"
    }).json()["access_token"]

    # Verify active access
    assert client.get("/api/master/dashboard", headers={"Authorization": f"Bearer {temp_token}"}).status_code == 200

    # Root Super Master disables the account
    dis_res = client.post(f"/api/master/accounts/{temp_id}/disable", headers={"Authorization": f"Bearer {root_token}"})
    assert dis_res.status_code == 200

    # Verify subsequent requests are rejected
    assert client.get("/api/master/dashboard", headers={"Authorization": f"Bearer {temp_token}"}).status_code == 403

    # Verify login is rejected
    assert client.post("/api/master/login", json={"login_id": temp_id, "password": "TempPass123!"}).status_code == 403

def test_no_passwords_or_secrets_in_api_response():
    """TEST 16: API responses never expose password hashes or sensitive secrets."""
    root_token = client.post("/api/master/login", json={
        "login_id": "Kirito@420",
        "password": "Uis001Digital"
    }).json()["access_token"]

    res = client.get("/api/master/accounts", headers={"Authorization": f"Bearer {root_token}"})
    assert res.status_code == 200
    text_content = res.text

    assert "password_hash" not in text_content
    assert "argon2" not in text_content
    assert "$2b$" not in text_content
    assert "bcrypt" not in text_content
