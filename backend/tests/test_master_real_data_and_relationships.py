import pytest
import uuid
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.database import Base, get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.crawl_session import CrawlSession
from app.models.page import Page
from app.models.audit_issue import AuditIssue
from app.models.ai_usage_log import AIUsageLog
from app.models.ai_wallet import AIWallet, AICreditTransaction, PlatformAISettings
from app.models.audit_log import AuditLog
from app.config.security import get_password_hash
from app.config.auth import create_access_token
from app.services.master_service import MasterService
from app.services.credit_service import CreditService, CreditTransactionType
from app.main import app

# In-memory test DB
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_clean_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    app.dependency_overrides[get_db] = override_get_db
    db = TestingSessionLocal()
    try:
        # Seed Super Master
        super_master = User(
            id="supermaster@test.com",
            email="supermaster@test.com",
            name="Super Master",
            password_hash=get_password_hash("SuperMaster@123"),
            platform_role="SUPER_MASTER",
            status="ACTIVE",
            permissions_json='["*"]'
        )
        db.add(super_master)

        # Seed Customer 1
        cust1 = User(
            id="cust1@domain.com",
            email="cust1@domain.com",
            name="Customer One",
            password_hash=get_password_hash("Customer@123"),
            platform_role="USER",
            status="ACTIVE"
        )
        db.add(cust1)

        # Seed Project 1 for Customer 1
        proj1 = Project(
            id=str(uuid.uuid4()),
            name="Solar Australia",
            url="https://solar.com.au"
        )
        db.add(proj1)

        membership1 = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id="cust1@domain.com",
            project_id=proj1.id,
            role="OWNER",
            status="ACTIVE"
        )
        db.add(membership1)

        db.commit()
    finally:
        db.close()
    yield
    app.dependency_overrides.pop(get_db, None)


def test_dashboard_metrics_live_database_queries():
    db = TestingSessionLocal()
    metrics = MasterService.get_dashboard_metrics(range_type="30d", db=db)
    
    assert metrics["total_customers"] == 2  # super_master + cust1
    assert metrics["active_customers"] == 2
    assert metrics["suspended_customers"] == 0
    assert metrics["total_websites"] == 1
    assert metrics["active_websites"] == 1
    assert metrics["crawls_today"] == 0
    assert metrics["ai_requests_today"] == 0
    assert metrics["ai_tokens_today"] == 0
    assert metrics["failed_ai_requests"] == 0
    assert metrics["system_errors"] == 0
    db.close()


def test_provider_summary_no_fake_attributions():
    db = TestingSessionLocal()
    # Add OpenAI log specifically
    log = AIUsageLog(
        id=str(uuid.uuid4()),
        user_id="cust1@domain.com",
        model="openai/gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        status="success",
        created_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()

    providers = MasterService.get_providers_summary(db=db)
    openai_summary = next(p for p in providers if p["key"] == "openai")
    gemini_summary = next(p for p in providers if p["key"] == "gemini")

    # OpenAI must reflect exactly 1 request and 1500 tokens
    assert openai_summary["requests"] == 1
    assert openai_summary["tokens"] == 1500
    assert openai_summary["failed"] == 0

    # Gemini must NOT have stolen the OpenAI request or token counts
    assert gemini_summary["requests"] == 0
    assert gemini_summary["tokens"] == 0
    db.close()


def test_ai_analytics_breakdown_by_provider_and_model():
    db = TestingSessionLocal()
    # Add logs for multiple models
    log1 = AIUsageLog(
        id=str(uuid.uuid4()),
        user_id="cust1@domain.com",
        model="models/gemini-1.5-flash",
        input_tokens=500,
        output_tokens=200,
        status="success",
        task_type="page_solution",
        created_at=datetime.utcnow()
    )
    log2 = AIUsageLog(
        id=str(uuid.uuid4()),
        user_id="cust1@domain.com",
        model="groq/llama-3.3-70b-versatile",
        input_tokens=800,
        output_tokens=400,
        status="success",
        task_type="problem_explanation",
        created_at=datetime.utcnow()
    )
    db.add_all([log1, log2])
    db.commit()

    analytics = MasterService.get_ai_analytics(range_type="30d", db=db)
    assert analytics["summary"]["requests"] == 2
    assert analytics["summary"]["total_tokens"] == (500 + 200) + (800 + 400)
    assert analytics["summary"]["successful"] == 2
    assert analytics["summary"]["failed"] == 0

    gemini_stat = next(p for p in analytics["by_provider"] if p["provider"] == "Gemini")
    groq_stat = next(p for p in analytics["by_provider"] if p["provider"] == "Groq")
    openai_stat = next(p for p in analytics["by_provider"] if p["provider"] == "OpenAI")

    assert gemini_stat["requests"] == 1
    assert groq_stat["requests"] == 1
    assert openai_stat["requests"] == 0
    db.close()


def test_credit_ledger_mathematical_consistency():
    db = TestingSessionLocal()
    wallet = CreditService.get_or_create_wallet("cust1@domain.com", db)
    initial_balance = wallet.remaining_credits
    assert initial_balance == 50000

    # 1. Deduct credits for AI usage
    CreditService.deduct_credits("cust1@domain.com", amount=500, reference_id="ref_1", reason="Page AI Scan", db=db)
    db.refresh(wallet)
    assert wallet.used_credits == 500
    assert wallet.remaining_credits == 49500

    # 2. Add manual adjustment with audit reason
    CreditService.allocate_credits("cust1@domain.com", amount=1000, transaction_type=CreditTransactionType.ADJUSTMENT, reason="Customer compensation", actor_user_id="supermaster@test.com", db=db)
    db.refresh(wallet)
    assert wallet.allocated_credits == 51000
    assert wallet.remaining_credits == 50500

    # Check transactions ledger
    txs = db.query(AICreditTransaction).filter(AICreditTransaction.customer_id == "cust1@domain.com").order_by(AICreditTransaction.created_at).all()
    assert len(txs) >= 3  # initial allocation, deduction, adjustment
    assert txs[-1].balance_after == 50500
    db.close()


def test_master_api_endpoints_live_responses():
    token = create_access_token("supermaster@test.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Dashboard
    res = client.get("/api/master/dashboard?range_type=today", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_customers" in data
    assert "active_customers" in data

    # 2. Providers
    res = client.get("/api/master/providers", headers=headers)
    assert res.status_code == 200
    providers = res.json()
    assert isinstance(providers, list)
    assert len(providers) >= 4

    # 3. Provider Health Check
    res = client.get("/api/master/providers/gemini/health", headers=headers)
    assert res.status_code == 200
    assert "status" in res.json()

    # 4. System Health
    res = client.get("/api/master/system-health", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] in ("Healthy", "Warning", "Critical")
