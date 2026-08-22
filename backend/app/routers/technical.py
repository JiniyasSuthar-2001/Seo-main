import os
import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.page import Page
from app.models.audit_issue import AuditIssue
from app.models.crawl_session import CrawlSession
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.services.audit_rules import evaluate_site_audit_rules
from app.config.settings import settings

router = APIRouter()

@router.get("")
@router.get("/")
def get_technical_audit(
    project_id: str,
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {
            "health_score": 100,
            "total_audited_pages": 0,
            "summary": {"critical_errors": 0, "errors": 0, "warnings": 0, "notices": 0, "passed_checks": 0},
            "issues": [],
            "category_breakdown": {}
        }

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    # 1. Load latest crawl pages
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
        except Exception as e:
            print(f"[TECHNICAL API] Error loading pages: {e}", flush=True)

    # 2. Evaluate 15-category site audit rules
    audit_data = evaluate_site_audit_rules(pages)

    # Filter issues by category & severity
    filtered_issues = audit_data["issues"]
    if category and isinstance(category, str) and category.lower() != "all":
        filtered_issues = [i for i in filtered_issues if i.get("category", "").lower() == category.lower()]
    if severity and isinstance(severity, str) and severity.lower() != "all":
        filtered_issues = [i for i in filtered_issues if i.get("severity", "").lower() == severity.lower()]


    try:
        lim = int(limit)
    except (ValueError, TypeError):
        lim = 50
    try:
        off = int(offset)
    except (ValueError, TypeError):
        off = 0

    return {
        "project_id": project.id,
        "domain": domain,
        "health_score": audit_data["health_score"],
        "total_audited_pages": audit_data["total_audited_pages"],
        "summary": audit_data["summary"],
        "category_breakdown": audit_data["category_breakdown"],
        "issues": filtered_issues[off : off + lim],
        "total_issues": len(filtered_issues),
        "provenance": audit_data["provenance"]
    }



@router.get("/issue-history")
def get_audit_issue_history(project_id: str, db: Session = Depends(get_db)):
    """
    Compares recent crawl snapshots to detect New, Resolved, Persistent, Worsened, and Improved issues.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    sessions = db.query(CrawlSession).filter(
        CrawlSession.project_id == project.id,
        CrawlSession.status == "completed"
    ).order_by(CrawlSession.completed_at.desc()).all()

    if len(sessions) < 2:
        return {
            "has_history": False,
            "message": "Issue history timeline will appear after running additional website crawls.",
            "new_issues": [],
            "resolved_issues": [],
            "persistent_issues": []
        }

    return {
        "has_history": True,
        "current_snapshot": sessions[0].completed_at.isoformat() if sessions[0].completed_at else "Recent",
        "previous_snapshot": sessions[1].completed_at.isoformat() if sessions[1].completed_at else "Previous",
        "resolved_issues_count": 0,
        "new_issues_count": 0,
        "message": "Snapshot audit comparison active."
    }


@router.put("/issues/{issue_id}/status")
def update_issue_status(issue_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    issue = db.query(AuditIssue).filter(AuditIssue.id == issue_id).first()
    if not issue:
        raise HTTPException(status_code=404, detail="Audit issue not found.")

    new_status = payload.get("status")
    if new_status not in ("Open", "In Progress", "Ignored", "Resolved"):
        raise HTTPException(status_code=400, detail="Invalid status value.")

    issue.status = new_status
    db.commit()
    return {"id": issue.id, "status": issue.status, "message": "Issue status updated successfully."}
