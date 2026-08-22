import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if not os.environ.get("ENCRYPTION_KEY"):
    os.environ["ENCRYPTION_KEY"] = "test-encryption-key-for-unit-audit-suite-32b"
if not os.environ.get("SECRET_KEY"):
    os.environ["SECRET_KEY"] = "test-secret-key-for-signing-session-32b"
if not os.environ.get("OAUTH_STATE_SECRET"):
    os.environ["OAUTH_STATE_SECRET"] = "test-oauth-state-secret-signing-32b"

def test_deep_endpoint_audit():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.config.database import SessionLocal
    from app.models.project import Project

    client = TestClient(app)
    db = SessionLocal()

    project = db.query(Project).first()
    if not project:
        project = Project(name="Audit Suite Project", domain="https://example.com")
        db.add(project)
        db.commit()
        db.refresh(project)

    project_id = project.id
    db.close()

    res = client.get("/api/health")
    assert res.status_code == 200

    res_projects = client.get("/api/projects")
    assert res_projects.status_code == 200

    res_proj = client.get(f"/api/projects/{project_id}")
    assert res_proj.status_code == 200

    res_tech = client.get(f"/api/projects/{project_id}/technical")
    assert res_tech.status_code == 200

    res_opps = client.get(f"/api/projects/{project_id}/opportunities")
    assert res_opps.status_code == 200

if __name__ == "__main__":
    test_deep_endpoint_audit()
