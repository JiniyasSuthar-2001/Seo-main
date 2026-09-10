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

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()


def _get_project_or_404(project_id: str, db: Session, user_id: str) -> Project:
    get_user_membership(db, user_id, project_id)
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
        "relevance_score": round(c.relevance_score, 1) if c.relevance_score is not None else None,
        "keyword_overlap": c.keyword_overlap if c.keyword_overlap is not None else None,
        "search_appearances": c.search_appearances if c.search_appearances is not None else None,
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
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns confirmed competitors for the project. If status parameter is provided,
    filters by that status (e.g. ?status=Confirmed or ?status=Suggested).
    """
    project = _get_project_or_404(project_id, db, user_id)
    
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
def get_discovered_competitors(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns suggested auto-discovered competitors for the project along with SERP provider status.
    """
    project = _get_project_or_404(project_id, db, user_id)
    disc_res = discover_competitors_for_project(project, db)
    suggested = disc_res.get("suggested_competitors", [])
    
    return {
        "has_serp_provider": disc_res.get("has_serp_provider", False),
        "provider_name": disc_res.get("provider_name", "None"),
        "message": disc_res.get("message", ""),
        "suggested_competitors": [_serialize_competitor(c) for c in suggested]
    }


@router.post("/discover")
def run_competitor_discovery(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Triggers automated competitor discovery for the project.
    """
    project = _get_project_or_404(project_id, db, user_id)
    disc_res = discover_competitors_for_project(project, db)
    
    suggested = disc_res.get("suggested_competitors", [])
    confirmed = disc_res.get("confirmed_competitors", [])
    
    return {
        "status": "success" if disc_res.get("has_serp_provider") else "no_serp_provider",
        "has_serp_provider": disc_res.get("has_serp_provider", False),
        "provider_name": disc_res.get("provider_name", "None"),
        "message": disc_res.get("message", ""),
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
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Manually adds a new competitor for the project (sets status to 'Confirmed').
    """
    project = _get_project_or_404(project_id, db, user_id)

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
        relevance_score=float(payload["relevance_score"]) if payload.get("relevance_score") is not None else None,
        keyword_overlap=int(payload["keyword_overlap"]) if payload.get("keyword_overlap") is not None else None,
        search_appearances=int(payload["search_appearances"]) if payload.get("search_appearances") is not None else None,
        status="Confirmed",
        is_primary=is_primary,
        discovery_source="User Specified Domain",
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
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Updates an existing competitor.
    """
    project = _get_project_or_404(project_id, db, user_id)
    
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
def approve_competitor(
    project_id: str,
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Approves a suggested competitor, moving its status to 'Confirmed'.
    """
    project = _get_project_or_404(project_id, db, user_id)
    
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
def ignore_competitor(
    project_id: str,
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Ignores a suggested competitor, moving its status to 'Ignored'.
    """
    project = _get_project_or_404(project_id, db, user_id)
    
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


@router.post("/{competitor_id}/unignore")
def unignore_competitor(
    project_id: str,
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Restores an ignored competitor back to 'Suggested'.
    """
    project = _get_project_or_404(project_id, db, user_id)
    
    competitor = db.query(Competitor).filter(
        Competitor.id == competitor_id,
        Competitor.project_id == project.id
    ).first()
    
    if not competitor:
        raise HTTPException(status_code=404, detail="Competitor not found.")

    competitor.status = "Suggested"
    competitor.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(competitor)
    return {
        "status": "success",
        "message": f"Competitor '{competitor.name}' restored to Suggested.",
        "competitor": _serialize_competitor(competitor)
    }



@router.delete("/{competitor_id}")
def delete_competitor(
    project_id: str,
    competitor_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Deletes a competitor from the database.
    """
    project = _get_project_or_404(project_id, db, user_id)
    
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
def get_keyword_gap_analysis(
    project_id: str,
    competitor_id: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns Keyword Gap Analysis comparing target website vs confirmed competitors.
    """
    project = _get_project_or_404(project_id, db, user_id)
    return perform_keyword_gap_analysis(project, db, competitor_id=competitor_id)

from app.models.competitor_ranking import CompetitorRanking
from app.models.external_connection import ExternalConnection
from app.providers.serp_provider import SERPRankTrackerProvider

@router.get("/rankings")
def get_competitor_rankings(
    project_id: str,
    competitor_id: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns verified competitor ranking records for the project.
    """
    project = _get_project_or_404(project_id, db, user_id)
    query = db.query(CompetitorRanking).filter(CompetitorRanking.project_id == project.id)
    if competitor_id:
        query = query.filter(CompetitorRanking.competitor_id == competitor_id)
    if keyword:
        query = query.filter(CompetitorRanking.keyword.ilike(f"%{keyword}%"))

    total = query.count()
    rankings = query.order_by(CompetitorRanking.checked_at.desc()).offset(offset).limit(limit).all()

    return {
        "project_id": project.id,
        "total": total,
        "rankings": [r.to_dict() for r in rankings]
    }

@router.post("/rankings")
def create_competitor_ranking(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Creates or updates a verified competitor ranking record.
    """
    project = _get_project_or_404(project_id, db, user_id)
    competitor_id = payload.get("competitor_id")
    keyword = (payload.get("keyword") or "").strip()
    if not competitor_id or not keyword:
        raise HTTPException(status_code=400, detail="competitor_id and keyword are required.")

    comp = db.query(Competitor).filter(Competitor.id == competitor_id, Competitor.project_id == project.id).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Competitor not found in project.")

    raw_pos = payload.get("position")
    pos_val = int(raw_pos) if (raw_pos is not None and str(raw_pos).isdigit() and int(raw_pos) >= 1) else None

    ranking = CompetitorRanking(
        project_id=project.id,
        competitor_id=comp.id,
        keyword=keyword,
        position=pos_val,
        ranking_url=payload.get("ranking_url"),
        search_engine=payload.get("search_engine", project.search_engine or "Google"),
        country=payload.get("country", project.target_country or "United States"),
        location=payload.get("location"),
        device=payload.get("device", project.target_device or "Desktop"),
        source=payload.get("source", "manual_import"),
        checked_at=datetime.utcnow()
    )
    db.add(ranking)
    db.commit()
    db.refresh(ranking)
    return {"status": "success", "ranking": ranking.to_dict()}

@router.post("/refresh-rankings")
def refresh_competitor_rankings(
    project_id: str,
    payload: dict = Body(default={}),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Checks real SERP ranking positions for target website keywords across confirmed competitors.
    Requires SERP Provider API key.
    """
    project = _get_project_or_404(project_id, db, user_id)
    conn = db.query(ExternalConnection).filter(
        ExternalConnection.user_id == user_id,
        ExternalConnection.provider.in_(["serp_provider", "serp"])
    ).first()

    serp_key = conn.get_api_key() if conn else os.environ.get("SERP_API_KEY", "")
    if not serp_key:
        return {
            "status": "not_configured",
            "message": "SERP Provider API key is not configured. Connect a SERP provider in Connected Accounts to check live rankings.",
            "checked_count": 0
        }

    provider = SERPRankTrackerProvider(api_key=serp_key)
    confirmed_comps = db.query(Competitor).filter(Competitor.project_id == project.id, Competitor.status == "Confirmed").all()
    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()

    kw_list = [k.keyword for k in keywords if k.keyword]
    comp_list = [{"id": c.id, "domain": c.domain, "name": c.name} for c in confirmed_comps]

    res = provider.check_competitor_rankings(
        keywords=kw_list,
        competitors=comp_list,
        country=project.target_country or "United States",
        language=project.target_language or "English",
        device=project.target_device or "Desktop"
    )

    return {
        "status": "success",
        "message": f"Checked rankings for {len(kw_list)} keywords across {len(confirmed_comps)} competitors.",
        "results": res
    }

from app.routers.reports import export_competitors_csv

@router.get("/export.csv")
def competitors_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_competitors_csv(project_id, user_id, db)
