from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.models.project import Project
from app.providers.datasources import DataSourceManager

router = APIRouter()
ds_manager = DataSourceManager()

@router.get("")
@router.get("/")
def get_datasources(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    sources = ds_manager.get_project_datasources(project_id, project.domain)
    return {
        "project_id": project_id,
        "domain": project.domain,
        "datasources": sources
    }

@router.post("/{source_id}")
def update_datasource(
    project_id: str,
    source_id: str,
    updates: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    updated = ds_manager.update_datasource(project_id, source_id, updates, project.domain)
    return {"status": "success", "datasources": updated}
