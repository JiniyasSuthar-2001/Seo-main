from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.providers.datasources import DataSourceManager

router = APIRouter()
ds_manager = DataSourceManager()

@router.get("")
@router.get("/")
def get_datasources(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    sources = ds_manager.get_project_datasources(project.domain)
    return {
        "project_id": project_id,
        "domain": project.domain,
        "datasources": sources
    }

@router.post("/{source_id}")
def update_datasource(project_id: str, source_id: str, updates: dict = Body(...), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    updated = ds_manager.update_datasource(project.domain, source_id, updates)
    return {"status": "success", "datasources": updated}
