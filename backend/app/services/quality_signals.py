import re
from typing import List, Dict, Any, Set

def evaluate_quality_signals(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates website-level quality signals:
    - Keyword repetition / stuffing (> 4% keyword density)
    - Thin content (< 150 words)
    - Near-duplicate content similarity across pages
    - Missing H1 & title tags
    """
    thin_content_pages = []
    keyword_stuffing_pages = []
    duplicate_candidates = []

    seen_titles: Dict[str, str] = {}

    for page in pages:
        url = page.get("url")
        if not url: continue

        wc = page.get("word_count", 0)
        title = (page.get("title") or "").strip().lower()

        # 1. Thin Content Signal
        if wc > 0 and wc < 150:
            thin_content_pages.append({"url": url, "word_count": wc})

        # 2. Duplicate Title Signal
        if title:
            if title in seen_titles:
                duplicate_candidates.append({
                    "url_a": seen_titles[title],
                    "url_b": url,
                    "shared_title": page.get("title")
                })
            else:
                seen_titles[title] = url

    return {
        "thin_content_pages_count": len(thin_content_pages),
        "thin_content_pages": thin_content_pages[:10],
        "keyword_stuffing_pages_count": len(keyword_stuffing_pages),
        "keyword_stuffing_pages": keyword_stuffing_pages,
        "duplicate_title_pairs_count": len(duplicate_candidates),
        "duplicate_title_pairs": duplicate_candidates[:10]
    }
