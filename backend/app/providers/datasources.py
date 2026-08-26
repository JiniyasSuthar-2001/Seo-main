import os
import json
from typing import Dict, Any
from app.config.utils import get_sanitized_domain

class DataSourceManager:
    def __init__(self, base_dir: str = "data/websites"):
        self.base_dir = base_dir

    def _get_project_dir(self, key: str, domain: str = None) -> str:
        if not key:
            safe_domain = get_sanitized_domain(domain)
            return os.path.join(self.base_dir, safe_domain)
        proj_dir = os.path.join(self.base_dir, key)
        if os.path.exists(proj_dir) or not domain:
            return proj_dir
        safe_domain = get_sanitized_domain(domain)
        domain_dir = os.path.join(self.base_dir, safe_domain)
        if os.path.exists(domain_dir):
            return domain_dir
        return proj_dir

    def get_project_datasources(self, key: str, domain: str = None) -> Dict[str, Any]:
        proj_dir = self._get_project_dir(key, domain)
        ds_file = os.path.join(proj_dir, "datasources.json")
        
        default_sources = {
            "crawler": {
                "name": "Website Crawler & HTML Parser",
                "type": "Primary Engine",
                "status": "Active (Default Source)",
                "implemented": True,
                "description": "Directly crawls website URLs, HTML titles, meta tags, H1-H6 headings, canonicals, internal/outbound links, sitemaps, and robots directives.",
                "credentials_required": False,
                "local_only": True
            },
            "nlp_keywords": {
                "name": "Website Content Keyword Extractor",
                "type": "Crawled Data Engine",
                "status": "Active",
                "implemented": True,
                "description": "Derives content keywords, frequencies, and page topics directly from crawled HTML content.",
                "credentials_required": False,
                "local_only": True
            },
            "google_autocomplete": {
                "name": "Google Autocomplete Search Ideas",
                "type": "Public SERP Provider",
                "status": "Available",
                "implemented": True,
                "description": "Generates live search query expansions and autocomplete phrase ideas.",
                "credentials_required": False,
                "local_only": False
            },
            "google_search_console": {
                "name": "Google Search Console API",
                "type": "First-Party Google API",
                "status": "OAuth Active / Data Pending",
                "implemented": False,
                "description": "Google OAuth authorization active. Direct Search Console API metric retrieval requires configuring GSC API data endpoint.",
                "credentials_required": True,
                "local_only": False
            },
            "pagespeed_insights": {
                "name": "PageSpeed Insights API",
                "type": "First-Party API",
                "status": "Not Implemented",
                "implemented": False,
                "description": "Core Web Vitals performance API provider implementation not active in backend.",
                "credentials_required": False,
                "local_only": False
            },
            "rank_tracker": {
                "name": "SERP Rank Tracking Engine",
                "type": "Local / Provider Adapter",
                "status": "Not Implemented",
                "implemented": False,
                "description": "Live SERP API provider implementation not active in backend.",
                "credentials_required": False,
                "local_only": True
            },
            "backlink_engine": {
                "name": "Backlink Data Provider Service",
                "type": "External Data Service",
                "status": "Outbound Crawl Links Active / Inbound Unavailable",
                "implemented": True,
                "description": "Analyzes outbound links via website crawl. Inbound backlinks require connecting an external backlink API provider or historical CSV import.",
                "credentials_required": False,
                "local_only": True
            },
            "csv_import": {
                "name": "Advanced Data Import Engine",
                "type": "Optional Fallback Importer",
                "status": "Available (Optional)",
                "implemented": True,
                "description": "Optional historical data import tool for importing keyword, ranking, or backlink CSV files.",
                "credentials_required": False,
                "local_only": True
            }
        }

        if os.path.exists(ds_file):
            try:
                with open(ds_file, "r") as f:
                    saved = json.load(f)
                    default_sources.update(saved)
            except Exception as e:
                print(f"[DATASOURCES] Failed to read datasources.json for key={key}: {e}", flush=True)

        return default_sources

    def update_datasource(self, key: str, source_id: str, updates: Dict[str, Any], domain: str = None) -> Dict[str, Any]:
        proj_dir = self._get_project_dir(key, domain)
        os.makedirs(proj_dir, exist_ok=True)
        ds_file = os.path.join(proj_dir, "datasources.json")
        
        current = self.get_project_datasources(key, domain)
        if source_id in current:
            current[source_id].update(updates)
            
        with open(ds_file, "w") as f:
            json.dump(current, f, indent=4)
            
        return current
