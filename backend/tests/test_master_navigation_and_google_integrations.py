import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.config.database import get_db, Base, engine
from app.models.user import User
from app.models.external_connection import ExternalConnection
from app.config.auth import create_access_token

client = TestClient(app)

@pytest.fixture(scope="module", autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield

def test_master_admin_authorization_enforcement():
    """
    Test that normal customer users cannot access Master Admin API routes,
    while Master Admin users (SUPER_ADMIN, ADMIN) can access them.
    """
    db: Session = next(get_db())
    
    # 1. Ensure regular customer user
    customer_user = db.query(User).filter(User.email == "customer_nav_test@example.com").first()
    if not customer_user:
        customer_user = User(
            id="cust_nav_user_1",
            email="customer_nav_test@example.com",
            name="Regular Customer",
            platform_role="USER"
        )
        db.add(customer_user)
        db.commit()
    else:
        customer_user.platform_role = "USER"
        db.commit()

    # 2. Ensure master admin user
    master_user = db.query(User).filter(User.email == "superadmin_nav_test@example.com").first()
    if not master_user:
        master_user = User(
            id="master_nav_user_1",
            email="superadmin_nav_test@example.com",
            name="Super Admin",
            platform_role="SUPER_ADMIN"
        )
        db.add(master_user)
        db.commit()
    else:
        master_user.platform_role = "SUPER_ADMIN"
        db.commit()

    customer_token = create_access_token(user_id=customer_user.id)
    master_token = create_access_token(user_id=master_user.id)

    # Regular customer accessing master space -> 403 Forbidden
    res_cust = client.get("/api/master/dashboard", headers={"Authorization": f"Bearer {customer_token}"})
    assert res_cust.status_code == 403, f"Expected 403 for regular user on /api/master/dashboard, got {res_cust.status_code}"

    # Master admin accessing master space -> 200 OK
    res_master = client.get("/api/master/dashboard", headers={"Authorization": f"Bearer {master_token}"})
    assert res_master.status_code == 200, f"Expected 200 for master user on /api/master/dashboard, got {res_master.status_code}"


def test_google_services_individual_status_breakdown():
    """
    Test that GET /api/integrations returns distinct status structures for:
    - google_search_console
    - google_business_profile
    - google_ads
    - serp_provider
    - backlink_provider
    """
    db: Session = next(get_db())
    test_user_id = "test_integrations_user_v2"

    user = db.query(User).filter(User.id == test_user_id).first()
    if not user:
        user = User(id=test_user_id, email="integration_v2@example.com", name="Integration Tester", platform_role="USER")
        db.add(user)
        db.commit()

    # Clean previous connections for test user
    db.query(ExternalConnection).filter(ExternalConnection.user_id == test_user_id).delete()
    db.commit()

    token = create_access_token(user_id=test_user_id)

    # 1. Initially all are not connected
    res = client.get("/api/integrations", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    data = res.json()

    assert "google_search_console" in data
    assert "google_business_profile" in data
    assert "google_ads" in data
    assert "serp_provider" in data
    assert "backlink_provider" in data

    assert data["google_search_console"]["status"] == "NOT_CONNECTED"
    assert data["google_business_profile"]["status"] == "NOT_CONNECTED"
    assert data["google_ads"]["status"] == "NOT_CONNECTED"

    # 2. Connect Google OAuth with Search Console and Business Profile scopes
    google_conn = ExternalConnection(
        id="conn_google_test_v2",
        user_id=test_user_id,
        provider="google",
        provider_account_name="Integration Google Account",
        provider_email="gsuite_v2@example.com",
        scopes="https://www.googleapis.com/auth/webmasters.readonly https://www.googleapis.com/auth/business.manage",
        status="CONNECTED"
    )
    google_conn.set_access_token("mock_access_token_12345")
    db.add(google_conn)
    db.commit()

    res2 = client.get("/api/integrations", headers={"Authorization": f"Bearer {token}"})
    assert res2.status_code == 200
    data2 = res2.json()

    # GSC and GBP are connected
    assert data2["google_search_console"]["status"] == "CONNECTED"
    assert data2["google_search_console"]["connected_account"] == "gsuite_v2@example.com"
    assert data2["google_business_profile"]["status"] == "CONNECTED"
    assert data2["google_business_profile"]["connected_account"] == "gsuite_v2@example.com"

    # Google Ads requires developer token configuration -> CONFIGURATION_REQUIRED
    assert data2["google_ads"]["status"] == "CONFIGURATION_REQUIRED"
    assert data2["google_ads"]["developer_token_configured"] is False


def test_google_ads_developer_token_secure_config_and_masking():
    """
    Test that Google Ads Developer Token is configured via POST /api/integrations/google_ads/config,
    encrypted at rest, never leaked in plain text, and updates Google Ads status to CONNECTED.
    """
    db: Session = next(get_db())
    test_user_id = "test_integrations_user_v2"
    token = create_access_token(user_id=test_user_id)

    raw_dev_token = "TEST_DEV_TOKEN_SECRET_987654321"

    res_post = client.post(
        "/api/integrations/google_ads/config",
        headers={"Authorization": f"Bearer {token}"},
        json={"developer_token": raw_dev_token}
    )
    assert res_post.status_code == 200
    post_data = res_post.json()
    assert post_data["status"] == "success"
    assert post_data["developer_token_configured"] is True
    # Verify masked format (never plain text)
    assert "TEST_DEV_TOKEN_SECRET" not in post_data["masked_developer_token"]

    # Verify encrypted at rest in database
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == test_user_id,
        ExternalConnection.provider == "google_ads"
    ).first()
    assert conn is not None
    assert conn.api_key_encrypted != raw_dev_token
    assert conn.get_api_key() == raw_dev_token

    # Verify GET /api/integrations now reports CONNECTED for Google Ads
    res_get = client.get("/api/integrations", headers={"Authorization": f"Bearer {token}"})
    assert res_get.status_code == 200
    get_data = res_get.json()
    assert get_data["google_ads"]["status"] == "CONNECTED"
    assert get_data["google_ads"]["developer_token_configured"] is True
    assert raw_dev_token not in str(get_data)


def test_serp_and_backlink_provider_config_and_isolation():
    """
    Test configuration, testing, and disconnect for SERP and Backlink providers.
    """
    db: Session = next(get_db())
    test_user_id = "test_integrations_user_v2"
    token = create_access_token(user_id=test_user_id)

    # 1. Configure SERP provider
    serp_key = "serp_secret_key_abc123"
    res_serp_conf = client.post(
        "/api/integrations/serp/config",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider_name": "SerpApi", "api_key": serp_key}
    )
    assert res_serp_conf.status_code == 200
    assert serp_key not in res_serp_conf.json().get("masked_key", "")

    # Test SERP connection
    res_serp_test = client.post("/api/integrations/serp/test", headers={"Authorization": f"Bearer {token}"})
    assert res_serp_test.status_code == 200

    # 2. Configure Backlink provider
    backlink_key = "backlink_secret_key_xyz789"
    res_bl_conf = client.post(
        "/api/integrations/backlink/config",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider_name": "Ahrefs API", "api_key": backlink_key}
    )
    assert res_bl_conf.status_code == 200
    assert backlink_key not in res_bl_conf.json().get("masked_key", "")

    # Test Backlink connection
    res_bl_test = client.post("/api/integrations/backlink/test", headers={"Authorization": f"Bearer {token}"})
    assert res_bl_test.status_code == 200

    # 3. Verify GET /api/integrations shows both connected
    res_get = client.get("/api/integrations", headers={"Authorization": f"Bearer {token}"})
    data = res_get.json()
    assert data["serp_provider"]["status"] == "CONNECTED"
    assert data["backlink_provider"]["status"] == "CONNECTED"

    # 4. Disconnect SERP provider without affecting Backlink provider
    res_disc = client.post("/api/integrations/serp/disconnect", headers={"Authorization": f"Bearer {token}"})
    assert res_disc.status_code == 200

    res_get2 = client.get("/api/integrations", headers={"Authorization": f"Bearer {token}"})
    data2 = res_get2.json()
    assert data2["serp_provider"]["status"] == "NOT_CONFIGURED"
    assert data2["backlink_provider"]["status"] == "CONNECTED"
