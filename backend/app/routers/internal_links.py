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
from app.crawler.crawler import canonicalize_url
from app.services.link_graph_engine import (
    build_internal_link_graph,
    get_incoming_links_for_page,
    get_outgoing_links_for_page,
    get_link_detail,
    normalize_graph_url
)

router = APIRouter()

ALLOWED_SECTIONS = {"graph", "orphans", "anchors", "opportunities", "broken"}


def normalize_link_url(url: Optional[str]) -> str:
    if not url:
        return ""
    return canonicalize_url(url)


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
            "broken_links": [],
            "link_records": []
        }

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, project.domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    pages = []
    internal_links = []
    external_links = []
    broken_links = []
    link_records = []
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

                rec_file = os.path.join(crawl_dir, "link_records.json")
                if os.path.exists(rec_file):
                    with open(rec_file, "r", encoding="utf-8") as rf:
                        link_records = json.load(rf)
        except Exception as e:
            print(f"[INTERNAL LINKS] Error loading crawl dataset: {e}", flush=True)

    return {
        "crawl_dir": crawl_dir,
        "pages": pages,
        "internal_links": internal_links,
        "external_links": external_links,
        "broken_links": broken_links,
        "link_records": link_records
    }


def _compute_link_graph_and_orphans(pages: List[Dict[str, Any]], internal_links: List[Dict[str, Any]], domain: str, link_records: Optional[List[Dict[str, Any]]] = None):
    """
    Computes incoming/outgoing link distributions, orphan pages, and anchor text frequency.
    """
    seed_url = f"https://{domain}/"
    graph = build_internal_link_graph(pages, internal_links, link_records=link_records, seed_url=seed_url)

    incoming_map = defaultdict(int, graph.get("inbound_counts", {}))
    outgoing_map = defaultdict(int, graph.get("outbound_counts", {}))
    orphan_pages = [o.get("url") for o in graph.get("orphan_pages", [])]

    anchor_counter = Counter()
    active_links = link_records if (link_records and len(link_records) > 0) else internal_links
    for link in active_links:
        if link.get("is_internal") is not False:
            anc = (link.get("anchor_text") or "").strip()
            if anc:
                anchor_counter[anc] += 1

    top_anchors = [{"anchor_text": k, "frequency": v} for k, v in anchor_counter.most_common(15)]
    return incoming_map, outgoing_map, orphan_pages, top_anchors, anchor_counter, graph


def _compute_opportunities(pages: List[Dict[str, Any]], internal_links: List[Dict[str, Any]], domain: str, link_records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Identifies internal link growth opportunities from graph structure.
    """
    seed_url = f"https://{domain}/"
    graph = build_internal_link_graph(pages, internal_links, link_records=link_records, seed_url=seed_url)
    incoming_map = graph.get("inbound_counts", {})
    clean_domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip('/')
    
    opportunities = []
    for p in pages:
        url = p.get("url")
        if not url:
            continue
        norm_url = normalize_link_url(url)
        c = norm_url.lower().replace("https://", "").replace("http://", "").replace("www.", "")
        if c == clean_domain or c == "":
            continue
            
        inc_count = incoming_map.get(norm_url, 0)
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
                    "error": pg.get("error") or f"HTTP {pg.get('status_code', 0)}",
                    "error_type": "not_found" if pg.get("status_code") == 404 else "http_error",
                    "source_section": l.get("source_section", "other"),
                    "nearest_heading": l.get("nearest_heading"),
                    "paragraph_index": l.get("paragraph_index"),
                    "sentence_index": l.get("sentence_index"),
                    "context_text": l.get("context_text", ""),
                    "html_snippet": l.get("html_snippet", "")
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
    link_records = dataset["link_records"]

    incoming_map, outgoing_map, orphan_pages, top_anchors, anchor_counter, graph = _compute_link_graph_and_orphans(pages, internal_links, domain, link_records)

    return {
        "domain": domain,
        "summary": {
            "total_internal_links": len(internal_links),
            "total_audited_pages": len(pages),
            "orphan_pages_count": len(orphan_pages),
            "unique_anchor_texts": len(anchor_counter),
            "deep_pages_count": graph.get("deep_pages_count", 0),
            "dead_end_pages_count": graph.get("dead_end_pages_count", 0)
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


@router.get("/incoming")
def get_incoming_links_api(
    project_id: str,
    url: str = Query(..., description="Target page URL to find incoming links for"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all incoming links pointing to a target URL with rich location, context, and source status.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = _load_crawl_dataset(project)
    incoming = get_incoming_links_for_page(
        target_url=url,
        link_records=dataset.get("link_records"),
        internal_links=dataset.get("internal_links"),
        pages=dataset.get("pages")
    )

    return {
        "project_id": project.id,
        "target_url": url,
        "total_incoming_links": len(incoming),
        "incoming_links": incoming
    }


@router.get("/outgoing")
def get_outgoing_links_api(
    project_id: str,
    url: str = Query(..., description="Source page URL to find outgoing links for"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns all outgoing links from a source URL with target status, location, and context.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = _load_crawl_dataset(project)
    outgoing = get_outgoing_links_for_page(
        source_url=url,
        link_records=dataset.get("link_records"),
        internal_links=dataset.get("internal_links"),
        external_links=dataset.get("external_links"),
        pages=dataset.get("pages")
    )

    return {
        "project_id": project.id,
        "source_url": url,
        "total_outgoing_links": len(outgoing),
        "outgoing_links": outgoing
    }


@router.get("/link-detail")
def get_link_detail_api(
    project_id: str,
    link_id: str = Query(..., description="Unique LinkRecord ID"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns complete LinkRecord evidence for a specific link ID.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = _load_crawl_dataset(project)
    rec = get_link_detail(link_id=link_id, link_records=dataset.get("link_records"))
    if not rec:
        raise HTTPException(status_code=404, detail="Link record not found")

    return {
        "project_id": project.id,
        "link_record": rec
    }


@router.get("/page-link-counts")
def get_page_link_counts_api(
    project_id: str,
    url: str = Query(..., description="Page URL to get counts for"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Returns incoming_internal_links, outgoing_internal_links, unique counts, depth, and orphan status for a page.
    """
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = _load_crawl_dataset(project)
    seed_url = f"https://{project.domain}/"
    graph = build_internal_link_graph(
        pages=dataset.get("pages", []),
        internal_links=dataset.get("internal_links", []),
        link_records=dataset.get("link_records"),
        seed_url=seed_url
    )

    norm_target = normalize_link_url(url)
    matched = None
    for pm in graph.get("page_metrics", []):
        if pm.get("normalized_url") == norm_target or pm.get("url") == url:
            matched = pm
            break

    if not matched:
        # Default zero-evaluated record
        matched = {
            "url": url,
            "normalized_url": norm_target,
            "title": "",
            "status_code": 0,
            "incoming_internal_links": 0,
            "outgoing_internal_links": 0,
            "unique_incoming_internal_links": 0,
            "unique_outgoing_internal_links": 0,
            "internal_link_depth": 0,
            "orphan_status": "not_in_crawl"
        }

    return {
        "project_id": project.id,
        "page": matched
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
    opportunities = _compute_opportunities(dataset["pages"], dataset["internal_links"], project.domain, dataset.get("link_records"))

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
        _, _, orphan_pages, _, _, _ = _compute_link_graph_and_orphans(dataset["pages"], dataset["internal_links"], domain, dataset.get("link_records"))
        csv_str = CSVExportService.generate_orphan_pages_csv(orphan_pages)
        filename_label = "orphan-pages"
        report_name = "Orphan Pages CSV"
    elif sec == "anchors":
        _, _, _, _, anchor_counter, _ = _compute_link_graph_and_orphans(dataset["pages"], dataset["internal_links"], domain, dataset.get("link_records"))
        all_anchors = [{"anchor_text": k, "frequency": v} for k, v in anchor_counter.most_common()]
        csv_str = CSVExportService.generate_anchor_texts_csv(all_anchors)
        filename_label = "link-text"
        report_name = "Link Text CSV"
    elif sec == "opportunities":
        opps = _compute_opportunities(dataset["pages"], dataset["internal_links"], domain, dataset.get("link_records"))
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
