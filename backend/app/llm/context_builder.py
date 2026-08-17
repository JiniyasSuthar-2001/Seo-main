import os
import json
from typing import Dict, Any, List, Optional

class LLMContextBuilder:
    def __init__(self, base_dir: str = "data/websites"):
        self.base_dir = base_dir

    def get_website_folder(self, domain: str) -> str:
        safe_domain = domain.replace("https://", "").replace("http://", "").replace("www.", "")
        safe_domain = "".join([c if c.isalnum() else "_" for c in safe_domain])
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

            crawl_dir = latest_pointer.get("path")
            
            # Load snapshot JSON files
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

            # Compact normalized context payload to optimize LLM tokens & evidence tracing
            normalized_pages = [
                {
                    "url": p.get("url"),
                    "status_code": p.get("status_code"),
                    "title": p.get("title"),
                    "h1": p.get("h1"),
                    "word_count": p.get("word_count"),
                    "links_count": p.get("internal_links_count")
                }
                for p in pages[:50]
            ]

            normalized_issues = [
                {
                    "severity": i.get("severity"),
                    "issue_type": i.get("issue_type"),
                    "affected_url": i.get("affected_url"),
                    "details": i.get("details")
                }
                for i in issues[:30]
            ]

            return {
                "has_data": True,
                "domain": domain,
                "crawl_id": metadata.get("crawl_id"),
                "timestamp": metadata.get("timestamp"),
                "pages_count": len(pages),
                "issues_count": len(issues),
                "summary": {
                    "critical": metadata.get("critical_issues", 0),
                    "warning": metadata.get("warning_issues", 0),
                    "notice": metadata.get("notice_issues", 0)
                },
                "pages_sample": normalized_pages,
                "issues_sample": normalized_issues,
                "links_sample_count": len(internal_links)
            }

        except Exception as e:
            print(f"[CONTEXT BUILDER ERROR] Failed to build context for {domain}: {e}", flush=True)
            return {
                "has_data": False,
                "error": str(e)
            }
