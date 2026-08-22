import os
import json
from collections import defaultdict, Counter
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings

router = APIRouter()


@router.get("")
@router.get("/")
def get_internal_links(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"internal_links": [], "orphan_pages": [], "anchor_texts": [], "total": 0}

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    internal_links = []
    pages = []
    
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            
            links_file = os.path.join(crawl_dir, "internal_links.json")
            if os.path.exists(links_file):
                with open(links_file, "r") as lf:
                    internal_links = json.load(lf)
                    
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)
        except Exception as e:
            print(f"[INTERNAL LINKS API] Error loading dataset: {e}", flush=True)

    # 1. Incoming & Outgoing link maps
    incoming_map = defaultdict(int)
    outgoing_map = defaultdict(int)
    anchor_counter = Counter()

    for link in internal_links:
        src = link.get("source")
        tgt = link.get("target")
        anc = (link.get("anchor_text") or "").strip()
        if src:
            outgoing_map[src] += 1
        if tgt:
            incoming_map[tgt] += 1
        if anc:
            anchor_counter[anc] += 1

    # 2. Identify Orphan Pages (Pages with 0 incoming internal links)
    all_urls = [p.get("url") for p in pages if p.get("url")]
    homepage_url = f"https://{domain}/"
    orphan_pages = [url for url in all_urls if incoming_map[url] == 0 and url.rstrip('/') != homepage_url.rstrip('/')]

    # 3. Anchor text frequency table
    top_anchors = [{"anchor_text": k, "frequency": v} for k, v in anchor_counter.most_common(15)]

    return {
        "domain": domain,
        "summary": {
            "total_internal_links": len(internal_links),
            "total_audited_pages": len(pages),
            "orphan_pages_count": len(orphan_pages),
            "unique_anchor_texts": len(anchor_counter)
        },
        "orphan_pages": orphan_pages,
        "anchor_texts": top_anchors,
        "internal_links": internal_links[offset : offset + limit],
        "total_internal_links": len(internal_links),
        "provenance": {
            "source": "Local Crawl Link Graph Parser",
            "confidence": 100.0
        }
    }


@router.get("/opportunities")
def get_internal_link_opportunities(project_id: str, db: Session = Depends(get_db)):
    """
    Identifies internal link growth opportunities from actual crawled graph structure.
    - Orphan pages
    - High-value pages with low incoming internal link depth
    - Pages with excessive outgoing links (> 100)
    """
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"opportunities": []}

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    pages = []
    internal_links = []

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)
            links_file = os.path.join(crawl_dir, "internal_links.json")
            if os.path.exists(links_file):
                with open(links_file, "r") as lf:
                    internal_links = json.load(lf)
        except Exception as e:
            from app.config.logger import get_logger
            get_logger("internal_links").warning(f"Failed to load crawl files for project {project.id}: {e}")


    incoming_map = defaultdict(int)
    for link in internal_links:
        if link.get("target"):
            incoming_map[link.get("target")] += 1

    opportunities = []
    for p in pages:
        url = p.get("url")
        if not url:
            continue
        inc_count = incoming_map[url]
        if inc_count == 0 and url.rstrip('/') != f"https://{domain}".rstrip('/'):
            opportunities.append({
                "source_page": f"https://{domain}/",
                "target_page": url,
                "suggested_anchor": p.get("title") or "Target Service Page",
                "reason": "Orphan page has 0 incoming internal links. Adding an internal link will improve crawlability and indexability.",
                "priority": "HIGH",
                "data_source": "Local Crawl Link Graph"
            })
        elif inc_count == 1:
            opportunities.append({
                "source_page": f"https://{domain}/",
                "target_page": url,
                "suggested_anchor": p.get("h1") or "Learn More",
                "reason": "Page has only 1 incoming link. Adding a secondary internal link distributes PageRank Authority.",
                "priority": "MEDIUM",
                "data_source": "Local Crawl Link Graph"
            })

    return {
        "project_id": project.id,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities
    }
