import os
import json
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings
from app.routers.projects import get_project_metrics

router = APIRouter()

@router.get("/overview")
def get_workspace_overview(db: Session = Depends(get_db)):
    """
    Account / Workspace-Level Overview Endpoint.
    Aggregates metrics, crawl history, and technical issues across ALL websites.
    """
    projects = db.query(Project).all()

    total_projects = len(projects)
    active_projects = 0
    total_crawls = 0
    total_pages_crawled = 0
    total_critical_issues = 0
    total_warnings = 0
    health_scores = []

    projects_summary = []
    all_crawls = []
    issues_by_type = defaultdict(lambda: {
        "title": "",
        "severity": "notice",
        "affected_websites": set(),
        "total_urls_count": 0
    })

    for p in projects:
        safe_domain = get_sanitized_domain(p.domain or p.url)
        website_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
        metrics = get_project_metrics(p.domain or p.url)

        has_crawled = metrics.get("has_crawled", False)
        if has_crawled:
            active_projects += 1
            total_pages_crawled += metrics.get("pages_count", 0)
            total_critical_issues += metrics.get("critical_issues", 0)
            total_warnings += metrics.get("warnings", 0)

        # Health score calculation for this project
        latest_path = os.path.join(website_dir, "latest.json")
        project_health = None

        if os.path.exists(latest_path):
            try:
                with open(latest_path, "r") as f:
                    latest = json.load(f)
                crawl_dir = normalize_stored_path(latest.get("path"))
                if crawl_dir and os.path.exists(crawl_dir):
                    issues_path = os.path.join(crawl_dir, "issues.json")
                    if os.path.exists(issues_path):
                        with open(issues_path, "r") as isf:
                            p_issues = json.load(isf)
                            crit = sum(1 for i in p_issues if i.get("severity") in ("critical", "error"))
                            warn = sum(1 for i in p_issues if i.get("severity") == "warning")
                            pages_c = metrics.get("pages_count", 1) or 1
                            total_checks = pages_c * 5
                            failed_weight = (crit * 2) + warn
                            passed = max(0, total_checks - failed_weight)
                            project_health = min(100, max(0, round((passed / total_checks) * 100)))
                            health_scores.append(project_health)

                            # Aggregate account-wide issue breakdown
                            for iss in p_issues:
                                itype = iss.get("issue_type") or iss.get("title") or "Technical Issue"
                                entry = issues_by_type[itype]
                                entry["title"] = iss.get("title") or itype
                                entry["severity"] = iss.get("severity", "notice")
                                entry["affected_websites"].add(p.name)
                                urls_cnt = len(iss.get("affected_urls", [])) or iss.get("affected_pages_count", 1)
                                entry["total_urls_count"] += urls_cnt
            except Exception as e:
                print(f"[WORKSPACE API] Error reading issues for {p.name}: {e}", flush=True)

        p_summary = {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "domain": p.domain,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "has_crawled": has_crawled,
            "health_score": project_health,
            "pages_crawled": metrics.get("pages_count", 0),
            "issues_count": metrics.get("issues_count", 0),
            "critical_issues": metrics.get("critical_issues", 0),
            "warnings": metrics.get("warnings", 0),
            "last_crawl": metrics.get("last_crawl"),
            "crawl_status": metrics.get("crawl_status", "No Crawls")
        }
        projects_summary.append(p_summary)

        # Collect crawl history
        crawls_dir = os.path.join(website_dir, "crawls")
        if os.path.exists(crawls_dir):
            try:
                for folder in os.listdir(crawls_dir):
                    meta_path = os.path.join(crawls_dir, folder, "metadata.json")
                    if os.path.exists(meta_path):
                        with open(meta_path, "r") as mf:
                            c_meta = json.load(mf)
                            c_meta["project_id"] = p.id
                            c_meta["project_name"] = p.name
                            c_meta["domain"] = p.domain
                            all_crawls.append(c_meta)
            except Exception:
                pass

    total_crawls = len(all_crawls)
    all_crawls.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    avg_health = round(sum(health_scores) / len(health_scores)) if health_scores else None

    # Format account-wide issue summary list
    account_issues = []
    for itype, data in issues_by_type.items():
        account_issues.append({
            "title": data["title"],
            "severity": data["severity"],
            "affected_websites_count": len(data["affected_websites"]),
            "affected_websites": list(data["affected_websites"]),
            "total_urls_count": data["total_urls_count"]
        })
    account_issues.sort(key=lambda x: (0 if x["severity"] in ("critical", "error") else (1 if x["severity"] == "warning" else 2), -x["affected_websites_count"]))

    return {
        "workspace_summary": {
            "total_projects": total_projects,
            "active_projects": active_projects,
            "total_crawls": total_crawls,
            "total_pages_crawled": total_pages_crawled,
            "critical_issues": total_critical_issues,
            "warnings": total_warnings,
            "average_health": avg_health
        },
        "projects": projects_summary,
        "recent_crawls": all_crawls[:10],
        "account_issues_summary": account_issues[:10]
    }
