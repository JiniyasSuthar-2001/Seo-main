import json
from typing import List, Dict, Any, Optional

def evaluate_site_audit_rules(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates Technical Site Audit Rule Categories across crawled website pages.
    
    EVALUATED CATEGORIES (8):
    1. Crawlability (HTTP 4xx / 5xx status codes)
    2. Indexability (Robots noindex tags)
    3. HTTPS (Insecure HTTP URLs)
    4. Metadata (Missing HTML Title & Meta Description tags)
    5. Content (Thin copy < 150 words)
    6. Headings (Missing <h1> headings)
    7. Canonicals (Missing rel='canonical' tags)
    8. Images (Missing alt text attributes)
    
    UNEVALUATED CATEGORIES (7):
    - Internal Links, External Links, Performance, Structured Data, Mobile, International SEO, Security.
    Unevaluated categories return status 'Not Evaluated' (evaluated=False) and are EXCLUDED from score calculations.
    
    HEALTH SCORE FORMULA:
    total_evaluated_checks = total_pages * 8 (number of evaluated rules)
    total_weighted_penalty = (critical * 3) + (error * 2) + (warning * 1) + (notice * 0.25)
    health_score = max(0, min(100, round(100 - (total_weighted_penalty / total_evaluated_checks * 100))))
    """
    total_pages = len(pages) if pages else 0
    issues = []

    # Category trackers with explicit evaluation state
    categories = {
        "Crawlability": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Indexability": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "HTTPS": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Metadata": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Content": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Headings": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Canonicals": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Images": {"status": "Passed", "evaluated": True, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        # Unevaluated categories requiring specialized external tools or payloads
        "Internal Links": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires full link graph parser payload", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "External Links": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires external link analysis API", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Performance": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires PageSpeed / Core Web Vitals audit engine", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Structured Data": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires Schema.org JSON-LD validator", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Mobile": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires Mobile-Friendly rendering audit engine", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "International SEO": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires hreflang language code validator", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Security": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires SSL Certificate & Header security scanner", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
    }

    if total_pages == 0:
        return {
            "health_score": 100,
            "total_audited_pages": 0,
            "summary": {
                "critical_errors": 0,
                "errors": 0,
                "warnings": 0,
                "notices": 0,
                "passed_checks": 0
            },
            "category_breakdown": categories,
            "issues": [],
            "provenance": {
                "source": "Deterministic 15-Category Site Audit Engine",
                "timestamp": "Real-time Crawl Snapshot Evaluation"
            }
        }

    # 1. Crawlability & HTTP Status (404s & 5xx)
    broken_pages = [p for p in pages if (p.get("status_code") or 200) >= 400]
    if broken_pages:
        issues.append({
            "rule_id": "CRAWL_001",
            "category": "Crawlability",
            "severity": "critical",
            "title": "HTTP 4xx / 5xx Broken Pages",
            "description": f"{len(broken_pages)} audited pages returned broken client/server status codes.",
            "evidence": f"Pages returning HTTP status >= 400: {', '.join([p.get('url', '') for p in broken_pages[:3]])}",
            "affected_urls": [p.get("url") for p in broken_pages],
            "affected_count": len(broken_pages),
            "recommendation": "Fix broken page URLs or implement 301 redirects to active destination pages."
        })
        categories["Crawlability"]["critical"] += len(broken_pages)
        categories["Crawlability"]["status"] = "Issues Found"
    else:
        categories["Crawlability"]["passed"] += total_pages

    # 2. Indexability (Noindex tags)
    noindex_pages = [p for p in pages if "noindex" in (p.get("indexability") or "").lower()]
    if noindex_pages:
        issues.append({
            "rule_id": "INDEX_001",
            "category": "Indexability",
            "severity": "warning",
            "title": "Pages Blocked with 'noindex' Robots Meta Tag",
            "description": f"{len(noindex_pages)} pages contain noindex directives preventing search engine indexing.",
            "evidence": f"URLs: {', '.join([p.get('url', '') for p in noindex_pages[:3]])}",
            "affected_urls": [p.get("url") for p in noindex_pages],
            "affected_count": len(noindex_pages),
            "recommendation": "Remove noindex tag if pages are intended to rank in organic search results."
        })
        categories["Indexability"]["warning"] += len(noindex_pages)
        categories["Indexability"]["status"] = "Issues Found"
    else:
        categories["Indexability"]["passed"] += total_pages

    # 3. HTTPS & Insecure HTTP
    http_pages = [p for p in pages if (p.get("url") or "").startswith("http://")]
    if http_pages:
        issues.append({
            "rule_id": "HTTPS_001",
            "category": "HTTPS",
            "severity": "error",
            "title": "Insecure HTTP Protocol URLs",
            "description": f"{len(http_pages)} pages are served over unencrypted HTTP protocol.",
            "evidence": f"Insecure URLs: {', '.join([p.get('url', '') for p in http_pages[:3]])}",
            "affected_urls": [p.get("url") for p in http_pages],
            "affected_count": len(http_pages),
            "recommendation": "Enforce SSL encryption and redirect HTTP requests to secure HTTPS endpoints."
        })
        categories["HTTPS"]["error"] += len(http_pages)
        categories["HTTPS"]["status"] = "Issues Found"
    else:
        categories["HTTPS"]["passed"] += total_pages

    # 4. Metadata (Missing Title & Meta Description)
    missing_titles = [p for p in pages if not p.get("title") or p.get("title", "").strip() == ""]
    if missing_titles:
        issues.append({
            "rule_id": "META_001",
            "category": "Metadata",
            "severity": "critical",
            "title": "Pages Missing HTML Title Tags",
            "description": f"{len(missing_titles)} pages lack primary HTML title tags required for search relevance.",
            "evidence": f"Affected URLs: {', '.join([p.get('url', '') for p in missing_titles[:3]])}",
            "affected_urls": [p.get("url") for p in missing_titles],
            "affected_count": len(missing_titles),
            "recommendation": "Specify unique 50-60 character title tags for all audited pages."
        })
        categories["Metadata"]["critical"] += len(missing_titles)
        categories["Metadata"]["status"] = "Issues Found"

    missing_desc = [p for p in pages if not p.get("meta_description") or p.get("meta_description", "").strip() == ""]
    if missing_desc:
        issues.append({
            "rule_id": "META_002",
            "category": "Metadata",
            "severity": "warning",
            "title": "Pages Missing Meta Descriptions",
            "description": f"{len(missing_desc)} pages are missing meta descriptions for search snippet optimization.",
            "evidence": f"Affected URLs: {', '.join([p.get('url', '') for p in missing_desc[:3]])}",
            "affected_urls": [p.get("url") for p in missing_desc],
            "affected_count": len(missing_desc),
            "recommendation": "Write compelling 140-160 character meta descriptions summarizing page topic."
        })
        categories["Metadata"]["warning"] += len(missing_desc)
        categories["Metadata"]["status"] = "Issues Found"

    if not missing_titles and not missing_desc:
        categories["Metadata"]["passed"] += total_pages

    # 5. Content (Thin content < 150 words)
    thin_pages = [p for p in pages if (p.get("word_count") or 0) > 0 and (p.get("word_count") or 0) < 150]
    if thin_pages:
        issues.append({
            "rule_id": "CONT_001",
            "category": "Content",
            "severity": "warning",
            "title": "Thin Content Pages (< 150 Words)",
            "description": f"{len(thin_pages)} pages contain minimal body copy, increasing risk of low-quality content flags.",
            "evidence": f"Thin pages: {', '.join([p.get('url', '') for p in thin_pages[:3]])}",
            "affected_urls": [p.get("url") for p in thin_pages],
            "affected_count": len(thin_pages),
            "recommendation": "Expand body copy depth with relevant topic headings and helpful content."
        })
        categories["Content"]["warning"] += len(thin_pages)
        categories["Content"]["status"] = "Issues Found"
    else:
        categories["Content"]["passed"] += total_pages

    # 6. Headings (Missing H1)
    missing_h1 = [p for p in pages if not (p.get("h1") if isinstance(p.get("h1"), list) else str(p.get("h1") or "").strip())]
    if missing_h1:
        issues.append({
            "rule_id": "HEAD_001",
            "category": "Headings",
            "severity": "warning",
            "title": "Pages Missing Main H1 Heading",
            "description": f"{len(missing_h1)} pages lack a primary <h1> heading element.",
            "evidence": f"URLs: {', '.join([p.get('url', '') for p in missing_h1[:3]])}",
            "affected_urls": [p.get("url") for p in missing_h1],
            "affected_count": len(missing_h1),
            "recommendation": "Include exactly one descriptive <h1> tag matching the page topic."
        })
        categories["Headings"]["warning"] += len(missing_h1)
        categories["Headings"]["status"] = "Issues Found"
    else:
        categories["Headings"]["passed"] += total_pages

    # 7. Canonicals (Missing Canonical Tag)
    missing_canon = [p for p in pages if not p.get("canonical") or p.get("canonical", "").strip() == ""]
    if missing_canon:
        issues.append({
            "rule_id": "CANON_001",
            "category": "Canonicals",
            "severity": "notice",
            "title": "Pages Missing Self-Referential Canonical Tag",
            "description": f"{len(missing_canon)} pages do not specify a rel='canonical' Link tag.",
            "evidence": f"URLs: {', '.join([p.get('url', '') for p in missing_canon[:3]])}",
            "affected_urls": [p.get("url") for p in missing_canon],
            "affected_count": len(missing_canon),
            "recommendation": "Add canonical link tags to establish authoritative URLs."
        })
        categories["Canonicals"]["notice"] += len(missing_canon)
        categories["Canonicals"]["status"] = "Issues Found"
    else:
        categories["Canonicals"]["passed"] += total_pages

    # 8. Images (Missing Alt Text)
    missing_alt_pages = [p for p in pages if p.get("images_missing_alt") and len(p.get("images_missing_alt", [])) > 0]
    if missing_alt_pages:
        issues.append({
            "rule_id": "IMG_001",
            "category": "Images",
            "severity": "notice",
            "title": "Images Missing Descriptive Alt Text",
            "description": f"{len(missing_alt_pages)} pages contain image tags missing descriptive alt text attributes.",
            "evidence": f"URLs: {', '.join([p.get('url', '') for p in missing_alt_pages[:3]])}",
            "affected_urls": [p.get("url") for p in missing_alt_pages],
            "affected_count": len(missing_alt_pages),
            "recommendation": "Add descriptive alt attributes to all content images for accessibility and image SEO."
        })
        categories["Images"]["notice"] += len(missing_alt_pages)
        categories["Images"]["status"] = "Issues Found"
    else:
        categories["Images"]["passed"] += total_pages

    # Factual Health Score Math based on Evaluated Rules
    crit_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "critical")
    err_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "error")
    warn_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "warning")
    not_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "notice")

    EVALUATED_RULE_COUNT = 8
    total_evaluated_checks = total_pages * EVALUATED_RULE_COUNT
    total_weighted_penalty = (crit_cnt * 3.0) + (err_cnt * 2.0) + (warn_cnt * 1.0) + (not_cnt * 0.25)
    
    if total_evaluated_checks > 0:
        score_deduction = (total_weighted_penalty / total_evaluated_checks) * 100
        health_score = max(0, min(100, round(100 - score_deduction)))
    else:
        health_score = 100

    return {
        "health_score": health_score,
        "total_audited_pages": total_pages,
        "summary": {
            "critical_errors": crit_cnt,
            "errors": err_cnt,
            "warnings": warn_cnt,
            "notices": not_cnt,
            "passed_checks": max(0, total_evaluated_checks - (crit_cnt + err_cnt + warn_cnt + not_cnt))
        },
        "category_breakdown": categories,
        "issues": issues,
        "provenance": {
            "source": "Deterministic 15-Category Site Audit Engine",
            "timestamp": "Real-time Crawl Snapshot Evaluation"
        }
    }
