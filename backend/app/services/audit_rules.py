import json
from typing import List, Dict, Any, Optional

def extract_schema_types(raw_data: Any) -> List[str]:
    """
    Extracts authentic Schema.org @type values from crawled JSON-LD structured data.
    Supports:
    - Standard dict with @type: {"@type": "Organization"}
    - @type arrays: {"@type": ["Organization", "LocalBusiness"]}
    - @graph collections: {"@graph": [{"@type": "WebSite"}, {"@type": "Organization"}]}
    - Multiple JSON-LD script blocks: list of dicts/lists/strings
    - JSON-encoded strings
    - Schema.org URI prefixes normalization (https://schema.org/Product -> Product)
    Deduplicates and returns types in order of detection.
    """
    if not raw_data:
        return []
    
    types = []
    
    def _clean_type_name(val: str) -> Optional[str]:
        if not val or not isinstance(val, str):
            return None
        t = val.strip()
        if not t:
            return None
        # Remove Schema.org URI / namespace prefixes
        if "schema.org/" in t:
            t = t.split("schema.org/")[-1].strip("/")
        elif "schema.org#" in t:
            t = t.split("schema.org#")[-1].strip("#")
        elif t.startswith("http://") or t.startswith("https://"):
            t = t.rstrip("/").split("/")[-1]
        
        # Remove any leading hash or colon if present (e.g., #Organization, schema:Organization)
        if ":" in t and not t.startswith("http"):
            t = t.split(":")[-1]
        t = t.lstrip("#")
        
        # Validate that it looks like a valid schema identifier
        if t and len(t) < 100:
            return t
        return None

    def _process_node(node: Any):
        if not node:
            return
        if isinstance(node, str):
            try:
                parsed = json.loads(node)
                _process_node(parsed)
            except Exception:
                cleaned = _clean_type_name(node)
                if cleaned and cleaned not in types:
                    types.append(cleaned)
            return
        if isinstance(node, list):
            for item in node:
                _process_node(item)
            return
        if isinstance(node, dict):
            # Check for @graph
            graph_items = node.get("@graph")
            if graph_items is not None:
                _process_node(graph_items)
            
            # Check @type
            raw_type = node.get("@type")
            if raw_type:
                if isinstance(raw_type, list):
                    for t in raw_type:
                        cleaned = _clean_type_name(t)
                        if cleaned and cleaned not in types:
                            types.append(cleaned)
                elif isinstance(raw_type, str):
                    cleaned = _clean_type_name(raw_type)
                    if cleaned and cleaned not in types:
                        types.append(cleaned)

    _process_node(raw_data)
    return types

def evaluate_site_audit_rules(pages: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Evaluates Technical Site Audit Rule Categories across crawled website pages.
    
    EVALUATED CATEGORIES (14):
    1. Crawlability (HTTP status codes)
    2. Indexability (Robots noindex tags)
    3. HTTPS (Insecure HTTP URLs)
    4. Metadata (Missing Title & Meta Description)
    5. Content (Thin content < 150 words)
    6. Headings (Missing H1 headings)
    7. Canonicals (Missing rel='canonical' tags)
    8. Images (Missing alt text)
    9. Internal Links (Orphan pages & broken internal links)
    10. External Links (Insecure external links)
    11. Structured Data (Schema.org JSON-LD structured data tags)
    12. Mobile (Mobile Viewport meta tags)
    13. International SEO (Hreflang language tags)
    14. Security (SSL/TLS verification & secure transport)
    
    UNEVALUATED CATEGORIES (1):
    15. Performance (Requires PageSpeed API key configured in Integrations -> status 'Not Analyzed')
    """
    total_pages = len(pages) if pages else 0
    issues = []

    # Separate HTTP 200 HTML pages from non-200 / blocked pages
    html_pages = [
        p for p in (pages or [])
        if (p.get("status_code") or 0) == 200 and p.get("is_success", True) is not False
    ]
    html_count = len(html_pages)

    blocked_pages = [
        p for p in (pages or [])
        if (p.get("status_code") or 0) in (401, 403) or p.get("fetch_status") == "BLOCKED"
    ]
    error_pages = [
        p for p in (pages or [])
        if (p.get("status_code") or 0) >= 400 and (p.get("status_code") or 0) not in (401, 403)
    ]

    categories = {
        "Crawlability": {"status": "Passed" if total_pages > 0 else "Not Evaluated", "evaluated": total_pages > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Indexability": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "HTTPS": {"status": "Passed" if total_pages > 0 else "Not Evaluated", "evaluated": total_pages > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Metadata": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Content": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Headings": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Canonicals": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Images": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Internal Links": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "External Links": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Structured Data": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Mobile": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "International SEO": {"status": "Passed" if html_count > 0 else "Not Evaluated", "evaluated": html_count > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Security": {"status": "Passed" if total_pages > 0 else "Not Evaluated", "evaluated": total_pages > 0, "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
        "Performance": {"status": "Not Evaluated", "evaluated": False, "reason": "Requires PageSpeed API key configured in Settings -> Integrations", "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0},
    }

    if total_pages == 0:
        unevaluated_categories = {}
        for k in categories:
            unevaluated_categories[k] = {
                "status": "Not Evaluated",
                "evaluated": False,
                "critical": 0, "error": 0, "warning": 0, "notice": 0, "passed": 0,
                "reason": "No pages crawled or available for analysis."
            }
        category_table = [
            {
                "category": cat_name,
                "evaluated": False,
                "checks_performed": 0,
                "passed": 0,
                "issues_count": 0,
                "critical": 0,
                "error": 0,
                "warning": 0,
                "notice": 0,
                "status": "Not Evaluated",
                "reason": "No pages crawled or available for analysis."
            }
            for cat_name in categories
        ]
        return {
            "health_score": None,
            "score_available": False,
            "total_audited_pages": 0,
            "successful_html_pages_count": 0,
            "blocked_pages_count": 0,
            "error_pages_count": 0,
            "evaluated_rules_count": 0,
            "total_evaluated_checks": 0,
            "checks_explanation": "0 analyzed pages",
            "summary": {
                "critical_errors": 0,
                "errors": 0,
                "warnings": 0,
                "notices": 0,
                "passed_checks": 0,
                "total_checks": 0
            },
            "category_breakdown": unevaluated_categories,
            "category_checks_table": category_table,
            "structured_data_summary": {
                "evaluated": False,
                "total_pages_checked": 0,
                "total_pages_with_schema": 0,
                "total_pages_missing_schema": 0,
                "total_schemas_detected": 0,
                "unique_schema_types_count": 0,
                "schema_types_found": {},
                "pages_detail": []
            },
            "issues": [],
            "provenance": {
                "source": "Deterministic 15-Category Site Audit Engine",
                "timestamp": "Real-time Crawl Snapshot Evaluation"
            }
        }

    # Mark non-evaluated HTML categories if no HTML pages were successfully fetched
    if html_count == 0:
        for cat_key in ["Indexability", "Metadata", "Content", "Headings", "Canonicals", "Images", "Internal Links", "External Links", "Structured Data", "Mobile", "International SEO"]:
            categories[cat_key]["status"] = "Not Evaluated"
            categories[cat_key]["evaluated"] = False
            categories[cat_key]["reason"] = "HTML unavailable due to crawl block or HTTP error."

    # 1. Crawlability & HTTP Status
    if blocked_pages:
        issues.append({
            "rule_id": "CRAWL_002",
            "category": "Crawlability",
            "severity": "critical",
            "title": "Crawl Blocked / Access Denied (HTTP 403)",
            "description": f"{len(blocked_pages)} audited page(s) returned HTTP 401/403 Access Denied. Server firewall blocked crawler access. HTML-dependent checks were not evaluated.",
            "evidence": f"Blocked URLs: {', '.join([p.get('url', '') for p in blocked_pages[:3]])}",
            "affected_urls": [p.get("url") for p in blocked_pages],
            "affected_count": len(blocked_pages),
            "recommendation": "Verify server firewall access rules, Cloudflare WAF policies, or user-agent headers."
        })
        categories["Crawlability"]["critical"] += len(blocked_pages)
        categories["Crawlability"]["status"] = "Issues Found"

    if error_pages:
        issues.append({
            "rule_id": "CRAWL_001",
            "category": "Crawlability",
            "severity": "critical",
            "title": "HTTP 4xx / 5xx Broken Pages",
            "description": f"{len(error_pages)} audited pages returned broken client/server status codes.",
            "evidence": f"Pages returning HTTP status >= 400: {', '.join([p.get('url', '') for p in error_pages[:3]])}",
            "affected_urls": [p.get("url") for p in error_pages],
            "affected_count": len(error_pages),
            "recommendation": "Fix broken page URLs or implement 301 redirects to active destination pages."
        })
        categories["Crawlability"]["critical"] += len(error_pages)
        categories["Crawlability"]["status"] = "Issues Found"

    if not blocked_pages and not error_pages:
        categories["Crawlability"]["passed"] += total_pages

    # Rules 2 to 14 evaluate ONLY html_pages (HTTP 200 OK)
    if html_count > 0:
        # 2. Indexability
        noindex_pages = [p for p in html_pages if "noindex" in (p.get("indexability") or p.get("robots_meta") or "").lower()]
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
            categories["Indexability"]["passed"] += html_count

        # 3. HTTPS
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

        # 4. Metadata
        missing_titles = [p for p in html_pages if not p.get("title") or p.get("title", "").strip() == ""]
        long_titles = [p for p in html_pages if p.get("title") and len(p.get("title", "").strip()) > 60]

        # Short titles and duplicate titles detection across pages (when > 1 page)
        short_titles = []
        duplicate_title_urls = []
        if len(html_pages) > 1:
            short_titles = [p for p in html_pages if p.get("title") and 0 < len(p.get("title", "").strip()) < 30]
            title_counts = {}
            for p in html_pages:
                t = (p.get("title") or "").strip().lower()
                if t:
                    title_counts[t] = title_counts.get(t, []) + [p.get("url")]
            for t_text, u_list in title_counts.items():
                if len(u_list) > 1:
                    duplicate_title_urls.extend(u_list)
            duplicate_title_urls = list(dict.fromkeys(duplicate_title_urls))

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

        if long_titles:
            issues.append({
                "rule_id": "META_003",
                "category": "Metadata",
                "severity": "warning",
                "title": "Page Titles Exceeding 60 Characters",
                "description": f"{len(long_titles)} pages have titles longer than 60 characters, risking truncation in SERP snippets.",
                "evidence": f"Long title URLs: {', '.join([p.get('url', '') for p in long_titles[:3]])}",
                "affected_urls": [p.get("url") for p in long_titles],
                "affected_count": len(long_titles),
                "recommendation": "Shorten title tags to 50-60 characters while placing primary keywords first."
            })
            categories["Metadata"]["warning"] += len(long_titles)
            categories["Metadata"]["status"] = "Issues Found"

        if short_titles:
            issues.append({
                "rule_id": "META_006",
                "category": "Metadata",
                "severity": "notice",
                "title": "Short Page Titles (< 30 Characters)",
                "description": f"{len(short_titles)} pages have concise titles under 30 characters that may lack descriptive keyword targeting.",
                "evidence": f"Short title URLs: {', '.join([p.get('url', '') for p in short_titles[:3]])}",
                "affected_urls": [p.get("url") for p in short_titles],
                "affected_count": len(short_titles),
                "recommendation": "Expand title tags to 40-60 characters with relevant brand and topical keywords."
            })
            categories["Metadata"]["notice"] += len(short_titles)
            categories["Metadata"]["status"] = "Issues Found"

        if duplicate_title_urls:
            issues.append({
                "rule_id": "META_004",
                "category": "Metadata",
                "severity": "warning",
                "title": "Duplicate Title Tags Detected Across Pages",
                "description": f"{len(duplicate_title_urls)} pages share identical title tags with other audited pages.",
                "evidence": f"Duplicate title pages: {', '.join(duplicate_title_urls[:3])}",
                "affected_urls": duplicate_title_urls,
                "affected_count": len(duplicate_title_urls),
                "recommendation": "Write distinct, unique title tags for every page to avoid keyword cannibalization."
            })
            categories["Metadata"]["warning"] += len(duplicate_title_urls)
            categories["Metadata"]["status"] = "Issues Found"

        missing_desc = [p for p in html_pages if not p.get("meta_description") or p.get("meta_description", "").strip() == ""]
        long_desc = [p for p in html_pages if p.get("meta_description") and len(p.get("meta_description", "").strip()) > 160]

        # Duplicate and short meta descriptions across pages (when > 1 page)
        short_desc = []
        duplicate_desc_urls = []
        if len(html_pages) > 1:
            short_desc = [p for p in html_pages if p.get("meta_description") and 0 < len(p.get("meta_description", "").strip()) < 70]
            desc_counts = {}
            for p in html_pages:
                d = (p.get("meta_description") or "").strip().lower()
                if d:
                    desc_counts[d] = desc_counts.get(d, []) + [p.get("url")]
            for d_text, u_list in desc_counts.items():
                if len(u_list) > 1:
                    duplicate_desc_urls.extend(u_list)
            duplicate_desc_urls = list(dict.fromkeys(duplicate_desc_urls))

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

        if long_desc:
            issues.append({
                "rule_id": "META_005",
                "category": "Metadata",
                "severity": "notice",
                "title": "Meta Descriptions Exceeding 160 Characters",
                "description": f"{len(long_desc)} pages have meta descriptions exceeding 160 characters.",
                "evidence": f"Truncated descriptions on: {', '.join([p.get('url', '') for p in long_desc[:3]])}",
                "affected_urls": [p.get("url") for p in long_desc],
                "affected_count": len(long_desc),
                "recommendation": "Shorten meta descriptions to 150-160 characters to prevent snippet truncation."
            })
            categories["Metadata"]["notice"] += len(long_desc)
            categories["Metadata"]["status"] = "Issues Found"

        if short_desc:
            issues.append({
                "rule_id": "META_008",
                "category": "Metadata",
                "severity": "notice",
                "title": "Short Meta Descriptions (< 70 Characters)",
                "description": f"{len(short_desc)} pages have meta descriptions under 70 characters.",
                "evidence": f"Short meta description pages: {', '.join([p.get('url', '') for p in short_desc[:3]])}",
                "affected_urls": [p.get("url") for p in short_desc],
                "affected_count": len(short_desc),
                "recommendation": "Expand meta descriptions to 140-160 characters to maximize SERP snippet engagement."
            })
            categories["Metadata"]["notice"] += len(short_desc)
            categories["Metadata"]["status"] = "Issues Found"

        if duplicate_desc_urls:
            issues.append({
                "rule_id": "META_007",
                "category": "Metadata",
                "severity": "notice",
                "title": "Duplicate Meta Descriptions Detected",
                "description": f"{len(duplicate_desc_urls)} pages share identical meta descriptions with other pages.",
                "evidence": f"Duplicate meta URLs: {', '.join(duplicate_desc_urls[:3])}",
                "affected_urls": duplicate_desc_urls,
                "affected_count": len(duplicate_desc_urls),
                "recommendation": "Provide unique meta descriptions tailored to each page's unique value proposition."
            })
            categories["Metadata"]["notice"] += len(duplicate_desc_urls)
            categories["Metadata"]["status"] = "Issues Found"

        if not missing_titles and not long_titles and not short_titles and not duplicate_title_urls and not missing_desc and not long_desc and not short_desc and not duplicate_desc_urls:
            categories["Metadata"]["passed"] += html_count



        # 5. Content
        thin_pages = [p for p in html_pages if (p.get("word_count") or 0) > 0 and (p.get("word_count") or 0) < 150]
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

        # Content hash exact duplicate detection
        content_hashes = {}
        for p in html_pages:
            h_val = p.get("content_hash") or (p.get("title") + "::" + str(p.get("word_count", 0)) if p.get("word_count", 0) > 50 else None)
            if h_val:
                content_hashes[h_val] = content_hashes.get(h_val, []) + [p.get("url")]
        duplicate_content_urls = []
        for h_k, u_list in content_hashes.items():
            if len(u_list) > 1 and len(u_list) < len(html_pages):
                duplicate_content_urls.extend(u_list)
        duplicate_content_urls = list(dict.fromkeys(duplicate_content_urls))

        if duplicate_content_urls:
            issues.append({
                "rule_id": "CONT_002",
                "category": "Content",
                "severity": "warning",
                "title": "Duplicate Body Content Detected",
                "description": f"{len(duplicate_content_urls)} pages contain identical content signatures.",
                "evidence": f"Duplicate content URLs: {', '.join(duplicate_content_urls[:3])}",
                "affected_urls": duplicate_content_urls,
                "affected_count": len(duplicate_content_urls),
                "recommendation": "Consolidate duplicate pages or implement canonical tags to point to the authoritative source."
            })
            categories["Content"]["warning"] += len(duplicate_content_urls)
            categories["Content"]["status"] = "Issues Found"

        if not thin_pages and not duplicate_content_urls:
            categories["Content"]["passed"] += html_count

        # 6. Headings
        missing_h1 = [p for p in html_pages if not (p.get("h1") if isinstance(p.get("h1"), list) else str(p.get("h1") or "").strip())]
        multiple_h1 = [p for p in html_pages if isinstance(p.get("h1"), list) and len(p.get("h1")) > 1]
        
        # Heading hierarchy skip (H1 -> H3 skipping H2)
        hierarchy_skip_pages = []
        for p in html_pages:
            h2_list = p.get("h2") or []
            h3_list = p.get("h3") or []
            h1_val = p.get("h1")
            if h1_val and not h2_list and h3_list:
                hierarchy_skip_pages.append(p.get("url"))

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

        if multiple_h1:
            issues.append({
                "rule_id": "HEAD_002",
                "category": "Headings",
                "severity": "notice",
                "title": "Pages with Multiple H1 Headings",
                "description": f"{len(multiple_h1)} pages contain more than one <h1> heading, diluting semantic hierarchy.",
                "evidence": f"URLs with multiple H1: {', '.join([p.get('url', '') for p in multiple_h1[:3]])}",
                "affected_urls": [p.get("url") for p in multiple_h1],
                "affected_count": len(multiple_h1),
                "recommendation": "Maintain a single primary <h1> heading per page and convert secondary headings to <h2>."
            })
            categories["Headings"]["notice"] += len(multiple_h1)
            categories["Headings"]["status"] = "Issues Found"

        if hierarchy_skip_pages:
            issues.append({
                "rule_id": "HEAD_003",
                "category": "Headings",
                "severity": "notice",
                "title": "Heading Hierarchy Skipping (H1 to H3 without H2)",
                "description": f"{len(hierarchy_skip_pages)} pages contain <h3> headings without intermediate <h2> headings.",
                "evidence": f"Skipped hierarchy pages: {', '.join(hierarchy_skip_pages[:3])}",
                "affected_urls": hierarchy_skip_pages,
                "affected_count": len(hierarchy_skip_pages),
                "recommendation": "Structure document hierarchy logically using <h2> before sub-level <h3> tags."
            })
            categories["Headings"]["notice"] += len(hierarchy_skip_pages)
            categories["Headings"]["status"] = "Issues Found"

        if not missing_h1 and not multiple_h1 and not hierarchy_skip_pages:
            categories["Headings"]["passed"] += html_count

        # 7. Canonicals
        missing_canon = [p for p in html_pages if not p.get("canonical") or p.get("canonical", "").strip() == ""]
        canon_conflicts = []
        for p in html_pages:
            c = (p.get("canonical") or "").strip()
            u = (p.get("url") or "").strip()
            if c and u and c.startswith("http://") and u.startswith("https://"):
                canon_conflicts.append(u)

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

        if canon_conflicts:
            issues.append({
                "rule_id": "CANON_002",
                "category": "Canonicals",
                "severity": "warning",
                "title": "Canonical Tag Points to Insecure HTTP Endpoint",
                "description": f"{len(canon_conflicts)} secure HTTPS pages specify an insecure HTTP canonical target.",
                "evidence": f"Conflict URLs: {', '.join(canon_conflicts[:3])}",
                "affected_urls": canon_conflicts,
                "affected_count": len(canon_conflicts),
                "recommendation": "Update canonical link targets to use secure https:// scheme."
            })
            categories["Canonicals"]["warning"] += len(canon_conflicts)
            categories["Canonicals"]["status"] = "Issues Found"

        if not missing_canon and not canon_conflicts:
            categories["Canonicals"]["passed"] += html_count

        # 8. Images
        def _has_missing_alt(p_obj):
            v = p_obj.get("images_missing_alt")
            if not v: return False
            if isinstance(v, int): return v > 0
            if isinstance(v, (list, tuple, set)): return len(v) > 0
            return False

        missing_alt_pages = [p for p in html_pages if _has_missing_alt(p)]
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

        # Missing image dimensions
        missing_dim_pages = []
        for p in html_pages:
            imgs = p.get("image_inventory") or []
            if isinstance(imgs, list) and any(not img.get("width") or not img.get("height") for img in imgs if isinstance(img, dict)):
                missing_dim_pages.append(p.get("url"))

        if missing_dim_pages:
            issues.append({
                "rule_id": "IMG_002",
                "category": "Images",
                "severity": "notice",
                "title": "Images Missing Explicit Width & Height Attributes",
                "description": f"{len(missing_dim_pages)} pages have images without explicit dimensions, risking Cumulative Layout Shift (CLS).",
                "evidence": f"URLs: {', '.join(missing_dim_pages[:3])}",
                "affected_urls": missing_dim_pages,
                "affected_count": len(missing_dim_pages),
                "recommendation": "Add width and height HTML attributes or CSS aspect-ratio properties to prevent layout shifts."
            })
            categories["Images"]["notice"] += len(missing_dim_pages)
            categories["Images"]["status"] = "Issues Found"

        if not missing_alt_pages and not missing_dim_pages:
            categories["Images"]["passed"] += html_count

        # 9. Internal Links
        orphan_pages = [p for p in html_pages if (p.get("inbound_internal_links_count", p.get("internal_links_count", 1)) == 0) and not p.get("url", "").endswith("/")]
        deep_pages = [p for p in html_pages if (p.get("crawl_depth") or 0) > 3]

        if orphan_pages:
            issues.append({
                "rule_id": "LINK_001",
                "category": "Internal Links",
                "severity": "warning",
                "title": "Orphan Pages (0 Inbound Internal Links)",
                "description": f"{len(orphan_pages)} pages have no incoming internal links discovered within this crawl.",
                "evidence": f"Orphan URLs: {', '.join([p.get('url', '') for p in orphan_pages[:3]])}",
                "affected_urls": [p.get("url") for p in orphan_pages],
                "affected_count": len(orphan_pages),
                "recommendation": "Add internal links from relevant contextually related category or hub pages."
            })
            categories["Internal Links"]["warning"] += len(orphan_pages)
            categories["Internal Links"]["status"] = "Issues Found"

        if deep_pages:
            issues.append({
                "rule_id": "LINK_002",
                "category": "Internal Links",
                "severity": "notice",
                "title": "Deep Pages (Crawl Depth > 3)",
                "description": f"{len(deep_pages)} pages require more than 3 clicks from seed to reach.",
                "evidence": f"Deep URLs: {', '.join([p.get('url', '') for p in deep_pages[:3]])}",
                "affected_urls": [p.get("url") for p in deep_pages],
                "affected_count": len(deep_pages),
                "recommendation": "Improve site architecture with direct category navigation and hub links."
            })
            categories["Internal Links"]["notice"] += len(deep_pages)
            categories["Internal Links"]["status"] = "Issues Found"

        if not orphan_pages and not deep_pages:
            categories["Internal Links"]["passed"] += html_count

        # 10. External Links
        insecure_external_pages = []
        for p in html_pages:
            links = p.get("links") or []
            if isinstance(links, list):
                if any(isinstance(l, dict) and l.get("is_external") and str(l.get("target_url") or "").startswith("http://") for l in links):
                    insecure_external_pages.append(p.get("url"))

        if insecure_external_pages:
            issues.append({
                "rule_id": "EXT_001",
                "category": "External Links",
                "severity": "notice",
                "title": "Outbound Links to Insecure HTTP Destinations",
                "description": f"{len(insecure_external_pages)} pages link out to unencrypted HTTP destinations.",
                "evidence": f"Pages with HTTP outbound links: {', '.join(insecure_external_pages[:3])}",
                "affected_urls": insecure_external_pages,
                "affected_count": len(insecure_external_pages),
                "recommendation": "Update outbound links to HTTPS destinations to maintain secure user navigation."
            })
            categories["External Links"]["notice"] += len(insecure_external_pages)
            categories["External Links"]["status"] = "Issues Found"
        else:
            categories["External Links"]["passed"] += html_count

        # 11. Structured Data
        structured_data_pages_detail = []
        schema_type_page_counts = {}
        total_pages_with_schema = 0
        total_schemas_count = 0

        for p in html_pages:
            raw_sd = p.get("structured_data") or p.get("schema_types") or []
            detected_types = extract_schema_types(raw_sd)
            has_sd = len(detected_types) > 0
            
            if has_sd:
                total_pages_with_schema += 1
                total_schemas_count += len(detected_types)
                for st in detected_types:
                    schema_type_page_counts[st] = schema_type_page_counts.get(st, 0) + 1
            
            structured_data_pages_detail.append({
                "url": p.get("url", ""),
                "has_structured_data": has_sd,
                "schema_count": len(detected_types),
                "detected_schema_types": detected_types,
                "raw_json_ld": raw_sd if isinstance(raw_sd, list) else ([raw_sd] if raw_sd else [])
            })

        missing_schema_pages = [p for p in structured_data_pages_detail if not p["has_structured_data"]]
        missing_count = len(missing_schema_pages)
        sorted_schema_types_found = dict(sorted(schema_type_page_counts.items(), key=lambda item: item[1], reverse=True))

        structured_data_summary = {
            "evaluated": html_count > 0,
            "total_pages_checked": html_count,
            "total_pages_with_schema": total_pages_with_schema,
            "total_pages_missing_schema": missing_count,
            "total_schemas_detected": total_schemas_count,
            "unique_schema_types_count": len(sorted_schema_types_found),
            "schema_types_found": sorted_schema_types_found,
            "pages_detail": structured_data_pages_detail
        }

        categories["Structured Data"]["structured_data_summary"] = structured_data_summary
        categories["Structured Data"]["schema_types_found"] = sorted_schema_types_found
        categories["Structured Data"]["total_pages_with_schema"] = total_pages_with_schema
        categories["Structured Data"]["total_pages_missing_schema"] = missing_count

        if missing_schema_pages:
            issues.append({
                "rule_id": "SCHEMA_001",
                "category": "Structured Data",
                "severity": "notice",
                "title": "Pages Missing Schema.org Structured Data",
                "description": f"{missing_count} pages lack JSON-LD structured data markups.",
                "evidence": f"URLs: {', '.join([p.get('url', '') for p in missing_schema_pages[:3]])}",
                "affected_urls": [p.get("url") for p in missing_schema_pages],
                "affected_count": missing_count,
                "recommendation": "Implement JSON-LD structured data (Article, Organization, Product) for rich snippet eligibility."
            })
            categories["Structured Data"]["notice"] += missing_count
            categories["Structured Data"]["status"] = "Issues Found"
        else:
            categories["Structured Data"]["passed"] += html_count

        # 12. Mobile
        missing_viewport_pages = [p for p in html_pages if "viewport" in p and not p.get("viewport")]
        if missing_viewport_pages:
            issues.append({
                "rule_id": "MOB_001",
                "category": "Mobile",
                "severity": "warning",
                "title": "Pages Missing Mobile Viewport Meta Tag",
                "description": f"{len(missing_viewport_pages)} pages lack a mobile viewport meta tag.",
                "evidence": f"URLs: {', '.join([p.get('url', '') for p in missing_viewport_pages[:3]])}",
                "affected_urls": [p.get("url") for p in missing_viewport_pages],
                "affected_count": len(missing_viewport_pages),
                "recommendation": "Add <meta name='viewport' content='width=device-width, initial-scale=1.0'>."
            })
            categories["Mobile"]["warning"] += len(missing_viewport_pages)
            categories["Mobile"]["status"] = "Issues Found"
        else:
            categories["Mobile"]["passed"] += html_count

        # 13. International SEO (Hreflang)
        missing_hreflang_self = []
        for p in html_pages:
            hlangs = p.get("hreflangs") or p.get("hreflang") or []
            if isinstance(hlangs, list) and hlangs:
                p_url = p.get("url", "")
                has_self = any(isinstance(h, dict) and h.get("href") == p_url for h in hlangs)
                if not has_self:
                    missing_hreflang_self.append(p_url)

        if missing_hreflang_self:
            issues.append({
                "rule_id": "HREF_001",
                "category": "International SEO",
                "severity": "notice",
                "title": "Hreflang Tags Missing Self-Reference",
                "description": f"{len(missing_hreflang_self)} pages contain alternate language annotations without self-referential hreflang tag.",
                "evidence": f"Affected URLs: {', '.join(missing_hreflang_self[:3])}",
                "affected_urls": missing_hreflang_self,
                "affected_count": len(missing_hreflang_self),
                "recommendation": "Ensure each alternate language tag set contains a self-referential return link."
            })
            categories["International SEO"]["notice"] += len(missing_hreflang_self)
            categories["International SEO"]["status"] = "Issues Found"
        else:
            categories["International SEO"]["passed"] += html_count

        # 14. Social / Open Graph & Twitter Cards
        missing_og_pages = [p for p in html_pages if "open_graph" in p and p.get("open_graph") is not None and not p.get("open_graph", {}).get("og:title")]
        if missing_og_pages:
            issues.append({
                "rule_id": "OG_001",
                "category": "Metadata",
                "severity": "notice",
                "title": "Pages Missing Open Graph (og:title) Social Tags",
                "description": f"{len(missing_og_pages)} pages lack Open Graph social share metadata.",
                "evidence": f"Affected URLs: {', '.join([p.get('url', '') for p in missing_og_pages[:3]])}",
                "affected_urls": [p.get("url") for p in missing_og_pages],
                "affected_count": len(missing_og_pages),
                "recommendation": "Add og:title, og:description, and og:image tags for rich social sharing previews."
            })
            categories["Metadata"]["notice"] += len(missing_og_pages)
            categories["Metadata"]["status"] = "Issues Found"

    # 15. Security
    ssl_error_pages = [p for p in pages if "ssl" in (p.get("error") or "").lower() or "tls" in (p.get("error") or "").lower()]
    if ssl_error_pages:
        issues.append({
            "rule_id": "SEC_001",
            "category": "Security",
            "severity": "critical",
            "title": "SSL / TLS Certificate Validation Error",
            "description": f"{len(ssl_error_pages)} pages failed TLS certificate verification.",
            "evidence": f"URLs: {', '.join([p.get('url', '') for p in ssl_error_pages[:3]])}",
            "affected_urls": [p.get("url") for p in ssl_error_pages],
            "affected_count": len(ssl_error_pages),
            "recommendation": "Renew expired SSL certificates and fix CA chain trust errors."
        })
        categories["Security"]["critical"] += len(ssl_error_pages)
        categories["Security"]["status"] = "Issues Found"
    else:
        categories["Security"]["passed"] += total_pages

    # Health Score Math based on Evaluated Rules
    crit_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "critical")
    err_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "error")
    warn_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "warning")
    not_cnt = sum(i["affected_count"] for i in issues if i["severity"] == "notice")

    EVALUATED_RULE_COUNT = sum(1 for c in categories.values() if c.get("evaluated", False))
    evaluated_pages_for_score = html_count if html_count > 0 else total_pages
    total_evaluated_checks = evaluated_pages_for_score * EVALUATED_RULE_COUNT
    total_weighted_penalty = (crit_cnt * 3.0) + (err_cnt * 2.0) + (warn_cnt * 1.0)

    
    if total_evaluated_checks > 0:
        score_deduction = (total_weighted_penalty / total_evaluated_checks) * 100
        health_score = max(0, min(100, round(100 - score_deduction)))
    else:
        health_score = 100

    category_table = []
    for cat_name, stats in categories.items():
        is_eval = stats.get("evaluated", False)
        if not is_eval:
            stats["status"] = "Not Evaluated"
        else:
            issues_count = stats.get("critical", 0) + stats.get("error", 0) + stats.get("warning", 0) + stats.get("notice", 0)
            if issues_count > 0 or stats.get("status") == "Issues Found":
                stats["status"] = "Issues Found"
            else:
                stats["status"] = "Passed"

        issues_count = stats.get("critical", 0) + stats.get("error", 0) + stats.get("warning", 0) + stats.get("notice", 0)
        checks_count = evaluated_pages_for_score if is_eval else 0
        passed_count = max(0, checks_count - issues_count) if is_eval else 0
        cat_entry = {
            "category": cat_name,
            "evaluated": is_eval,
            "checks_performed": checks_count,
            "passed": passed_count,
            "issues_count": issues_count,
            "critical": stats.get("critical", 0),
            "error": stats.get("error", 0),
            "warning": stats.get("warning", 0),
            "notice": stats.get("notice", 0),
            "status": stats.get("status", "Not Evaluated"),
            "reason": stats.get("reason", "")
        }
        if cat_name == "Structured Data" and "structured_data_summary" in stats:
            cat_entry["structured_data_summary"] = stats["structured_data_summary"]
            cat_entry["schema_types_found"] = stats.get("schema_types_found", {})
            cat_entry["total_pages_with_schema"] = stats.get("total_pages_with_schema", 0)
            cat_entry["total_pages_missing_schema"] = stats.get("total_pages_missing_schema", 0)
        category_table.append(cat_entry)

    return {
        "health_score": health_score,
        "score_available": total_pages > 0,
        "total_audited_pages": total_pages,
        "successful_html_pages_count": html_count,
        "blocked_pages_count": len(blocked_pages),
        "error_pages_count": len(error_pages),
        "evaluated_rules_count": EVALUATED_RULE_COUNT,
        "total_evaluated_checks": total_evaluated_checks,
        "checks_explanation": f"{evaluated_pages_for_score} analyzed pages × {EVALUATED_RULE_COUNT} evaluated rules",
        "health_score_formula": "100 - ((critical*3.0 + error*2.0 + warning*1.0 + notice*0.25) / total_evaluated_checks) * 100",
        "summary": {
            "critical_errors": crit_cnt,
            "errors": err_cnt,
            "warnings": warn_cnt,
            "notices": not_cnt,
            "passed_checks": max(0, total_evaluated_checks - (crit_cnt + err_cnt + warn_cnt + not_cnt)),
            "total_checks": total_evaluated_checks
        },
        "category_breakdown": categories,
        "category_checks_table": category_table,
        "structured_data_summary": categories.get("Structured Data", {}).get("structured_data_summary"),
        "issues": issues,
        "provenance": {
            "source": "Deterministic 15-Category Site Audit Engine",
            "timestamp": "Real-time Crawl Snapshot Evaluation"
        }
    }

