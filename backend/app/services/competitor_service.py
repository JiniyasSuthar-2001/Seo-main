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


from app.models.competitor_ranking import CompetitorRanking

from sqlalchemy import func

def perform_keyword_gap_analysis(project: Project, db: Session, competitor_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Performs Keyword Gap Analysis comparing Target Website keywords against Confirmed Competitors.
    Production rule: Based 100% on actual project database data and verified CompetitorRanking records.
    Never fabricates keywords, positions, or search metrics.
    """
    comp_query = db.query(Competitor).filter(
        Competitor.project_id == project.id,
        func.lower(Competitor.status) == "confirmed"
    )
    if competitor_id:
        comp_query = comp_query.filter(Competitor.id == competitor_id)
        
    confirmed_competitors = comp_query.all()

    # Load all project keywords
    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    
    # Load all competitor rankings for this project
    comp_rankings_query = db.query(CompetitorRanking).filter(
        CompetitorRanking.project_id == project.id
    )
    if competitor_id:
        comp_rankings_query = comp_rankings_query.filter(CompetitorRanking.competitor_id == competitor_id)
        
    comp_rankings = comp_rankings_query.order_by(CompetitorRanking.checked_at.desc()).all()

    # Map latest competitor ranking by (keyword.lower(), competitor_id)
    latest_comp_rankings: Dict[Tuple[str, str], CompetitorRanking] = {}
    for cr in comp_rankings:
        key = (cr.keyword.strip().lower(), cr.competitor_id)
        if key not in latest_comp_rankings:
            latest_comp_rankings[key] = cr

    # Map confirmed competitors by ID
    comp_map = {c.id: c for c in confirmed_competitors}

    gap_data = []
    processed_keys = set()

    # 1. Process target website keywords
    for kw_record in keywords:
        if not kw_record.keyword:
            continue
        
        kw_clean = kw_record.keyword.strip()
        kw_lower = kw_clean.lower()
        target_pos = kw_record.position  # 1-indexed int or None

        # For each confirmed competitor, evaluate the gap
        if confirmed_competitors:
            for comp in confirmed_competitors:
                processed_keys.add((kw_lower, comp.id))
                comp_ranking = latest_comp_rankings.get((kw_lower, comp.id))
                comp_pos = comp_ranking.position if comp_ranking else None

                # Calculate mathematical gap: competitor_pos - target_pos
                # Positive (+8) => You are 8 spots ahead (e.g. You #1, Comp #9)
                # Negative (-8) => Competitor is 8 spots ahead (e.g. You #9, Comp #1)
                pos_diff = None
                diff_display = "N/A"
                if target_pos is not None and comp_pos is not None:
                    pos_diff = comp_pos - target_pos
                    diff_display = f"+{pos_diff}" if pos_diff > 0 else str(pos_diff)

                # Determine opportunity level
                if comp_pos is not None and (target_pos is None or target_pos > comp_pos):
                    opportunity = "HIGH"  # Competitor ranks ahead or you are unranked
                elif target_pos is not None and comp_pos is not None and target_pos <= comp_pos:
                    opportunity = "LOW"   # You outrank the competitor
                elif target_pos is not None and comp_pos is None:
                    opportunity = "MEDIUM" # You rank, competitor is unranked
                else:
                    opportunity = "NOT_CHECKED"

                gap_data.append({
                    "keyword": kw_clean,
                    "competitor_id": comp.id,
                    "competitor_name": comp.name,
                    "competitor_domain": comp.domain,
                    "target_position": target_pos,
                    "target_position_display": f"#{target_pos}" if target_pos is not None else "Not Ranking",
                    "competitor_position": comp_pos,
                    "competitor_position_display": f"#{comp_pos}" if comp_pos is not None else "Data Unavailable",
                    "position_difference": pos_diff,
                    "position_difference_display": diff_display,
                    "search_volume": kw_record.search_volume or 0,
                    "keyword_difficulty": kw_record.difficulty or 0,
                    "opportunity_level": opportunity,
                    "ranking_url": comp_ranking.ranking_url if comp_ranking else None,
                    "source": comp_ranking.source if comp_ranking else "None",
                    "source_display": (comp_ranking.source.replace("_", " ").title() if comp_ranking else "Not Checked"),
                    "checked_at": comp_ranking.checked_at.isoformat() if (comp_ranking and comp_ranking.checked_at) else None,
                    "recommended_action": f"Optimize page content targeting '{kw_clean}'"
                })
        else:
            # No confirmed competitors configured
            gap_data.append({
                "keyword": kw_clean,
                "competitor_id": None,
                "competitor_name": "No Competitor Configured",
                "competitor_domain": None,
                "target_position": target_pos,
                "target_position_display": f"#{target_pos}" if target_pos is not None else "Not Ranking",
                "competitor_position": None,
                "competitor_position_display": "Data Unavailable",
                "position_difference": None,
                "position_difference_display": "N/A",
                "search_volume": kw_record.search_volume or 0,
                "keyword_difficulty": kw_record.difficulty or 0,
                "opportunity_level": "NOT_CHECKED",
                "ranking_url": None,
                "source": "None",
                "source_display": "Not Checked",
                "checked_at": None,
                "recommended_action": f"Confirm competitors to compare rankings for '{kw_clean}'"
            })

    # 2. Add any keywords that competitors rank for which are NOT yet in the project's keywords table
    for (kw_lower, comp_id), comp_ranking in latest_comp_rankings.items():
        if (kw_lower, comp_id) in processed_keys:
            continue
        
        comp = comp_map.get(comp_id)
        if not comp:
            continue

        comp_pos = comp_ranking.position
        gap_data.append({
            "keyword": comp_ranking.keyword,
            "competitor_id": comp.id,
            "competitor_name": comp.name,
            "competitor_domain": comp.domain,
            "target_position": None,
            "target_position_display": "Not Ranking",
            "competitor_position": comp_pos,
            "competitor_position_display": f"#{comp_pos}" if comp_pos is not None else "Data Unavailable",
            "position_difference": None,
            "position_difference_display": "N/A",
            "search_volume": 0,
            "keyword_difficulty": 0,
            "opportunity_level": "HIGH" if comp_pos is not None else "NOT_CHECKED",
            "ranking_url": comp_ranking.ranking_url,
            "source": comp_ranking.source,
            "source_display": comp_ranking.source.replace("_", " ").title(),
            "checked_at": comp_ranking.checked_at.isoformat() if comp_ranking.checked_at else None,
            "recommended_action": f"Create targeted content to compete for '{comp_ranking.keyword}'"
        })

    # Summary metrics
    missing_count = sum(1 for g in gap_data if g["opportunity_level"] == "HIGH")
    winning_count = sum(1 for g in gap_data if g["opportunity_level"] == "LOW")
    shared_count = sum(1 for g in gap_data if g["target_position"] is not None and g["competitor_position"] is not None)
    
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
            "winning_keywords": winning_count,
            "shared_keywords": shared_count,
        },
        "keyword_gap": gap_data,
        "gap_items": gap_data,
        "message": "Keyword gap analysis complete." if gap_data else "No keyword dataset or verified competitor data available for gap analysis."
    }


def store_competitor_ranking(
    db: Session,
    project_id: str,
    competitor_id: str,
    keyword: str,
    position: Optional[int],
    ranking_url: Optional[str] = None,
    search_engine: str = "google",
    country: Optional[str] = None,
    location: Optional[str] = None,
    device: str = "desktop",
    source: str = "serp_provider",
    checked_at: Optional[datetime] = None,
) -> CompetitorRanking:
    """
    Persist a single verified competitor ranking record.
    """
    if checked_at is None:
        checked_at = datetime.utcnow()

    rec = CompetitorRanking(
        id=str(uuid.uuid4()),
        project_id=project_id,
        competitor_id=competitor_id,
        keyword=keyword.strip(),
        position=position,
        ranking_url=ranking_url,
        search_engine=search_engine.lower() if search_engine else "google",
        country=country,
        location=location,
        device=device.lower() if device else "desktop",
        source=source,
        checked_at=checked_at,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    return rec


def bulk_store_competitor_rankings(
    db: Session,
    rankings: List[Dict[str, Any]]
) -> int:
    """
    Bulk persist verified competitor ranking records.
    """
    count = 0
    now = datetime.utcnow()
    for r in rankings:
        rec = CompetitorRanking(
            id=str(uuid.uuid4()),
            project_id=r["project_id"],
            competitor_id=r["competitor_id"],
            keyword=r["keyword"].strip(),
            position=r.get("position"),
            ranking_url=r.get("ranking_url"),
            search_engine=r.get("search_engine", "google").lower(),
            country=r.get("country"),
            location=r.get("location"),
            device=r.get("device", "desktop").lower(),
            source=r.get("source", "serp_provider"),
            checked_at=r.get("checked_at") or now,
        )
        db.add(rec)
        count += 1
    db.commit()
    return count

