from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.config.database import get_db
from app.models.project import Project
from app.llm.seo_analyst import SEOAnalystAgent

router = APIRouter()

class ChatRequest(BaseModel):
    query: str

@router.post("/{project_id}/ai/analyze")
def analyze_project_ai(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if (project and project.domain) else "uisdigital.com"
    
    agent = SEOAnalystAgent()
    analysis = agent.analyze_project(domain)
    return analysis

@router.get("/{project_id}/ai/insights")
def get_project_insights(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if (project and project.domain) else "uisdigital.com"
    
    agent = SEOAnalystAgent()
    return agent.analyze_project(domain)

@router.post("/{project_id}/ai/chat")
def chat_with_project_ai(project_id: str, request: ChatRequest, db: Session = Depends(get_db)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if (project and project.domain) else "uisdigital.com"
    
    agent = SEOAnalystAgent()
    return agent.chat_with_data(domain, request.query)
