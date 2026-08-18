import os
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain

router = APIRouter()


def _competitors_path(domain: str) -> str:
    safe_domain = get_sanitized_domain(domain)
    website_dir = os.path.join("data", "websites", safe_domain)
    os.makedirs(website_dir, exist_ok=True)
    return os.path.join(website_dir, "competitors.json")


def _load(path: str):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save(path: str, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("")
@router.get("/")
def get_competitors(project_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    return _load(_competitors_path(project.domain))


@router.post("")
@router.post("/")
def add_competitor(project_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)

    name = (payload.get("name") or "").strip()
    url = (payload.get("url") or "").strip()
    if not name or not url:
        raise HTTPException(status_code=400, detail="Competitor name and URL are required.")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    path = _competitors_path(project.domain)
    competitors = _load(path)
    competitor = {
        "id": str(uuid.uuid4()),
        "name": name,
        "url": url,
        "notes": (payload.get("notes") or "").strip(),
        "added_at": datetime.utcnow().isoformat(),
    }
    competitors.append(competitor)
    _save(path, competitors)
    return competitor


@router.delete("/{competitor_id}")
def delete_competitor(project_id: str, competitor_id: str, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    path = _competitors_path(project.domain)
    competitors = _load(path)
    remaining = [c for c in competitors if c.get("id") != competitor_id]
    if len(remaining) == len(competitors):
        raise HTTPException(status_code=404, detail="Competitor not found")
    _save(path, remaining)
    return {"status": "deleted", "id": competitor_id}
