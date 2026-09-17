import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.config.utils import get_project_storage_dir, normalize_stored_path
from app.config.settings import settings
from app.services.audit_rules import evaluate_site_audit_rules, get_canonical_rule_registry
from app.services.schema_intelligence import SchemaIntelligenceService
from app.services.robots_sitemap_service import RobotsSitemapService


class CanonicalAuditService:
    """
    Produces ONE canonical audit result normalized object that acts as the single source of truth
    for Website Health, Checks Performed popup, PDF, Master XLSX, and API endpoints.
    """

    @classmethod
    def get_canonical_audit_result(
        cls,
        project_id: str,
        domain: Optional[str] = None,
        crawl_id: Optional[str] = None,
        pages_override: Optional[List[Dict[str, Any]]] = None,
        metadata_override: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pages = pages_override if pages_override is not None else []
        metadata = metadata_override if metadata_override is not None else {}
        crawl_ts = metadata.get("timestamp") or datetime.now().strftime("%Y-%m-%d_%H%M%S")
        active_crawl_id = crawl_id or metadata.get("crawl_id")

        if pages_override is None:
            proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
            crawl_dir = None

            if active_crawl_id:
                direct_path = os.path.join(proj_dir, "crawls", active_crawl_id)
                if os.path.isdir(direct_path):
                    crawl_dir = direct_path

            if not crawl_dir:
                latest_path = os.path.join(proj_dir, "latest.json")
                if os.path.exists(latest_path):
                    try:
                        with open(latest_path, "r", encoding="utf-8") as lf:
                            latest_ptr = json.load(lf)
                            crawl_dir = normalize_stored_path(latest_ptr.get("path"))
                            active_crawl_id = active_crawl_id or latest_ptr.get("crawl_id")
                            crawl_ts = latest_ptr.get("timestamp") or crawl_ts
                    except Exception:
                        pass

            if crawl_dir and os.path.exists(crawl_dir):
                pages_file = os.path.join(crawl_dir, "pages.json")
                meta_file = os.path.join(crawl_dir, "metadata.json")
                if os.path.exists(meta_file):
                    try:
                        with open(meta_file, "r", encoding="utf-8") as mf:
                            metadata = json.load(mf)
                            active_crawl_id = metadata.get("crawl_id") or active_crawl_id
                            crawl_ts = metadata.get("timestamp") or crawl_ts
                            domain = domain or metadata.get("website")
                    except Exception:
                        pass
                if os.path.exists(pages_file):
                    try:
                        with open(pages_file, "r", encoding="utf-8") as pf:
                            pages = json.load(pf)
                    except Exception:
                        pass

        # Perform canonical deterministic 15-category evaluation
        audit_eval = evaluate_site_audit_rules(pages)
        schema_info = SchemaIntelligenceService.summarize_dataset_schemas(pages)
        robots_info = RobotsSitemapService.evaluate_robots_evidence(pages, domain=domain)

        html_pages = [p for p in pages if (p.get("status_code") or 0) == 200]
        affected_pages = [
            {
                "url": p.get("url"),
                "status_code": p.get("status_code"),
                "title": p.get("title"),
                "word_count": p.get("word_count", 0),
                "h1": p.get("h1"),
                "canonical_url": p.get("canonical_url"),
                "meta_description": p.get("meta_description")
            }
            for p in pages if p.get("status_code", 200) != 200 or not p.get("title") or (p.get("word_count") or 0) < 150
        ]

        return {
            "crawl_id": active_crawl_id,
            "project_id": project_id,
            "domain": domain or metadata.get("website") or "unknown",
            "crawl_timestamp": crawl_ts,
            "analyzed_pages": len(pages),
            "html_pages_analyzed": len(html_pages),
            "evaluated_rules": audit_eval.get("evaluated_rules_count", 14),
            "total_evaluated_checks": audit_eval.get("total_evaluated_checks", 0),
            "health_score": audit_eval.get("health_score"),
            "score_available": audit_eval.get("score_available", False),
            "summary": audit_eval.get("summary", {}),
            "rule_definitions": audit_eval.get("rule_definitions") or get_canonical_rule_registry(),
            "rule_execution_results": audit_eval.get("rule_execution_results", []),
            "category_breakdown": audit_eval.get("category_breakdown", {}),
            "category_checks_table": audit_eval.get("category_checks_table", []),
            "issues": audit_eval.get("issues", []),
            "affected_pages": affected_pages,
            "schema_summary": {
                "evaluated": True,
                "total_pages_checked": len(html_pages),
                "total_pages_with_schema": schema_info.get("pages_with_schema_count", 0),
                "total_pages_missing_schema": schema_info.get("pages_missing_schema_count", 0),
                "total_schemas_detected": sum(r.get("schema_count", 0) for r in schema_info.get("schema_evidence", [])),
                "unique_schema_types_count": len(schema_info.get("schema_types_summary", {})),
                "schema_types_found": schema_info.get("schema_types_summary", {}),
                "status_breakdown": schema_info.get("status_breakdown", {}),
                "complete_entities_count": sum(1 for r in schema_info.get("schema_evidence", []) if r.get("status") in ("Verified/Supported", "Recognized Schema.org Type")),
                "incomplete_entities_count": sum(1 for r in schema_info.get("schema_evidence", []) if r.get("status") == "Incomplete"),
                "potential_mismatches_count": sum(1 for r in schema_info.get("schema_evidence", []) if r.get("status") == "Potential Mismatch")
            },
            "schema_evidence": schema_info.get("schema_evidence", []),
            "robots_summary": robots_info.get("robots_summary", {}),
            "robots_evidence": robots_info.get("robots_evidence", []),
            "scoring_formula": audit_eval.get("scoring_formula"),
            "scoring_weights": audit_eval.get("scoring_weights")
        }
