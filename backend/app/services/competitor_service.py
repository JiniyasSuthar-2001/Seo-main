import re
import json
import uuid
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


from app.services.location_resolver import resolve_location, LocationConfidence


def extract_location_info(project: Project) -> Dict[str, Any]:
    """
    Extracts location details from project metadata using data-driven evidence resolution.
    Never defaults country-code TLDs (.au, .uk, etc.) to arbitrary cities like Brisbane.
    """
    resolved = resolve_location(
        project_url=getattr(project, "url", None) or getattr(project, "domain", None),
        target_country=getattr(project, "target_country", None),
        notes=getattr(project, "notes", None),
        description=getattr(project, "description", None)
    )

    return {
        "city": resolved["city"] or "Unknown",
        "state": resolved["region"] or "Unknown",
        "country": resolved["country"] or "Global",
        "confidence": resolved["confidence"],
        "sources": resolved["sources"]
    }



import os
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, get_project_storage_dir
from app.providers.datasources import DataSourceManager

def check_serp_provider_status(project: Project) -> Dict[str, Any]:
    """
    Determines whether a real SERP/search-data provider or imported SERP dataset exists.
    Production rule: Groq/LLM alone is an AI analysis engine, NOT a SERP data provider.
    """
    if not project or not project.domain:
        return {
            "has_serp_provider": False,
            "provider_name": "None",
            "message": "No project domain configured."
        }

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    
    # 1. Check if an imported SERP / competitor dataset exists
    comp_file = os.path.join(proj_dir, "competitors.json")
    serp_file = os.path.join(proj_dir, "serp_results.json")
    rankings_file = os.path.join(proj_dir, "rankings.json")
    
    if os.path.exists(comp_file) or os.path.exists(serp_file) or os.path.exists(rankings_file):
        return {
            "has_serp_provider": True,
            "provider_name": "Imported SERP Dataset",
            "source_type": "Imported Data",
            "message": "Imported SERP data available."
        }

    # 2. Check DataSourceManager for configured SERP provider
    ds_mgr = DataSourceManager()
    datasources = ds_mgr.get_project_datasources(project.id, project.domain)
    rank_tracker = datasources.get("rank_tracker", {})

    if rank_tracker.get("implemented") and rank_tracker.get("status", "").startswith("Active"):
        return {
            "has_serp_provider": True,
            "provider_name": rank_tracker.get("name", "SERP Data Provider"),
            "source_type": "SERP Data",
            "message": "Active SERP provider configured."
        }

    return {
        "has_serp_provider": False,
        "provider_name": "None",
        "message": "Competitor discovery requires search-result data. Connect a supported SERP/search provider or import ranking/SERP data."
    }


def discover_competitors_for_project(project: Project, db: Session) -> Dict[str, Any]:
    """
    Retrieves auto-discovered competitors for the project.
    Production rule: Checks for real SERP data / imported datasets before discovering candidates.
    Never fabricates competitors or SERP rankings out of thin air.
    """
    serp_status = check_serp_provider_status(project)

    existing_competitors = db.query(Competitor).filter(
        Competitor.project_id == project.id
    ).order_by(Competitor.is_primary.desc(), Competitor.relevance_score.desc()).all()

    suggested = [c for c in existing_competitors if c.status == "Suggested"]
    confirmed = [c for c in existing_competitors if c.status == "Confirmed"]

    # If imported dataset exists and no suggested competitors stored yet, load imported candidates
    if serp_status["has_serp_provider"] and not suggested:
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
        comp_file = os.path.join(proj_dir, "competitors.json")
        if os.path.exists(comp_file):
            try:
                with open(comp_file, "r") as cf:
                    imported_comps = json.load(cf)
                    target_dom = normalize_domain(project.domain)
                    for item in imported_comps:
                        dom = normalize_domain(item.get("domain") or item.get("url") or "")
                        if dom and dom != target_dom:
                            existing = db.query(Competitor).filter(
                                Competitor.project_id == project.id,
                                Competitor.domain == dom
                            ).first()
                            if not existing:
                                rel_val = float(item["relevance_score"]) if item.get("relevance_score") is not None else None
                                kw_val = int(item["keyword_overlap"]) if item.get("keyword_overlap") is not None else None
                                search_val = int(item["search_appearances"]) if item.get("search_appearances") is not None else None
                                new_comp = Competitor(
                                    id=str(uuid.uuid4()),
                                    project_id=project.id,
                                    name=item.get("name") or dom,
                                    domain=dom,
                                    url=item.get("url") or f"https://{dom}",
                                    location=item.get("location") or "Market Candidate",
                                    geographic_level=item.get("geographic_level") or "City",
                                    relevance_score=rel_val,
                                    keyword_overlap=kw_val,
                                    search_appearances=search_val,
                                    status="Suggested",
                                    is_primary=False,
                                    discovery_source="Imported SERP Dataset",
                                    notes=item.get("notes") or "Imported competitor candidate",
                                    first_discovered=datetime.utcnow(),
                                    last_checked=datetime.utcnow()
                                )
                                db.add(new_comp)
                                db.commit()
                                suggested.append(new_comp)
            except Exception as e:
                print(f"[COMPETITOR DISCOVERY ERROR] {e}", flush=True)

    return {
        "has_serp_provider": serp_status["has_serp_provider"],
        "provider_name": serp_status["provider_name"],
        "message": serp_status["message"],
        "suggested_competitors": suggested,
        "confirmed_competitors": confirmed,
        "all_competitors": existing_competitors
    }


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
