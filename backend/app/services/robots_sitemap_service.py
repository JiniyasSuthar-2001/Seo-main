from typing import Dict, Any, List, Optional


class RobotsSitemapService:
    """
    Extracts and standardizes robots.txt rules, directives, user-agent restrictions, and sitemap references.
    """

    @classmethod
    def evaluate_robots_evidence(cls, pages: List[Dict[str, Any]], domain: Optional[str] = None) -> Dict[str, Any]:
        noindex_pages = [p for p in (pages or []) if p.get("is_noindex") or "noindex" in (p.get("meta_robots") or "").lower()]
        disallowed_pages = [p for p in (pages or []) if p.get("is_blocked_by_robots_txt")]
        sitemap_found = any("sitemap" in (p.get("url") or "").lower() for p in (pages or []))

        robots_evidence = []
        for p in (pages or []):
            is_noindex = p.get("is_noindex") or "noindex" in (p.get("meta_robots") or "").lower()
            is_disallowed = p.get("is_blocked_by_robots_txt", False)
            if is_noindex or is_disallowed:
                robots_evidence.append({
                    "url": p.get("url"),
                    "noindex_directive": is_noindex,
                    "disallowed_by_robots_txt": is_disallowed,
                    "robots_meta_content": p.get("meta_robots", ""),
                    "status_code": p.get("status_code")
                })

        return {
            "domain": domain or "unknown",
            "robots_txt_status": "Evaluated",
            "sitemap_referenced": sitemap_found,
            "total_noindex_pages": len(noindex_pages),
            "total_disallowed_pages": len(disallowed_pages),
            "robots_summary": {
                "has_noindex_rules": len(noindex_pages) > 0,
                "has_disallow_rules": len(disallowed_pages) > 0,
                "noindex_count": len(noindex_pages),
                "disallowed_count": len(disallowed_pages)
            },
            "robots_evidence": robots_evidence
        }
