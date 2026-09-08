import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.keyword import Keyword
from app.models.page import Page
from app.models.action_opportunity import ActionOpportunity
from app.services.audit_rules import evaluate_site_audit_rules
from app.services.opportunity_engine import generate_central_opportunities

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

import os
import json
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir

@router.get("")
@router.get("/")
def get_project_opportunities(
    project_id: str,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 1. Load latest crawl snapshot from disk
    domain = project.domain or project.url
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    has_crawl = False
    pages = []
    issues = []
    latest_meta = {}

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest_meta = json.load(f)
            crawl_dir = normalize_stored_path(latest_meta.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            issues_file = os.path.join(crawl_dir, "issues.json")
            
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)
                has_crawl = True
            if os.path.exists(issues_file):
                with open(issues_file, "r") as isf:
                    issues = json.load(isf)
        except Exception as e:
            from app.config.logger import get_logger
            get_logger("opportunities").warning(f"Error reading latest crawl snapshot for project {project_id}: {e}")

    # Fallback to DB pages if disk pages empty
    if not pages:
        pages_records = db.query(Page).filter(Page.project_id == project.id).all()
        if pages_records:
            pages = [p.__dict__ for p in pages_records]
            has_crawl = True

    # 2. Generate initial opportunities only if none exist in DB for this project
    existing_opps = db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).all()
    if has_crawl and pages and not existing_opps:
        kw_records = db.query(Keyword).filter(Keyword.project_id == project.id).all()
        keywords = [k.__dict__ for k in kw_records]

        audit_eval = evaluate_site_audit_rules(pages)
        generated = generate_central_opportunities(audit_eval, keywords, pages)
        
        for item in generated:
            new_opp = ActionOpportunity(
                id=str(uuid.uuid4()),
                project_id=project.id,
                title=item["title"],
                category=item["category"],
                priority_score=item["priority_score"],
                priority_level=item["priority_level"],
                impact=item["impact"],
                evidence=item["evidence"],
                affected_urls_json=json.dumps(item.get("affected_urls", [])),
                affected_count=item.get("affected_count", 1),
                recommendation=item["recommendation"],
                status="Open"
            )
            db.add(new_opp)
        db.commit()

    # 3. Fetch DB opportunities
    db_opps = db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).all()

    # Filter by category and status
    filtered = db_opps
    if category and category.lower() != "all":
        filtered = [o for o in filtered if o.category.lower() == category.lower()]
    if status and status.lower() != "all":
        filtered = [o for o in filtered if o.status.lower() == status.lower()]

    last_crawled_at = latest_meta.get("completed_at") or latest_meta.get("timestamp") or (project.updated_at.isoformat() if project.updated_at else None)

    result = []
    for o in filtered:
        urls = []
        if o.affected_urls_json:
            try:
                urls = json.loads(o.affected_urls_json)
            except Exception:
                urls = []

        result.append({
            "id": o.id,
            "project_id": o.project_id,
            "title": o.title,
            "category": o.category,
            "priority_score": o.priority_score,
            "priority_level": o.priority_level,
            "impact": o.impact,
            "evidence": o.evidence,
            "affected_urls": urls,
            "affected_count": o.affected_count,
            "recommendation": o.recommendation,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "provenance": {
                "source": "Crawled Data",
                "confidence": 100.0,
                "last_detected": last_crawled_at
            }
        })

    crawl_status = latest_meta.get("status", "completed") if has_crawl else "no_crawl"
    pages_failed = latest_meta.get("failed_pages", 0) or latest_meta.get("pages_failed", 0)

    return {
        "project_id": project.id,
        "has_crawl": has_crawl,
        "status": crawl_status,
        "crawl_context": {
            "timestamp": last_crawled_at,
            "pages_analyzed": len(pages),
            "pages_failed": pages_failed,
            "total_issues": len(issues)
        },
        "total_opportunities": len(result),
        "opportunities": result
    }


@router.put("/{opportunity_id}/status")
def update_opportunity_status(
    opportunity_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    opp = db.query(ActionOpportunity).filter(ActionOpportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Action opportunity not found.")

    get_user_membership(db, user_id, opp.project_id)

    new_status = payload.get("status")
    if new_status not in ("Open", "In Progress", "Ignored", "Resolved"):
        raise HTTPException(status_code=400, detail="Invalid status value. Must be Open, In Progress, Ignored, or Resolved.")

    opp.status = new_status
    db.commit()
    db.refresh(opp)
    return {"id": opp.id, "status": opp.status, "message": f"Opportunity status updated to '{new_status}'."}

from app.routers.reports import export_opportunities_csv

@router.get("/export.csv")
def opportunities_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_opportunities_csv(project_id, user_id, db)

def json_dumps(val):
    import json
    return json.dumps(val)
