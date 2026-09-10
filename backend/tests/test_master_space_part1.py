import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.ai_usage_log import AIUsageLog
from app.models.platform_event import PlatformEvent
from app.models.audit_log import AuditLog
from app.config.auth import create_access_token

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_data():
    db = SessionLocal()
    try:
        # Create super admin user
        super_admin = db.query(User).filter(User.id == "test_super_admin").first()
        if not super_admin:
            super_admin = User(
                id="test_super_admin",
                email="admin@platform.com",
                name="Test Admin",
                platform_role="SUPER_ADMIN",
                status="ACTIVE"
            )
            db.add(super_admin)

        # Create standard customer user
        customer = db.query(User).filter(User.id == "test_customer").first()
        if not customer:
            customer = User(
                id="test_customer",
                email="customer@example.com",
                name="Test Customer",
                platform_role="USER",
                status="ACTIVE"
            )
            db.add(customer)

        # Create test project
        project = db.query(Project).filter(Project.id == "test_master_project").first()
        if not project:
            project = Project(
                id="test_master_project",
                name="Test Master Website",
                url="https://master-test.com",
                target_country="United States"
            )
            db.add(project)

        # Create test AI usage log
        ai_log = db.query(AIUsageLog).filter(AIUsageLog.id == "test_ai_log_1").first()
        if not ai_log:
            ai_log = AIUsageLog(
                id="test_ai_log_1",
                user_id="test_customer",
                project_id="test_master_project",
                task_type="page_solution",
                model="gemini-2.5-flash",
                input_tokens=1500,
                output_tokens=500,
                status="success"
            )
            db.add(ai_log)

        db.commit()
    finally:
        db.close()

def test_master_authorization_enforcement():
    """Verify that standard customer receives 403 Forbidden while Super Admin receives 200 OK."""
    customer_token = create_access_token("test_customer")
    admin_token = create_access_token("test_super_admin")

    # 1. Standard customer attempt -> 403 Forbidden
    res_cust = client.get(
        "/api/master/dashboard",
        headers={"Authorization": f"Bearer {customer_token}"}
    )
    assert res_cust.status_code == 403
    assert "Access denied" in res_cust.json()["detail"]

    # 2. Super Admin attempt -> 200 OK
    res_admin = client.get(
        "/api/master/dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_admin.status_code == 200
    data = res_admin.json()
    assert "total_customers" in data
    assert "total_websites" in data
    assert "ai_requests_today" in data

def test_master_customers_endpoints():
    """Verify customer list and Customer 360 detail payload."""
    admin_token = create_access_token("test_super_admin")

    res = client.get(
        "/api/master/customers",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    body = res.json()
    assert "items" in body
    assert body["total"] >= 1

    # Detail
    res_detail = client.get(
        "/api/master/customers/test_customer",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["user"]["email"] == "customer@example.com"
    assert "ai_analytics" in detail

def test_master_websites_endpoints():
    """Verify website list and Website 360 detail payload."""
    admin_token = create_access_token("test_super_admin")

    res = client.get(
        "/api/master/websites",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    body = res.json()
    assert "items" in body

    # Detail
    res_detail = client.get(
        "/api/master/websites/test_master_project",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_detail.status_code == 200
    detail = res_detail.json()
    assert detail["project"]["name"] == "Test Master Website"
    assert "timeline" in detail

def test_master_ai_analytics_and_providers():
    """Verify AI analytics aggregations and provider monitoring."""
    admin_token = create_access_token("test_super_admin")

    res_ai = client.get(
        "/api/master/ai-analytics",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_ai.status_code == 200
    ai_data = res_ai.json()
    assert "summary" in ai_data
    assert "by_customer" in ai_data

    res_prov = client.get(
        "/api/master/providers",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_prov.status_code == 200
    providers = res_prov.json()
    assert len(providers) >= 1
    assert providers[0]["name"] == "Google Gemini"

def test_master_system_health_and_audit():
    """Verify system health monitoring and audit log recording."""
    admin_token = create_access_token("test_super_admin")

    res_health = client.get(
        "/api/master/system-health",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_health.status_code == 200
    health = res_health.json()
    assert health["services"]["database"]["status"] == "Healthy"

    # Status update trigger -> Audit log
    res_status = client.post(
        "/api/master/customers/test_customer/status",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"status": "SUSPENDED", "reason": "Test audit trigger"}
    )
    assert res_status.status_code == 200
    assert res_status.json()["status"] == "SUSPENDED"

    # Check audit log
    res_audit = client.get(
        "/api/master/audit-logs",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res_audit.status_code == 200
    audit_data = res_audit.json()
    assert audit_data["total"] >= 1
    actions = [a["action"] for a in audit_data["items"]]
    assert "CUSTOMER_STATUS_UPDATE" in actions
