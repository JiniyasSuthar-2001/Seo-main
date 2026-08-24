import os
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings
from app.models.project import Project

router = APIRouter()

def get_latest_pages_from_storage(domain: str) -> list:
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
        print(f"[PAGES API ERROR] Failed to read pages.json for domain '{domain}': {e}", flush=True)
        
    return []

@router.get("")
@router.get("/")
def get_pages(
    project_id: str,
    limit: int = Query(100),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    print(f"[PAGES] Request received for project_id='{project_id}'", flush=True)
    print(f"[PAGES] User resolved: '{user_id}'", flush=True)

    # Enforce project membership authorization
    membership = get_user_membership(db, user_id, project_id)
    print(f"[PAGES] Authorization verified. Role='{membership.role}'", flush=True)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        print(f"[PAGES] Project or domain not found. Returning empty pages list.", flush=True)
        return {"pages": [], "total": 0}
    
    print(f"[PAGES] Querying crawl/page records for domain '{project.domain}'...", flush=True)
    all_pages = get_latest_pages_from_storage(project.domain)
    paginated = all_pages[offset : offset + limit]
    print(f"[PAGES] Returning {len(paginated)} pages (Total={len(all_pages)}).", flush=True)

    return {"pages": paginated, "total": len(all_pages)}

@router.get("/{page_id}")
def get_page(
    project_id: str,
    page_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found.")
        
    all_pages = get_latest_pages_from_storage(project.domain)
    for page in all_pages:
        if page.get("url") == page_id or page.get("title") == page_id or page.get("id") == page_id:
            return page
    raise HTTPException(status_code=404, detail="Page not found in latest crawl snapshot.")
