import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.config.settings import settings


from urllib.parse import urlparse

class BacklinkDataService:
    """
    Backlink Data Provider & Service Abstraction.
    Distinguishes strictly between:
      1. Outbound External Links (Discovered by crawling the target website - Crawled Data)
      2. Inbound Backlinks (Links pointing TO the website from external domains - Backlink Provider or Imported Dataset)
    """

    @classmethod
    def get_project_backlink_data(
        cls, 
        project: Project, 
        limit: int = 50, 
        offset: int = 0
    ) -> Dict[str, Any]:
        if not project or not project.domain:
            return {
                "domain": project.domain if project else "",
                "status": "unavailable",
                "backlinks": [],
                "referring_domains": [],
                "summary": {
                    "inbound_backlinks": 0,
                    "referring_domains": 0,
                    "outbound_external_links": 0
                },
                "outbound_summary": {
                    "total_outbound_links": 0,
                    "unique_external_urls": 0,
                    "unique_external_domains": 0,
                    "nofollow_count": 0,
                    "sponsored_count": 0,
                    "ugc_count": 0,
                    "broken_count": 0
                },
                "outbound_links": [],
                "provenance": {
                    "source_type": "unavailable",
                    "source_label": "Unavailable",
                    "message": "No project domain configured."
                }
            }

        domain = project.domain
        proj_storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)

        # 1. Fetch imported / provider inbound backlink JSON dataset if present
        backlinks_file = os.path.join(proj_storage_dir, "backlinks.json")
        inbound_backlinks: List[Dict[str, Any]] = []
        is_imported = False

        if os.path.exists(backlinks_file):
            try:
                with open(backlinks_file, "r") as bf:
                    inbound_backlinks = json.load(bf)
                    is_imported = True
            except Exception as e:
                print(f"[BACKLINK SERVICE] Error reading backlinks file for {domain}: {e}", flush=True)

        # 2. Fetch outbound external links discovered by the crawler using canonical dataset service
        from app.services.crawl_data.crawl_dataset_service import CrawlDatasetService

        artifacts = CrawlDatasetService.load_crawl_artifacts(project.id, domain)
        grouped_outbound = []

        if artifacts:
            grouped_outbound = CrawlDatasetService.get_external_links_dataset(artifacts)
        else:
            # Fallback to direct snapshot files if legacy structure
            latest_path = os.path.join(proj_storage_dir, "latest.json")
            raw_outbound: List[Dict[str, Any]] = []
            crawl_timestamp = "Not collected"
            if os.path.exists(latest_path):
                try:
                    with open(latest_path, "r") as f:
                        latest = json.load(f)
                    crawl_dir = normalize_stored_path(latest.get("path"))
                    if crawl_dir and os.path.exists(os.path.join(crawl_dir, "external_links.json")):
                        with open(os.path.join(crawl_dir, "external_links.json"), "r") as ef:
                            raw_outbound = json.load(ef)
                except Exception as e:
                    print(f"[BACKLINK SERVICE] Error loading external outbound links: {e}", flush=True)
            
            grouped_outbound = CrawlDatasetService.get_external_links_dataset({
                "external_links": raw_outbound,
                "timestamp": crawl_timestamp
            })

        # Calculate metrics from canonical grouped dataset
        total_destinations = len(grouped_outbound)
        total_outbound_links = sum(g.get("occurrences", 1) for g in grouped_outbound)
        unique_domains = set()
        nofollow_count = 0
        sponsored_count = 0
        ugc_count = 0
        broken_count = 0

        for g in grouped_outbound:
            dom = g.get("destination_domain")
            if dom and dom not in ("Not collected", "Unknown", ""):
                unique_domains.add(dom)

            rel_str = str(g.get("rel") or "").lower()
            if "nofollow" in rel_str:
                nofollow_count += 1
            if "sponsored" in rel_str:
                sponsored_count += 1
            if "ugc" in rel_str:
                ugc_count += 1

            if g.get("is_broken") or (isinstance(g.get("status_code"), int) and g.get("status_code") >= 400):
                broken_count += 1

        # 3. Calculate referring domains for inbound backlinks
        ref_domains = set()
        for b in inbound_backlinks:
            src_domain = b.get("source_domain") or b.get("referring_domain")
            if src_domain:
                ref_domains.add(src_domain)

        has_inbound_data = len(inbound_backlinks) > 0

        # Provenance mapping
        if has_inbound_data:
            source_type = "import" if is_imported else "backlink_provider"
            source_label = "Imported Data" if is_imported else "Backlink Provider"
            message = f"Inbound backlink dataset active ({len(inbound_backlinks)} links discovered)."
        else:
            source_type = "unavailable"
            source_label = "Unavailable"
            message = (
                "No backlink dataset connected. Website crawling analyzes outbound links found on your pages, "
                "but backlinks pointing TO your website require a backlink data provider or imported CSV dataset."
            )

        return {
            "domain": domain,
            "status": "connected" if has_inbound_data else "not_connected",
            "summary": {
                "inbound_backlinks": len(inbound_backlinks),
                "referring_domains": len(ref_domains),
                "outbound_external_links": total_outbound_links,
                "outbound_destinations": total_destinations
            },
            "outbound_summary": {
                "total_outbound_links": total_outbound_links,
                "unique_external_urls": total_destinations,
                "unique_external_domains": len(unique_domains),
                "nofollow_count": nofollow_count,
                "sponsored_count": sponsored_count,
                "ugc_count": ugc_count,
                "broken_count": broken_count
            },
            "backlinks": inbound_backlinks[offset : offset + limit],
            "referring_domains": list(ref_domains),
            "outbound_links": grouped_outbound,
            "outbound_links_paginated": grouped_outbound[offset : offset + limit],
            "provenance": {
                "source_type": source_type,
                "source_label": source_label,
                "outbound_label": "Crawled Data — Outbound",
                "confidence": 100.0 if has_inbound_data else 0.0,
                "message": message
            }
        }

