import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.keyword import Keyword
from app.models.page import Page
from app.models.action_opportunity import ActionOpportunity
from app.services.audit_rules import evaluate_site_audit_rules
from app.services.opportunity_engine import generate_central_opportunities

router = APIRouter()

@router.get("")
@router.get("/")
def get_project_opportunities(
    project_id: str,
    category: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 1. Fetch DB stored opportunities
    db_opps = db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).all()

    # 2. If DB opportunities empty, generate from crawl data & audit engine
    if not db_opps and project.domain:
        pages_records = db.query(Page).filter(Page.project_id == project.id).all()
        pages = [p.__dict__ for p in pages_records]
        
        kw_records = db.query(Keyword).filter(Keyword.project_id == project.id).all()
        keywords = [k.__dict__ for k in kw_records]

        audit_eval = evaluate_site_audit_rules(pages)
        generated = generate_central_opportunities(audit_eval, keywords, pages)

        for item in generated:
            new_opp = ActionOpportunity(
                id=str(uuid.uuid4()),
                project_id=project.id,
                title=item["title"],
                category=item["category"],
                priority_score=item["priority_score"],
                priority_level=item["priority_level"],
                impact=item["impact"],
                evidence=item["evidence"],
                affected_urls_json=json_dumps(item.get("affected_urls", [])),
                affected_count=item.get("affected_count", 1),
                recommendation=item["recommendation"],
                status="Open"
            )
            db.add(new_opp)
            db_opps.append(new_opp)
        if generated:
            db.commit()

    # Filter
    filtered = db_opps
    if category and category.lower() != "all":
        filtered = [o for o in filtered if o.category.lower() == category.lower()]
    if status and status.lower() != "all":
        filtered = [o for o in filtered if o.status.lower() == status.lower()]

    result = []
    for o in filtered:
        import json
        urls = []
        if o.affected_urls_json:
            try:
                urls = json.loads(o.affected_urls_json)
            except Exception as e:
                from app.config.logger import get_logger
                get_logger("opportunities").warning(f"Error parsing affected URLs for opportunity {o.id}: {e}")

        result.append({
            "id": o.id,
            "project_id": o.project_id,
            "title": o.title,
            "category": o.category,
            "priority_score": o.priority_score,
            "priority_level": o.priority_level,
            "impact": o.impact,
            "evidence": o.evidence,
            "affected_urls": urls,
            "affected_count": o.affected_count,
            "recommendation": o.recommendation,
            "status": o.status,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "provenance": {
                "source": "Central SEO Action Center",
                "confidence": 100.0
            }
        })

    return {
        "project_id": project.id,
        "total_opportunities": len(result),
        "opportunities": result
    }


@router.put("/{opportunity_id}/status")
def update_opportunity_status(
    opportunity_id: str,
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    opp = db.query(ActionOpportunity).filter(ActionOpportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Action opportunity not found.")

    new_status = payload.get("status")
    if new_status not in ("Open", "In Progress", "Ignored", "Resolved"):
        raise HTTPException(status_code=400, detail="Invalid status value. Must be Open, In Progress, Ignored, or Resolved.")

    opp.status = new_status
    db.commit()
    return {"id": opp.id, "status": opp.status, "message": f"Opportunity status updated to '{new_status}'."}

def json_dumps(val):
    import json
    return json.dumps(val)
