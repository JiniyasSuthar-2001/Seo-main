from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
import os
import json

router = APIRouter()

def get_latest_pages_from_storage(domain: str) -> list:
    safe_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    safe_domain = "".join([c if c.isalnum() else "_" for c in safe_domain])
    
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        return []
        
    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
            
        pages_file = os.path.join(latest.get("path"), "pages.json")
        if os.path.exists(pages_file):
            with open(pages_file, "r") as pf:
                return json.load(pf)
    except Exception as e:
        print(f"[PAGES API] Failed to read pages.json: {e}", flush=True)
        
    return []

@router.get("/")
def get_pages(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if project else "uisdigital.com"
    
    all_pages = get_latest_pages_from_storage(domain)
    paginated = all_pages[offset : offset + limit]
    return paginated

@router.get("/{page_id}")
def get_page(project_id: str, page_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if project else "uisdigital.com"
    
    all_pages = get_latest_pages_from_storage(domain)
    for page in all_pages:
        if page.get("url") == page_id or page.get("title") == page_id:
            return page
    raise HTTPException(status_code=404, detail="Page not found in latest crawl snapshot")
