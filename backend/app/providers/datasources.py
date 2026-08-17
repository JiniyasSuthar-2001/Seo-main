import os
import json
from typing import Dict, Any
from app.config.utils import get_sanitized_domain

class DataSourceManager:
    def __init__(self, base_dir: str = "data/websites"):
        self.base_dir = base_dir

    def get_project_datasources(self, domain: str) -> Dict[str, Any]:
        safe_domain = get_sanitized_domain(domain)
        ds_file = os.path.join(self.base_dir, safe_domain, "datasources.json")
        
        default_sources = {
            "crawler": {
                "name": "Website Crawler & HTML Parser",
                "type": "Local Engine",
                "status": "Connected",
                "description": "Directly crawls HTML, sitemaps, canonicals, and metadata.",
                "credentials_required": False,
                "local_only": True
            },
            "nlp_keywords": {
                "name": "Local Open-Source NLP Keyword Extractor",
                "type": "Local Engine",
                "status": "Connected",
                "description": "Extracts content topics, n-grams, and page-to-topic mappings.",
                "credentials_required": False,
                "local_only": True
            },
            "google_autocomplete": {
                "name": "Google Autocomplete Keyword Ideas",
                "type": "Public Free API",
                "status": "Available",
                "description": "Generates real-time keyword suggestions from Google Search API.",
                "credentials_required": False,
                "local_only": False
            },
            "google_search_console": {
                "name": "Google Search Console API",
                "type": "First-Party Official API",
                "status": "Not Connected",
                "description": "Fetches clicks, impressions, CTR, and search queries.",
                "credentials_required": True,
                "local_only": False
            },
            "pagespeed_insights": {
                "name": "PageSpeed Insights API",
                "type": "First-Party API",
                "status": "Available",
                "description": "Measures Core Web Vitals (LCP, INP, CLS, TTFB).",
                "credentials_required": False,
                "local_only": False
            },
            "rank_tracker": {
                "name": "SERP Rank Tracking Engine",
                "type": "Local / Provider Adapter",
                "status": "Available",
                "description": "Monitors target keyword positions across Google & Bing.",
                "credentials_required": False,
                "local_only": True
            },
            "backlink_engine": {
                "name": "Backlink & Link Graph Engine",
                "type": "Crawler + Provider Adapter",
                "status": "Connected (Outbound Links)",
                "description": "Maps internal/external outbound links. Inbound backlinks require provider/CSV dataset.",
                "credentials_required": False,
                "local_only": True
            },
            "csv_import": {
                "name": "CSV Fallback Dataset Import",
                "type": "Import Fallback",
                "status": "Available",
                "description": "Import external keyword, backlink, or ranking CSV files.",
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
                print(f"[DATASOURCES] Failed to read datasources.json for {domain}: {e}", flush=True)

        return default_sources

    def update_datasource(self, domain: str, source_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        safe_domain = get_sanitized_domain(domain)
        proj_dir = os.path.join(self.base_dir, safe_domain)
        os.makedirs(proj_dir, exist_ok=True)
        ds_file = os.path.join(proj_dir, "datasources.json")
        
        current = self.get_project_datasources(domain)
        if source_id in current:
            current[source_id].update(updates)
            
        with open(ds_file, "w") as f:
            json.dump(current, f, indent=4)
            
        return current
