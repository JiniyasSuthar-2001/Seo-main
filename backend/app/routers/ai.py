from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.config.database import get_db
from app.models.project import Project
from app.llm.seo_analyst import SEOAnalystAgent

router = APIRouter()

class ChatRequest(BaseModel):
    query: str


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.domain:
        raise HTTPException(status_code=400, detail="This project has no website URL configured.")
    return project


@router.post("/{project_id}/ai/analyze")
def analyze_project_ai(project_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    agent = SEOAnalystAgent()
    return agent.analyze_project(project.domain)

@router.get("/{project_id}/ai/insights")
def get_project_insights(project_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    agent = SEOAnalystAgent()
    return agent.analyze_project(project.domain)

@router.post("/{project_id}/ai/chat")
def chat_with_project_ai(project_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    project = _get_project_or_404(project_id, db)
    agent = SEOAnalystAgent()
    return agent.chat_with_data(project.domain, request.query)
