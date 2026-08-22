import re
import json
import urllib.parse
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.competitor import Competitor
from app.models.keyword import Keyword
from app.models.page import Page


def normalize_domain(url_or_domain: str) -> str:
    """
    Normalizes any URL or domain string down to a clean root domain without
    protocol, www, ports, paths, or query parameters.
    """
    if not url_or_domain:
        return ""
    
    val = url_or_domain.strip().lower()
    
    if not val.startswith(("http://", "https://")):
        val = "http://" + val
        
    try:
        parsed = urllib.parse.urlparse(val)
        netloc = parsed.netloc or parsed.path
        host = netloc.split(":")[0]
        if host.startswith("www."):
            host = host[4:]
        return host
    except Exception:
        val = re.sub(r"^https?://", "", val)
        val = re.sub(r"^www\.", "", val)
        val = val.split("/")[0].split(":")[0].split("?")[0]
        return val.strip()


def extract_location_info(project: Project) -> Dict[str, str]:
    """
    Extracts location details (city, state, country) from project metadata.
    """
    text = f"{project.name or ''} {project.description or ''} {project.notes or ''} {project.url or ''}".lower()
    
    loc_info = {
        "city": "Unknown",
        "state": "Unknown",
        "country": "Global"
    }
    
    if "sydney" in text or "nsw" in text:
        loc_info["city"] = "Sydney"
        loc_info["state"] = "New South Wales"
        loc_info["country"] = "Australia"
    elif "melbourne" in text or "vic" in text:
        loc_info["city"] = "Melbourne"
        loc_info["state"] = "Victoria"
        loc_info["country"] = "Australia"
    elif "perth" in text or "wa" in text:
        loc_info["city"] = "Perth"
        loc_info["state"] = "Western Australia"
        loc_info["country"] = "Australia"
    elif "brisbane" in text or "qld" in text or "queensland" in text or ".au" in text:
        loc_info["city"] = "Brisbane"
        loc_info["state"] = "Queensland"
        loc_info["country"] = "Australia"
        
    return loc_info


def discover_competitors_for_project(project: Project, db: Session) -> List[Competitor]:
    """
    Retrieves confirmed or manually added competitors for the project.
    Production rule: Never fabricates or returns invented competitor companies.
    If no real competitors are registered, returns an empty list.
    """
    existing_competitors = db.query(Competitor).filter(
        Competitor.project_id == project.id
    ).order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()

    return existing_competitors


def perform_keyword_gap_analysis(project: Project, db: Session) -> Dict[str, Any]:
    """
    Performs Keyword Gap Analysis comparing Target Website keywords against Confirmed Competitors.
    Production rule: Based 100% on actual project database data. Never fabricates keywords or metrics.
    """
    confirmed_competitors = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        Competitor.status == "Confirmed"
    ).all()

    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    
    gap_data = []
    
    # Process actual project keywords if present
    for kw_record in keywords:
        if not kw_record.keyword:
            continue
        
        target_pos = kw_record.position
        comp_pos = None  # Competitor ranking positions would come from verified SERP provider APIs
        
        opportunity = "MEDIUM"
        status_text = "Target Ranking" if target_pos else "Target Unranked"
        if not target_pos:
            opportunity = "HIGH"
            
        gap_data.append({
            "keyword": kw_record.keyword,
            "target_position": target_pos if target_pos is not None else "Not Ranking",
            "competitor_position": comp_pos if comp_pos is not None else "Data Unavailable",
            "position_difference": (target_pos - comp_pos) if (target_pos and comp_pos) else "N/A",
            "search_volume": kw_record.search_volume or 0,
            "keyword_difficulty": kw_record.difficulty or 0,
            "opportunity_level": opportunity,
            "status_text": status_text,
            "recommended_action": f"Optimize page content targeting '{kw_record.keyword}'"
        })

    # Summary metrics
    missing_count = sum(1 for g in gap_data if g["opportunity_level"] == "HIGH")
    shared_count = sum(1 for g in gap_data if g["target_position"] != "Not Ranking")
    
    return {
        "project_id": project.id,
        "target_domain": normalize_domain(project.domain or project.url or ""),
        "confirmed_competitors_count": len(confirmed_competitors),
        "confirmed_competitors": [
            {
                "id": c.id,
                "name": c.name,
                "domain": c.domain,
                "location": c.location,
                "is_primary": c.is_primary
            } for c in confirmed_competitors
        ],
        "summary": {
            "total_keywords_analyzed": len(gap_data),
            "high_opportunity_keywords": missing_count,
            "shared_keywords": shared_count,
        },
        "keyword_gap": gap_data,
        "message": "Keyword gap analysis complete." if gap_data else "No keyword dataset or verified competitor data available for gap analysis."
    }
