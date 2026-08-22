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

router = APIRouter()

@router.get("")
@router.get("/")
def get_project_alerts(project_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Returns active technical & SEO alerts for a project based strictly on deterministic crawl and audit evidence.
    Never fabricates alerts or claims 'All Systems Normal' unless zero issues actually exist.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    alerts = []
    
    # 1. Check for latest completed crawl session & pages
    safe_domain = get_sanitized_domain(project.domain or "")
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")
    pages = []

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)
        except Exception:
            pages = []

    # 2. Evaluate site audit rules for pages
    if pages:
        audit_res = evaluate_site_audit_rules(pages)
        for issue in audit_res.get("issues", []):
            alerts.append({
                "id": issue.get("rule_id"),
                "category": issue.get("category"),
                "severity": issue.get("severity", "warning").capitalize(), # Critical, Error, Warning, Notice
                "title": issue.get("title"),
                "description": issue.get("description"),
                "affected_count": issue.get("affected_count", 0),
                "recommendation": issue.get("recommendation"),
                "target_link": "#/technical"
            })
    else:
        # Check if crawl has been run
        recent_session = db.query(CrawlSession).filter(CrawlSession.project_id == project.id).first()
        if not recent_session:
            alerts.append({
                "id": "ALERT_NO_CRAWL",
                "category": "Crawl & Audit",
                "severity": "Notice",
                "title": "No Crawl Data Available",
                "description": "This project has not completed a website crawl yet. Run a site crawl to identify technical SEO issues.",
                "affected_count": 0,
                "recommendation": "Go to Technical SEO or Dashboard and start a site crawl.",
                "target_link": "#/technical"
            })

    crit_count = sum(1 for a in alerts if a["severity"] in ("Critical", "Error"))
    warn_count = sum(1 for a in alerts if a["severity"] == "Warning")
    notice_count = sum(1 for a in alerts if a["severity"] == "Notice")

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
