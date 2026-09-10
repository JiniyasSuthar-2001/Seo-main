import os
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token

client = TestClient(app)

@pytest.fixture
def multi_tenant_setup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())

    # User A
    user_a = db.query(User).filter(User.email == "user_a@example.com").first()
    if not user_a:
        user_a = User(id="usr_a_part2", email="user_a@example.com", name="User A", platform_role="customer")
        db.add(user_a)
        db.commit()

    proj_a = db.query(Project).filter(Project.id == "proj_a_part2").first()
    if not proj_a:
        proj_a = Project(id="proj_a_part2", name="Project A", domain="usera-site.com", url="https://usera-site.com")
        db.add(proj_a)
        db.commit()


    mem_a = db.query(ProjectMembership).filter(ProjectMembership.project_id == proj_a.id, ProjectMembership.user_id == user_a.id).first()
    if not mem_a:
        mem_a = ProjectMembership(id="mem_a_part2", project_id=proj_a.id, user_id=user_a.id, role="owner")
        db.add(mem_a)
        db.commit()

    # User B
    user_b = db.query(User).filter(User.email == "user_b@example.com").first()
    if not user_b:
        user_b = User(id="usr_b_part2", email="user_b@example.com", name="User B", platform_role="customer")
        db.add(user_b)
        db.commit()

    token_a = create_access_token(user_a.id, {"email": user_a.email, "role": user_a.platform_role})
    token_b = create_access_token(user_b.id, {"email": user_b.email, "role": user_b.platform_role})

    return {
        "user_a": user_a,
        "proj_a": proj_a,
        "token_a": token_a,
        "headers_a": {"Authorization": f"Bearer {token_a}"},
        "user_b": user_b,
        "token_b": token_b,
        "headers_b": {"Authorization": f"Bearer {token_b}"}
    }


def test_unauthorized_user_blocked_from_project_endpoints(multi_tenant_setup):
    data = multi_tenant_setup
    proj_id = data["proj_a"].id
    headers_b = data["headers_b"]  # User B attempting to access User A's project

    # 1. PageSpeed
    res_ps = client.get(f"/api/projects/{proj_id}/pagespeed", headers=headers_b)
    assert res_ps.status_code in (403, 404)

    # 2. GSC
    res_gsc = client.get(f"/api/projects/{proj_id}/gsc/performance", headers=headers_b)
    assert res_gsc.status_code in (403, 404)

    # 3. GSC Priorities
    res_prio = client.get(f"/api/projects/{proj_id}/gsc/priorities", headers=headers_b)
    assert res_prio.status_code in (403, 404)

    # 4. Crawl Comparison
    res_comp = client.get(f"/api/projects/{proj_id}/technical/crawl-comparison", headers=headers_b)
    assert res_comp.status_code in (403, 404)


def test_unauthenticated_requests_rejected(multi_tenant_setup):
    data = multi_tenant_setup
    proj_id = data["proj_a"].id

    res = client.get(f"/api/projects/{proj_id}/pagespeed")
    assert res.status_code in (401, 403)

    res = client.get(f"/api/projects/{proj_id}/gsc/performance")
    assert res.status_code in (401, 403)


def test_reports_never_generate_ai_on_export(multi_tenant_setup):
    data = multi_tenant_setup
    proj_id = data["proj_a"].id
    headers_a = data["headers_a"]

    with patch("app.services.ai_solution_service.AISolutionService.get_or_generate_solution") as mock_ai:
        # Request report exports
        res_csv = client.get(f"/api/projects/{proj_id}/technical/export.csv", headers=headers_a)
        assert res_csv.status_code in (200, 404)

        res_rank_csv = client.get(f"/api/projects/{proj_id}/rankings/export.csv", headers=headers_a)
        assert res_rank_csv.status_code in (200, 404)

        # Ensure AI service was NEVER invoked
        mock_ai.assert_not_called()

