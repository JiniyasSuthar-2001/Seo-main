from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
import os
import json

router = APIRouter()

@router.get("")
@router.get("/")
def get_backlinks(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"outbound_links": [], "inbound_backlinks": [], "status": "empty"}

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    outbound_links = []
    
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            ext_file = os.path.join(crawl_dir, "external_links.json")
            if os.path.exists(ext_file):
                with open(ext_file, "r") as ef:
                    outbound_links = json.load(ef)
        except Exception as e:
            print(f"[BACKLINKS API] Error loading external links: {e}", flush=True)

    return {
        "domain": domain,
        "outbound_links": outbound_links[offset : offset + limit],
        "total_outbound_links": len(outbound_links),
        "inbound_backlinks": [],
        "inbound_status": "Provider Not Connected",
        "message": "Outbound external links are collected automatically from your website crawl. Inbound web-wide backlink intelligence requires a backlink provider connection or CSV dataset import."
    }
