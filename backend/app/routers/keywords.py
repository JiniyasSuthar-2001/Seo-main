from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.config.database import get_db
from app.models.keyword import Keyword

router = APIRouter()

@router.get("/")
def get_keywords(project_id: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    keywords = db.query(Keyword).filter(Keyword.project_id == project_id).offset(skip).limit(limit).all()
    total = db.query(Keyword).filter(Keyword.project_id == project_id).count()
    return {
        "data": keywords,
        "meta": {
            "skip": skip,
            "limit": limit,
            "total": total
        }
    }
