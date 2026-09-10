import os
import json
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.config.settings import settings
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.models.project import Project
from app.config.utils import get_project_storage_dir
from app.providers.pagespeed_provider import GooglePageSpeedProvider

router = APIRouter()

@router.get("")
@router.get("/")
def get_pagespeed_metrics(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns authentic Google PageSpeed / Core Web Vitals performance data for the project.
    If no PageSpeed analysis has been run yet, returns explicit 'Not Evaluated' status without fabricating numbers.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    ps_file = os.path.join(proj_dir, "pagespeed.json")

    if os.path.exists(ps_file):
        try:
            with open(ps_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {
                "project_id": project.id,
                "domain": project.domain,
                "status": "evaluated",
                "data": data,
                "provenance": {
                    "source": "Google PageSpeed Insights API v5",
                    "engine": "Lighthouse Lab & Field Diagnostics"
                }
            }
        except Exception as e:
            print(f"[PAGESPEED] Error reading pagespeed.json: {e}", flush=True)

    return {
        "project_id": project.id,
        "domain": project.domain,
        "status": "not_evaluated",
        "data": None,
        "message": "PageSpeed performance was not measured during the crawl. Click 'Analyze Core Web Vitals' to measure live Lighthouse metrics.",
        "provenance": {
            "source": "Google PageSpeed Insights API",
            "status": "Not Evaluated"
        }
    }


@router.post("/analyze")
async def run_pagespeed_analysis(
    project_id: str,
    payload: Dict[str, Any] = Body(default={}),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Executes live Core Web Vitals analysis on project URL using Google PageSpeed Insights API.
    Stores results in project storage and updates dataset.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    target_url = payload.get("url") or project.url or f"https://{project.domain}"
    strategy = payload.get("strategy", "mobile")
    api_key = payload.get("api_key")

    provider = GooglePageSpeedProvider()
    result = await provider.analyze_url_async(target_url, strategy=strategy, api_key=api_key)

    # Persist in project directory
    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    os.makedirs(proj_dir, exist_ok=True)
    ps_file = os.path.join(proj_dir, "pagespeed.json")

    with open(ps_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return {
        "project_id": project.id,
        "domain": project.domain,
        "result": result
    }
