from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
import os
import json

router = APIRouter()

def get_latest_issues_from_storage(domain: str) -> list:
    safe_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    safe_domain = "".join([c if c.isalnum() else "_" for c in safe_domain])
    
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        return []
        
    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
            
        issues_file = os.path.join(latest.get("path"), "issues.json")
        if os.path.exists(issues_file):
            with open(issues_file, "r") as pf:
                return json.load(pf)
    except Exception as e:
        print(f"[TECHNICAL API] Failed to read issues.json: {e}", flush=True)
        
    return []

@router.get("/")
def get_technical_issues(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if project else "uisdigital.com"
    
    all_issues = get_latest_issues_from_storage(domain)
    paginated = all_issues[offset : offset + limit]
    return paginated
