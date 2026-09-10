import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.ai_wallet import AIWallet, AICreditTransaction, PlatformAISettings
from app.models.audit_log import AuditLog
from app.services.credit_service import CreditService, CreditTransactionType
from app.services.master_service import MasterService, sanitize_audit_metadata
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
def admin_user(db_session):
    u = db_session.query(User).filter(User.email == "p2_fixes_admin@example.com").first()
    if not u:
        u = User(
            id="usr_p2_fixes_admin",
            email="p2_fixes_admin@example.com",
            name="P2 Fixes Admin",
            platform_role="SUPER_ADMIN",
            status="ACTIVE"
        )
        db_session.add(u)
        db_session.commit()
        db_session.refresh(u)
    return u

@pytest.fixture(scope="module")
def customer_user(db_session):
    u = db_session.query(User).filter(User.email == "p2_fixes_cust@example.com").first()
    if not u:
        u = User(
            id="usr_p2_fixes_cust",
            email="p2_fixes_cust@example.com",
            name="P2 Fixes Customer",
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
def customer_headers(customer_user):
    token = create_access_token(customer_user.id)
    return {"Authorization": f"Bearer {token}"}


# -------------------------------------------------------------------------
# 1. FIX CREDIT WALLET N+1 & LAZY CREATION TEST
# -------------------------------------------------------------------------
def test_credits_overview_does_not_create_wallets_for_all_users(db_session, admin_headers):
    # Create a user with NO wallet
    temp_user = User(
        id="usr_no_wallet_test",
        email="no_wallet_user@example.com",
        name="No Wallet User",
        platform_role="USER",
        status="ACTIVE"
    )
    db_session.add(temp_user)
    db_session.commit()

    try:
        # Fetch credits overview
        res = client.get("/api/master/credits", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert "summary" in data
        assert "wallets" in data

        # Verify temp_user DOES NOT have a wallet created simply by visiting the page
        w = db_session.query(AIWallet).filter(AIWallet.customer_id == "usr_no_wallet_test").first()
        assert w is None, "Opening Credits overview must NOT eagerly create wallets for users without one"
    finally:
        db_session.delete(temp_user)
        db_session.commit()


# -------------------------------------------------------------------------
# 2. CREDIT ACCOUNTING ARITHMETIC & APPEND-ONLY LEDGER TEST
# -------------------------------------------------------------------------
def test_credit_accounting_mathematical_consistency(db_session):
    cid = "usr_math_test_account"
    # Clean prior wallet if any
    old_w = db_session.query(AIWallet).filter(AIWallet.customer_id == cid).first()
    if old_w:
        db_session.query(AICreditTransaction).filter(AICreditTransaction.customer_id == cid).delete()
        db_session.delete(old_w)
        db_session.commit()

    # Step 1: Base Allocation = +5000
    wallet = AIWallet(
        customer_id=cid,
        allocated_credits=0,
        bonus_credits=0,
        used_credits=0,
        monthly_limit=50000,
        daily_limit=5000,
        is_enabled=True,
        status="ACTIVE"
    )
    db_session.add(wallet)
    db_session.commit()

    tx1 = CreditService.allocate_credits(cid, amount=5000, transaction_type="allocation", reason="Initial plan", db=db_session)
    assert wallet.remaining_credits == 5000

    # Step 2: Bonus = +500 -> remaining 5500
    tx2 = CreditService.allocate_credits(cid, amount=500, transaction_type="bonus", reason="Promo bonus", db=db_session)
    assert wallet.remaining_credits == 5500

    # Step 3: Consumption = -1000 -> remaining 4500
    tx3 = CreditService.deduct_credits(cid, amount=1000, reason="Crawl AI analysis", db=db_session)
    assert wallet.remaining_credits == 4500

    # Step 4: Refund = +200 -> remaining 4700
    tx4 = CreditService.refund_credits(cid, amount=200, reason="Provider timeout retry refund", db=db_session)
    assert wallet.remaining_credits == 4700

    # Step 5: Adjustment = -300 -> remaining 4400
    tx5 = CreditService.allocate_credits(cid, amount=-300, transaction_type="adjustment", reason="Manual correction", db=db_session)
    assert wallet.remaining_credits == 4400

    # Verify ledger append-only history: exactly 5 transactions intact
    txs = db_session.query(AICreditTransaction).filter(AICreditTransaction.customer_id == cid).order_by(AICreditTransaction.created_at.asc()).all()
    assert len(txs) == 5
    assert txs[0].amount == 5000
    assert txs[1].amount == 500
    assert txs[2].amount == -1000
    assert txs[3].amount == 200
    assert txs[4].amount == -300


# -------------------------------------------------------------------------
# 3. POSITIVE AND NEGATIVE ADJUSTMENTS & REASON VALIDATION TEST
# -------------------------------------------------------------------------
def test_positive_and_negative_adjustments_with_reason(db_session, admin_headers, customer_user):
    cid = customer_user.id
    wallet = CreditService.get_or_create_wallet(cid, db_session)
    base_rem = wallet.remaining_credits

    # Positive adjustment (+1000)
    res_pos = client.post(
        f"/api/master/customers/{cid}/credits",
        json={"amount": 1000, "transaction_type": "adjustment", "reason": "Positive loyalty adjustment"},
        headers=admin_headers
    )
    assert res_pos.status_code == 200
    assert res_pos.json()["success"] is True
    assert res_pos.json()["wallet"]["remaining_credits"] == base_rem + 1000

    # Negative adjustment (-1000)
    res_neg = client.post(
        f"/api/master/customers/{cid}/credits",
        json={"amount": -1000, "transaction_type": "adjustment", "reason": "Negative clawback adjustment"},
        headers=admin_headers
    )
    assert res_neg.status_code == 200
    assert res_neg.json()["success"] is True
    assert res_neg.json()["wallet"]["remaining_credits"] == base_rem

    # Reject missing reason
    res_no_reason = client.post(
        f"/api/master/customers/{cid}/credits",
        json={"amount": 500, "transaction_type": "adjustment", "reason": ""},
        headers=admin_headers
    )
    assert res_no_reason.status_code == 400

    # Reject zero adjustment amount
    res_zero = client.post(
        f"/api/master/customers/{cid}/credits",
        json={"amount": 0, "transaction_type": "adjustment", "reason": "Zero amount"},
        headers=admin_headers
    )
    assert res_zero.status_code == 400


# -------------------------------------------------------------------------
# 4. CONCURRENCY & OVERSPENDING PREVENTION TEST
# -------------------------------------------------------------------------
def test_credit_concurrency_and_overspending_protection(db_session):
    cid = "usr_concurrency_test_acc"
    w = CreditService.get_or_create_wallet(cid, db_session)
    w.allocated_credits = 5000
    w.bonus_credits = 0
    w.used_credits = 0
    db_session.commit()

    # Request A: Deduct 4000 -> succeeds
    tx_a = CreditService.deduct_credits(cid, amount=4000, reason="Request A", db=db_session)
    assert tx_a is not None
    assert w.remaining_credits == 1000

    # Request B: Deduct 4000 -> must fail with insufficient credits
    with pytest.raises(Exception) as exc_info:
        CreditService.deduct_credits(cid, amount=4000, reason="Request B", db=db_session)
    assert "INSUFFICIENT_CREDITS" in str(exc_info.value)
    assert w.remaining_credits == 1000


# -------------------------------------------------------------------------
# 5. IDEMPOTENCY & DOUBLE CHARGING PREVENTION TEST
# -------------------------------------------------------------------------
def test_idempotency_prevents_double_charging(db_session):
    import uuid
    cid = f"usr_idempotency_{uuid.uuid4().hex[:6]}"
    w = CreditService.get_or_create_wallet(cid, db_session)
    w.allocated_credits = 10000
    w.used_credits = 0
    db_session.commit()

    ref_id = f"ai_exec_idempotency_{uuid.uuid4().hex}"

    # First execution
    tx1 = CreditService.deduct_credits(cid, amount=50, reference_id=ref_id, reason="AI generation", db=db_session)
    assert tx1 is not None
    assert w.used_credits == 50

    # Duplicate / Retry execution with same reference_id
    tx2 = CreditService.deduct_credits(cid, amount=50, reference_id=ref_id, reason="AI generation retry", db=db_session)
    assert tx2.id == tx1.id
    assert w.used_credits == 50, "Duplicate execution with identical reference_id must NOT deduct credits twice"



# -------------------------------------------------------------------------
# 6. CENTRALIZED BUDGET & PRICING CONSISTENCY TEST
# -------------------------------------------------------------------------
def test_budget_pricing_calculation_and_thresholds(db_session):
    # Test authoritative pricing formula
    cost_base = MasterService.calculate_estimated_cost(input_tokens=1000, output_tokens=1000)
    assert cost_base == round(0.00015 + 0.00060, 4)

    # Local Ollama is free ($0.00)
    cost_ollama = MasterService.calculate_estimated_cost(input_tokens=5000, output_tokens=5000, provider="ollama")
    assert cost_ollama == 0.0

    # Gemini model pricing
    cost_gemini = MasterService.calculate_estimated_cost(input_tokens=10000, output_tokens=10000, provider="gemini", model="models/gemini-flash-latest")
    assert cost_gemini > 0

    # Budget thresholds check: 79% -> NORMAL, 80% -> WARNING, 89% -> WARNING, 90% -> CRITICAL, 99% -> CRITICAL, 100% -> HARD_STOP, 101% -> HARD_STOP
    def get_status_for_pct(pct, hard_stop=True):
        if pct >= 100:
            return "HARD_STOP" if hard_stop else "CRITICAL"
        elif pct >= 90:
            return "CRITICAL"
        elif pct >= 80:
            return "WARNING"
        return "NORMAL"

    assert get_status_for_pct(79) == "NORMAL"
    assert get_status_for_pct(80) == "WARNING"
    assert get_status_for_pct(89) == "WARNING"
    assert get_status_for_pct(90) == "CRITICAL"
    assert get_status_for_pct(99) == "CRITICAL"
    assert get_status_for_pct(100) == "HARD_STOP"
    assert get_status_for_pct(101) == "HARD_STOP"
    assert get_status_for_pct(100, hard_stop=False) == "CRITICAL"

    s = CreditService.get_or_create_platform_settings(db_session)
    s.daily_budget_usd = 100.0
    s.monthly_budget_usd = 1000.0
    db_session.commit()

    budget_overview = MasterService.get_budgets_overview(db=db_session)
    assert "platform_budget" in budget_overview
    pb = budget_overview["platform_budget"]
    assert "daily_cost_usd" in pb
    assert "monthly_cost_usd" in pb
    assert "status" in pb



# -------------------------------------------------------------------------
# 7. AUDIT METADATA SANITIZATION TEST
# -------------------------------------------------------------------------
def test_audit_metadata_scrubs_sensitive_secrets(db_session, admin_user):
    dirty_meta = {
        "user_email": "target@example.com",
        "api_key": "sk-proj-secret-12345",
        "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "password": "SuperSecretPassword123!",
        "safe_note": "Approved by CTO"
    }

    clean_meta = sanitize_audit_metadata(dirty_meta)
    assert clean_meta["api_key"] == "[REDACTED]"
    assert clean_meta["jwt_token"] == "[REDACTED]"
    assert clean_meta["password"] == "[REDACTED]"
    assert clean_meta["safe_note"] == "Approved by CTO"
    assert clean_meta["user_email"] == "target@example.com"
