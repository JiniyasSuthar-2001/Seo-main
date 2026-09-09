from typing import List, Dict, Any, Set, Optional
from collections import defaultdict

def build_internal_link_graph(pages: List[Dict[str, Any]], internal_links: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a deterministic internal link graph from crawl evidence.
    Calculates:
    - Inbound internal links per page
    - Outbound internal links per page
    - Click depth from seed
    - Reverse link mappings (inbound source pages & anchors)
    - Orphan candidates (pages with 0 inbound links within this crawl scope)
    - Dead-end pages (pages with 0 outbound links)
    - Deep pages (depth > 3)
    """
    url_set: Set[str] = {p.get("url") for p in pages if p.get("url")}
    inbound_counts: Dict[str, int] = defaultdict(int)
    outbound_counts: Dict[str, int] = defaultdict(int)
    link_map: Dict[str, List[str]] = defaultdict(list)
    anchors_map: Dict[str, List[str]] = defaultdict(list)
    inbound_sources_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for link in internal_links:
        src = link.get("source_url") or link.get("source")
        tgt = link.get("destination_url") or link.get("target_url") or link.get("target") or link.get("href")
        anchor = (link.get("anchor_text") or link.get("anchor") or "").strip()
        rel = link.get("rel") or "follow"

        if src and tgt:
            outbound_counts[src] += 1
            inbound_counts[tgt] += 1
            link_map[src].append(tgt)
            inbound_sources_map[tgt].append({
                "source_url": src,
                "anchor_text": anchor or "[No Text]",
                "rel": rel
            })
            if anchor:
                anchors_map[tgt].append(anchor)

    orphans = []
    dead_ends = []
    deep_pages = []
    overlinked = []
    underlinked = []

    for page in pages:
        u = page.get("url")
        if not u:
            continue
        in_cnt = inbound_counts[u]
        out_cnt = outbound_counts[u]
        depth = page.get("crawl_depth") or 0

        # Non-seed page with 0 discovered inbound links within this crawl scope
        if in_cnt == 0 and not u.endswith("/"):
            orphans.append({
                "url": u,
                "title": page.get("title") or "Untitled",
                "inbound_count": 0,
                "status": "No incoming internal links discovered within this crawl scope",
                "status_code": page.get("status_code", 200)
            })
        elif in_cnt <= 1 and not u.endswith("/"):
            underlinked.append({
                "url": u,
                "title": page.get("title") or "Untitled",
                "inbound_count": in_cnt,
                "status_code": page.get("status_code", 200)
            })
        elif in_cnt > 20:
            overlinked.append({
                "url": u,
                "title": page.get("title") or "Untitled",
                "inbound_count": in_cnt,
                "status_code": page.get("status_code", 200)
            })

        # Dead-end pages (0 outbound internal links)
        if out_cnt == 0:
            dead_ends.append({
                "url": u,
                "title": page.get("title") or "Untitled",
                "status_code": page.get("status_code", 200)
            })

        # Deep pages (depth > 3)
        if depth > 3:
            deep_pages.append({
                "url": u,
                "title": page.get("title") or "Untitled",
                "crawl_depth": depth,
                "status_code": page.get("status_code", 200)
            })

    return {
        "total_nodes": len(url_set),
        "total_edges": len(internal_links),
        "inbound_counts": dict(inbound_counts),
        "outbound_counts": dict(outbound_counts),
        "inbound_sources_map": dict(inbound_sources_map),
        "orphan_pages_count": len(orphans),
        "orphan_pages": orphans,
        "dead_end_pages_count": len(dead_ends),
        "dead_end_pages": dead_ends[:20],
        "deep_pages_count": len(deep_pages),
        "deep_pages": deep_pages[:20],
        "underlinked_pages_count": len(underlinked),
        "underlinked_pages": underlinked[:10],
        "overlinked_pages_count": len(overlinked),
        "overlinked_pages": overlinked[:10]
    }


def get_inbound_sources_for_url(target_url: str, internal_links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Returns list of source pages linking to target_url with anchor text and rel.
    """
    if not target_url:
        return []
    clean_target = target_url.strip().lower()
    sources = []
    for link in internal_links:
        tgt = (link.get("destination_url") or link.get("target_url") or link.get("target") or link.get("href") or "").strip().lower()
        if tgt == clean_target:
            sources.append({
                "source_url": link.get("source_url") or link.get("source") or "",
                "anchor_text": link.get("anchor_text") or link.get("anchor") or "[No Text]",
                "rel": link.get("rel") or "follow"
            })
    return sources
