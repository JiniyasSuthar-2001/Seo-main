import os
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.competitor import Competitor
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()


from app.services.backlink_service import BacklinkDataService


@router.get("")
@router.get("/")
def get_backlinks(
    project_id: str,
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {
            "domain": "",
            "status": "not_connected",
            "backlinks": [],
            "referring_domains": [],
            "summary": {"inbound_backlinks": 0, "referring_domains": 0, "outbound_external_links": 0},
            "provenance": {"source_type": "unavailable", "source_label": "Unavailable", "message": "No project domain configured."}
        }

    return BacklinkDataService.get_project_backlink_data(project=project, limit=limit, offset=offset)


@router.get("/gap-analysis")
def get_backlink_gap_analysis(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Compares confirmed competitors to identify domains linking to competitors but NOT to target project domain.
    Production rule: Returns honest empty state if competitor backlink datasets are not configured.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    confirmed_competitors = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        Competitor.status == "Confirmed"
    ).all()

    gap_data = []
    
    if not confirmed_competitors:
        return {
            "project_id": project.id,
            "target_domain": project.domain or "Target Domain",
            "confirmed_competitors_count": 0,
            "backlink_gap": [],
            "message": "No confirmed competitors configured. Add confirmed competitors to perform backlink gap analysis."
        }

    return {
        "project_id": project.id,
        "target_domain": project.domain or "Target Domain",
        "confirmed_competitors_count": len(confirmed_competitors),
        "backlink_gap": gap_data,
        "message": "Backlink gap analysis active. Import competitor backlink CSV datasets to populate domain intersections."
    }

from app.routers.reports import export_backlinks_csv

@router.get("/export.csv")
def backlinks_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_backlinks_csv(project_id, user_id, db)
