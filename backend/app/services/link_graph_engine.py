from typing import List, Dict, Any, Set, Optional, Tuple
from collections import defaultdict
from app.crawler.crawler import canonicalize_url
import uuid


def normalize_graph_url(url: Optional[str]) -> str:
    """
    Centralized canonical URL normalizer for graph operations.
    """
    if not url:
        return ""
    return canonicalize_url(url)


def build_internal_link_graph(
    pages: List[Dict[str, Any]], 
    internal_links: List[Dict[str, Any]],
    link_records: Optional[List[Dict[str, Any]]] = None,
    seed_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    Builds a deterministic internal link graph from crawl evidence.
    Calculates:
    - Inbound internal links per page (total & unique)
    - Outbound internal links per page (total & unique)
    - Click depth from seed
    - Reverse link mappings (inbound source pages & anchors)
    - Orphan candidates (pages with 0 inbound links within this crawl scope, excluding seed)
    - Dead-end pages (pages with 0 outbound links)
    - Deep pages (depth > 3)
    """
    # Track pages by normalized URL
    page_map: Dict[str, Dict[str, Any]] = {}
    seed_norm = normalize_graph_url(seed_url) if seed_url else ""
    
    for p in pages:
        u = p.get("url")
        if u:
            norm_u = normalize_graph_url(u)
            page_map[norm_u] = p
            # If seed isn't explicit, check depth == 0
            if not seed_norm and (p.get("crawl_depth") == 0 or p.get("depth") == 0):
                seed_norm = norm_u

    inbound_counts: Dict[str, int] = defaultdict(int)
    outbound_counts: Dict[str, int] = defaultdict(int)
    unique_inbound_sources: Dict[str, Set[str]] = defaultdict(set)
    unique_outbound_targets: Dict[str, Set[str]] = defaultdict(set)
    
    link_map: Dict[str, List[str]] = defaultdict(list)
    anchors_map: Dict[str, List[str]] = defaultdict(list)
    inbound_sources_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    # If link_records is provided, we can use the richer data
    active_links = link_records if (link_records and len(link_records) > 0) else internal_links

    for link in active_links:
        src = link.get("source_url") or link.get("source") or ""
        tgt = link.get("target_url") or link.get("destination_url") or link.get("target") or link.get("href") or ""
        
        # Check scope if available in link record
        is_internal = link.get("is_internal")
        if is_internal is False or link.get("link_scope") == "external":
            continue

        norm_src = normalize_graph_url(src)
        norm_tgt = normalize_graph_url(tgt)
        anchor = (link.get("anchor_text") or link.get("anchor") or "").strip()
        rel = link.get("rel") or "follow"

        if norm_src and norm_tgt:
            outbound_counts[norm_src] += 1
            inbound_counts[norm_tgt] += 1
            unique_inbound_sources[norm_tgt].add(norm_src)
            unique_outbound_targets[norm_src].add(norm_tgt)

            link_map[norm_src].append(tgt)
            inbound_sources_map[norm_tgt].append({
                "source_url": src,
                "anchor_text": anchor or "[No Text]",
                "rel": rel,
                "source_section": link.get("source_section", "other"),
                "nearest_heading": link.get("nearest_heading"),
                "paragraph_index": link.get("paragraph_index"),
                "sentence_index": link.get("sentence_index"),
                "context_text": link.get("context_text", ""),
                "html_snippet": link.get("html_snippet", "")
            })
            if anchor:
                anchors_map[norm_tgt].append(anchor)

    orphans = []
    dead_ends = []
    deep_pages = []
    overlinked = []
    underlinked = []
    page_metrics: List[Dict[str, Any]] = []

    has_explicit_depth = any(p.get("crawl_depth") is not None or p.get("depth") is not None for p in pages)

    for norm_u, page in page_map.items():
        raw_u = page.get("url") or norm_u
        in_cnt = inbound_counts[norm_u]
        out_cnt = outbound_counts[norm_u]
        uniq_in = len(unique_inbound_sources[norm_u])
        uniq_out = len(unique_outbound_targets[norm_u])
        depth = page.get("crawl_depth") if page.get("crawl_depth") is not None else (page.get("depth") if page.get("depth") is not None else 0)
        
        # Is this the seed URL or homepage root?
        from urllib.parse import urlparse
        is_root_path = urlparse(norm_u).path in ("/", "")
        is_seed = (norm_u == seed_norm) or is_root_path
        if not is_seed and not seed_norm and has_explicit_depth:
            is_seed = (depth == 0)

        # Orphan calculation: 0 incoming links and NOT the seed page
        is_orphan = (in_cnt == 0 and not is_seed)

        page_metric = {
            "url": raw_u,
            "normalized_url": norm_u,
            "title": page.get("title") or "Untitled",
            "status_code": page.get("status_code", 200),
            "incoming_internal_links": in_cnt,
            "outgoing_internal_links": out_cnt,
            "unique_incoming_internal_links": uniq_in,
            "unique_outgoing_internal_links": uniq_out,
            "internal_link_depth": depth,
            "orphan_status": "orphan" if is_orphan else "connected"
        }
        page_metrics.append(page_metric)

        if is_orphan:
            orphans.append({
                "url": raw_u,
                "title": page.get("title") or "Untitled",
                "inbound_count": 0,
                "status": "No incoming internal links discovered within this crawl scope",
                "status_code": page.get("status_code", 200)
            })
        elif in_cnt <= 1 and not is_seed:
            underlinked.append({
                "url": raw_u,
                "title": page.get("title") or "Untitled",
                "inbound_count": in_cnt,
                "status_code": page.get("status_code", 200)
            })
        elif in_cnt > 20:
            overlinked.append({
                "url": raw_u,
                "title": page.get("title") or "Untitled",
                "inbound_count": in_cnt,
                "status_code": page.get("status_code", 200)
            })

        # Dead-end pages (0 outbound internal links)
        if out_cnt == 0:
            dead_ends.append({
                "url": raw_u,
                "title": page.get("title") or "Untitled",
                "status_code": page.get("status_code", 200)
            })

        # Deep pages (depth > 3)
        if depth > 3:
            deep_pages.append({
                "url": raw_u,
                "title": page.get("title") or "Untitled",
                "crawl_depth": depth,
                "status_code": page.get("status_code", 200)
            })

    return {
        "total_nodes": len(page_map),
        "total_edges": sum(outbound_counts.values()),
        "page_metrics": page_metrics,
        "inbound_counts": dict(inbound_counts),
        "outbound_counts": dict(outbound_counts),
        "unique_inbound_counts": {k: len(v) for k, v in unique_inbound_sources.items()},
        "unique_outbound_counts": {k: len(v) for k, v in unique_outbound_targets.items()},
        "inbound_sources_map": dict(inbound_sources_map),
        "orphan_pages_count": len(orphans),
        "orphan_pages": orphans,
        "dead_end_pages_count": len(dead_ends),
        "dead_end_pages": dead_ends[:50],
        "deep_pages_count": len(deep_pages),
        "deep_pages": deep_pages[:50],
        "underlinked_pages_count": len(underlinked),
        "underlinked_pages": underlinked[:20],
        "overlinked_pages_count": len(overlinked),
        "overlinked_pages": overlinked[:20]
    }


def get_incoming_links_for_page(
    target_url: str,
    link_records: Optional[List[Dict[str, Any]]] = None,
    internal_links: Optional[List[Dict[str, Any]]] = None,
    pages: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Returns all incoming links to target_url with rich location, context, and source status.
    """
    if not target_url:
        return []

    norm_target = normalize_graph_url(target_url)
    page_status_map = {normalize_graph_url(p.get("url", "")): p.get("status_code", 200) for p in (pages or []) if p.get("url")}

    results: List[Dict[str, Any]] = []

    if link_records:
        for rec in link_records:
            tgt = rec.get("normalized_target_url") or normalize_graph_url(rec.get("target_url") or rec.get("target"))
            if tgt == norm_target:
                src = rec.get("source_url") or rec.get("source") or ""
                norm_src = rec.get("normalized_source_url") or normalize_graph_url(src)
                results.append({
                    "id": rec.get("id") or str(uuid.uuid4()),
                    "source_url": src,
                    "target_url": rec.get("target_url") or rec.get("target") or target_url,
                    "anchor_text": rec.get("anchor_text") or "[No Anchor Text]",
                    "link_type": rec.get("link_type") or ("internal" if rec.get("is_internal") else "external"),
                    "link_scope": rec.get("link_scope") or "internal",
                    "rel": rec.get("rel") or "follow",
                    "source_section": rec.get("source_section", "other"),
                    "nearest_heading": rec.get("nearest_heading"),
                    "heading_level": rec.get("heading_level"),
                    "paragraph_index": rec.get("paragraph_index"),
                    "sentence_index": rec.get("sentence_index"),
                    "context_before": rec.get("context_before", ""),
                    "context_text": rec.get("context_text", ""),
                    "context_after": rec.get("context_after", ""),
                    "html_snippet": rec.get("html_snippet", ""),
                    "source_status": page_status_map.get(norm_src, 200)
                })
    elif internal_links:
        for link in internal_links:
            tgt = normalize_graph_url(link.get("target_url") or link.get("target") or link.get("destination_url"))
            if tgt == norm_target:
                src = link.get("source_url") or link.get("source") or ""
                norm_src = normalize_graph_url(src)
                results.append({
                    "id": link.get("id") or str(uuid.uuid4()),
                    "source_url": src,
                    "target_url": link.get("target") or target_url,
                    "anchor_text": link.get("anchor_text") or "[No Anchor Text]",
                    "link_type": "internal",
                    "link_scope": "internal",
                    "rel": link.get("rel") or "follow",
                    "source_section": link.get("source_section", "other"),
                    "nearest_heading": link.get("nearest_heading"),
                    "heading_level": link.get("heading_level"),
                    "paragraph_index": link.get("paragraph_index"),
                    "sentence_index": link.get("sentence_index"),
                    "context_before": link.get("context_before", ""),
                    "context_text": link.get("context_text", ""),
                    "context_after": link.get("context_after", ""),
                    "html_snippet": link.get("html_snippet", ""),
                    "source_status": page_status_map.get(norm_src, 200)
                })

    return results


def get_outgoing_links_for_page(
    source_url: str,
    link_records: Optional[List[Dict[str, Any]]] = None,
    internal_links: Optional[List[Dict[str, Any]]] = None,
    external_links: Optional[List[Dict[str, Any]]] = None,
    pages: Optional[List[Dict[str, Any]]] = None
) -> List[Dict[str, Any]]:
    """
    Returns all outgoing links from source_url with target status, location, and context.
    """
    if not source_url:
        return []

    norm_source = normalize_graph_url(source_url)
    page_status_map = {normalize_graph_url(p.get("url", "")): p.get("status_code", 200) for p in (pages or []) if p.get("url")}

    results: List[Dict[str, Any]] = []

    if link_records:
        for rec in link_records:
            src = rec.get("normalized_source_url") or normalize_graph_url(rec.get("source_url") or rec.get("source"))
            if src == norm_source:
                tgt = rec.get("target_url") or rec.get("target") or ""
                norm_tgt = rec.get("normalized_target_url") or normalize_graph_url(tgt)
                is_int = rec.get("is_internal") if rec.get("is_internal") is not None else (rec.get("link_scope") == "internal")
                tgt_status = rec.get("status_code") or (page_status_map.get(norm_tgt, 200) if is_int else None)
                
                results.append({
                    "id": rec.get("id") or str(uuid.uuid4()),
                    "target_url": tgt,
                    "anchor_text": rec.get("anchor_text") or "[No Anchor Text]",
                    "link_type": rec.get("link_type") or ("internal" if is_int else "external"),
                    "link_scope": "internal" if is_int else "external",
                    "rel": rec.get("rel") or "follow",
                    "target_status": tgt_status,
                    "source_section": rec.get("source_section", "other"),
                    "nearest_heading": rec.get("nearest_heading"),
                    "heading_level": rec.get("heading_level"),
                    "paragraph_index": rec.get("paragraph_index"),
                    "sentence_index": rec.get("sentence_index"),
                    "context_before": rec.get("context_before", ""),
                    "context_text": rec.get("context_text", ""),
                    "context_after": rec.get("context_after", ""),
                    "html_snippet": rec.get("html_snippet", "")
                })
    else:
        # Fallback to internal_links + external_links
        for link in (internal_links or []):
            src = normalize_graph_url(link.get("source_url") or link.get("source"))
            if src == norm_source:
                tgt = link.get("target_url") or link.get("target") or ""
                norm_tgt = normalize_graph_url(tgt)
                results.append({
                    "id": link.get("id") or str(uuid.uuid4()),
                    "target_url": tgt,
                    "anchor_text": link.get("anchor_text") or "[No Anchor Text]",
                    "link_type": "internal",
                    "link_scope": "internal",
                    "rel": link.get("rel") or "follow",
                    "target_status": page_status_map.get(norm_tgt, 200),
                    "source_section": link.get("source_section", "other"),
                    "nearest_heading": link.get("nearest_heading"),
                    "heading_level": link.get("heading_level"),
                    "paragraph_index": link.get("paragraph_index"),
                    "sentence_index": link.get("sentence_index"),
                    "context_before": link.get("context_before", ""),
                    "context_text": link.get("context_text", ""),
                    "context_after": link.get("context_after", ""),
                    "html_snippet": link.get("html_snippet", "")
                })
        for link in (external_links or []):
            src = normalize_graph_url(link.get("source_url") or link.get("source"))
            if src == norm_source:
                tgt = link.get("target_url") or link.get("target") or ""
                results.append({
                    "id": link.get("id") or str(uuid.uuid4()),
                    "target_url": tgt,
                    "anchor_text": link.get("anchor_text") or "[External Link]",
                    "link_type": "external",
                    "link_scope": "external",
                    "rel": link.get("rel") or "follow",
                    "target_status": link.get("status_code"),
                    "source_section": link.get("source_section", "other"),
                    "nearest_heading": link.get("nearest_heading"),
                    "heading_level": link.get("heading_level"),
                    "paragraph_index": link.get("paragraph_index"),
                    "sentence_index": link.get("sentence_index"),
                    "context_before": link.get("context_before", ""),
                    "context_text": link.get("context_text", ""),
                    "context_after": link.get("context_after", ""),
                    "html_snippet": link.get("html_snippet", "")
                })

    return results


def get_link_detail(
    link_id: str,
    link_records: Optional[List[Dict[str, Any]]] = None
) -> Optional[Dict[str, Any]]:
    """
    Returns complete LinkRecord evidence for a specific link ID.
    """
    if not link_id or not link_records:
        return None
    for rec in link_records:
        if str(rec.get("id")) == str(link_id):
            return rec
    return None


def get_inbound_sources_for_url(
    target_url: str,
    internal_links: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Legacy helper: Returns list of source pages linking to target_url with anchor text and rel.
    """
    if not target_url or not internal_links:
        return []
    clean_target = normalize_graph_url(target_url)
    sources = []
    for link in internal_links:
        tgt = normalize_graph_url(link.get("destination_url") or link.get("target_url") or link.get("target") or link.get("href"))
        if tgt == clean_target:
            sources.append({
                "source_url": link.get("source_url") or link.get("source") or "",
                "anchor_text": link.get("anchor_text") or link.get("anchor") or "[No Text]",
                "rel": link.get("rel") or "follow"
            })
    return sources
