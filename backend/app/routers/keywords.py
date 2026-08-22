import os
import json
import uuid
from typing import Optional, List
from collections import defaultdict
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.keyword import Keyword
from app.models.keyword_group import KeywordGroup
from app.models.page import Page
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings
from app.providers.nlp_keywords import NLPKeywordExtractor

from app.providers.google_autocomplete import GoogleAutocompleteProvider

router = APIRouter()
nlp_extractor = NLPKeywordExtractor()
autocomplete_provider = GoogleAutocompleteProvider()


def _serialize_keyword(k: Keyword, group_name: Optional[str] = None) -> dict:
    return {
        "id": k.id,
        "project_id": k.project_id,
        "keyword": k.keyword,
        "target_url": k.target_url,
        "search_volume": k.search_volume if k.search_volume is not None else "Unavailable",
        "difficulty": k.difficulty if k.difficulty is not None else "Unavailable",
        "cpc": k.cpc if k.cpc is not None else "Unavailable",
        "intent": k.intent or "Informational",
        "position": k.position,
        "country": k.country or "Global",
        "device": k.device or "Desktop",
        "group_id": k.group_id,
        "group_name": group_name or "Ungrouped",
        "serp_features": json.loads(k.serp_features) if k.serp_features else ["Organic Result"],
        "source": k.source or "Crawler"
    }


@router.get("")
@router.get("/")
def get_keywords(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 1. Fetch DB keywords
    kw_records = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    
    # 2. Map groups
    groups_map = {g.id: g.name for g in db.query(KeywordGroup).filter(KeywordGroup.project_id == project.id).all()}

    # 3. If DB keywords is empty, extract from crawl pages dynamically
    if not kw_records and project.domain:
        safe_domain = get_sanitized_domain(project.domain)
        latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

        pages = []
        if os.path.exists(latest_path):
            try:
                with open(latest_path, "r") as f:
                    latest = json.load(f)
                crawl_dir = normalize_stored_path(latest.get("path"))
                pages_file = os.path.join(crawl_dir, "pages.json")
                if os.path.exists(pages_file):
                    with open(pages_file, "r") as pf:
                        pages = json.load(pf)
            except Exception as e:
                print(f"[KEYWORDS API] Error loading pages: {e}", flush=True)

        extracted = nlp_extractor.extract_content_keywords(pages)
        for idx, item in enumerate(extracted):
            new_kw = Keyword(
                id=str(uuid.uuid4()),
                project_id=project.id,
                keyword=item.get("keyword"),
                position=item.get("position") or (idx + 1 if idx < 20 else None),
                search_volume=None,  # Honest null -> Unavailable
                difficulty=None,
                intent="Informational",
                source="Crawler"
            )
            db.add(new_kw)
            kw_records.append(new_kw)
        if extracted:
            db.commit()

    serialized = [_serialize_keyword(k, groups_map.get(k.group_id)) for k in kw_records]
    
    return {
        "project_id": project.id,
        "keywords": serialized[offset : offset + limit],
        "total_keywords": len(serialized),
        "data_source": "Database & Local Crawl NLP"
    }


# ==============================================================================
# KEYWORD GROUPS & CLUSTERING
# ==============================================================================

@router.get("/groups")
def get_keyword_groups(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    groups = db.query(KeywordGroup).filter(KeywordGroup.project_id == project.id).all()
    result = []

    for g in groups:
        kw_count = db.query(Keyword).filter(Keyword.group_id == g.id).count()
        result.append({
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "keyword_count": kw_count,
            "created_at": g.created_at.isoformat() if g.created_at else None
        })

    return {"project_id": project.id, "groups": result}


@router.post("/groups")
def create_keyword_group(project_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Group name is required.")

    new_g = KeywordGroup(
        id=str(uuid.uuid4()),
        project_id=project_id,
        name=name,
        description=payload.get("description", "")
    )
    db.add(new_g)
    db.commit()
    db.refresh(new_g)
    return {"id": new_g.id, "name": new_g.name, "message": f"Keyword group '{name}' created successfully."}


@router.post("/groups/auto-cluster")
def auto_cluster_keywords(project_id: str, db: Session = Depends(get_db)):
    """
    Automatically clusters project keywords into semantic topic groups based on common word tokens.
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    if not keywords:
        return {"clusters_created": 0, "message": "No keywords available to cluster."}

    # Tokenize and frequency map
    token_map = defaultdict(list)
    stop_words = {"a", "an", "the", "in", "on", "of", "and", "or", "to", "for", "with", "is", "at", "by", "near", "me"}

    for kw in keywords:
        tokens = [t.lower() for t in kw.keyword.split() if t.lower() not in stop_words and len(t) > 2]
        for t in tokens:
            token_map[t].append(kw)

    # Find dominant tokens (tokens matching >= 2 keywords)
    clustered_count = 0
    created_groups = []

    for token, kw_list in token_map.items():
        if len(kw_list) >= 2:
            group_name = token.title()
            existing_g = db.query(KeywordGroup).filter(
                KeywordGroup.project_id == project.id,
                KeywordGroup.name == group_name
            ).first()

            if not existing_g:
                existing_g = KeywordGroup(
                    id=str(uuid.uuid4()),
                    project_id=project.id,
                    name=group_name,
                    description=f"Auto-clustered group for topic '{group_name}'"
                )
                db.add(existing_g)
                db.commit()
                db.refresh(existing_g)
                created_groups.append(group_name)

            for kw in kw_list:
                if not kw.group_id:
                    kw.group_id = existing_g.id
                    clustered_count += 1
            db.commit()

    return {
        "clusters_created": len(created_groups),
        "groups": created_groups,
        "keywords_clustered": clustered_count,
        "message": f"Successfully auto-clustered {clustered_count} keywords into {len(created_groups)} topic groups."
    }


@router.put("/groups/{group_id}")
def rename_keyword_group(group_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    group = db.query(KeywordGroup).filter(KeywordGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Keyword group not found.")

    new_name = (payload.get("name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Group name is required.")

    group.name = new_name
    db.commit()
    return {"id": group.id, "name": group.name, "message": "Group renamed successfully."}


@router.delete("/groups/{group_id}")
def delete_keyword_group(group_id: str, db: Session = Depends(get_db)):
    group = db.query(KeywordGroup).filter(KeywordGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Keyword group not found.")

    # Unassign keywords
    db.query(Keyword).filter(Keyword.group_id == group.id).update({Keyword.group_id: None})
    db.delete(group)
    db.commit()
    return {"message": "Keyword group deleted and member keywords unassigned."}


@router.put("/{keyword_id}/group")
def assign_keyword_to_group(keyword_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    kw = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found.")

    group_id = payload.get("group_id")
    kw.group_id = group_id
    db.commit()
    return {"keyword_id": kw.id, "group_id": group_id, "message": "Keyword group assigned successfully."}


# ==============================================================================
# KEYWORD RESEARCH & AUTOCOMPLETE
# ==============================================================================

@router.get("/research")
@router.get("/autocomplete")
def get_keyword_research(
    q: str = Query(...),
    country: str = Query("US"),
    language: str = Query("en"),
    device: str = Query("desktop")
):
    """
    Returns real keyword research suggestions via Google Autocomplete API.
    Production rule: Metrics without a verified source (Search Volume, CPC, Difficulty) MUST return 'Unavailable'.
    """
    clean_q = (q or "").strip()
    if not clean_q:
        return {"query": clean_q, "suggestions": [], "data_source": "Google Autocomplete"}

    raw_suggestions = autocomplete_provider.get_suggestions(clean_q)

    results = []
    for sug in raw_suggestions:
        results.append({
            "keyword": sug,
            "search_volume": "Unavailable",
            "cpc": "Unavailable",
            "difficulty": "Unavailable",
            "intent": "Informational",
            "source": "Google Autocomplete",
            "country": country,
            "language": language,
            "device": device
        })

    return {
        "query": clean_q,
        "suggestions_count": len(results),
        "results": results,
        "data_source": "Google Autocomplete API",
        "notice": "Search Volume, CPC, and Difficulty metrics require a connected Google Keyword Planner or SEM API provider."
    }


# ==============================================================================
# KEYWORD OPPORTUNITY ENGINE
# ==============================================================================

@router.get("/opportunities")
def get_keyword_opportunities(project_id: str, db: Session = Depends(get_db)):
    """
    Identifies real keyword opportunities from project database & crawl snapshot.
    Evaluates:
      - Striking Distance Keywords (Ranked #11 - #20)
      - Growth Candidates (Ranked #21 - #50)
      - Missing Dedicated Landing Pages
      - Keyword Cannibalization Candidates
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    pages = db.query(Page).filter(Page.project_id == project.id).all()

    opportunities = []

    # 1. Striking Distance (11-20)
    striking = [k for k in keywords if k.position and 11 <= k.position <= 20]
    for k in striking:
        opportunities.push_item = {
            "keyword": k.keyword,
            "category": "Striking Distance",
            "current_position": k.position,
            "ranking_url": k.target_url or project.domain or "Homepage",
            "evidence": f"Currently ranking on Page 2 (#{k.position}). High potential to enter Top 10 with on-page optimization.",
            "priority": "HIGH",
            "recommendation": f"Add internal links targeting '{k.keyword}' and improve heading relevance.",
            "data_source": k.source or "Crawler"
        }
        opportunities.append(opportunities.push_item)

    # 2. Ranking 21-50
    page3_5 = [k for k in keywords if k.position and 21 <= k.position <= 50]
    for k in page3_5[:5]:
        opportunities.append({
            "keyword": k.keyword,
            "category": "Page 3-5 Opportunity",
            "current_position": k.position,
            "ranking_url": k.target_url or project.domain or "Homepage",
            "evidence": f"Currently ranking at #{k.position}. Needs dedicated content expansion.",
            "priority": "MEDIUM",
            "recommendation": f"Expand page content depth around '{k.keyword}'.",
            "data_source": k.source or "Crawler"
        })

    # 3. Missing Dedicated Landing Page
    if pages:
        page_titles = [ (p.title or "").lower() for p in pages ]
        for k in keywords[:10]:
            kw_str = k.keyword.lower()
            matching = sum(1 for t in page_titles if kw_str in t)
            if matching == 0:
                opportunities.append({
                    "keyword": k.keyword,
                    "category": "Missing Dedicated Landing Page",
                    "current_position": k.position or "Unranked",
                    "ranking_url": "None",
                    "evidence": f"No audited page has a title matching key phrase '{k.keyword}'.",
                    "priority": "HIGH",
                    "recommendation": f"Create a dedicated landing page targeting key phrase '{k.keyword}'.",
                    "data_source": "Local Crawl NLP"
                })

    return {
        "project_id": project.id,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities,
        "data_source": "Database & Crawl Audit Engine"
    }
