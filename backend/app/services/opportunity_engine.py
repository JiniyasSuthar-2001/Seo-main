import json
from typing import List, Dict, Any

def compute_priority_score(severity: str, affected_count: int, confidence: float = 100.0) -> Dict[str, Any]:
    """
    Computes deterministic opportunity priority score based on formula:
    Priority Score = (Severity Weight * 0.4) + (min(100, Affected Pages * 5) * 0.3) + (Confidence * 0.3)
    """
    sev_map = {
        "critical": 100.0,
        "error": 80.0,
        "warning": 60.0,
        "notice": 40.0,
        "info": 20.0
    }
    sev_weight = sev_map.get(severity.lower(), 50.0)
    page_weight = min(100.0, affected_count * 5.0)
    conf_weight = min(100.0, max(0.0, confidence))

    score = round((sev_weight * 0.4) + (page_weight * 0.3) + (conf_weight * 0.3), 1)

    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 40:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": score,
        "level": level
    }


def generate_central_opportunities(audit_results: Dict[str, Any], keywords: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates central action center opportunities across 6 categories:
    Technical, Content, Keywords, Internal Links, Backlinks, Competitors.
    """
    opps = []

    # 1. Technical Audit Opportunities
    for issue in audit_results.get("issues", []):
        aff_cnt = issue.get("affected_count", 1)
        calc = compute_priority_score(issue.get("severity", "warning"), aff_cnt)
        opps.append({
            "id": f"opp_tech_{issue.get('rule_id', '001')}",
            "title": issue.get("title"),
            "category": "Technical",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"Affects {aff_cnt} page(s). Requires technical fix.",
            "evidence": issue.get("evidence"),
            "affected_urls": issue.get("affected_urls", []),
            "affected_count": aff_cnt,
            "recommendation": issue.get("recommendation"),
            "status": "Open",
            "data_source": "Site Audit Rule Engine"
        })

    # 2. Content Opportunities (Thin content & Missing Meta)
    missing_desc = [p for p in pages if not p.get("meta_description")]
    if missing_desc:
        calc = compute_priority_score("warning", len(missing_desc))
        opps.append({
            "id": "opp_cont_meta_desc",
            "title": "Pages Missing Meta Descriptions",
            "category": "Content",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"{len(missing_desc)} pages lack search snippet metadata.",
            "evidence": f"Missing on URLs: {', '.join([p.get('url', '') for p in missing_desc[:3]])}",
            "affected_urls": [p.get("url") for p in missing_desc],
            "affected_count": len(missing_desc),
            "recommendation": "Add descriptive meta descriptions to improve CTR in search results.",
            "status": "Open",
            "data_source": "Crawl HTML Parser"
        })

    # 3. Keyword Opportunities (Striking distance 11-20)
    striking = [k for k in keywords if k.get("position") and 11 <= k.get("position") <= 20]
    if striking:
        calc = compute_priority_score("critical", len(striking))
        opps.append({
            "id": "opp_kw_striking",
            "title": "Striking Distance Keywords (#11 - #20)",
            "category": "Keywords",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"{len(striking)} keywords are on Page 2 of Google results.",
            "evidence": f"Terms: {', '.join([k.get('keyword', '') for k in striking[:4]])}",
            "affected_urls": [k.get("target_url") for k in striking if k.get("target_url")],
            "affected_count": len(striking),
            "recommendation": "Optimize heading tags and add internal links targeting Page 2 keywords.",
            "status": "Open",
            "data_source": "Rank Tracker Dataset"
        })

    # Sort opportunities by priority score descending
    opps.sort(key=lambda x: x["priority_score"], reverse=True)
    return opps
