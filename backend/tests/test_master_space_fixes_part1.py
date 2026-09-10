import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.services.master_service import MasterService

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def admin_user(db_session):
    u = db_session.query(User).filter(User.email == "fix1_admin@example.com").first()
    if not u:
        u = User(
            id="usr_fix1_admin",
            email="fix1_admin@example.com",
            name="Fix1 Admin",
            platform_role="SUPER_ADMIN",
            status="ACTIVE"
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
    return u

@pytest.fixture(scope="module")
def normal_user(db_session):
    u = db_session.query(User).filter(User.email == "fix1_normal@example.com").first()
    if not u:
        u = User(
            id="usr_fix1_normal",
            email="fix1_normal@example.com",
            name="Fix1 Normal User",
            platform_role="USER",
            status="ACTIVE"
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
    return u

@pytest.fixture(scope="module")
def admin_headers(admin_user):
    token = create_access_token(admin_user.id)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def normal_headers(normal_user):
    token = create_access_token(normal_user.id)
    return {"Authorization": f"Bearer {token}"}

# -------------------------------------------------------------------------
# 1. NORMAL USER BLOCKED FROM MASTER SPACE
# -------------------------------------------------------------------------
def test_normal_user_blocked_from_master_endpoints(normal_headers):
    endpoints = [
        "/api/master/dashboard",
        "/api/master/customers",
        "/api/master/websites",
        "/api/master/ai/control",
        "/api/master/credits",
        "/api/master/providers",
        "/api/master/activity",
        "/api/master/system-health",
        "/api/master/audit-logs"
    ]
    for ep in endpoints:
        res = client.get(ep, headers=normal_headers)
        assert res.status_code == 403, f"Endpoint {ep} should be forbidden for normal user, got {res.status_code}"

# -------------------------------------------------------------------------
# 2. LAST-ADMIN PRIVILEGE ESCALATION PREVENTION TEST
# -------------------------------------------------------------------------
def test_no_privilege_escalation_when_zero_active_admins(db_session, admin_user, normal_user, normal_headers):
    # Suspend Admin User
    admin_user.status = "SUSPENDED"
    db_session.commit()

    try:
        # Access Master endpoint as normal user
        res = client.get("/api/master/dashboard", headers=normal_headers)
        assert res.status_code == 403

        # Verify normal user WAS NOT auto-promoted to SUPER_ADMIN in DB
        db_session.refresh(normal_user)
        assert normal_user.platform_role == "USER"
    finally:
        # Restore Admin status
        admin_user.status = "ACTIVE"
        db_session.commit()

# -------------------------------------------------------------------------
# 3. AUTH ME ENDPOINT INCLUDES AUTHORITATIVE PLATFORM ROLE
# -------------------------------------------------------------------------
def test_auth_me_returns_authoritative_platform_role(admin_headers, normal_headers, admin_user, normal_user):
    res_admin = client.get("/api/auth/me", headers=admin_headers)
    assert res_admin.status_code == 200
    assert res_admin.json()["platform_role"] == "SUPER_ADMIN"

    res_normal = client.get("/api/auth/me", headers=normal_headers)
    assert res_normal.status_code == 200
    assert res_normal.json()["platform_role"] == "USER"

# -------------------------------------------------------------------------
# 4. CUSTOMER SUSPENSION ENFORCEMENT
# -------------------------------------------------------------------------
def test_customer_suspension_blocks_api_access(db_session, normal_user, normal_headers):
    normal_user.status = "SUSPENDED"
    db_session.commit()

    try:
        res = client.get("/api/ai/my-wallet", headers=normal_headers)
        assert res.status_code == 403
        assert "ACCOUNT_SUSPENDED" in res.json()["detail"]
    finally:
        normal_user.status = "ACTIVE"
        db_session.commit()

# -------------------------------------------------------------------------
# 5. IDENTITY ALIAS MATCHING & MULTI-TENANT ISOLATION
# -------------------------------------------------------------------------
def test_identity_alias_matching_and_tenant_isolation(db_session):
    # Create Customer A and Customer B
    cust_a = db_session.query(User).filter(User.email == "tenant_a@example.com").first()
    if not cust_a:
        cust_a = User(id="usr_tenant_a_id", email="tenant_a@example.com", name="Tenant A", platform_role="USER", status="ACTIVE")
        db_session.add(cust_a)
    
    cust_b = db_session.query(User).filter(User.email == "tenant_b@example.com").first()
    if not cust_b:
        cust_b = User(id="usr_tenant_b_id", email="tenant_b@example.com", name="Tenant B", platform_role="USER", status="ACTIVE")
        db_session.add(cust_b)
    db_session.commit()

    # Project A owned by Customer A via EMAIL format membership
    proj_a = db_session.query(Project).filter(Project.id == "prj_tenant_a").first()
    if not proj_a:
        proj_a = Project(id="prj_tenant_a", name="Site A", url="https://site-a.com", domain="site-a.com")
        db_session.add(proj_a)
        m_a = ProjectMembership(id="mem_tenant_a", project_id="prj_tenant_a", user_id="tenant_a@example.com", role="OWNER", status="ACTIVE")
        db_session.add(m_a)

    # Project B owned by Customer B via ID format membership
    proj_b = db_session.query(Project).filter(Project.id == "prj_tenant_b").first()
    if not proj_b:
        proj_b = Project(id="prj_tenant_b", name="Site B", url="https://site-b.com", domain="site-b.com")
        db_session.add(proj_b)
        m_b = ProjectMembership(id="mem_tenant_b", project_id="prj_tenant_b", user_id="usr_tenant_b_id", role="OWNER", status="ACTIVE")
        db_session.add(m_b)

    db_session.commit()

    # Query Master Detail for Customer A
    detail_a = MasterService.get_customer_detail(customer_id=cust_a.id, db=db_session)
    assert detail_a is not None
    site_urls_a = [w["url"] for w in detail_a["websites"]]
    assert "site-a.com" in site_urls_a
    assert "site-b.com" not in site_urls_a # Isolation check

    # Query Master Detail for Customer B
    detail_b = MasterService.get_customer_detail(customer_id=cust_b.id, db=db_session)
    assert detail_b is not None
    site_urls_b = [w["url"] for w in detail_b["websites"]]
    assert "site-b.com" in site_urls_b
    assert "site-a.com" not in site_urls_b # Isolation check
