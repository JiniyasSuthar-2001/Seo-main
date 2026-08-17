from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
import os
import json

router = APIRouter()

@router.get("/")
def get_projects(db: Session = Depends(get_db)):
    return db.query(Project).all()

@router.post("/")
def create_project(project: dict, db: Session = Depends(get_db)):
    domain_val = project.get('domain') or project.get('url') or ''
    name_val = project.get('name') or 'New SEO Project'
    
    if not domain_val:
        raise HTTPException(status_code=400, detail="Website domain/URL is required.")

    new_proj = Project(name=name_val, url=domain_val)
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)
    return new_proj

@router.get("/{project_id}/summary")
def get_project_summary(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"status": "empty", "message": "Project not found or website domain unconfigured."}

    domain = project.domain
    safe_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
    safe_domain = "".join([c if c.isalnum() else "_" for c in safe_domain])
    
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    
    if not os.path.exists(latest_path):
        return {"status": "empty", "message": "No crawl data available yet."}
        
    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
            
        crawl_dir = latest.get("path")
        metadata_path = os.path.join(crawl_dir, "metadata.json")
        
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as mf:
                metadata = json.load(mf)
                return {
                    "status": "success",
                    "latest_crawl": metadata
                }
    except Exception as e:
        print(f"[PROJECTS API] Exception reading snapshot: {e}", flush=True)
        
    return {"status": "error", "message": "Failed to read crawl data"}
