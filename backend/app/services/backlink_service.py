import os
import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
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
        safe_domain = get_sanitized_domain(domain)

        # 1. Fetch imported / provider inbound backlink JSON dataset if present
        backlinks_file = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "backlinks.json")
        inbound_backlinks: List[Dict[str, Any]] = []
        is_imported = False

        if os.path.exists(backlinks_file):
            try:
                with open(backlinks_file, "r") as bf:
                    inbound_backlinks = json.load(bf)
                    is_imported = True
            except Exception as e:
                print(f"[BACKLINK SERVICE] Error reading backlinks file for {domain}: {e}", flush=True)

        # 2. Fetch outbound external links discovered by the crawler
        latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")
        raw_outbound: List[Dict[str, Any]] = []
        crawl_timestamp = "Not collected"
        if os.path.exists(latest_path):
            try:
                with open(latest_path, "r") as f:
                    latest = json.load(f)
                crawl_dir = normalize_stored_path(latest.get("path"))
                if crawl_dir:
                    meta_file = os.path.join(crawl_dir, "metadata.json")
                    if os.path.exists(meta_file):
                        try:
                            with open(meta_file, "r") as mf:
                                meta_data = json.load(mf)
                                crawl_timestamp = meta_data.get("timestamp") or "Not collected"
                        except Exception:
                            pass

                    ext_file = os.path.join(crawl_dir, "external_links.json")
                    if os.path.exists(ext_file):
                        with open(ext_file, "r") as ef:
                            raw_outbound = json.load(ef)
            except Exception as e:
                print(f"[BACKLINK SERVICE] Error loading external outbound links: {e}", flush=True)

        # Process and normalize outbound links
        formatted_outbound = []
        unique_urls = set()
        unique_domains = set()
        nofollow_count = 0
        sponsored_count = 0
        ugc_count = 0
        broken_count = 0

        for link in raw_outbound:
            src = link.get("source") or link.get("source_url") or link.get("source_page") or "Not collected"
            target = link.get("target") or link.get("destination_url") or link.get("target_url") or "Not collected"
            
            dest_domain = "Not collected"
            if target and target != "Not collected":
                unique_urls.add(target)
                try:
                    parsed_dest = urlparse(target)
                    dest_domain = parsed_dest.netloc.lower().replace("www.", "") or "Not collected"
                    if dest_domain != "Not collected":
                        unique_domains.add(dest_domain)
                except Exception:
                    pass

            # Classify Link Type (Social, Email, Telephone, External, Nofollow, etc.)
            target_lower = target.lower()
            rel_str = str(link.get("rel") or "").lower()
            rel_types = []
            
            if target_lower.startswith("mailto:"):
                link_type_category = "Email Link"
            elif target_lower.startswith("tel:"):
                link_type_category = "Telephone Link"
            elif any(s in target_lower for s in ["facebook.com", "instagram.com", "twitter.com", "x.com", "linkedin.com", "youtube.com", "pinterest.com", "tiktok.com"]):
                link_type_category = "Social Link"
            else:
                link_type_category = "External Link"

            if "nofollow" in rel_str:
                rel_types.append("Nofollow")
                nofollow_count += 1
            if "sponsored" in rel_str:
                rel_types.append("Sponsored")
                sponsored_count += 1
            if "ugc" in rel_str:
                rel_types.append("UGC")
                ugc_count += 1

            rel_label = ", ".join(rel_types) if rel_types else "Follow"
            full_link_type = f"{link_type_category} ({rel_label})" if rel_types else link_type_category

            st_code = link.get("status_code")
            if isinstance(st_code, int) and st_code >= 400:
                broken_count += 1
            formatted_status = st_code if isinstance(st_code, int) and st_code > 0 else "Not checked"

            # Smart Anchor Text Fallback
            raw_anchor = (link.get("anchor_text") or "").strip()
            if not raw_anchor or raw_anchor == "[External Link]":
                if any(ext in target_lower for ext in [".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", "image", "icon"]):
                    anchor_display = "Image link"
                else:
                    anchor_display = "No anchor text"
            else:
                anchor_display = raw_anchor

            formatted_outbound.append({
                "source_url": src,
                "source_page": src,
                "source": src,
                "destination_url": target,
                "target_url": target,
                "target": target,
                "destination_domain": dest_domain,
                "anchor_text": anchor_display,
                "link_type": full_link_type,
                "rel": rel_str or "Not collected",
                "status_code": formatted_status,
                "first_discovered": link.get("first_discovered") or crawl_timestamp,
                "last_discovered": link.get("last_discovered") or crawl_timestamp,
                "data_source": "Website Scan"
            })

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
                "outbound_external_links": len(formatted_outbound)
            },
            "outbound_summary": {
                "total_outbound_links": len(formatted_outbound),
                "unique_external_urls": len(unique_urls),
                "unique_external_domains": len(unique_domains),
                "nofollow_count": nofollow_count,
                "sponsored_count": sponsored_count,
                "ugc_count": ugc_count,
                "broken_count": broken_count
            },
            "backlinks": inbound_backlinks[offset : offset + limit],
            "referring_domains": list(ref_domains),
            "outbound_links": formatted_outbound,  # Return full list for client filtering/searching or pagination
            "outbound_links_paginated": formatted_outbound[offset : offset + limit],
            "provenance": {
                "source_type": source_type,
                "source_label": source_label,
                "outbound_label": "Crawled Data — Outbound",
                "confidence": 100.0 if has_inbound_data else 0.0,
                "message": message
            }
        }
