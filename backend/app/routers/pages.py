import os
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings
from app.models.project import Project

router = APIRouter()

def get_latest_pages_from_storage(project_id: str, domain: Optional[str] = None) -> list:
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, project_id, "latest.json")
    if not os.path.exists(latest_path) and domain:
        safe_domain = get_sanitized_domain(domain)
        latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    if not os.path.exists(latest_path):
        return []
        
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            latest = json.load(f)
            
        crawl_dir = normalize_stored_path(latest.get("path"))
        pages_file = os.path.join(crawl_dir, "pages.json")
        if os.path.exists(pages_file):
            with open(pages_file, "r", encoding="utf-8") as pf:
                return json.load(pf)
    except Exception as e:
        print(f"[PAGES API ERROR] Failed to read pages.json for project '{project_id}': {e}", flush=True)
        
    return []

@router.get("")
@router.get("/")
def get_pages(
    project_id: str,
    limit: int = Query(20),
    offset: int = Query(0),
    status: Optional[str] = Query("all"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    membership = get_user_membership(db, user_id, project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"pages": [], "items": [], "total": 0, "pages_crawled": 0, "pages_failed": 0, "pages_blocked": 0, "pages_skipped": 0, "limit": limit, "offset": offset}
    
    all_pages = get_latest_pages_from_storage(project.id, project.domain)

    crawled = []
    failed = []
    blocked = []
    skipped = []

    for p in all_pages:
        st_code = p.get("status_code") or 0
        fetch_st = (p.get("fetch_status") or "").upper()

        if fetch_st == "SKIPPED":
            skipped.append(p)
        elif st_code in (401, 403) or fetch_st == "BLOCKED":
            blocked.append(p)
        elif not p.get("is_success", True) or st_code >= 400 or fetch_st in ("FAILED", "TIMEOUT", "ERROR"):
            failed.append(p)
        else:
            crawled.append(p)

    target_status = (status or "all").lower().strip()
    if target_status == "crawled":
        filtered = crawled
    elif target_status == "failed":
        filtered = failed
    elif target_status == "blocked":
        filtered = blocked
    elif target_status == "skipped":
        filtered = skipped
    else:
        filtered = all_pages

    try:
        lim = max(1, min(int(limit), 100))
    except (ValueError, TypeError):
        lim = 20

    try:
        off = max(0, int(offset))
    except (ValueError, TypeError):
        off = 0

    paginated = filtered[off : off + lim]

    return {
        "pages": paginated,
        "items": paginated,
        "total": len(filtered),
        "total_all": len(all_pages),
        "pages_crawled": len(crawled),
        "pages_failed": len(failed),
        "pages_blocked": len(blocked),
        "pages_skipped": len(skipped),
        "limit": lim,
        "offset": off
    }

@router.get("/{page_id}")
def get_page(
    project_id: str,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    all_pages = get_latest_pages_from_storage(project.id, project.domain)
    for page in all_pages:
        if page.get("url") == page_id or page.get("title") == page_id or page.get("id") == page_id:
            return page
    raise HTTPException(status_code=404, detail="Page not found in latest crawl snapshot.")
