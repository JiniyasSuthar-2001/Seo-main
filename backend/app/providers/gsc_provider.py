import os
import urllib.parse
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import httpx

from app.providers.base import BaseSearchConsoleProvider
from app.config.settings import settings

class GoogleSearchConsoleProvider(BaseSearchConsoleProvider):
    """
    Google Search Console Provider implementing BaseSearchConsoleProvider.
    Queries official Google Search Analytics API v3 using authentic OAuth2 bearer tokens.
    Never fabricates impressions, clicks, CTR, or position metrics.
    """
    SEARCH_ANALYTICS_ENDPOINT = "https://www.googleapis.com/webmasters/v3/sites/{site_url}/searchAnalytics/query"

    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def get_search_analytics(
        self,
        site_url: str,
        days: int = 30,
        access_token: Optional[str] = None,
        dimensions: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves authentic search analytics rows (queries, pages, clicks, impressions, CTR, position).
        """
        if not access_token or not access_token.strip():
            return []

        dims = dimensions or ["query", "page"]
        end_date = datetime.utcnow().date() - timedelta(days=2) # GSC data typically has a 2-day lag
        start_date = end_date - timedelta(days=days)

        encoded_site = urllib.parse.quote_plus(site_url)
        url = self.SEARCH_ANALYTICS_ENDPOINT.format(site_url=encoded_site)

        payload = {
            "startDate": start_date.isoformat(),
            "endDate": end_date.isoformat(),
            "dimensions": dims,
            "rowLimit": 500
        }

        headers = {
            "Authorization": f"Bearer {access_token.strip()}",
            "Content-Type": "application/json"
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                res = client.post(url, json=payload, headers=headers)
                if res.status_code == 200:
                    data = res.json()
                    rows = data.get("rows", [])
                    results = []
                    for r in rows:
                        keys = r.get("keys", [])
                        q_val = keys[0] if len(keys) > 0 else ""
                        p_val = keys[1] if len(keys) > 1 else (keys[0] if "page" in dims else "")
                        
                        clicks = r.get("clicks", 0)
                        impressions = r.get("impressions", 0)
                        ctr = round(r.get("ctr", 0.0) * 100, 2)
                        pos = round(r.get("position", 0.0), 1)

                        results.append({
                            "query": q_val,
                            "page": p_val,
                            "clicks": clicks,
                            "impressions": impressions,
                            "ctr": ctr,
                            "position": pos,
                            "start_date": start_date.isoformat(),
                            "end_date": end_date.isoformat()
                        })
                    return results
                else:
                    return []
        except Exception:
            return []

    @staticmethod
    def calculate_page_priorities(
        pages: List[Dict[str, Any]],
        gsc_data: List[Dict[str, Any]],
        audit_issues: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Deterministic Page Prioritization Model combining Crawler Data + GSC Search Performance.
        
        Formula:
          Priority Score (0-100) = (Impressions_Score * 0.40) + (CTR_Gap_Score * 0.30) + (SEO_Issues_Penalty * 0.30)
          
        Rationale:
          - High impressions with below-average CTR (< 2.0%) indicates high organic search demand with weak snippet/title.
          - High-traffic or high-visibility pages with critical/warning SEO issues represent immediate ROI opportunities.
        """
        if not pages:
            return []

        # Aggregate GSC metrics per page URL
        gsc_page_map: Dict[str, Dict[str, Any]] = {}
        for row in (gsc_data or []):
            p_url = (row.get("page") or "").strip().rstrip("/")
            if not p_url:
                continue
            if p_url not in gsc_page_map:
                gsc_page_map[p_url] = {
                    "clicks": 0,
                    "impressions": 0,
                    "queries": [],
                    "weighted_pos_sum": 0.0
                }
            entry = gsc_page_map[p_url]
            entry["clicks"] += row.get("clicks", 0)
            entry["impressions"] += row.get("impressions", 0)
            entry["weighted_pos_sum"] += (row.get("position", 0) * row.get("impressions", 0))
            if row.get("query") and row.get("query") not in entry["queries"]:
                entry["queries"].append(row.get("query"))

        # Map audit issues to affected URLs
        issue_map: Dict[str, List[Dict[str, Any]]] = {}
        for issue in (audit_issues or []):
            for u in (issue.get("affected_urls") or []):
                norm_u = u.strip().rstrip("/")
                issue_map.setdefault(norm_u, []).append(issue)

        max_impressions = max([e["impressions"] for e in gsc_page_map.values()], default=1) or 1
        prioritized_pages = []

        for p in pages:
            url = (p.get("url") or "").strip()
            norm_url = url.rstrip("/")
            gsc_stats = gsc_page_map.get(norm_url, {"clicks": 0, "impressions": 0, "queries": [], "weighted_pos_sum": 0.0})
            
            impressions = gsc_stats["impressions"]
            clicks = gsc_stats["clicks"]
            avg_pos = round(gsc_stats["weighted_pos_sum"] / impressions, 1) if impressions > 0 else None
            ctr = round((clicks / impressions) * 100, 2) if impressions > 0 else 0.0

            # 1. Impressions Component (0 to 40 pts)
            imp_ratio = min(1.0, impressions / max_impressions) if impressions > 0 else 0.0
            imp_score = imp_ratio * 40.0

            # 2. CTR Gap Component (0 to 30 pts)
            # If page ranks in top 10 (avg_pos <= 10) but CTR is low (< 2.5%), high opportunity
            ctr_gap_score = 0.0
            if avg_pos and avg_pos <= 10 and impressions >= 10:
                expected_ctr = max(2.5, 30.0 / avg_pos)
                if ctr < expected_ctr:
                    ctr_gap_score = min(30.0, (expected_ctr - ctr) * 4.0)
            elif impressions > 0:
                ctr_gap_score = 5.0

            # 3. SEO Issues Penalty / Remediation Score (0 to 30 pts)
            page_issues = issue_map.get(norm_url, [])
            issue_score = 0.0
            for iss in page_issues:
                sev = iss.get("severity", "notice").lower()
                if sev == "critical":
                    issue_score += 12.0
                elif sev == "error":
                    issue_score += 8.0
                elif sev == "warning":
                    issue_score += 4.0
                else:
                    issue_score += 1.5
            issue_score = min(30.0, issue_score)

            total_priority = round(min(100.0, imp_score + ctr_gap_score + issue_score), 1)

            prioritized_pages.append({
                "url": url,
                "title": p.get("title") or "Untitled Page",
                "priority_score": total_priority,
                "priority_level": "High" if total_priority >= 65 else ("Medium" if total_priority >= 35 else "Low"),
                "gsc_connected": impressions > 0,
                "impressions": impressions if impressions > 0 else "Not Available",
                "clicks": clicks if impressions > 0 else "Not Available",
                "ctr": f"{ctr}%" if impressions > 0 else "Not Available",
                "average_position": avg_pos if avg_pos is not None else "Not Tracked",
                "top_queries": gsc_stats["queries"][:5],
                "issues_count": len(page_issues),
                "critical_issues": sum(1 for i in page_issues if i.get("severity") == "critical"),
                "warning_issues": sum(1 for i in page_issues if i.get("severity") == "warning"),
                "prioritization_formula": "Priority = (Impressions_Score * 0.40) + (CTR_Gap * 0.30) + (SEO_Issues * 0.30)"
            })

        prioritized_pages.sort(key=lambda x: x["priority_score"], reverse=True)
        return prioritized_pages
