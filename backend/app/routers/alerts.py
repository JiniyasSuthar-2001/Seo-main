import os
import json
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.models.crawl_session import CrawlSession
from app.services.audit_rules import evaluate_site_audit_rules
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

@router.get("")
@router.get("/")
def get_project_alerts(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Returns active technical & SEO alerts for a project based strictly on deterministic crawl and audit evidence.
    Supports snapshot delta comparison (PREVIOUS CRAWL vs CURRENT CRAWL) when multiple crawls exist.
    Never fabricates alerts or claims 'All Systems Normal' unless zero issues actually exist.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    alerts = []
    
    # 1. Check for latest completed crawl session & pages
    safe_domain = get_sanitized_domain(project.domain or project.url or "")
    domain_dir = os.path.join(settings.CRAWL_DATA_DIR, safe_domain)
    latest_path = os.path.join(domain_dir, "latest.json")
    pages = []
    crawl_timestamp = None

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            crawl_timestamp = latest.get("timestamp") or latest.get("completed_at")
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r", encoding="utf-8") as pf:
                    pages = json.load(pf)
        except Exception:
            pages = []

    # 2. Delta Comparison: Find previous crawl snapshot if available
    prev_pages = []
    if os.path.exists(domain_dir):
        try:
            subdirs = [os.path.join(domain_dir, d) for d in os.listdir(domain_dir) if os.path.isdir(os.path.join(domain_dir, d))]
            subdirs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            # Find second most recent dir containing pages.json
            for sd in subdirs[1:]:
                p_file = os.path.join(sd, "pages.json")
                if os.path.exists(p_file):
                    with open(p_file, "r", encoding="utf-8") as pf:
                        prev_pages = json.load(pf)
                    break
        except Exception:
            prev_pages = []

    # 3. Delta Alerts (PREVIOUS CRAWL vs CURRENT CRAWL)
    if prev_pages and pages:
        prev_map = {p.get("url"): p for p in prev_pages if p.get("url")}
        curr_map = {p.get("url"): p for p in pages if p.get("url")}

        # Delta A: Pages that became unavailable or broken in current crawl
        newly_broken = []
        for url, p in curr_map.items():
            prev_p = prev_map.get(url)
            curr_st = p.get("status_code", 200)
            prev_st = prev_p.get("status_code", 200) if prev_p else 200
            if isinstance(curr_st, int) and curr_st >= 400 and (prev_st < 400 or not prev_p):
                newly_broken.append(url)

        if newly_broken:
            alerts.append({
                "id": "DELTA_BROKEN_PAGES",
                "category": "Crawl Delta",
                "type": "critical",
                "severity": "Critical",
                "title": f"Newly Broken Pages Detected ({len(newly_broken)})",
                "message": f"{len(newly_broken)} page(s) that were previously working now return HTTP error status codes.",
                "description": f"{len(newly_broken)} page(s) that were previously working now return HTTP error status codes.",
                "affected_count": len(newly_broken),
                "affected_urls": newly_broken,
                "recommendation": "Check target server routes, redirects, or restored page availability.",
                "timestamp": crawl_timestamp,
                "target_link": "#/technical"
            })

        # Delta B: Title tags removed in current crawl
        title_removed = []
        for url, p in curr_map.items():
            prev_p = prev_map.get(url)
            if prev_p and prev_p.get("title") and not p.get("title"):
                title_removed.append(url)

        if title_removed:
            alerts.append({
                "id": "DELTA_TITLE_REMOVED",
                "category": "Crawl Delta",
                "type": "error",
                "severity": "Error",
                "title": f"Page Title Tags Removed ({len(title_removed)})",
                "message": f"{len(title_removed)} page(s) had title tags in the previous scan but now lack title tags.",
                "description": f"{len(title_removed)} page(s) had title tags in the previous scan but now lack title tags.",
                "affected_count": len(title_removed),
                "affected_urls": title_removed,
                "recommendation": "Restore HTML <title> elements on affected pages immediately to prevent ranking drops.",
                "timestamp": crawl_timestamp,
                "target_link": "#/technical"
            })

    # 4. Evaluate site audit rules for pages
    if pages:
        audit_res = evaluate_site_audit_rules(pages)
        for issue in audit_res.get("issues", []):
            sev_raw = issue.get("severity", "warning").lower()
            sev_cap = sev_raw.capitalize()
            desc = issue.get("description") or issue.get("evidence") or ""

            alerts.append({
                "id": issue.get("rule_id"),
                "category": issue.get("category"),
                "type": sev_raw, # critical, error, warning, notice
                "severity": sev_cap, # Critical, Error, Warning, Notice
                "title": issue.get("title"),
                "message": desc,
                "description": desc,
                "affected_count": issue.get("affected_count", 0),
                "affected_urls": issue.get("affected_urls") or issue.get("sample_urls") or issue.get("affected_items") or [],
                "recommendation": issue.get("recommendation"),
                "timestamp": crawl_timestamp,
                "target_link": "#/technical"
            })
    else:
        # Check if crawl has been run
        recent_session = db.query(CrawlSession).filter(CrawlSession.project_id == project.id).first()
        if not recent_session:
            alerts.append({
                "id": "ALERT_NO_CRAWL",
                "category": "Crawl & Audit",
                "type": "notice",
                "severity": "Notice",
                "title": "No Website Scan Data Available",
                "message": "This website project has not completed a scan yet. Scan your website to detect active SEO alerts.",
                "description": "This website project has not completed a scan yet. Scan your website to detect active SEO alerts.",
                "affected_count": 0,
                "affected_urls": [],
                "recommendation": "Click 'Scan My Website' to start analyzing your pages.",
                "timestamp": None,
                "target_link": "#/technical"
            })

    crit_count = sum(1 for a in alerts if a["type"] in ("critical", "error"))
    warn_count = sum(1 for a in alerts if a["type"] == "warning")
    notice_count = sum(1 for a in alerts if a["type"] == "notice")

    return {
        "project_id": project.id,
        "domain": project.domain,
        "total_alerts": len(alerts),
        "summary": {
            "critical": crit_count,
            "warning": warn_count,
            "notice": notice_count
        },
        "alerts": alerts,
        "has_alerts": len(alerts) > 0,
        "message": f"Identified {len(alerts)} active alerts." if alerts else "No active alerts detected for this project."
    }
