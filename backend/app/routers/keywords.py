from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.keyword import Keyword
from typing import List

router = APIRouter()

@router.get("/")
def get_keywords(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    keywords = db.query(Keyword).filter(Keyword.project_id == project_id).offset(offset).limit(limit).all()
    # Return [] empty list instead of fake data
    return keywords

@router.get("/{keyword_id}")
def get_keyword(project_id: str, keyword_id: str, db: Session = Depends(get_db)):
    return db.query(Keyword).filter(Keyword.id == keyword_id, Keyword.project_id == project_id).first()

@router.get("/keyword-page-analysis")
def get_keyword_page_analysis(project_id: str, db: Session = Depends(get_db)):
    # Advanced feature to cross-reference keywords with pages. Currently empty state.
    return []
