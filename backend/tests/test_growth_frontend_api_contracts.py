import pytest
import os
import json
import uuid
import tempfile
import shutil
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config.database import Base, get_db
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.keyword import Keyword
from app.models.competitor import Competitor
from app.config.settings import settings
from app.config.auth import create_access_token


@pytest.fixture(scope="module")
def client_env():
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_growth_fe.db")
    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    old_crawl_dir = settings.CRAWL_DATA_DIR
    settings.CRAWL_DATA_DIR = os.path.join(temp_dir, "crawl_data")
    os.makedirs(settings.CRAWL_DATA_DIR, exist_ok=True)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    db = TestingSessionLocal()
    user = User(
        id=str(uuid.uuid4()),
        email="growth_fe_tester@example.com",
        name="Growth FE Tester"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    project = Project(
        id=str(uuid.uuid4()),
        name="Growth Test Site",
        domain="growthtest.com"
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    membership = ProjectMembership(
        id=str(uuid.uuid4()),
        user_id=user.id,
        project_id=project.id,
        role="owner"
    )
    db.add(membership)
    db.commit()

    token = create_access_token(user_id=user.id)
    headers = {"Authorization": f"Bearer {token}"}

    from app.config.utils import get_project_storage_dir
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    os.makedirs(proj_dir, exist_ok=True)
    crawl_session_dir = os.path.join(proj_dir, "session_test")
    os.makedirs(crawl_session_dir, exist_ok=True)

    with open(os.path.join(proj_dir, "latest.json"), "w", encoding="utf-8") as f:
        json.dump({"path": crawl_session_dir, "session_id": "session_test"}, f)

    pages = [
        {"url": "https://growthtest.com/", "status_code": 200, "title": "Home", "is_success": True, "depth": 0},
        {"url": "https://growthtest.com/services", "status_code": 200, "title": "Services", "is_success": True, "depth": 1},
        {"url": "https://growthtest.com/old-page", "status_code": 404, "title": "404 Not Found", "is_success": False, "depth": 1},
        {"url": "https://growthtest.com/orphan", "status_code": 200, "title": "Orphan Page", "is_success": True, "depth": 1}
    ]
    with open(os.path.join(crawl_session_dir, "pages.json"), "w", encoding="utf-8") as f:
        json.dump(pages, f)

    link_records = [
        {
            "id": "rec-1",
            "source_page": "https://growthtest.com/",
            "target_page": "https://growthtest.com/services",
            "anchor_text": "Our Services",
            "is_internal": True,
            "link_type": "internal",
            "rel": "follow",
            "status_code": 200,
            "target_status_code": 200,
            "source_section": "main",
            "nearest_heading": "What We Offer",
            "heading_level": "h2",
            "paragraph_index": 1,
            "sentence_index": 0,
            "context_before": "Learn more about our company and",
            "context_text": "Our Services",
            "context_after": "to see what we can do.",
            "html_snippet": '<a href="/services">Our Services</a>'
        },
        {
            "id": "rec-2",
            "source_page": "https://growthtest.com/services",
            "target_page": "https://growthtest.com/old-page",
            "anchor_text": "Legacy Solutions",
            "is_internal": True,
            "link_type": "internal",
            "rel": "nofollow",
            "status_code": 404,
            "target_status_code": 404,
            "source_section": "article",
            "nearest_heading": "Archived Information",
            "heading_level": "h3",
            "paragraph_index": 3,
            "sentence_index": 1,
            "context_before": "For archived systems, view",
            "context_text": "Legacy Solutions",
            "context_after": "in our documentation.",
            "html_snippet": '<a href="/old-page" rel="nofollow">Legacy Solutions</a>'
        },
        {
            "id": "rec-3",
            "source_page": "https://growthtest.com/services",
            "target_page": "https://external-partner.org/docs",
            "anchor_text": "Partner Reference",
            "is_internal": False,
            "link_type": "external",
            "rel": "sponsored",
            "status_code": 200,
            "target_status_code": 200,
            "source_section": "sidebar",
            "nearest_heading": "External Resources",
            "heading_level": "h2",
            "paragraph_index": 0,
            "sentence_index": 0,
            "context_before": "Read the official",
            "context_text": "Partner Reference",
            "context_after": "guide for details.",
            "html_snippet": '<a href="https://external-partner.org/docs" rel="sponsored">Partner Reference</a>'
        }
    ]
    with open(os.path.join(crawl_session_dir, "link_records.json"), "w", encoding="utf-8") as f:
        json.dump(link_records, f)

    internal_links = [
        {"source": "https://growthtest.com/", "target": "https://growthtest.com/services", "anchor_text": "Our Services"},
        {"source": "https://growthtest.com/services", "target": "https://growthtest.com/old-page", "anchor_text": "Legacy Solutions"}
    ]
    with open(os.path.join(crawl_session_dir, "internal_links.json"), "w", encoding="utf-8") as f:
        json.dump(internal_links, f)

    external_links = [
        {"source": "https://growthtest.com/services", "target": "https://external-partner.org/docs", "anchor_text": "Partner Reference", "rel": "sponsored"}
    ]
    with open(os.path.join(crawl_session_dir, "external_links.json"), "w", encoding="utf-8") as f:
        json.dump(external_links, f)

    broken_links = [
        {
            "source": "https://growthtest.com/services",
            "target": "https://growthtest.com/old-page",
            "anchor_text": "Legacy Solutions",
            "link_type": "internal",
            "status_code": 404,
            "error_type": "not_found",
            "source_section": "article",
            "nearest_heading": "Archived Information",
            "paragraph_index": 3,
            "sentence_index": 1,
            "context_text": "Legacy Solutions",
            "html_snippet": '<a href="/old-page" rel="nofollow">Legacy Solutions</a>'
        }
    ]
    with open(os.path.join(crawl_session_dir, "broken_links.json"), "w", encoding="utf-8") as f:
        json.dump(broken_links, f)

    issues = [
        {
            "id": "iss-1",
            "rule_id": "BROKEN_INTERNAL_LINKS",
            "title": "Broken Internal Links Detected",
            "category": "Internal Links",
            "priority": "HIGH",
            "severity": "HIGH",
            "impact": "Broken links damage user experience and waste crawl budget.",
            "recommendation": "Update or remove dead target URL /old-page.",
            "affected_urls": ["https://growthtest.com/services"],
            "evidence": "Target /old-page returns HTTP 404"
        }
    ]
    with open(os.path.join(crawl_session_dir, "issues.json"), "w", encoding="utf-8") as f:
        json.dump(issues, f)

    yield {
        "client": client,
        "headers": headers,
        "project_id": project.id,
        "db": db
    }

    app.dependency_overrides.clear()
    settings.CRAWL_DATA_DIR = old_crawl_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_internal_links_canonical_endpoints(client_env):
    client = client_env["client"]
    headers = client_env["headers"]
    project_id = client_env["project_id"]

    # 1. Main internal links
    res = client.get(f"/api/projects/{project_id}/internal-links", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["summary"]["total_internal_links"] >= 1
    assert "https://growthtest.com/orphan" in data["orphan_pages"]

    # 2. Incoming links for services page
    res = client.get(f"/api/projects/{project_id}/internal-links/incoming?url=https://growthtest.com/services", headers=headers)
    assert res.status_code == 200
    inc = res.json()
    assert inc["total_incoming_links"] >= 1
    assert inc["incoming_links"][0]["source_section"] == "main"
    assert inc["incoming_links"][0]["nearest_heading"] == "What We Offer"

    # 3. Outgoing links from services page
    res = client.get(f"/api/projects/{project_id}/internal-links/outgoing?url=https://growthtest.com/services", headers=headers)
    assert res.status_code == 200
    out = res.json()
    assert out["total_outgoing_links"] >= 1

    # 4. Link Detail API
    res = client.get(f"/api/projects/{project_id}/internal-links/link-detail?link_id=rec-1", headers=headers)
    assert res.status_code == 200
    det = res.json()["link_record"]
    assert det["paragraph_index"] == 1
    assert det["html_snippet"] == '<a href="/services">Our Services</a>'

    # 5. Broken links API
    res = client.get(f"/api/projects/{project_id}/internal-links/broken", headers=headers)
    assert res.status_code == 200
    brk = res.json()
    assert brk["internal_count"] == 1
    assert brk["broken_links"][0]["status_code"] == 404


def test_opportunities_lifecycle_persistence(client_env):
    client = client_env["client"]
    headers = client_env["headers"]
    project_id = client_env["project_id"]

    # Fetch opportunities
    res = client.get(f"/api/projects/{project_id}/opportunities", headers=headers)
    assert res.status_code == 200
    data = res.json()
    opps = data["opportunities"]
    assert len(opps) > 0

    first_opp = opps[0]
    opp_id = first_opp["id"]
    assert first_opp["status"] == "Open"

    # Update status to "In Progress"
    res = client.put(f"/api/projects/{project_id}/opportunities/{opp_id}/status", json={"status": "In Progress"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "In Progress"

    # Re-fetch opportunities and verify persisted status
    res2 = client.get(f"/api/projects/{project_id}/opportunities", headers=headers)
    assert res2.status_code == 200
    updated_opp = next(o for o in res2.json()["opportunities"] if o["id"] == opp_id)
    assert updated_opp["status"] == "In Progress"

    # Update to "Resolved"
    res3 = client.put(f"/api/projects/{project_id}/opportunities/{opp_id}/status", json={"status": "Resolved"}, headers=headers)
    assert res3.status_code == 200

    res4 = client.get(f"/api/projects/{project_id}/opportunities", headers=headers)
    resolved_opp = next(o for o in res4.json()["opportunities"] if o["id"] == opp_id)
    assert resolved_opp["status"] == "Resolved"
