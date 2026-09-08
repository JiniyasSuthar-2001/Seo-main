import os
import json
import csv
import io
from collections import defaultdict, Counter
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, Response
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.config.settings import settings
from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership
from app.services.reports.export_service import CSVExportService
from app.routers.reports import build_export_filename, record_report_generation
from pydantic import BaseModel
from app.services.anchor_suggestion_service import AnchorSuggestionService

router = APIRouter()

ALLOWED_SECTIONS = {"graph", "orphans", "anchors", "opportunities", "broken"}


def normalize_link_url(url: Optional[str]) -> str:
    if not url:
        return ""
    clean = url.split('#')[0].strip()
    if clean.endswith('/') and clean not in ("https://", "http://", "https:///", "http:///"):
        clean = clean.rstrip('/')
    return clean


def _is_homepage_url(url: str, clean_dom: str) -> bool:
    c = normalize_link_url(url).lower().replace("https://", "").replace("http://", "").replace("www.", "")
    return c == clean_dom or c == ""


def _load_crawl_dataset(project: Project) -> Dict[str, Any]:
    """
    Shared helper: centralizes loading crawl snapshot artifacts for a project.
    """
    if not project or not project.domain:
        return {
            "crawl_dir": None,
            "pages": [],
            "internal_links": [],
            "external_links": [],
            "broken_links": []
        }

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    pages = []
    internal_links = []
    external_links = []
    broken_links = []
    crawl_dir = None

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))

            if crawl_dir and os.path.exists(crawl_dir):
                pages_file = os.path.join(crawl_dir, "pages.json")
                if os.path.exists(pages_file):
                    with open(pages_file, "r", encoding="utf-8") as pf:
                        pages = json.load(pf)

                links_file = os.path.join(crawl_dir, "internal_links.json")
                if os.path.exists(links_file):
                    with open(links_file, "r", encoding="utf-8") as lf:
                        internal_links = json.load(lf)

                ext_file = os.path.join(crawl_dir, "external_links.json")
                if os.path.exists(ext_file):
                    with open(ext_file, "r", encoding="utf-8") as ef:
                        external_links = json.load(ef)

                broken_file = os.path.join(crawl_dir, "broken_links.json")
                if os.path.exists(broken_file):
                    with open(broken_file, "r", encoding="utf-8") as bf:
                        broken_links = json.load(bf)
        except Exception as e:
            print(f"[INTERNAL LINKS] Error loading crawl dataset: {e}", flush=True)

    return {
        "crawl_dir": crawl_dir,
        "pages": pages,
        "internal_links": internal_links,
        "external_links": external_links,
        "broken_links": broken_links
    }


def _compute_link_graph_and_orphans(pages: List[Dict[str, Any]], internal_links: List[Dict[str, Any]], domain: str):
    """
    Computes incoming/outgoing link distributions, orphan pages, and anchor text frequency.
    """
    incoming_map = defaultdict(int)
    outgoing_map = defaultdict(int)
    anchor_counter = Counter()

    for link in internal_links:
        src = normalize_link_url(link.get("source"))
        tgt = normalize_link_url(link.get("target"))
        anc = (link.get("anchor_text") or "").strip()
        if src:
            outgoing_map[src] += 1
        if tgt:
            incoming_map[tgt] += 1
        if anc:
            anchor_counter[anc] += 1

    all_urls = [p.get("url") for p in pages if p.get("url")]
    clean_domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip('/')
    orphan_pages = []
    for url in all_urls:
        norm_url = normalize_link_url(url)
        if _is_homepage_url(norm_url, clean_domain):
            continue
        if incoming_map[norm_url] == 0:
            orphan_pages.append(url)

    top_anchors = [{"anchor_text": k, "frequency": v} for k, v in anchor_counter.most_common(15)]
    return incoming_map, outgoing_map, orphan_pages, top_anchors, anchor_counter


def _compute_opportunities(pages: List[Dict[str, Any]], internal_links: List[Dict[str, Any]], domain: str) -> List[Dict[str, Any]]:
    """
    Identifies internal link growth opportunities from graph structure.
    """
    incoming_map = defaultdict(int)
    for link in internal_links:
        tgt = normalize_link_url(link.get("target"))
        if tgt:
            incoming_map[tgt] += 1

    clean_domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip('/')
    opportunities = []
    for p in pages:
        url = p.get("url")
        if not url:
            continue
        norm_url = normalize_link_url(url)
        if _is_homepage_url(norm_url, clean_domain):
            continue
        inc_count = incoming_map[norm_url]
        if inc_count == 0:
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
                "suggested_anchor": p.get("h1") or p.get("title") or "Target Page Topic",
                "reason": "Page has only 1 incoming link. Adding a secondary internal link distributes PageRank Authority.",
                "priority": "MEDIUM",
                "data_source": "Local Crawl Link Graph"
            })
    return opportunities


def _get_broken_links_list(dataset: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Returns the broken links list from crawl dataset, with fallback for legacy crawl snapshots.
    """
    broken_links = dataset.get("broken_links", [])
    if not broken_links:
        pages = dataset.get("pages", [])
        i_links = dataset.get("internal_links", [])
        page_map = {normalize_link_url(p.get("url", "")): p for p in pages if p.get("url")}
        computed_broken = []
        for l in i_links:
            tgt = normalize_link_url(l.get("target"))
            pg = page_map.get(tgt)
            if pg and ((pg.get("status_code", 0) or 0) >= 400 or not pg.get("is_success", True)):
                computed_broken.append({
                    "source": l.get("source", ""),
                    "target": l.get("target", ""),
                    "anchor_text": l.get("anchor_text", "") or "[No Text]",
                    "link_type": "internal",
                    "status_code": pg.get("status_code", 0),
                    "is_broken": True,
                    "error": pg.get("error") or f"HTTP {pg.get('status_code', 0)}"
                })
        return computed_broken
    return broken_links


@router.get("")
@router.get("/")
def get_internal_links(
    project_id: str,
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"internal_links": [], "orphan_pages": [], "anchor_texts": [], "total": 0}

    domain = project.domain
    dataset = _load_crawl_dataset(project)
    internal_links = dataset["internal_links"]
    pages = dataset["pages"]

    incoming_map, outgoing_map, orphan_pages, top_anchors, anchor_counter = _compute_link_graph_and_orphans(pages, internal_links, domain)

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
def get_internal_link_opportunities(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Identifies internal link growth opportunities from actual crawled graph structure.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"opportunities": []}

    dataset = _load_crawl_dataset(project)
    opportunities = _compute_opportunities(dataset["pages"], dataset["internal_links"], project.domain)

    return {
        "project_id": project.id,
        "total_opportunities": len(opportunities),
        "opportunities": opportunities
    }


class AnchorSuggestionRequest(BaseModel):
    source_url: str
    target_url: str
    refresh: Optional[bool] = False


@router.post("/anchor-suggestions")
@router.get("/anchor-suggestions")
def get_anchor_suggestions(
    project_id: str,
    source_url: Optional[str] = Query(None),
    target_url: Optional[str] = Query(None),
    refresh: Optional[bool] = Query(False),
    payload: Optional[AnchorSuggestionRequest] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found.")

    src = (payload.source_url if payload and payload.source_url else source_url) or ""
    tgt = (payload.target_url if payload and payload.target_url else target_url) or ""
    force_refresh = (payload.refresh if payload and payload.refresh is not None else refresh) or False

    if not src or not tgt:
        raise HTTPException(status_code=400, detail="Both source_url and target_url parameters are required.")

    return AnchorSuggestionService.get_suggestions(
        project_id=project.id,
        domain=project.domain,
        source_url=src,
        target_url=tgt,
        refresh=force_refresh
    )


@router.get("/broken")
@router.get("/broken-links")
def get_broken_links(
    project_id: str,
    type: Optional[str] = Query(None), # all, internal, external
    search: Optional[str] = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"broken_links": [], "total": 0, "internal_count": 0, "external_count": 0, "summary": {}}

    domain = project.domain
    dataset = _load_crawl_dataset(project)
    broken_links = _get_broken_links_list(dataset)

    internal_count = sum(1 for b in broken_links if b.get("link_type") == "internal")
    external_count = sum(1 for b in broken_links if b.get("link_type") == "external")

    filtered = broken_links
    if type and type.lower() in ("internal", "external"):
        filtered = [b for b in filtered if b.get("link_type", "").lower() == type.lower()]

    if search and search.strip():
        q = search.strip().lower()
        filtered = [b for b in filtered if q in (b.get("source", "") or "").lower() or q in (b.get("target", "") or "").lower() or q in (b.get("anchor_text", "") or "").lower()]

    try:
        lim = int(limit)
    except (ValueError, TypeError):
        lim = 50
    try:
        off = int(offset)
    except (ValueError, TypeError):
        off = 0

    return {
        "domain": domain,
        "summary": {
            "total_broken_links": len(broken_links),
            "internal_broken_links": internal_count,
            "external_broken_links": external_count
        },
        "total": len(filtered),
        "total_unfiltered": len(broken_links),
        "internal_count": internal_count,
        "external_count": external_count,
        "broken_links": filtered[off : off + lim]
    }


@router.get("/broken/export.csv")
@router.get("/broken-links/export.csv")
def export_broken_links_csv(
    project_id: str,
    type: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    return internal_links_export_csv(project_id=project_id, section="broken", type=type, user_id=user_id, db=db)


@router.get("/export.csv")
def internal_links_export_csv(
    project_id: str,
    section: str = Query("graph"),
    type: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Section-aware CSV export for Links & Navigation.
    Supported sections: graph, orphans, anchors, opportunities, broken.
    Defaults to 'graph' for full backward compatibility.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    sec = (section or "graph").strip().lower()
    if sec not in ALLOWED_SECTIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid section '{section}'. Allowed values: {', '.join(sorted(ALLOWED_SECTIONS))}."
        )

    domain = project.domain
    dataset = _load_crawl_dataset(project)

    if sec == "graph":
        csv_str = CSVExportService.generate_internal_links_csv(dataset["internal_links"])
        filename_label = "internal-links"
        report_name = "Internal Links CSV"
    elif sec == "orphans":
        _, _, orphan_pages, _, _ = _compute_link_graph_and_orphans(dataset["pages"], dataset["internal_links"], domain)
        csv_str = CSVExportService.generate_orphan_pages_csv(orphan_pages)
        filename_label = "orphan-pages"
        report_name = "Orphan Pages CSV"
    elif sec == "anchors":
        _, _, _, _, anchor_counter = _compute_link_graph_and_orphans(dataset["pages"], dataset["internal_links"], domain)
        all_anchors = [{"anchor_text": k, "frequency": v} for k, v in anchor_counter.most_common()]
        csv_str = CSVExportService.generate_anchor_texts_csv(all_anchors)
        filename_label = "link-text"
        report_name = "Link Text CSV"
    elif sec == "opportunities":
        opps = _compute_opportunities(dataset["pages"], dataset["internal_links"], domain)
        csv_str = CSVExportService.generate_link_opportunities_csv(opps)
        filename_label = "suggested-links"
        report_name = "Suggested Links CSV"
    elif sec == "broken":
        broken_list = _get_broken_links_list(dataset)
        if type and type.lower() in ("internal", "external"):
            broken_list = [b for b in broken_list if b.get("link_type", "").lower() == type.lower()]
        csv_str = CSVExportService.generate_broken_links_csv(broken_list)
        filename_label = "broken-links"
        report_name = "Broken Links CSV"

    filename = build_export_filename(domain, filename_label, "csv")
    record_report_generation(db, project, report_name, "csv", filename, None, "Website Scan")
    return Response(
        content=csv_str.encode("utf-8"),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
    )
