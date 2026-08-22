from typing import List, Dict, Any, Set
from collections import defaultdict

def build_internal_link_graph(pages: List[Dict[str, Any]], internal_links: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Builds a deterministic internal link graph from crawl evidence.
    Calculates inbound/outbound link counts, click depth, orphan pages, and link opportunities.
    """
    url_set: Set[str] = {p.get("url") for p in pages if p.get("url")}
    inbound_counts: Dict[str, int] = defaultdict(int)
    outbound_counts: Dict[str, int] = defaultdict(int)
    link_map: Dict[str, List[str]] = defaultdict(list)
    anchors_map: Dict[str, List[str]] = defaultdict(list)

    for link in internal_links:
        src = link.get("source")
        tgt = link.get("target")
        anchor = link.get("anchor_text", "").strip()

        if src and tgt:
            outbound_counts[src] += 1
            inbound_counts[tgt] += 1
            link_map[src].append(tgt)
            if anchor:
                anchors_map[tgt].append(anchor)

    orphans = []
    overlinked = []
    underlinked = []

    for page in pages:
        u = page.get("url")
        if not u: continue
        in_cnt = inbound_counts[u]
        out_cnt = outbound_counts[u]

        # Root URL is not an orphan
        if in_cnt == 0 and not u.endswith("/"):
            orphans.append({"url": u, "title": page.get("title")})
        elif in_cnt <= 1 and not u.endswith("/"):
            underlinked.append({"url": u, "title": page.get("title"), "inbound_count": in_cnt})
        elif in_cnt > 20:
            overlinked.append({"url": u, "title": page.get("title"), "inbound_count": in_cnt})

    return {
        "total_nodes": len(url_set),
        "total_edges": len(internal_links),
        "orphan_pages_count": len(orphans),
        "orphan_pages": orphans,
        "underlinked_pages_count": len(underlinked),
        "underlinked_pages": underlinked[:10],
        "overlinked_pages_count": len(overlinked),
        "overlinked_pages": overlinked[:10]
    }
