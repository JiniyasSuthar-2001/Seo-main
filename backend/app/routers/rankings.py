from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain
import os
import json

router = APIRouter()

@router.get("")
@router.get("/")
def get_rankings(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"rankings": [], "status": "empty"}

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    rankings_file = os.path.join("data", "websites", safe_domain, "rankings.json")
    rankings_data = []
    
    if os.path.exists(rankings_file):
        try:
            with open(rankings_file, "r") as rf:
                rankings_data = json.load(rf)
        except Exception as e:
            print(f"[RANKINGS API] Error loading rankings: {e}", flush=True)

    return {
        "domain": domain,
        "rankings": rankings_data[offset : offset + limit],
        "total_rankings": len(rankings_data),
        "status": "connected" if len(rankings_data) > 0 else "not_connected",
        "message": "Connect Google Search Console API or Rank Tracker provider to auto-sync target SERP positions."
    }
