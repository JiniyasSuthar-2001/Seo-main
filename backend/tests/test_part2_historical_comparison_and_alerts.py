import os
import json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.config.settings import settings

client = TestClient(app)

@pytest.fixture
def auth_setup():
    Base.metadata.create_all(bind=engine)
    db = next(get_db())

    user = db.query(User).filter(User.email == "tester_part2@example.com").first()
    if not user:
        user = User(
            id="usr_part2_test",
            email="tester_part2@example.com",
            name="Part 2 Tester",
            platform_role="customer"
        )
        db.add(user)
        db.commit()

    project = db.query(Project).filter(Project.id == "proj_part2_test").first()
    if not project:
        project = Project(
            id="proj_part2_test",
            name="Part 2 Project",
            domain="part2-example.com",
            url="https://part2-example.com"
        )
        db.add(project)
        db.commit()


    membership = db.query(ProjectMembership).filter(
        ProjectMembership.project_id == project.id,
        ProjectMembership.user_id == user.id
    ).first()
    if not membership:
        membership = ProjectMembership(
            id="mem_part2_test",
            project_id=project.id,
            user_id=user.id,
            role="owner"
        )
        db.add(membership)
        db.commit()

    token = create_access_token(user.id, {"email": user.email, "role": user.platform_role})
    headers = {"Authorization": f"Bearer {token}"}
    return user, project, headers



def test_crawl_comparison_endpoint_with_snapshots(auth_setup):
    user, project, headers = auth_setup
    from app.config.utils import get_project_storage_dir
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    crawls_dir = os.path.join(proj_dir, "crawls")
    os.makedirs(crawls_dir, exist_ok=True)


    crawl1_dir = os.path.join(crawls_dir, "2026-09-01T10-00-00")
    crawl2_dir = os.path.join(crawls_dir, "2026-09-10T10-00-00")
    os.makedirs(crawl1_dir, exist_ok=True)
    os.makedirs(crawl2_dir, exist_ok=True)

    # Crawl 1: has page1 and page2 (both missing title)
    pages1 = [
        {"url": "https://part2-example.com/page1", "title": "", "status_code": 200, "word_count": 300},
        {"url": "https://part2-example.com/page2", "title": "", "status_code": 200, "word_count": 400}
    ]
    with open(os.path.join(crawl1_dir, "pages.json"), "w") as f:
        json.dump(pages1, f)

    # Crawl 2: page1 is fixed (has title), page2 is removed, page3 is new
    pages2 = [
        {"url": "https://part2-example.com/page1", "title": "Fixed Valid Title For Page One Here", "status_code": 200, "word_count": 300},
        {"url": "https://part2-example.com/page3", "title": "New Page Three Title Optimization", "status_code": 200, "word_count": 500}
    ]
    with open(os.path.join(crawl2_dir, "pages.json"), "w") as f:
        json.dump(pages2, f)

    res = client.get(
        f"/api/projects/{project.id}/technical/crawl-comparison?crawl_a=2026-09-10T10-00-00&crawl_b=2026-09-01T10-00-00",
        headers=headers
    )
    assert res.status_code == 200
    data = res.json()
    assert data["has_comparison"] is True
    assert data["pages_summary"]["new_pages_count"] == 1
    assert data["pages_summary"]["removed_pages_count"] == 1
    assert data["pages_summary"]["changed_pages_count"] == 1
    assert "https://part2-example.com/page3" in data["pages_summary"]["new_pages"]
    assert "https://part2-example.com/page2" in data["pages_summary"]["removed_pages"]


def test_pagespeed_and_gsc_endpoints(auth_setup):
    user, project, headers = auth_setup

    # Test PageSpeed unanalyzed endpoint
    ps_res = client.get(f"/api/projects/{project.id}/pagespeed", headers=headers)
    assert ps_res.status_code == 200
    ps_data = ps_res.json()
    assert "status" in ps_data

    # Test GSC performance endpoint
    gsc_res = client.get(f"/api/projects/{project.id}/gsc/performance", headers=headers)
    assert gsc_res.status_code == 200
    gsc_data = gsc_res.json()
    assert "status" in gsc_data

    # Test GSC priorities endpoint
    prio_res = client.get(f"/api/projects/{project.id}/gsc/priorities", headers=headers)
    assert prio_res.status_code == 200
    prio_data = prio_res.json()
    assert "total_prioritized_pages" in prio_data
