import json
from typing import Dict, Any, List, Optional, Tuple

KNOWN_SCHEMA_TYPES = {
    "Organization", "LocalBusiness", "FAQPage", "QAPage", "Article", "NewsArticle",
    "BlogPosting", "Product", "Offer", "AggregateRating", "Review", "BreadcrumbList",
    "WebSite", "WebPage", "Event", "JobPosting", "Course", "Recipe", "SoftwareApplication",
    "VideoObject", "ImageObject", "SearchAction", "Person", "Place", "PostalAddress",
    "ContactPoint", "ListItem", "Question", "Answer"
}

REQUIRED_PROPERTIES = {
    "Organization": ["name", "url"],
    "LocalBusiness": ["name", "address"],
    "FAQPage": ["mainEntity"],
    "QAPage": ["mainEntity"],
    "Article": ["headline", "author"],
    "NewsArticle": ["headline", "author"],
    "BlogPosting": ["headline", "author"],
    "Product": ["name"],
    "BreadcrumbList": ["itemListElement"],
    "WebSite": ["name", "url"],
    "Event": ["name", "startDate", "location"],
    "JobPosting": ["title", "hiringOrganization"]
}


class SchemaIntelligenceService:
    """
    Evaluates JSON-LD structured data and microdata to categorize schema compliance into:
    - Not Detected
    - Detected
    - Parsed
    - Recognized Schema.org Type
    - Incomplete
    - Partial Evidence
    - Potential Mismatch
    - Verified/Supported
    - Unable to Verify
    """

    @classmethod
    def evaluate_page_schema(cls, page_url: str, raw_structured_data: Any) -> Dict[str, Any]:
        if not raw_structured_data:
            return {
                "url": page_url,
                "status": "Not Detected",
                "types_found": [],
                "schema_count": 0,
                "detail": "No JSON-LD script blocks or microdata tags detected.",
                "evidence": [],
                "is_verified": False
            }

        status = "Detected"
        parsed_nodes = []
        parse_errors = []

        # Step 1: Parse
        if isinstance(raw_structured_data, str):
            try:
                parsed_nodes = [json.loads(raw_structured_data)]
                status = "Parsed"
            except Exception as e:
                parse_errors.append(str(e))
                status = "Unable to Verify"
        elif isinstance(raw_structured_data, list):
            for idx, item in enumerate(raw_structured_data):
                if isinstance(item, str):
                    try:
                        parsed_nodes.append(json.loads(item))
                    except Exception as e:
                        parse_errors.append(f"Block {idx}: {e}")
                elif isinstance(item, dict):
                    parsed_nodes.append(item)
            status = "Parsed" if parsed_nodes else ("Unable to Verify" if parse_errors else "Detected")
        elif isinstance(raw_structured_data, dict):
            parsed_nodes = [raw_structured_data]
            status = "Parsed"

        if not parsed_nodes:
            return {
                "url": page_url,
                "status": "Unable to Verify" if parse_errors else "Not Detected",
                "types_found": [],
                "schema_count": 0,
                "detail": f"JSON parse failure or invalid schema content: {'; '.join(parse_errors[:2])}" if parse_errors else "No valid JSON structure found.",
                "evidence": [],
                "is_verified": False
            }

        # Step 2: Extract @type and inspect properties
        types_found = []
        evidence_list = []
        has_incomplete = False
        has_recognized = False

        def _flatten_nodes(node: Any):
            if not node:
                return
            if isinstance(node, list):
                for item in node:
                    _flatten_nodes(item)
                return
            if isinstance(node, dict):
                graph = node.get("@graph")
                if graph:
                    _flatten_nodes(graph)
                raw_type = node.get("@type")
                if raw_type:
                    t_list = raw_type if isinstance(raw_type, list) else [raw_type]
                    for t in t_list:
                        if isinstance(t, str):
                            clean_t = t.rstrip("/").split("/")[-1].split(":")[-1].lstrip("#")
                            if clean_t and clean_t not in types_found:
                                types_found.append(clean_t)

                            # Check required fields
                            req_fields = REQUIRED_PROPERTIES.get(clean_t, [])
                            missing_req = [f for f in req_fields if not node.get(f)]
                            
                            is_known = clean_t in KNOWN_SCHEMA_TYPES
                            if is_known:
                                nonlocal has_recognized
                                has_recognized = True

                            if missing_req:
                                nonlocal has_incomplete
                                has_incomplete = True
                                evidence_list.append({
                                    "type": clean_t,
                                    "status": "Incomplete",
                                    "missing_fields": missing_req,
                                    "found_fields": list(node.keys())
                                })
                            else:
                                evidence_list.append({
                                    "type": clean_t,
                                    "status": "Verified/Supported" if is_known else "Recognized Schema.org Type",
                                    "missing_fields": [],
                                    "found_fields": list(node.keys())
                                })

        _flatten_nodes(parsed_nodes)

        # Step 3: Final Status Resolution
        if not types_found:
            final_status = "Partial Evidence"
        elif parse_errors:
            final_status = "Unable to Verify"
        elif has_incomplete:
            final_status = "Incomplete"
        elif has_recognized:
            final_status = "Verified/Supported"
        else:
            final_status = "Recognized Schema.org Type"

        return {
            "url": page_url,
            "status": final_status,
            "types_found": types_found,
            "schema_count": len(types_found),
            "detail": f"{len(types_found)} schema types detected ({', '.join(types_found[:3])}).",
            "evidence": evidence_list,
            "is_verified": final_status in ("Verified/Supported", "Recognized Schema.org Type")
        }

    @classmethod
    def summarize_dataset_schemas(cls, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        html_pages = [p for p in (pages or []) if (p.get("status_code") or 0) == 200]
        results = [cls.evaluate_page_schema(p.get("url", ""), p.get("structured_data") or p.get("schema_types")) for p in html_pages]

        status_counts = {
            "Not Detected": sum(1 for r in results if r["status"] == "Not Detected"),
            "Detected": sum(1 for r in results if r["status"] == "Detected"),
            "Parsed": sum(1 for r in results if r["status"] == "Parsed"),
            "Recognized Schema.org Type": sum(1 for r in results if r["status"] == "Recognized Schema.org Type"),
            "Incomplete": sum(1 for r in results if r["status"] == "Incomplete"),
            "Partial Evidence": sum(1 for r in results if r["status"] == "Partial Evidence"),
            "Potential Mismatch": sum(1 for r in results if r["status"] == "Potential Mismatch"),
            "Verified/Supported": sum(1 for r in results if r["status"] == "Verified/Supported"),
            "Unable to Verify": sum(1 for r in results if r["status"] == "Unable to Verify")
        }

        type_counts = {}
        for r in results:
            for t in r["types_found"]:
                type_counts[t] = type_counts.get(t, 0) + 1

        total_with_schema = sum(1 for r in results if r["schema_count"] > 0)

        return {
            "total_html_pages_analyzed": len(html_pages),
            "pages_with_schema_count": total_with_schema,
            "pages_missing_schema_count": len(html_pages) - total_with_schema,
            "status_breakdown": status_counts,
            "schema_types_summary": dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)),
            "schema_evidence": results
        }
