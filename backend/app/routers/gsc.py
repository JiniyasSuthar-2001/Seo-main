import os
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.models.project import Project
from app.models.external_connection import ExternalConnection
from app.config.utils import get_project_storage_dir, normalize_stored_path
from app.providers.gsc_provider import GoogleSearchConsoleProvider
from app.services.audit_rules import evaluate_site_audit_rules

router = APIRouter()

@router.get("/performance")
def get_gsc_performance(
    project_id: str,
    days: int = Query(30),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns authentic Google Search Console search analytics (clicks, impressions, CTR, position).
    If no GSC connection or data exists, returns explicit 'Not Connected' status without inventing fake numbers.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    gsc_file = os.path.join(proj_dir, "gsc_performance.json")

    gsc_data = []
    if os.path.exists(gsc_file):
        try:
            with open(gsc_file, "r", encoding="utf-8") as f:
                gsc_data = json.load(f)
        except Exception:
            gsc_data = []

    # Check for active Google OAuth Connection for this user
    google_conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "google",
        ExternalConnection.status == "CONNECTED"
    ).first()

    total_clicks = sum(r.get("clicks", 0) for r in gsc_data)
    total_impressions = sum(r.get("impressions", 0) for r in gsc_data)
    avg_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions > 0 else 0.0
    avg_pos = round(sum(r.get("position", 0) * r.get("impressions", 0) for r in gsc_data) / total_impressions, 1) if total_impressions > 0 else None

    is_connected = len(gsc_data) > 0 or (google_conn is not None)

    return {
        "project_id": project.id,
        "domain": project.domain,
        "status": "connected" if is_connected else "not_connected",
        "oauth_status": "CONNECTED" if google_conn else "DISCONNECTED",
        "total_clicks": total_clicks if is_connected else "Not Available",
        "total_impressions": total_impressions if is_connected else "Not Available",
        "average_ctr": f"{avg_ctr}%" if total_impressions > 0 else "Not Available",
        "average_position": avg_pos if avg_pos is not None else "Not Available",
        "rows_count": len(gsc_data),
        "queries": gsc_data[:100],
        "message": "Google Search Console active." if is_connected else "Connect Google Search Console in Integrations to view authentic organic search queries and click-through rates.",
        "provenance": {
            "source": "Google Search Console API",
            "date_range": f"Last {days} days"
        }
    }


@router.get("/priorities")
def get_gsc_crawler_priorities(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Computes deterministic Page Prioritization matrix combining Crawler Data + Google Search Console.
    Prioritizes high-opportunity URLs with high organic search impressions but low CTR or high SEO severity issues.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)

    # 1. Load latest crawl pages
    pages = []
    latest_path = os.path.join(proj_dir, "latest.json")
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r", encoding="utf-8") as pf:
                    pages = json.load(pf)
        except Exception:
            pages = []

    # 2. Evaluate site audit rules for pages
    audit_res = evaluate_site_audit_rules(pages) if pages else {"issues": []}
    audit_issues = audit_res.get("issues", [])

    # 3. Load GSC dataset
    gsc_file = os.path.join(proj_dir, "gsc_performance.json")
    gsc_data = []
    if os.path.exists(gsc_file):
        try:
            with open(gsc_file, "r", encoding="utf-8") as gf:
                gsc_data = json.load(gf)
        except Exception:
            gsc_data = []

    # 4. Calculate priorities using deterministic mathematical model
    prioritized_pages = GoogleSearchConsoleProvider.calculate_page_priorities(pages, gsc_data, audit_issues)

    return {
        "project_id": project.id,
        "domain": project.domain,
        "total_prioritized_pages": len(prioritized_pages),
        "high_priority_count": sum(1 for p in prioritized_pages if p["priority_level"] == "High"),
        "medium_priority_count": sum(1 for p in prioritized_pages if p["priority_level"] == "Medium"),
        "low_priority_count": sum(1 for p in prioritized_pages if p["priority_level"] == "Low"),
        "pages": prioritized_pages[:50],
        "prioritization_model": {
            "formula": "Priority Score = (Impressions_Score * 0.40) + (CTR_Gap_Score * 0.30) + (SEO_Issues_Penalty * 0.30)",
            "rationale": "High impression pages with weak CTR or critical SEO errors receive highest remediation priority."
        }
    }


@router.post("/sync")
def sync_gsc_data(
    project_id: str,
    days: int = Body(30, embed=True),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Synchronizes Search Analytics rows from connected Google Search Console account for this domain.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    google_conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider == "google",
        ExternalConnection.status == "CONNECTED"
    ).first()

    if not google_conn:
        raise HTTPException(status_code=400, detail="Google Search Console is not connected. Please connect Google in Settings -> Integrations.")

    access_token = google_conn.get_access_token()
    if not access_token:
        raise HTTPException(status_code=400, detail="Google access token is missing or expired. Please re-authorize Google.")

    provider = GoogleSearchConsoleProvider()
    site_url = f"sc-domain:{project.domain}" if project.domain else project.url
    rows = provider.get_search_analytics(site_url, days=days, access_token=access_token)

    # Persist in project directory
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    os.makedirs(proj_dir, exist_ok=True)
    gsc_file = os.path.join(proj_dir, "gsc_performance.json")

    with open(gsc_file, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)

    return {
        "status": "ok",
        "synced_rows": len(rows),
        "message": f"Successfully synchronized {len(rows)} Search Console queries."
    }
