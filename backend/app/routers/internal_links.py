from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
import os
import json

router = APIRouter()

def get_latest_links_from_storage(domain: str) -> list:
    safe_domain = get_sanitized_domain(domain)
    
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        return []
        
    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
            
        crawl_dir = normalize_stored_path(latest.get("path"))
        links_file = os.path.join(crawl_dir, "internal_links.json")
        if os.path.exists(links_file):
            with open(links_file, "r") as pf:
                return json.load(pf)
    except Exception as e:
        print(f"[LINKS API] Failed to read internal_links.json: {e}", flush=True)
        
    return []

@router.get("")
@router.get("/")
def get_internal_links(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return []
        
    all_links = get_latest_links_from_storage(project.domain)
    paginated = all_links[offset : offset + limit]
    return paginated
