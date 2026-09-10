import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.ai_wallet import AIWallet, AICreditTransaction, PlatformAISettings
from app.services.credit_service import CreditService
from app.services.provider_routing_service import ProviderRoutingService
from app.config.auth import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module")
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def master_user(db_session):
    u = db_session.query(User).filter(User.email == "master_part2_admin@example.com").first()
    if not u:
        u = User(
            id="usr_master_part2_admin",
            email="master_part2_admin@example.com",
            name="Master Part2 Admin",
            platform_role="SUPER_ADMIN"
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
    return u

@pytest.fixture(scope="module")
def normal_user(db_session):
    u = db_session.query(User).filter(User.email == "normal_part2_customer@example.com").first()
    if not u:
        u = User(
            id="usr_normal_part2_customer",
            email="normal_part2_customer@example.com",
            name="Normal Part2 Customer",
            platform_role="CUSTOMER"
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
    return u

@pytest.fixture(scope="module")
def master_headers(master_user):
    token = create_access_token(master_user.id)
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope="module")
def normal_headers(normal_user):
    token = create_access_token(normal_user.id)
    return {"Authorization": f"Bearer {token}"}

# -------------------------------------------------------------------------
# 1. AI WALLETS & IMMUTABLE LEDGER TESTS
# -------------------------------------------------------------------------
def test_ai_wallet_creation_and_ledger(db_session, normal_user):
    wallet = CreditService.get_or_create_wallet(normal_user.id, db_session)
    assert wallet is not None
    assert wallet.customer_id == normal_user.id
    assert wallet.remaining_credits >= 0

    # Initial transaction check
    txs = db_session.query(AICreditTransaction).filter(AICreditTransaction.customer_id == normal_user.id).all()
    assert len(txs) >= 1

# -------------------------------------------------------------------------
# 2. CREDIT ALLOCATION, DEDUCTION, REFUND & CONCURRENCY
# -------------------------------------------------------------------------
def test_credit_deduction_and_refund(db_session, normal_user):
    cid = normal_user.id
    wallet = CreditService.get_or_create_wallet(cid, db_session)
    initial_rem = wallet.remaining_credits

    # Deduct 50 credits
    tx_ded = CreditService.deduct_ai_credits(cid, amount=50, task_type="test_req", db=db_session)
    assert tx_ded.amount == -50
    assert wallet.remaining_credits == initial_rem - 50

    # Refund 50 credits
    tx_ref = CreditService.refund_ai_credits(cid, amount=50, reason="Test refund", db=db_session)
    assert tx_ref.amount == 50
    assert wallet.remaining_credits == initial_rem

# -------------------------------------------------------------------------
# 3. GLOBAL KILL SWITCH & ENFORCEMENT
# -------------------------------------------------------------------------
def test_global_ai_kill_switch(db_session, master_headers, normal_user):
    cid = normal_user.id

    # Disable Global AI
    res = client.patch("/api/master/ai/control", json={"global_ai_enabled": False, "reason": "Testing kill switch"}, headers=master_headers)
    assert res.status_code == 200
    assert res.json()["global_ai_enabled"] is False

    # Attempt authorization check -> must raise HTTP 403
    with pytest.raises(Exception) as exc_info:
        CreditService.check_ai_authorization(cid, estimated_credits=1, db=db_session)
    assert "AI_DISABLED_GLOBALLY" in str(exc_info.value)

    # Re-enable Global AI
    res_enable = client.patch("/api/master/ai/control", json={"global_ai_enabled": True, "reason": "Testing restore"}, headers=master_headers)
    assert res_enable.status_code == 200
    assert res_enable.json()["global_ai_enabled"] is True

    # Confirm platform settings in DB are restored
    s = CreditService.get_or_create_platform_settings(db_session)
    s.global_ai_enabled = True
    db_session.commit()

# -------------------------------------------------------------------------
# 4. CUSTOMER-LEVEL KILL SWITCH & LIMITS
# -------------------------------------------------------------------------
def test_customer_kill_switch_and_limits(db_session, master_headers, normal_user):
    cid = normal_user.id

    # Disable AI for this customer
    res = client.patch(f"/api/master/customers/{cid}/ai-settings", json={"is_enabled": False, "reason": "Customer kill switch test"}, headers=master_headers)
    assert res.status_code == 200
    assert res.json()["wallet"]["is_enabled"] is False

    # Check authorization -> must fail with AI_DISABLED_FOR_CUSTOMER
    with pytest.raises(Exception) as exc_info:
        CreditService.check_ai_authorization(cid, estimated_credits=1, db=db_session)
    assert "AI_DISABLED_FOR_CUSTOMER" in str(exc_info.value)

    # Re-enable AI for customer
    client.patch(f"/api/master/customers/{cid}/ai-settings", json={"is_enabled": True, "daily_limit": 10}, headers=master_headers)
    
    # Check daily limit violation
    CreditService.deduct_ai_credits(cid, amount=10, task_type="consumption", db=db_session)
    with pytest.raises(Exception) as exc_info:
        CreditService.check_ai_authorization(cid, estimated_credits=1, db=db_session)
    assert "DAILY_LIMIT_EXCEEDED" in str(exc_info.value)

    # Reset daily limit back to 5000
    client.patch(f"/api/master/customers/{cid}/ai-settings", json={"daily_limit": 5000}, headers=master_headers)

# -------------------------------------------------------------------------
# 5. PROVIDER ROUTING & FAILOVER
# -------------------------------------------------------------------------
def test_provider_routing_failover(db_session, master_headers):
    res_route = client.patch("/api/master/providers/routing", json={"primary_provider": "gemini", "fallback_provider": "ollama"}, headers=master_headers)
    assert res_route.status_code == 200
    assert res_route.json()["primary_provider"] == "gemini"
    assert res_route.json()["fallback_provider"] == "ollama"

# -------------------------------------------------------------------------
# 6. SECURITY & RBAC ISOLATION
# -------------------------------------------------------------------------
def test_rbac_security(normal_headers):
    # Customer user calling master endpoints must get 403 Forbidden
    r1 = client.get("/api/master/ai/control", headers=normal_headers)
    assert r1.status_code == 403

    r2 = client.get("/api/master/credits", headers=normal_headers)
    assert r2.status_code == 403

    r3 = client.patch("/api/master/ai/control", json={"global_ai_enabled": False}, headers=normal_headers)
    assert r3.status_code == 403

# -------------------------------------------------------------------------
# 7. CUSTOMER SELF-SERVICE ENDPOINT
# -------------------------------------------------------------------------
def test_customer_my_wallet(normal_headers):
    res = client.get("/api/ai/my-wallet", headers=normal_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "remaining_credits" in data
    assert "monthly_limit" in data
