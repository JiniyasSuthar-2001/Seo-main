import os
import json
from datetime import datetime
from typing import Dict, Any, List
from app.config.utils import get_sanitized_domain, normalize_stored_path

class CrawlStorage:
    def __init__(self, base_dir: str = "data/websites"):
        self.base_dir = base_dir

    def _get_website_folder(self, domain: str) -> str:
        safe_domain = get_sanitized_domain(domain)
        return os.path.join(self.base_dir, safe_domain)

    def save_crawl_snapshot(self, domain: str, session_id: str, results: Dict[str, Any]) -> str:
        website_dir = self._get_website_folder(domain)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        crawl_dir = os.path.join(website_dir, "crawls", timestamp)
        os.makedirs(crawl_dir, exist_ok=True)

        pages = results.get("pages", [])
        issues = results.get("issues", [])
        internal_links = results.get("internal_links", [])
        external_links = results.get("external_links", [])

        # 1. Check for previous crawl to run diff comparison
        latest_pointer_path = os.path.join(website_dir, "latest.json")
        prev_snapshot_path = None
        if os.path.exists(latest_pointer_path):
            try:
                with open(latest_pointer_path, "r") as pf:
                    prev_pointer = json.load(pf)
                    prev_snapshot_path = normalize_stored_path(prev_pointer.get("path"))
            except Exception as e:
                print(f"[STORAGE] Could not read previous latest.json: {e}", flush=True)

        # 2. Save Snapshot JSON Artifacts
        critical_count = sum(1 for i in issues if i.get("severity") == "Critical")
        warning_count = sum(1 for i in issues if i.get("severity") == "Warning")
        notice_count = sum(1 for i in issues if i.get("severity") == "Notice")

        metadata = {
            "crawl_id": session_id,
            "website": domain,
            "timestamp": timestamp,
            "status": results.get("status", "completed"),
            "pages_crawled": results.get("successful_pages_count", len(pages)),
            "failed_pages_count": results.get("failed_pages_count", 0),
            "total_issues": len(issues),
            "critical_issues": critical_count,
            "warning_issues": warning_count,
            "notice_issues": notice_count,
            "internal_links_count": len(internal_links),
            "external_links_count": len(external_links)
        }

        # Write files
        files_to_write = {
            "metadata.json": metadata,
            "pages.json": pages,
            "issues.json": issues,
            "internal_links.json": internal_links,
            "external_links.json": external_links,
            "summary.json": metadata
        }

        for fname, content in files_to_write.items():
            fpath = os.path.join(crawl_dir, fname)
            with open(fpath, "w") as f:
                json.dump(content, f, indent=4)

        # Storage Verification Step
        required_artifacts = ["metadata.json", "pages.json", "issues.json", "internal_links.json", "external_links.json", "summary.json"]
        missing_artifacts = [f for f in required_artifacts if not os.path.exists(os.path.join(crawl_dir, f))]
        
        if missing_artifacts:
            raise RuntimeError(f"Storage Verification Failed. Missing artifacts: {missing_artifacts}")

        print(f"[STORAGE VERIFIED] All 6 snapshot artifacts written successfully to {crawl_dir}", flush=True)

        # 3. Generate Crawl Comparison if previous snapshot exists
        if prev_snapshot_path and os.path.exists(prev_snapshot_path):
            try:
                comp_dir = os.path.join(website_dir, "comparisons")
                os.makedirs(comp_dir, exist_ok=True)

                prev_pages_path = os.path.join(prev_snapshot_path, "pages.json")
                prev_issues_path = os.path.join(prev_snapshot_path, "issues.json")

                prev_pages = []
                if os.path.exists(prev_pages_path):
                    with open(prev_pages_path, "r") as pf:
                        prev_pages = json.load(pf)

                prev_issues = []
                if os.path.exists(prev_issues_path):
                    with open(prev_issues_path, "r") as pf:
                        prev_issues = json.load(pf)

                prev_urls = set(p.get("url") for p in prev_pages)
                curr_urls = set(p.get("url") for p in pages)

                new_pages = list(curr_urls - prev_urls)
                removed_pages = list(prev_urls - curr_urls)

                prev_issue_keys = set(f"{i.get('issue_type')}:{i.get('affected_url')}" for i in prev_issues)
                curr_issue_keys = set(f"{i.get('issue_type')}:{i.get('affected_url')}" for i in issues)

                new_issues = [i for i in issues if f"{i.get('issue_type')}:{i.get('affected_url')}" not in prev_issue_keys]
                resolved_issues = [i for i in prev_issues if f"{i.get('issue_type')}:{i.get('affected_url')}" not in curr_issue_keys]

                prev_ts = os.path.basename(prev_snapshot_path)
                comp_data = {
                    "previous_crawl": prev_ts,
                    "current_crawl": timestamp,
                    "new_pages_count": len(new_pages),
                    "removed_pages_count": len(removed_pages),
                    "new_pages": new_pages,
                    "removed_pages": removed_pages,
                    "new_issues_count": len(new_issues),
                    "resolved_issues_count": len(resolved_issues),
                    "new_issues": new_issues,
                    "resolved_issues": resolved_issues
                }

                comp_file = os.path.join(comp_dir, f"{prev_ts}_to_{timestamp}.json")
                with open(comp_file, "w") as cf:
                    json.dump(comp_data, cf, indent=4)
                    
                print(f"[STORAGE] Generated crawl comparison: {comp_file}", flush=True)

            except Exception as ce:
                print(f"[STORAGE] Failed to generate crawl comparison safely: {ce}", flush=True)

        # 4. Update latest pointer
        latest_pointer = {
            "crawl_id": session_id,
            "timestamp": timestamp,
            "path": crawl_dir
        }
        with open(latest_pointer_path, "w") as f:
            json.dump(latest_pointer, f, indent=4)

        print(f"[STORAGE] Snapshot saved successfully to {crawl_dir}", flush=True)
        return crawl_dir

    def get_crawl_history(self, domain: str) -> List[Dict[str, Any]]:
        website_dir = self._get_website_folder(domain)
        crawls_dir = os.path.join(website_dir, "crawls")
        if not os.path.exists(crawls_dir):
            return []

        history = []
        for ts_folder in sorted(os.listdir(crawls_dir), reverse=True):
            meta_path = os.path.join(crawls_dir, ts_folder, "metadata.json")
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                        meta["folder_name"] = ts_folder
                        history.append(meta)
                except Exception as e:
                    pass
        return history
