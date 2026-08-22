import os
import sys

# Ensure backend directory is on Python path
sys.path.insert(0, os.path.abspath("backend"))

def test_full_system_deep_audit():
    print("============================================================", flush=True)
    print(" SEO INTELLIGENCE PLATFORM - COMPREHENSIVE ENDPOINT AUDIT", flush=True)
    print("============================================================\n", flush=True)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.config.database import SessionLocal
    from app.models.project import Project

    client = TestClient(app)
    db = SessionLocal()

    # 1. Health Check
    res_health = client.get("/api/health")
    print(f"[HEALTH CHECK] GET /api/health -> status={res_health.status_code}, payload={res_health.json()}", flush=True)
    assert res_health.status_code == 200, "Health check failed"

    # 2. Query Existing Projects
    projects = db.query(Project).all()
    print(f"\n[PROJECTS] Found {len(projects)} projects in local SQLite database.", flush=True)
    assert len(projects) > 0, "No projects in DB"

    test_project = projects[0]
    p_id = test_project.id
    print(f"--> Target Test Project: ID={p_id}, Name='{test_project.name}', Domain='{test_project.domain}'\n", flush=True)

    endpoints_to_test = [
        ("Projects List", f"/api/projects", "GET"),
        ("Single Project", f"/api/projects/{p_id}", "GET"),
        ("Project Summary", f"/api/projects/{p_id}/summary", "GET"),
        ("Project Crawls", f"/api/projects/{p_id}/crawls", "GET"),
        ("Pages Audit", f"/api/projects/{p_id}/pages?limit=50", "GET"),
        ("Technical Issues", f"/api/projects/{p_id}/technical?limit=50", "GET"),
        ("Internal Link Graph", f"/api/projects/{p_id}/internal-links?limit=50", "GET"),
        ("Keywords Extracted", f"/api/projects/{p_id}/keywords?limit=50", "GET"),
        ("Google Autocomplete", f"/api/projects/{p_id}/keywords/autocomplete?q=seo", "GET"),
        ("Backlinks Intelligence", f"/api/projects/{p_id}/backlinks", "GET"),
        ("SERP Rankings", f"/api/projects/{p_id}/rankings", "GET"),
        ("Discovered Competitors", f"/api/projects/{p_id}/competitors/discovered", "GET"),
        ("Confirmed Competitors", f"/api/projects/{p_id}/competitors?status=Confirmed", "GET"),
        ("Competitor Gap Analysis", f"/api/projects/{p_id}/competitors/gap-analysis", "GET"),
        ("Data Source Center", f"/api/projects/{p_id}/datasources", "GET"),
        ("Crawl History", f"/api/projects/{p_id}/crawl-history", "GET"),
        ("Executive PDF Report", f"/api/projects/{p_id}/report.pdf", "GET"),
        ("Pages PDF Report", f"/api/projects/{p_id}/pages/report.pdf", "GET"),
        ("Technical PDF Report", f"/api/projects/{p_id}/technical/report.pdf", "GET"),
        ("Keywords PDF Report", f"/api/projects/{p_id}/reports/keywords", "GET"),
        ("Internal Links PDF Report", f"/api/projects/{p_id}/internal-links/report.pdf", "GET"),
        ("Project Data Export JSON", f"/api/projects/{p_id}/export", "GET"),
        ("Pages CSV Export", f"/api/projects/{p_id}/pages/export.csv", "GET"),
        ("Technical CSV Export", f"/api/projects/{p_id}/technical/export.csv", "GET"),
        ("Internal Links CSV Export", f"/api/projects/{p_id}/internal-links/export.csv", "GET"),
        ("Keywords CSV Export", f"/api/projects/{p_id}/keywords/export.csv", "GET"),
        ("Rankings CSV Export", f"/api/projects/{p_id}/rankings/export.csv", "GET"),
        ("Backlinks CSV Export", f"/api/projects/{p_id}/backlinks/export.csv", "GET"),
        ("Competitors CSV Export", f"/api/projects/{p_id}/competitors/export.csv", "GET"),
        ("All Projects PDF Overview", f"/api/projects/all/pdf", "GET"),
        ("All Projects ZIP Export", f"/api/projects/all/export", "GET"),
        ("AI Insights Analysis", f"/api/projects/{p_id}/ai/insights", "GET"),
    ]

    passed_count = 0
    failed_count = 0

    for label, url, method in endpoints_to_test:
        try:
            if method == "GET":
                res = client.get(url)
            elif method == "POST":
                res = client.post(url)

            if res.status_code == 200:
                content_len = len(res.content)
                header_snippet = res.content[:10].decode('latin-1', errors='replace') if content_len > 0 else "empty"
                print(f"[PASS] {label:28} | {method} {url:55} | 200 OK ({content_len} bytes)", flush=True)
                passed_count += 1
            else:
                print(f"[FAIL] {label:28} | {method} {url:55} | status={res.status_code}, body={res.text[:100]}", flush=True)
                failed_count += 1
        except Exception as err:
            print(f"[ERROR] {label:27} | {method} {url:55} | EXCEPTION: {err}", flush=True)
            failed_count += 1

    # 3. Test AI Chat Endpoint (POST)
    try:
        res_chat = client.post(f"/api/projects/{p_id}/ai/chat", json={"query": "What are top technical issues?"})
        if res_chat.status_code == 200:
            print(f"[PASS] {'AI Chat Assistant':28} | POST /api/projects/{p_id}/ai/chat               | 200 OK ({len(res_chat.content)} bytes)", flush=True)
            passed_count += 1
        else:
            print(f"[FAIL] {'AI Chat Assistant':28} | POST /api/projects/{p_id}/ai/chat               | status={res_chat.status_code}", flush=True)
            failed_count += 1
    except Exception as err:
        print(f"[ERROR] AI Chat Assistant | EXCEPTION: {err}", flush=True)
        failed_count += 1

    # 4. Test CRUD Project Creation & Deletion Safety
    try:
        test_domain = "https://audit-test-temp-site.com/"
        res_create = client.post("/api/projects", json={"name": "Temp Audit Project", "url": test_domain})
        assert res_create.status_code == 200, f"Project creation returned {res_create.status_code}"
        created_json = res_create.json()
        created_proj_id = created_json.get("project", {}).get("id") or created_json.get("id")
        assert created_proj_id, "No project ID returned"
        print(f"[PASS] {'Create Temp Project':28} | POST /api/projects                                  | 200 OK (Created ID={created_proj_id})", flush=True)

        res_del = client.delete(f"/api/projects/{created_proj_id}")
        assert res_del.status_code == 200, f"Project deletion returned {res_del.status_code}"
        print(f"[PASS] {'Delete Temp Project':28} | DELETE /api/projects/{created_proj_id:36} | 200 OK (Clean deletion)", flush=True)
        passed_count += 2
    except Exception as err:
        print(f"[ERROR] CRUD Project Creation/Deletion | EXCEPTION: {err}", flush=True)
        failed_count += 1

    db.close()

    print("\n============================================================", flush=True)
    print(f" AUDIT VERIFICATION RESULTS: {passed_count} PASSED / {failed_count} FAILED", flush=True)
    print("============================================================\n", flush=True)
    assert failed_count == 0, f"{failed_count} endpoints failed verification!"

if __name__ == "__main__":
    test_full_system_deep_audit()
