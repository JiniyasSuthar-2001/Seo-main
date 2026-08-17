from sqlalchemy.orm import Session
from app.repositories import project_repository
from app.schemas.project import ProjectCreate

def get_projects(db: Session, skip: int = 0, limit: int = 100):
    return project_repository.get_projects(db, skip=skip, limit=limit)

def create_project(db: Session, project: ProjectCreate):
    return project_repository.create_project(db, project=project)

def get_project(db: Session, project_id: str):
    return project_repository.get_project(db, project_id=project_id)
