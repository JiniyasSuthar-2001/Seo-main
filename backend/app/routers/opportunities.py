import uuid
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.keyword import Keyword
from app.models.page import Page
from app.models.action_opportunity import ActionOpportunity
from app.services.audit_rules import evaluate_site_audit_rules
from app.services.opportunity_engine import (
    generate_central_opportunities,
    sync_project_opportunities
)
from app.services.link_graph_engine import build_internal_link_graph
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.routers.reports import export_opportunities_csv

router = APIRouter()


def _load_project_crawl_data(project: Project) -> Dict[str, Any]:
    domain = project.domain or project.url
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    has_crawl = False
    pages = []
    issues = []
    internal_links = []
    link_records = []
    latest_meta = {}

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest_meta = json.load(f)
            crawl_dir = normalize_stored_path(latest_meta.get("path"))
            
            if crawl_dir and os.path.exists(crawl_dir):
                pages_file = os.path.join(crawl_dir, "pages.json")
                issues_file = os.path.join(crawl_dir, "issues.json")
                links_file = os.path.join(crawl_dir, "internal_links.json")
                rec_file = os.path.join(crawl_dir, "link_records.json")

                if os.path.exists(pages_file):
                    with open(pages_file, "r", encoding="utf-8") as pf:
                        pages = json.load(pf)
                    has_crawl = True
                if os.path.exists(issues_file):
                    with open(issues_file, "r", encoding="utf-8") as isf:
                        issues = json.load(isf)
                if os.path.exists(links_file):
                    with open(links_file, "r", encoding="utf-8") as lf:
                        internal_links = json.load(lf)
                if os.path.exists(rec_file):
                    with open(rec_file, "r", encoding="utf-8") as rf:
                        link_records = json.load(rf)
        except Exception as e:
            from app.config.logger import get_logger
            get_logger("opportunities").warning(f"Error reading latest crawl snapshot for project {project.id}: {e}")

    return {
        "has_crawl": has_crawl,
        "pages": pages,
        "issues": issues,
        "internal_links": internal_links,
        "link_records": link_records,
        "latest_meta": latest_meta
    }


@router.get("")
@router.get("/")
def get_project_opportunities(
    project_id: str,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    refresh: Optional[bool] = Query(False, description="Sync new crawl evidence while preserving user status"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    crawl_data = _load_project_crawl_data(project)
    has_crawl = crawl_data["has_crawl"]
    pages = crawl_data["pages"]
    issues = crawl_data["issues"]
    internal_links = crawl_data["internal_links"]
    link_records = crawl_data["link_records"]
    latest_meta = crawl_data["latest_meta"]

    # Fallback to DB pages if disk pages empty
    if not pages:
        pages_records = db.query(Page).filter(Page.project_id == project.id).all()
        if pages_records:
            pages = [p.__dict__ for p in pages_records]
            has_crawl = True

    # 1. Sync opportunities if none exist OR if refresh is requested
    existing_count = db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).count()
    if (existing_count == 0 or refresh) and has_crawl and pages:
        kw_records = db.query(Keyword).filter(Keyword.project_id == project.id).all()
        keywords = [k.__dict__ for k in kw_records]
        
        audit_eval = evaluate_site_audit_rules(pages) if not issues else {"issues": issues}
        graph_data = build_internal_link_graph(pages, internal_links, link_records=link_records, seed_url=f"https://{project.domain}/")

        sync_project_opportunities(
            db=db,
            project_id=project.id,
            audit_results=audit_eval,
            keywords=keywords,
            pages=pages,
            internal_links=internal_links,
            graph_data=graph_data
        )

    # 2. Query persisted DB opportunities (Strictly read-only)
    db_opps = db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).order_by(ActionOpportunity.priority_score.desc()).all()

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
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
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


@router.post("/sync")
def sync_opportunities_api(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Explicitly synchronizes opportunities from latest crawl data while preserving user lifecycle statuses.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    crawl_data = _load_project_crawl_data(project)
    pages = crawl_data["pages"]
    issues = crawl_data["issues"]
    internal_links = crawl_data["internal_links"]
    link_records = crawl_data["link_records"]

    if not pages:
        pages_records = db.query(Page).filter(Page.project_id == project.id).all()
        if pages_records:
            pages = [p.__dict__ for p in pages_records]

    if not pages:
        return {"project_id": project.id, "message": "No crawl data available to evaluate opportunities.", "opportunities_count": 0}

    kw_records = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    keywords = [k.__dict__ for k in kw_records]

    audit_eval = evaluate_site_audit_rules(pages) if not issues else {"issues": issues}
    graph_data = build_internal_link_graph(pages, internal_links, link_records=link_records, seed_url=f"https://{project.domain}/")

    synced = sync_project_opportunities(
        db=db,
        project_id=project.id,
        audit_results=audit_eval,
        keywords=keywords,
        pages=pages,
        internal_links=internal_links,
        graph_data=graph_data
    )

    return {
        "project_id": project.id,
        "message": f"Successfully evaluated and synchronized {len(synced)} opportunities.",
        "opportunities_count": len(synced)
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
    if new_status not in ("Open", "In Progress", "Ignored", "Resolved", "Detected"):
        raise HTTPException(status_code=400, detail="Invalid status value. Must be Detected, Open, In Progress, Ignored, or Resolved.")

    opp.status = new_status
    opp.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(opp)
    return {"id": opp.id, "status": opp.status, "message": f"Opportunity status updated to '{new_status}'."}


@router.get("/export.csv")
def opportunities_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_opportunities_csv(project_id, user_id, db)
