import json
import hashlib
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.models.action_opportunity import ActionOpportunity


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


def generate_stable_opp_id(project_id: str, category: str, unique_key: str) -> str:
    """
    Generates a deterministic stable ID for an opportunity so status persists across crawls.
    """
    raw = f"{project_id}:{category.lower()}:{unique_key.strip().lower()}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
    return f"opp_{category.lower()[:4]}_{digest}"


def generate_central_opportunities(
    audit_results: Dict[str, Any],
    keywords: List[Dict[str, Any]],
    pages: List[Dict[str, Any]],
    project_id: Optional[str] = None,
    internal_links: Optional[List[Dict[str, Any]]] = None,
    graph_data: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Generates central action center opportunities across categories:
    Technical, Content, Keywords, Internal Links, Backlinks, Competitors.
    Evidence-based ONLY: does not invent backlink or competitor data if not present.
    """
    pid = project_id or "default_project"
    opps = []

    # 1. Technical Audit Opportunities
    for issue in audit_results.get("issues", []):
        aff_cnt = issue.get("affected_count", len(issue.get("affected_urls", []))) or 1
        rule_id = issue.get("rule_id", issue.get("issue_type", "tech_rule"))
        calc = compute_priority_score(issue.get("severity", "warning"), aff_cnt)
        opp_id = generate_stable_opp_id(pid, "technical", str(rule_id))

        opps.append({
            "id": opp_id,
            "title": issue.get("title") or f"Fix Technical SEO Issue: {rule_id}",
            "category": "Technical",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"Affects {aff_cnt} page(s). Requires technical fix.",
            "evidence": issue.get("evidence") or f"Detected in audit rule {rule_id}",
            "affected_urls": issue.get("affected_urls", []),
            "affected_count": aff_cnt,
            "recommendation": issue.get("recommendation") or "Review and correct the identified technical issue on affected URLs.",
            "status": "Open",
            "data_source": "Site Audit Rule Engine"
        })

    # 2. Content Opportunities (Missing Meta Descriptions, Missing H1s, Thin Content)
    missing_desc = [p for p in pages if not p.get("meta_description") and p.get("status_code") == 200]
    if missing_desc:
        calc = compute_priority_score("warning", len(missing_desc))
        opp_id = generate_stable_opp_id(pid, "content", "missing_meta_descriptions")
        opps.append({
            "id": opp_id,
            "title": "Pages Missing Meta Descriptions",
            "category": "Content",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"{len(missing_desc)} pages lack search snippet metadata.",
            "evidence": f"Missing on URLs: {', '.join([p.get('url', '') for p in missing_desc[:3]])}",
            "affected_urls": [p.get("url") for p in missing_desc],
            "affected_count": len(missing_desc),
            "recommendation": "Add descriptive, click-worthy meta descriptions (120-160 chars) to improve CTR in search results.",
            "status": "Open",
            "data_source": "Crawl HTML Parser"
        })

    missing_h1 = [p for p in pages if not p.get("h1") and p.get("status_code") == 200]
    if missing_h1:
        calc = compute_priority_score("warning", len(missing_h1))
        opp_id = generate_stable_opp_id(pid, "content", "missing_h1_tags")
        opps.append({
            "id": opp_id,
            "title": "Pages Missing H1 Heading Tags",
            "category": "Content",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"{len(missing_h1)} pages lack a primary H1 heading.",
            "evidence": f"Missing on URLs: {', '.join([p.get('url', '') for p in missing_h1[:3]])}",
            "affected_urls": [p.get("url") for p in missing_h1],
            "affected_count": len(missing_h1),
            "recommendation": "Include exactly one descriptive H1 tag per page representing the main topic.",
            "status": "Open",
            "data_source": "Crawl HTML Parser"
        })

    # 3. Keyword Opportunities (Striking distance #11 - #20)
    striking = [k for k in keywords if k.get("position") and 11 <= k.get("position") <= 20]
    if striking:
        calc = compute_priority_score("critical", len(striking))
        opp_id = generate_stable_opp_id(pid, "keywords", "striking_distance_keywords")
        opps.append({
            "id": opp_id,
            "title": "Striking Distance Keywords (#11 - #20)",
            "category": "Keywords",
            "priority_score": calc["score"],
            "priority_level": calc["level"],
            "impact": f"{len(striking)} keywords are on Page 2 of Google search results.",
            "evidence": f"Terms: {', '.join([k.get('keyword', '') for k in striking[:4]])}",
            "affected_urls": [k.get("target_url") for k in striking if k.get("target_url")],
            "affected_count": len(striking),
            "recommendation": "Optimize heading tags, body copy, and add internal links targeting Page 2 keywords.",
            "status": "Open",
            "data_source": "Rank Tracker Dataset"
        })

    # 4. Internal Link Opportunities (Orphan pages & Underlinked pages)
    if graph_data:
        orphans = graph_data.get("orphan_pages", [])
        if orphans:
            calc = compute_priority_score("critical", len(orphans))
            opp_id = generate_stable_opp_id(pid, "internal_links", "orphan_pages_linking")
            opps.append({
                "id": opp_id,
                "title": "Resolve Orphan Pages With Internal Links",
                "category": "Internal Links",
                "priority_score": calc["score"],
                "priority_level": calc["level"],
                "impact": f"{len(orphans)} crawled pages have zero incoming internal links.",
                "evidence": f"Orphan URLs: {', '.join([o.get('url', '') for o in orphans[:3]])}",
                "affected_urls": [o.get("url") for o in orphans],
                "affected_count": len(orphans),
                "recommendation": "Add contextual internal links from relevant high-authority pages to integrate orphan URLs into site navigation.",
                "status": "Open",
                "data_source": "Link Graph Engine"
            })

    # Sort opportunities by priority score descending
    opps.sort(key=lambda x: x["priority_score"], reverse=True)
    return opps


def sync_project_opportunities(
    db: Session,
    project_id: str,
    audit_results: Dict[str, Any],
    keywords: List[Dict[str, Any]],
    pages: List[Dict[str, Any]],
    internal_links: Optional[List[Dict[str, Any]]] = None,
    graph_data: Optional[Dict[str, Any]] = None
) -> List[ActionOpportunity]:
    """
    Deterministic opportunity synchronization:
    - Evaluates opportunities from real crawl/keyword evidence.
    - Preserves user-assigned lifecycle states (In Progress, Resolved, Ignored).
    - Updates evidence, impact, affected URLs, and priority scores on existing opportunities.
    - Inserts new opportunities as 'Open'.
    """
    generated = generate_central_opportunities(
        audit_results=audit_results,
        keywords=keywords,
        pages=pages,
        project_id=project_id,
        internal_links=internal_links,
        graph_data=graph_data
    )

    existing_opps = {o.id: o for o in db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project_id).all()}

    for item in generated:
        opp_id = item["id"]
        if opp_id in existing_opps:
            # Update evidence and metrics while strictly PRESERVING user status
            existing = existing_opps[opp_id]
            existing.title = item["title"]
            existing.category = item["category"]
            existing.priority_score = item["priority_score"]
            existing.priority_level = item["priority_level"]
            existing.impact = item["impact"]
            existing.evidence = item["evidence"]
            existing.affected_urls_json = json.dumps(item.get("affected_urls", []))
            existing.affected_count = item.get("affected_count", 1)
            existing.recommendation = item["recommendation"]
            existing.updated_at = datetime.utcnow()
        else:
            # Create new opportunity with status 'Open'
            new_opp = ActionOpportunity(
                id=opp_id,
                project_id=project_id,
                title=item["title"],
                category=item["category"],
                priority_score=item["priority_score"],
                priority_level=item["priority_level"],
                impact=item["impact"],
                evidence=item["evidence"],
                affected_urls_json=json.dumps(item.get("affected_urls", [])),
                affected_count=item.get("affected_count", 1),
                recommendation=item["recommendation"],
                status="Open",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(new_opp)

    db.commit()
    return db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project_id).all()
