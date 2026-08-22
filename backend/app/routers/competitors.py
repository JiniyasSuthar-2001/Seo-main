import json
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Body, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.competitor import Competitor
from app.services.competitor_service import (
    normalize_domain,
    discover_competitors_for_project,
    perform_keyword_gap_analysis
)

router = APIRouter()


def _get_project_or_404(project_id: str, db: Session) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail=f"SEO Project '{project_id}' not found.")
    return project


def _serialize_competitor(c: Competitor) -> dict:
    discovered_kws = []
    competing_svcs = []
    
    if c.discovered_keywords:
        try:
            discovered_kws = json.loads(c.discovered_keywords)
        except Exception:
            discovered_kws = []
            
    if c.competing_services:
        try:
            competing_svcs = json.loads(c.competing_services)
        except Exception:
            competing_svcs = []

    return {
        "id": c.id,
        "project_id": c.project_id,
        "name": c.name,
        "domain": c.domain,
        "url": c.url,
        "location": c.location or "City / Regional",
        "geographic_level": c.geographic_level or "City",
        "relevance_score": round(c.relevance_score or 0.0, 1),
        "keyword_overlap": c.keyword_overlap or 0,
        "search_appearances": c.search_appearances or 0,
        "status": c.status or "Suggested",
        "is_primary": bool(c.is_primary),
        "discovery_source": c.discovery_source or "SERP Analysis",
        "discovered_keywords": discovered_kws,
        "competing_services": competing_svcs,
        "notes": c.notes or "",
        "first_discovered": c.first_discovered.isoformat() if c.first_discovered else None,
        "last_checked": c.last_checked.isoformat() if c.last_checked else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


@router.get("")
@router.get("/")
def get_competitors(
    project_id: str,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Returns confirmed competitors for the project. If status parameter is provided,
    filters by that status (e.g. ?status=Confirmed or ?status=Suggested).
    """
    project = _get_project_or_404(project_id, db)
    
    query = db.query(Competitor).filter(Competitor.project_id == project.id)
    if status:
        query = query.filter(Competitor.status == status)
    else:
        # Default to Confirmed competitors if no status specified
        query = query.filter(Competitor.status == "Confirmed")
        
    competitors = query.order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()
    
    # If project has 0 competitors in database at all, trigger auto-discovery so user has initial suggestions
    total_any_status = db.query(Competitor).filter(Competitor.project_id == project.id).count()
    if total_any_status == 0:
        discover_competitors_for_project(project, db)
        query = db.query(Competitor).filter(Competitor.project_id == project.id)
        if status:
            query = query.filter(Competitor.status == status)
        else:
            query = query.filter(Competitor.status == "Confirmed")
        competitors = query.order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()

    return [_serialize_competitor(c) for c in competitors]


@router.get("/discovered")
def get_discovered_competitors(project_id: str, db: Session = Depends(get_db)):
    """
    Returns suggested auto-discovered competitors for the project.
    """
    project = _get_project_or_404(project_id, db)
    
    suggested = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        Competitor.status == "Suggested"
    ).order_by(Competitor.relevance_score.desc()).all()
    
    if not suggested:
        discover_competitors_for_project(project, db)
        suggested = db.query(Competitor).filter(
            Competitor.project_id == project.id,
            Competitor.status == "Suggested"
        ).order_by(Competitor.relevance_score.desc()).all()
        
    return [_serialize_competitor(c) for c in suggested]


@router.post("/discover")
def run_competitor_discovery(project_id: str, db: Session = Depends(get_db)):
    """
    Triggers automated competitor discovery for the project.
    """
    project = _get_project_or_404(project_id, db)
    all_competitors = discover_competitors_for_project(project, db)
    
    suggested = [c for c in all_competitors if c.status == "Suggested"]
    confirmed = [c for c in all_competitors if c.status == "Confirmed"]
    
    return {
        "status": "success",
        "message": f"Competitor discovery completed for '{project.name}'.",
        "discovered_count": len(suggested),
        "confirmed_count": len(confirmed),
        "suggested_competitors": [_serialize_competitor(c) for c in suggested],
        "confirmed_competitors": [_serialize_competitor(c) for c in confirmed],
    }


@router.post("")
@router.post("/")
def add_competitor(
    project_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Manually adds a new competitor for the project (sets status to 'Confirmed').
    """
    project = _get_project_or_404(project_id, db)

    name = (payload.get("name") or "").strip()
    raw_url = (payload.get("url") or payload.get("domain") or "").strip()
    
    if not name or not raw_url:
        raise HTTPException(status_code=400, detail="Competitor name and website URL/domain are required.")

    norm_domain = normalize_domain(raw_url)
    if not norm_domain:
        raise HTTPException(status_code=400, detail="Invalid domain or URL format.")

    target_domain = normalize_domain(project.domain or project.url or "")
    if norm_domain == target_domain:
        raise HTTPException(status_code=400, detail="Cannot add the target project website as its own competitor.")

    full_url = raw_url
    if not full_url.startswith(("http://", "https://")):
        full_url = "https://" + full_url

    # Check if competitor already exists in DB for this project
    existing = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        Competitor.domain == norm_domain
    ).first()

    if existing:
        existing.name = name
        existing.url = full_url
        existing.location = payload.get("location") or existing.location or "Local Market"
        existing.notes = payload.get("notes") or existing.notes or ""
        existing.status = "Confirmed"
        existing.is_primary = bool(payload.get("is_primary", existing.is_primary))
        existing.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return _serialize_competitor(existing)

    is_primary = bool(payload.get("is_primary", False))
    if is_primary:
        # Clear primary flag from other competitors in project
        db.query(Competitor).filter(Competitor.project_id == project.id).update({"is_primary": False})

    competitor = Competitor(
        id=str(uuid.uuid4()),
        project_id=project.id,
        name=name,
        domain=norm_domain,
        url=full_url,
        location=payload.get("location") or "Local Market",
        geographic_level=payload.get("geographic_level") or "City",
        relevance_score=float(payload.get("relevance_score", 85.0)),
        keyword_overlap=int(payload.get("keyword_overlap", 40)),
        search_appearances=int(payload.get("search_appearances", 20)),
        status="Confirmed",
        is_primary=is_primary,
        discovery_source="Manual Entry",
        notes=(payload.get("notes") or "").strip(),
        first_discovered=datetime.utcnow(),
        last_checked=datetime.utcnow()
    )
    db.add(competitor)
    db.commit()
    db.refresh(competitor)
    return _serialize_competitor(competitor)


@router.put("/{competitor_id}")
def update_competitor(
    project_id: str,
    competitor_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Updates an existing competitor.
    """
    project = _get_project_or_404(project_id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.project_id == project.id
    ).first()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found.")

    if "name" in payload and payload["name"]:
        competitor.name = payload["name"].strip()
        
    if "url" in payload and payload["url"]:
        raw_url = payload["url"].strip()
        competitor.domain = normalize_domain(raw_url)
        if not raw_url.startswith(("http://", "https://")):
            raw_url = "https://" + raw_url
        competitor.url = raw_url
        
    if "location" in payload:
        competitor.location = payload["location"]
        
    if "geographic_level" in payload:
        competitor.geographic_level = payload["geographic_level"]
        
    if "notes" in payload:
        competitor.notes = payload["notes"]
        
    if "status" in payload and payload["status"]:
        competitor.status = payload["status"]

    if "is_primary" in payload:
        new_primary = bool(payload["is_primary"])
        if new_primary and not competitor.is_primary:
            # Clear primary flag from others
            db.query(Competitor).filter(Competitor.project_id == project.id).update({"is_primary": False})
        competitor.is_primary = new_primary

    competitor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(competitor)
    return _serialize_competitor(competitor)


@router.post("/{competitor_id}/approve")
def approve_competitor(project_id: str, competitor_id: str, db: Session = Depends(get_db)):
    """
    Approves a suggested competitor, moving its status to 'Confirmed'.
    """
    project = _get_project_or_404(project_id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.project_id == project.id
    ).first()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found.")

    competitor.status = "Confirmed"
    competitor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(competitor)
    return {
        "status": "success",
        "message": f"Competitor '{competitor.name}' approved as Confirmed.",
        "competitor": _serialize_competitor(competitor)
    }


@router.post("/{competitor_id}/ignore")
def ignore_competitor(project_id: str, competitor_id: str, db: Session = Depends(get_db)):
    """
    Ignores a suggested competitor, moving its status to 'Ignored'.
    """
    project = _get_project_or_404(project_id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.project_id == project.id
    ).first()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found.")

    competitor.status = "Ignored"
    competitor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(competitor)
    return {
        "status": "success",
        "message": f"Competitor '{competitor.name}' marked as Ignored.",
        "competitor": _serialize_competitor(competitor)
    }


@router.delete("/{competitor_id}")
def delete_competitor(project_id: str, competitor_id: str, db: Session = Depends(get_db)):
    """
    Deletes a competitor from the database.
    """
    project = _get_project_or_404(project_id, db)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.project_id == project.id
    ).first()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found.")

    db.delete(competitor)
    db.commit()
    return {"status": "deleted", "id": competitor_id}


@router.get("/gap-analysis")
def get_keyword_gap_analysis(project_id: str, db: Session = Depends(get_db)):
    """
    Returns Keyword Gap Analysis comparing target website vs confirmed competitors.
    """
    project = _get_project_or_404(project_id, db)
    return perform_keyword_gap_analysis(project, db)
