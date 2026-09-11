import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime

from app.main import app
from app.config.database import get_db, SessionLocal
from app.config.auth import create_access_token
from app.config.security import get_password_hash
from app.models.user import User, AccountStatus
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.ai_wallet import AIWallet, PlatformAISettings, AICreditTransaction
from app.services.credit_service import CreditService
from app.services.ai_access_service import AIAccessService

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    db: Session = SessionLocal()
    try:
        # Reset platform settings to enabled default
        settings = CreditService.get_or_create_platform_settings(db)
        settings.global_ai_enabled = True
        settings.new_requests_enabled = True
        settings.background_ai_enabled = True
        settings.ai_reports_enabled = True
        db.commit()
    finally:
        db.close()

def create_test_customer(customer_id="cust_ai_test_1", email="cust_ai_1@example.com", status="ACTIVE"):
    db: Session = SessionLocal()
    try:
        from app.models.ai_usage_log import AIUsageLog
        db.query(AICreditTransaction).filter(AICreditTransaction.customer_id == customer_id).delete()
        db.query(AIUsageLog).filter(AIUsageLog.user_id == customer_id).delete()
        db.commit()

        u = db.query(User).filter(User.id == customer_id).first()
        if not u:
            u = User(
                id=customer_id,
                email=email,
                name="AI Test Customer",
                password_hash=get_password_hash("Password123!"),
                platform_role="USER",
                status=status
            )
            db.add(u)
        else:
            u.status = status
            u.password_hash = get_password_hash("Password123!")
        db.commit()
        db.refresh(u)
        return u
    finally:
        db.close()

def create_test_project(project_id="proj_ai_test_1", user_id="cust_ai_test_1", domain="testsite.com"):
    db: Session = SessionLocal()
    try:
        p = db.query(Project).filter(Project.id == project_id).first()
        if not p:
            p = Project(
                id=project_id,
                name="Test AI Project",
                url=f"https://{domain}"
            )
            db.add(p)
            db.commit()
            db.refresh(p)

        m = db.query(ProjectMembership).filter(
            ProjectMembership.project_id == project_id,
            ProjectMembership.user_id == user_id
        ).first()
        if not m:
            m = ProjectMembership(
                id=f"mem_{project_id}_{user_id}",
                project_id=project_id,
                user_id=user_id,
                role="owner",
                status="ACTIVE"
            )
            db.add(m)
            db.commit()
        return p
    finally:
        db.close()


def test_global_ai_kill_switch():
    """TEST A & B: Global AI enabled vs disabled"""
    create_test_customer("cust_global_ai", "global_ai@example.com", "ACTIVE")
    create_test_project("proj_global_ai", "cust_global_ai", "globalsite.com")
    token = create_access_token("cust_global_ai")

    db = SessionLocal()
    try:
        # 1. Global AI Enabled
        settings = CreditService.get_or_create_platform_settings(db)
        settings.global_ai_enabled = True
        db.commit()
    finally:
        db.close()

    with patch("app.llm.seo_analyst.SEOAnalystAgent.chat_with_data") as mock_chat:
        mock_chat.return_value = {"status": "success", "is_llm_generated": True, "answer": "Hello"}
        res = client.post(
            "/api/projects/proj_global_ai/ai/chat",
            json={"query": "test query"},
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200

    # 2. Disable Global AI
    db = SessionLocal()
    try:
        settings = CreditService.get_or_create_platform_settings(db)
        settings.global_ai_enabled = False
        db.commit()
    finally:
        db.close()

    res = client.post(
        "/api/projects/proj_global_ai/ai/chat",
        json={"query": "test query"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403
    assert "AI services are temporarily unavailable" in res.json().get("detail", "")


def test_customer_ai_enable_disable_isolation():
    """TEST C & D: Customer AI disabled vs another customer still enabled"""
    create_test_customer("cust_disabled", "disabled@example.com", "ACTIVE")
    create_test_project("proj_disabled", "cust_disabled", "disabledsite.com")
    token_disabled = create_access_token("cust_disabled")

    create_test_customer("cust_enabled", "enabled@example.com", "ACTIVE")
    create_test_project("proj_enabled", "cust_enabled", "enabledsite.com")
    token_enabled = create_access_token("cust_enabled")

    db = SessionLocal()
    try:
        # Disable AI for cust_disabled
        w_disabled = CreditService.get_or_create_wallet("cust_disabled", db)
        w_disabled.is_enabled = False
        w_disabled.status = "DISABLED"

        # Ensure cust_enabled has AI enabled
        w_enabled = CreditService.get_or_create_wallet("cust_enabled", db)
        w_enabled.is_enabled = True
        w_enabled.status = "ACTIVE"
        db.commit()
    finally:
        db.close()

    # Disabled customer request should fail with 403
    res_dis = client.post(
        "/api/projects/proj_disabled/ai/chat",
        json={"query": "test query"},
        headers={"Authorization": f"Bearer {token_disabled}"}
    )
    assert res_dis.status_code == 403
    assert "AI access is currently disabled for this account" in res_dis.json().get("detail", "")

    # Enabled customer request should succeed
    with patch("app.llm.seo_analyst.SEOAnalystAgent.chat_with_data") as mock_chat:
        mock_chat.return_value = {"status": "success", "is_llm_generated": True, "answer": "OK"}
        res_en = client.post(
            "/api/projects/proj_enabled/ai/chat",
            json={"query": "test query"},
            headers={"Authorization": f"Bearer {token_enabled}"}
        )
        assert res_en.status_code == 200


def test_daily_ai_limit_enforcement():
    """TEST E: Daily limit reached rejects next request"""
    create_test_customer("cust_daily", "daily@example.com", "ACTIVE")
    create_test_project("proj_daily", "cust_daily", "dailysite.com")
    token = create_access_token("cust_daily")

    db = SessionLocal()
    try:
        w = CreditService.get_or_create_wallet("cust_daily", db)
        w.daily_limit = 2
        w.is_enabled = True
        w.status = "ACTIVE"
        db.commit()
    finally:
        db.close()

    with patch("app.llm.seo_analyst.SEOAnalystAgent.chat_with_data") as mock_chat:
        mock_chat.return_value = {"status": "success", "is_llm_generated": True, "answer": "Answer"}
        
        # 1st request
        r1 = client.post("/api/projects/proj_daily/ai/chat", json={"query": "q1"}, headers={"Authorization": f"Bearer {token}"})
        assert r1.status_code == 200

        # 2nd request
        r2 = client.post("/api/projects/proj_daily/ai/chat", json={"query": "q2"}, headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 200

        # 3rd request should exceed daily limit (2)
        r3 = client.post("/api/projects/proj_daily/ai/chat", json={"query": "q3"}, headers={"Authorization": f"Bearer {token}"})
        assert r3.status_code == 429
        assert "daily AI usage limit has been reached" in r3.json().get("detail", "")


def test_monthly_ai_limit_enforcement():
    """TEST F: Monthly limit reached rejects next request"""
    create_test_customer("cust_monthly", "monthly@example.com", "ACTIVE")
    create_test_project("proj_monthly", "cust_monthly", "monthlysite.com")
    token = create_access_token("cust_monthly")

    db = SessionLocal()
    try:
        w = CreditService.get_or_create_wallet("cust_monthly", db)
        w.daily_limit = 100
        w.monthly_limit = 1
        w.is_enabled = True
        w.status = "ACTIVE"
        db.commit()
    finally:
        db.close()

    with patch("app.llm.seo_analyst.SEOAnalystAgent.chat_with_data") as mock_chat:
        mock_chat.return_value = {"status": "success", "is_llm_generated": True, "answer": "Answer"}
        
        # 1st request consumes 1 credit
        r1 = client.post("/api/projects/proj_monthly/ai/chat", json={"query": "q1"}, headers={"Authorization": f"Bearer {token}"})
        assert r1.status_code == 200

        # 2nd request exceeds monthly limit (1)
        r2 = client.post("/api/projects/proj_monthly/ai/chat", json={"query": "q2"}, headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 429
        assert "monthly AI usage limit has been reached" in r2.json().get("detail", "")


def test_per_request_limit_enforcement():
    """TEST G: Per-request limit exceeded rejects request"""
    create_test_customer("cust_per_req", "per_req@example.com", "ACTIVE")
    create_test_project("proj_per_req", "cust_per_req", "perreqsite.com")
    token = create_access_token("cust_per_req")

    db = SessionLocal()
    try:
        w = CreditService.get_or_create_wallet("cust_per_req", db)
        w.per_request_limit = 2  # Max 2 credits per request
        w.is_enabled = True
        w.status = "ACTIVE"
        db.commit()
    finally:
        db.close()

    # /api/projects/{id}/ai/analyze requests 5 credits, which exceeds per_request_limit (2)
    res = client.post(
        "/api/projects/proj_per_req/ai/analyze",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 400
    assert "exceeds your allowed request limit" in res.json().get("detail", "")


def test_insufficient_credits_rejection_and_deduction():
    """TEST H & I: Insufficient credits vs Available credits deduction"""
    create_test_customer("cust_credits", "credits@example.com", "ACTIVE")
    create_test_project("proj_credits", "cust_credits", "creditssite.com")
    token = create_access_token("cust_credits")

    db = SessionLocal()
    try:
        w = CreditService.get_or_create_wallet("cust_credits", db)
        w.allocated_credits = 1
        w.used_credits = 0
        w.bonus_credits = 0
        w.is_enabled = True
        w.status = "ACTIVE"
        db.commit()
    finally:
        db.close()

    with patch("app.llm.seo_analyst.SEOAnalystAgent.chat_with_data") as mock_chat:
        mock_chat.return_value = {"status": "success", "is_llm_generated": True, "answer": "Answer"}
        
        # 1st request: has 1 credit, spends 1 credit
        r1 = client.post("/api/projects/proj_credits/ai/chat", json={"query": "q1"}, headers={"Authorization": f"Bearer {token}"})
        assert r1.status_code == 200

        # Verify wallet used_credits is now 1, remaining is 0
        db = SessionLocal()
        w = CreditService.get_or_create_wallet("cust_credits", db)
        assert w.remaining_credits == 0
        db.close()

        # 2nd request: 0 credits remaining -> 402 Payment Required
        r2 = client.post("/api/projects/proj_credits/ai/chat", json={"query": "q2"}, headers={"Authorization": f"Bearer {token}"})
        assert r2.status_code == 402
        assert "not have enough AI credits" in r2.json().get("detail", "")


def test_failed_provider_does_not_deduct_credits():
    """TEST J: Failed provider call does not deduct credits"""
    create_test_customer("cust_fail", "fail@example.com", "ACTIVE")
    create_test_project("proj_fail", "cust_fail", "failsite.com")
    token = create_access_token("cust_fail")

    db = SessionLocal()
    try:
        w = CreditService.get_or_create_wallet("cust_fail", db)
        w.allocated_credits = 100
        w.used_credits = 0
        w.is_enabled = True
        w.status = "ACTIVE"
        db.commit()
    finally:
        db.close()

    from app.llm.llm_provider import AIProviderException
    with patch("app.llm.seo_analyst.SEOAnalystAgent.chat_with_data", side_effect=AIProviderException("LLM Timeout", status_code=502)):
        res = client.post("/api/projects/proj_fail/ai/chat", json={"query": "q1"}, headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 502

    # Verify no credits were deducted
    db = SessionLocal()
    w = CreditService.get_or_create_wallet("cust_fail", db)
    assert w.used_credits == 0
    assert w.remaining_credits == 100
    db.close()


def test_customer_account_statuses_login_and_token_blocking():
    """TEST L, M, N, O, P, Q: Canonical Account Statuses (ACTIVE, SUSPENDED, DISABLED, INACTIVE)"""
    create_test_customer("user_active", "user_active@example.com", "ACTIVE")
    create_test_customer("user_suspended", "user_suspended@example.com", "SUSPENDED")
    create_test_customer("user_disabled", "user_disabled@example.com", "DISABLED")
    create_test_customer("user_inactive", "user_inactive@example.com", "INACTIVE")

    # TEST L: ACTIVE login succeeds
    r_act = client.post("/api/auth/login", json={"email": "user_active@example.com", "password": "Password123!"})
    assert r_act.status_code == 200
    assert "access_token" in r_act.json()

    # TEST M: SUSPENDED login rejected
    r_susp = client.post("/api/auth/login", json={"email": "user_suspended@example.com", "password": "Password123!"})
    assert r_susp.status_code == 403
    assert "ACCOUNT_SUSPENDED" in r_susp.json().get("detail", "")

    # TEST N: DISABLED login rejected
    r_dis = client.post("/api/auth/login", json={"email": "user_disabled@example.com", "password": "Password123!"})
    assert r_dis.status_code == 403
    assert "ACCOUNT_DISABLED" in r_dis.json().get("detail", "")

    # TEST O: INACTIVE login rejected
    r_inact = client.post("/api/auth/login", json={"email": "user_inactive@example.com", "password": "Password123!"})
    assert r_inact.status_code == 403
    assert "ACCOUNT_INACTIVE" in r_inact.json().get("detail", "")

    # TEST P: Suspended customer trying pre-existing token
    token_susp = create_access_token("user_suspended")
    r_api_susp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_susp}"})
    assert r_api_susp.status_code == 403

    # TEST Q: Disabled customer trying pre-existing token
    token_dis = create_access_token("user_disabled")
    r_api_dis = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token_dis}"})
    assert r_api_dis.status_code == 403


def test_project_cross_tenant_isolation_on_ai_endpoints():
    """TEST S: Customer A cannot invoke AI on Customer B's project"""
    create_test_customer("cust_a", "cust_a@example.com", "ACTIVE")
    create_test_project("proj_a", "cust_a", "site-a.com")
    token_a = create_access_token("cust_a")

    create_test_customer("cust_b", "cust_b@example.com", "ACTIVE")
    create_test_project("proj_b", "cust_b", "site-b.com")

    # Customer A tries to call AI endpoint for Customer B's project
    res = client.post(
        "/api/projects/proj_b/ai/chat",
        json={"query": "hello"},
        headers={"Authorization": f"Bearer {token_a}"}
    )
    # Should be rejected with 403/404 because cust_a has no membership in proj_b
    assert res.status_code in (403, 404)
