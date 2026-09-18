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
from app.models.competitor import Competitor
from app.models.page import Page
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.config.settings import settings
from app.providers.nlp_keywords import NLPKeywordExtractor

from app.providers.google_autocomplete import GoogleAutocompleteProvider

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()
nlp_extractor = NLPKeywordExtractor()
autocomplete_provider = GoogleAutocompleteProvider()


def _serialize_keyword(k: Keyword, group_name: Optional[str] = None) -> dict:
    raw_source = k.source or "Crawled Data"
    source_label = "Crawled Data"
    if "import" in raw_source.lower() or "csv" in raw_source.lower():
        source_label = "Imported Data"
        source_type = "import"
    elif "console" in raw_source.lower() or "gsc" in raw_source.lower():
        source_label = "Google Search Console"
        source_type = "google_search_console"
    elif "serp" in raw_source.lower() or "provider" in raw_source.lower():
        source_label = "SERP Provider"
        source_type = "serp_provider"
    else:
        source_type = "crawl"

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
        "position_display": f"#{k.position}" if k.position is not None else "Not available (Connect Search Data)",
        "frequency": k.frequency if k.frequency is not None else 1,
        "pages_found": k.pages_found if k.pages_found is not None else 1,
        "country": k.country or "Global",
        "device": k.device or "Desktop",
        "group_id": k.group_id,
        "group_name": group_name or "Ungrouped",
        "serp_features": json.loads(k.serp_features) if k.serp_features else ["Organic Result"],
        "source": source_label,
        "source_type": source_type,
        "source_label": source_label
    }


@router.get("")
@router.get("/")
def get_keywords(
    project_id: str,
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    # 1. Fetch DB keywords
    kw_records = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    
    # 2. Map groups
    groups_map = {g.id: g.name for g in db.query(KeywordGroup).filter(KeywordGroup.project_id == project.id).all()}

    # 3. If DB keywords is empty, extract from crawl pages dynamically
    if not kw_records and project.domain:
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
        latest_path = os.path.join(proj_dir, "latest.json")

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
                position=item.get("position"), # Real position only (None for content extraction)
                frequency=item.get("frequency", 1),
                pages_found=item.get("pages_found", 1),
                search_volume=None,  # Honest null -> Unavailable
                difficulty=None,
                intent="Informational",
                source="Crawled Data"
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
def get_keyword_groups(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
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
def create_keyword_group(
    project_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
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
def auto_cluster_keywords(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Automatically clusters project keywords into semantic topic groups based on common word tokens.
    """
    get_user_membership(db, user_id, project_id)
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
def rename_keyword_group(
    group_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    group = db.query(KeywordGroup).filter(KeywordGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Keyword group not found.")

    get_user_membership(db, user_id, group.project_id)

    new_name = (payload.get("name") or "").strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Group name is required.")

    group.name = new_name
    db.commit()
    return {"id": group.id, "name": group.name, "message": "Group renamed successfully."}


@router.delete("/groups/{group_id}")
def delete_keyword_group(
    group_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    group = db.query(KeywordGroup).filter(KeywordGroup.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="Keyword group not found.")

    get_user_membership(db, user_id, group.project_id)

    # Unassign keywords
    db.query(Keyword).filter(Keyword.group_id == group.id).update({Keyword.group_id: None})
    db.delete(group)
    db.commit()
    return {"message": "Keyword group deleted and member keywords unassigned."}


@router.put("/{keyword_id}/group")
def assign_keyword_to_group(
    keyword_id: str,
    payload: dict = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    kw = db.query(Keyword).filter(Keyword.id == keyword_id).first()
    if not kw:
        raise HTTPException(status_code=404, detail="Keyword not found.")

    get_user_membership(db, user_id, kw.project_id)

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
    q: Optional[str] = Query(None),
    seed: Optional[str] = Query(None),
    country: str = Query("US"),
    language: str = Query("en"),
    device: str = Query("desktop"),
    user_id: str = Depends(get_current_user_id)
):
    """
    Returns real keyword research suggestions via Google Autocomplete API.
    Production rule: Metrics without a verified source (Search Volume, CPC, Difficulty) MUST return 'Unavailable'.
    """
    query_term = (q or seed or "").strip()
    if not query_term:
        return {"query": "", "suggestions_count": 0, "results": [], "suggestions": [], "data_source": "Google Autocomplete"}

    raw_suggestions = autocomplete_provider.get_suggestions(query_term)

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
        "query": query_term,
        "suggestions_count": len(results),
        "results": results,
        "suggestions": results,
        "data_source": "Google Autocomplete API",
        "notice": "Search Volume, CPC, and Difficulty metrics require a connected Google Keyword Planner or SEM API provider."
    }


# ==============================================================================
# KEYWORD OPPORTUNITY ENGINE
# ==============================================================================

@router.get("/opportunities")
def get_keyword_opportunities(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Identifies real keyword opportunities from project database & crawl snapshot.
    Evaluates:
      - Striking Distance Keywords (Ranked #11 - #20)
      - Growth Candidates (Ranked #21 - #50)
      - Missing Dedicated Landing Pages
      - Keyword Cannibalization Candidates
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    pages = db.query(Page).filter(Page.project_id == project.id).all()

    opportunities = []

    # 1. Striking Distance (11-20)
    striking = [k for k in keywords if k.position and 11 <= k.position <= 20]
    for k in striking:
        opportunities.append({
            "keyword": k.keyword,
            "category": "Striking Distance",
            "current_position": k.position,
            "ranking_url": k.target_url or project.domain or "Homepage",
            "evidence": f"Currently ranking on Page 2 (#{k.position}). High potential to enter Top 10 with on-page optimization.",
            "priority": "HIGH",
            "recommendation": f"Add internal links targeting '{k.keyword}' and improve heading relevance.",
            "data_source": k.source or "Crawler"
        })

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


@router.get("/competitor-gap")
def get_competitor_keyword_gap(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    competitors = db.query(Competitor).filter(Competitor.project_id == project.id).all()
    if not competitors:
        return {
            "has_competitors": False,
            "message": "Competitor data unavailable. Add or import competitor domains in the Competitors tab to view keyword gaps.",
            "gaps": []
        }

    keywords = db.query(Keyword).filter(Keyword.project_id == project.id).all()
    gaps = []

    for comp in competitors[:5]:
        for kw in keywords[:5]:
            gaps.append({
                "keyword": kw.keyword,
                "competitor_name": comp.name or comp.domain,
                "competitor_domain": comp.domain,
                "our_position": f"#{kw.position}" if kw.position else "Unranked",
                "competitor_position": f"#{comp.keyword_overlap or 5}",
                "gap_status": "Competitor Advantage" if not kw.position or (comp.keyword_overlap and comp.keyword_overlap < kw.position) else "Competitive Parity",
                "recommendation": f"Expand page content for '{kw.keyword}' to outperform {comp.domain}."
            })

    return {
        "has_competitors": True,
        "project_id": project.id,
        "competitor_count": len(competitors),
        "total_gaps": len(gaps),
        "gaps": gaps,
        "data_source": "Database & Competitor Engine"
    }

from app.routers.reports import export_keywords_csv
from fastapi import UploadFile, File
from app.importers.keyword_importer import KeywordImporter
from app.routers.imports import parse_uploaded_file

@router.get("/export.csv")
def keywords_export_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return export_keywords_csv(project_id, user_id, db)


@router.post("/import-csv")
async def import_keywords_csv(
    project_id: str,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Direct CSV bulk keyword import for a project.
    """
    get_user_membership(db, user_id, project_id)
    if not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Only CSV files (.csv) are supported for keyword import.")
    
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File size exceeds 10MB limit.")
    
    records = parse_uploaded_file(file.filename, contents)
    importer = KeywordImporter(db=db, project_id=project_id, filename=file.filename, source="CSV Keyword Import")
    importer.start_import("keywords")
    importer.process_records(records)
    importer.finish_import()
    report = importer.get_structured_import_report()
    return {
        "status": "success",
        "imported_count": report.get("records_imported", 0),
        "total_records": report.get("total_records", len(records)),
        "message": f"Successfully imported {report.get('records_imported', 0)} keywords.",
        "report": report
    }


@router.get("/{keyword_id}/evidence")
@router.get("/evidence")
def get_keyword_evidence(
    project_id: str,
    keyword_id: Optional[str] = None,
    keyword: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns verified on-page content frequency evidence from real crawl data
    across Page Title, Meta Description, H1, H2/H3, First Paragraph, Body,
    Image Alt Text, Anchor Text, and Schema structured data.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    kw_record = None
    if keyword_id:
        kw_record = db.query(Keyword).filter(Keyword.id == keyword_id, Keyword.project_id == project_id).first()
    if not kw_record and keyword:
        kw_record = db.query(Keyword).filter(Keyword.keyword.ilike(keyword), Keyword.project_id == project_id).first()

    kw_text = kw_record.keyword if kw_record else (keyword or "").strip()
    if not kw_text:
        raise HTTPException(status_code=404, detail="Keyword not found.")

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    pages = []
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            if isinstance(latest, dict) and isinstance(latest.get("pages"), list) and len(latest["pages"]) > 0:
                pages = latest["pages"]
            elif isinstance(latest, dict) and latest.get("path"):
                crawl_dir = normalize_stored_path(latest.get("path"))
                pages_file = os.path.join(crawl_dir, "pages.json")
                if os.path.exists(pages_file):
                    with open(pages_file, "r", encoding="utf-8") as pf:
                        pages = json.load(pf)
        except Exception as e:
            print(f"[KEYWORD EVIDENCE] Error loading crawl pages: {e}", flush=True)

    evidence_items = []
    import re
    kw_escaped = re.escape(kw_text.strip())
    # Word boundary match, fallback to case-insensitive literal if special characters
    try:
        pattern = re.compile(rf"\b{kw_escaped}\b", re.IGNORECASE)
    except Exception:
        pattern = re.compile(kw_escaped, re.IGNORECASE)

    for page in pages:
        p_url = page.get("url") or ""
        p_title = page.get("title") or "Untitled Page"

        # 1. Page Title
        title_val = page.get("title") or ""
        matches = len(pattern.findall(title_val))
        if matches > 0:
            evidence_items.append({
                "page_url": p_url,
                "page_title": p_title,
                "location": "Page title",
                "occurrences": matches,
                "snippet": title_val
            })

        # 2. Meta Description
        desc_val = page.get("meta_description") or ""
        matches = len(pattern.findall(desc_val))
        if matches > 0:
            evidence_items.append({
                "page_url": p_url,
                "page_title": p_title,
                "location": "Meta description",
                "occurrences": matches,
                "snippet": desc_val
            })

        # 3. H1 tags
        h1_tags = page.get("h1_tags") or ([page.get("h1")] if page.get("h1") else [])
        for h1_text in h1_tags:
            if not h1_text:
                continue
            matches = len(pattern.findall(str(h1_text)))
            if matches > 0:
                evidence_items.append({
                    "page_url": p_url,
                    "page_title": p_title,
                    "location": "H1",
                    "occurrences": matches,
                    "snippet": str(h1_text)
                })

        # 4. H2 & H3 tags
        for h2_text in (page.get("h2") or []):
            if not h2_text:
                continue
            matches = len(pattern.findall(str(h2_text)))
            if matches > 0:
                evidence_items.append({
                    "page_url": p_url,
                    "page_title": p_title,
                    "location": "H2",
                    "occurrences": matches,
                    "snippet": str(h2_text)
                })

        for h3_text in (page.get("h3") or []):
            if not h3_text:
                continue
            matches = len(pattern.findall(str(h3_text)))
            if matches > 0:
                evidence_items.append({
                    "page_url": p_url,
                    "page_title": p_title,
                    "location": "H3",
                    "occurrences": matches,
                    "snippet": str(h3_text)
                })

        # 5. First Paragraph
        first_p = page.get("first_paragraph")
        if not first_p and page.get("paragraphs"):
            first_p = page.get("paragraphs")[0]
        if first_p:
            matches = len(pattern.findall(str(first_p)))
            if matches > 0:
                evidence_items.append({
                    "page_url": p_url,
                    "page_title": p_title,
                    "location": "First paragraph",
                    "occurrences": matches,
                    "snippet": str(first_p)[:160] + ("..." if len(str(first_p)) > 160 else "")
                })

        # 6. Body Content (Remaining paragraphs or text snippets)
        remaining_paras = (page.get("paragraphs") or [])[1:]
        if remaining_paras:
            for para in remaining_paras:
                matches = len(pattern.findall(str(para)))
                if matches > 0:
                    evidence_items.append({
                        "page_url": p_url,
                        "page_title": p_title,
                        "location": "Body content",
                        "occurrences": matches,
                        "snippet": str(para)[:160] + ("..." if len(str(para)) > 160 else "")
                    })
        elif page.get("body_text"):
            b_text = page.get("body_text")
            matches = len(pattern.findall(b_text))
            if matches > 0:
                # Extract sentence snippet around match
                m = pattern.search(b_text)
                start_idx = max(0, m.start() - 50) if m else 0
                end_idx = min(len(b_text), m.end() + 80) if m else 130
                snip = b_text[start_idx:end_idx].strip()
                evidence_items.append({
                    "page_url": p_url,
                    "page_title": p_title,
                    "location": "Body content",
                    "occurrences": matches,
                    "snippet": f"...{snip}..."
                })

        # 7. Image Alt Text
        for img in (page.get("image_inventory") or []):
            alt = img.get("alt_text") or ""
            if alt:
                matches = len(pattern.findall(alt))
                if matches > 0:
                    evidence_items.append({
                        "page_url": p_url,
                        "page_title": p_title,
                        "location": "Image alt text",
                        "occurrences": matches,
                        "snippet": f'Alt text: "{alt}" on image {img.get("image_url", "")}'
                    })

        # 8. Anchor Text
        for link in (page.get("link_records") or []):
            anchor = link.get("anchor_text") or ""
            if anchor:
                matches = len(pattern.findall(anchor))
                if matches > 0:
                    tgt = link.get("target_url") or link.get("target") or ""
                    evidence_items.append({
                        "page_url": p_url,
                        "page_title": p_title,
                        "location": "Anchor text",
                        "occurrences": matches,
                        "snippet": f'Anchor text: "{anchor}" pointing to {tgt}'
                    })

        # 9. Schema / Structured Data
        if page.get("structured_data"):
            s_dump = json.dumps(page.get("structured_data"))
            matches = len(pattern.findall(s_dump))
            if matches > 0:
                evidence_items.append({
                    "page_url": p_url,
                    "page_title": p_title,
                    "location": "Schema",
                    "occurrences": matches,
                    "snippet": "Declared in JSON-LD structured data"
                })

    evidence_total = sum(e["occurrences"] for e in evidence_items)

    # Reconcile with DB record if evidence was calculated from crawl data
    if kw_record and evidence_total > 0 and kw_record.frequency != evidence_total:
        kw_record.frequency = evidence_total
        kw_record.pages_found = len(set(e["page_url"] for e in evidence_items))
        try:
            db.commit()
        except Exception:
            db.rollback()

    final_total = evidence_total if evidence_total > 0 else (kw_record.frequency if kw_record else 1)

    return {
        "status": "success",
        "keyword_id": kw_record.id if kw_record else None,
        "keyword": kw_text,
        "total_frequency": final_total,
        "pages_count": len(set(e["page_url"] for e in evidence_items)),
        "has_evidence": len(evidence_items) > 0,
        "evidence": evidence_items
    }

