import os
import json
from typing import Dict, Any, List, Optional
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.config.settings import settings

class LLMContextBuilder:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or settings.CRAWL_DATA_DIR

    def get_website_folder(self, domain: str) -> str:
        safe_domain = get_sanitized_domain(domain)
        return os.path.join(self.base_dir, safe_domain)

    def build_project_context(self, domain: str) -> Dict[str, Any]:
        website_dir = self.get_website_folder(domain)
        latest_path = os.path.join(website_dir, "latest.json")

        if not os.path.exists(latest_path):
            return {
                "has_data": False,
                "message": "No crawl snapshot available for this website."
            }

        try:
            with open(latest_path, "r") as f:
                latest_pointer = json.load(f)

            crawl_dir = normalize_stored_path(latest_pointer.get("path"))
            
            # Load snapshot JSON files safely
            metadata = {}
            pages = []
            issues = []
            internal_links = []

            meta_file = os.path.join(crawl_dir, "metadata.json")
            if os.path.exists(meta_file):
                with open(meta_file, "r") as mf:
                    metadata = json.load(mf)

            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)

            issues_file = os.path.join(crawl_dir, "issues.json")
            if os.path.exists(issues_file):
                with open(issues_file, "r") as isf:
                    issues = json.load(isf)

            links_file = os.path.join(crawl_dir, "internal_links.json")
            if os.path.exists(links_file):
                with open(links_file, "r") as lf:
                    internal_links = json.load(lf)

            # Compact normalized context payload with full validation against None and malformed records
            normalized_pages = []
            if isinstance(pages, list):
                for p in pages[:50]:
                    if isinstance(p, dict):
                        wc = p.get("word_count")
                        wc_val = int(wc) if isinstance(wc, (int, float)) and wc is not None else 0
                        
                        lc = p.get("internal_links_count")
                        lc_val = int(lc) if isinstance(lc, (int, float)) and lc is not None else 0

                        sc = p.get("status_code")
                        sc_val = int(sc) if isinstance(sc, (int, float)) and sc is not None else 200

                        normalized_pages.append({
                            "url": p.get("url") or "",
                            "status_code": sc_val,
                            "title": p.get("title"),
                            "h1": p.get("h1"),
                            "word_count": wc_val,
                            "links_count": lc_val
                        })
                    else:
                        print(f"[CONTEXT BUILDER WARNING] Skipping non-dict page record: {p}", flush=True)

            normalized_issues = []
            if isinstance(issues, list):
                for i in issues[:30]:
                    if isinstance(i, dict):
                        normalized_issues.append({
                            "severity": i.get("severity") or "Notice",
                            "issue_type": i.get("issue_type") or "General",
                            "affected_url": i.get("affected_url") or "",
                            "details": i.get("details") or ""
                        })
                    else:
                        print(f"[CONTEXT BUILDER WARNING] Skipping non-dict issue record: {i}", flush=True)

            return {
                "has_data": True,
                "domain": domain,
                "crawl_id": metadata.get("crawl_id") if isinstance(metadata, dict) else None,
                "timestamp": metadata.get("timestamp") if isinstance(metadata, dict) else None,
                "pages_count": len(pages) if isinstance(pages, list) else 0,
                "issues_count": len(issues) if isinstance(issues, list) else 0,
                "summary": {
                    "critical": metadata.get("critical_issues", 0) if isinstance(metadata, dict) else 0,
                    "warning": metadata.get("warning_issues", 0) if isinstance(metadata, dict) else 0,
                    "notice": metadata.get("notice_issues", 0) if isinstance(metadata, dict) else 0
                },
                "pages_sample": normalized_pages,
                "issues_sample": normalized_issues,
                "links_sample_count": len(internal_links) if isinstance(internal_links, list) else 0
            }

        except Exception as e:
            print(f"[CONTEXT BUILDER ERROR] Failed to build context for {domain}: {e}", flush=True)
            return {
                "has_data": False,
                "error": str(e)
            }
