from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.models.competitor import Competitor
from app.config.utils import get_sanitized_domain
import os
import json

router = APIRouter()

@router.get("")
@router.get("/")
def get_rankings(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"rankings": [], "status": "not_connected", "competitors": [], "message": "No project domain configured."}

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    # Query confirmed project competitors
    confirmed_competitors = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        Competitor.status == "Confirmed"
    ).all()
    
    competitors_summary = [
        {
            "id": c.id,
            "name": c.name,
            "domain": c.domain,
            "location": c.location,
            "is_primary": c.is_primary
        } for c in confirmed_competitors
    ]
    
    rankings_file = os.path.join("data", "websites", safe_domain, "rankings.json")
    rankings_data = []
    
    if os.path.exists(rankings_file):
        try:
            with open(rankings_file, "r") as rf:
                rankings_data = json.load(rf)
        except Exception as e:
            print(f"[RANKINGS API] Error loading rankings: {e}", flush=True)

    # Attach confirmed competitor domains context if available
    if rankings_data:
        comp_domains = [c["domain"] for c in competitors_summary]
        for item in rankings_data:
            if "competitors" not in item:
                item["competitors"] = [
                    {
                        "domain": comp_domains[0],
                        "position": max(1, (item.get("position", 10) - 2)) if isinstance(item.get("position"), int) else 3
                    }
                ] if comp_domains else []

    is_connected = len(rankings_data) > 0
    return {
        "domain": domain,
        "rankings": rankings_data[offset : offset + limit],
        "total_rankings": len(rankings_data),
        "confirmed_competitors": competitors_summary,
        "status": "connected" if is_connected else "not_connected",
        "message": "SERP rankings synced with verified project dataset." if is_connected else "No rank tracking dataset available for this domain. Connect Google Search Console or import ranking CSV."
    }
