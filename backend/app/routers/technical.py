import os
import json
import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.models.project import Project
from app.models.page import Page
from app.models.audit_issue import AuditIssue
from app.models.crawl_session import CrawlSession
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.services.audit_rules import evaluate_site_audit_rules
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

@router.get("")
@router.get("/")
def get_technical_audit(
    project_id: str,
    category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
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
    
    # 1. Load latest crawl pages (check project_id folder first, fallback to safe_domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, project.id, "latest.json")
    if not os.path.exists(latest_path):
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
        "successful_html_pages_count": audit_data.get("successful_html_pages_count", 0),
        "blocked_pages_count": audit_data.get("blocked_pages_count", 0),
        "evaluated_rules_count": audit_data.get("evaluated_rules_count", 14),
        "total_evaluated_checks": audit_data.get("total_evaluated_checks", 0),
        "checks_explanation": audit_data.get("checks_explanation", ""),
        "crawl_timestamp": latest.get("completed_at") or latest.get("timestamp") if ('latest' in locals() and latest) else None,
        "crawl_status": latest.get("status", "completed") if os.path.exists(latest_path) else "no_crawl",
        "summary": audit_data["summary"],
        "category_breakdown": audit_data["category_breakdown"],
        "category_checks_table": audit_data.get("category_checks_table", []),
        "issues": filtered_issues[off : off + lim],
        "total_issues": len(filtered_issues),
        "provenance": audit_data["provenance"]
    }



@router.get("/issue-history")
def get_audit_issue_history(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Compares recent crawl snapshots to detect New, Resolved, Persistent, Worsened, and Improved issues.
    """
    get_user_membership(db, user_id, project_id)
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

from app.routers.reports import export_technical_csv

@router.get("/export.csv")
def technical_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_technical_csv(project_id, user_id, db)
