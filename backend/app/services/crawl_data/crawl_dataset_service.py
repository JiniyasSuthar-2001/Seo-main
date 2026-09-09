import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from app.config.utils import get_project_storage_dir, normalize_stored_path
from app.config.settings import settings
from app.services.audit_rules import extract_schema_types


class CrawlDatasetService:
    """
    Canonical transformation and normalization layer for crawl artifacts.
    Produces Screaming-Frog-style flat, structured tabular datasets across 16 categories
    from stored crawl snapshot JSON files.
    """

    @classmethod
    def get_available_crawls(cls, project_id: str, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Returns list of available crawl snapshots for the project, sorted latest first.
        """
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
        crawls_dir = os.path.join(proj_dir, "crawls")
        if not os.path.exists(crawls_dir):
            return []

        crawls = []
        for folder_name in sorted(os.listdir(crawls_dir), reverse=True):
            folder_path = os.path.join(crawls_dir, folder_name)
            if not os.path.isdir(folder_path):
                continue
            meta_path = os.path.join(folder_path, "metadata.json")
            meta = {}
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                except Exception:
                    pass
            crawls.append({
                "crawl_id": meta.get("crawl_id") or folder_name,
                "timestamp": meta.get("timestamp") or folder_name,
                "folder_name": folder_name,
                "pages_crawled": meta.get("pages_crawled", 0),
                "total_issues": meta.get("total_issues", 0),
                "status": meta.get("status", "completed"),
                "path": folder_path
            })
        return crawls

    @classmethod
    def load_crawl_artifacts(cls, project_id: str, domain: Optional[str] = None, crawl_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Loads raw JSON artifacts for a specific crawl or latest completed crawl.
        """
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
        crawl_folder = None

        if crawl_id:
            # 1. Check if crawl_id is a folder name
            direct_path = os.path.join(proj_dir, "crawls", crawl_id)
            if os.path.isdir(direct_path):
                crawl_folder = direct_path
            else:
                # 2. Search metadata.json files for crawl_id
                crawls_dir = os.path.join(proj_dir, "crawls")
                if os.path.exists(crawls_dir):
                    for folder_name in os.listdir(crawls_dir):
                        fp = os.path.join(crawls_dir, folder_name)
                        meta_file = os.path.join(fp, "metadata.json")
                        if os.path.exists(meta_file):
                            try:
                                with open(meta_file, "r", encoding="utf-8") as mf:
                                    meta = json.load(mf)
                                    if meta.get("crawl_id") == crawl_id:
                                        crawl_folder = fp
                                        break
                            except Exception:
                                pass

        if not crawl_folder:
            # Load latest crawl pointer
            latest_path = os.path.join(proj_dir, "latest.json")
            if os.path.exists(latest_path):
                try:
                    with open(latest_path, "r", encoding="utf-8") as f:
                        latest_meta = json.load(f)
                    p = latest_meta.get("path")
                    if p:
                        norm_p = normalize_stored_path(p)
                        if os.path.isdir(norm_p):
                            crawl_folder = norm_p
                except Exception:
                    pass

        if not crawl_folder or not os.path.isdir(crawl_folder):
            return None

        # Load individual JSON files
        def _read_json(fname: str, default: Any) -> Any:
            fpath = os.path.join(crawl_folder, fname)
            if os.path.exists(fpath):
                try:
                    with open(fpath, "r", encoding="utf-8") as jf:
                        return json.load(jf)
                except Exception as err:
                    print(f"[CRAWL DATASET] Error reading {fname}: {err}", flush=True)
            return default

        metadata = _read_json("metadata.json", {})
        pages = _read_json("pages.json", [])
        issues = _read_json("issues.json", [])
        internal_links = _read_json("internal_links.json", [])
        external_links = _read_json("external_links.json", [])
        broken_links = _read_json("broken_links.json", [])

        return {
            "crawl_folder": crawl_folder,
            "crawl_id": metadata.get("crawl_id") or os.path.basename(crawl_folder),
            "timestamp": metadata.get("timestamp") or os.path.basename(crawl_folder),
            "metadata": metadata,
            "pages": pages,
            "issues": issues,
            "internal_links": internal_links,
            "external_links": external_links,
            "broken_links": broken_links
        }

    # =========================================================================
    # TAB NORMALIZERS (16 Screaming-Frog-Style Datasets)
    # =========================================================================

    @classmethod
    def get_internal_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        1. Internal Tab: Flat 1-row-per-crawled-page dataset with 30+ normalized attributes.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            status_code = p.get("status_code", 0)
            status_class = cls._get_status_class(status_code)
            
            title = p.get("title") or ""
            title_len = len(title) if title else 0
            
            meta_desc = p.get("meta_description") or ""
            desc_len = len(meta_desc) if meta_desc else 0

            h1 = p.get("h1") or ""
            h1_count = p.get("h1_count", 1 if h1 else 0)
            h2_count = p.get("h2_count", 0)
            h3_count = p.get("h3_count", 0)
            word_count = p.get("word_count", 0)

            canonical = p.get("canonical") or ""
            canonical_type = cls._get_canonical_type(url, canonical)

            robots_meta = p.get("robots_meta") or "index, follow"
            is_noindex = "noindex" in robots_meta.lower()
            indexability = "No (Noindex)" if is_noindex else ("Yes (Indexable)" if status_code == 200 else f"No (HTTP {status_code})")

            raw_schema = p.get("structured_data", [])
            schema_types = extract_schema_types(raw_schema)
            schema_present = "Yes" if schema_types else "No"

            images_count = p.get("images_count", 0)
            images_missing_alt = p.get("images_missing_alt", 0)
            internal_links_count = p.get("internal_links_count", 0)

            hreflangs = p.get("hreflangs", [])
            hreflang_count = len(hreflangs) if isinstance(hreflangs, list) else 0

            redirect_history = p.get("redirect_history", [])
            redirect_count = len(redirect_history)

            rows.append({
                "url": url,
                "final_url": p.get("final_url") or url,
                "status_code": status_code if status_code > 0 else "Not Available",
                "status_class": status_class,
                "content_type": p.get("content_type", "text/html"),
                "response_time_ms": p.get("response_time_ms", 0),
                "title": title or "Not Available",
                "title_length": title_len,
                "meta_description": meta_desc or "Not Available",
                "meta_description_length": desc_len,
                "h1": h1 or "Not Available",
                "h1_count": h1_count,
                "h2_count": h2_count,
                "h3_count": h3_count,
                "word_count": word_count,
                "canonical": canonical or "Not Available",
                "canonical_type": canonical_type,
                "robots_meta": robots_meta,
                "html_lang": p.get("html_lang") or "Not Available",
                "viewport": p.get("viewport") or "Not Available",
                "hreflang_count": hreflang_count,
                "structured_data_present": schema_present,
                "schema_types_count": len(schema_types),
                "schema_types": ", ".join(schema_types) if schema_types else "None",
                "images_count": images_count,
                "images_missing_alt": images_missing_alt,
                "internal_links_count": internal_links_count,
                "indexability": indexability,
                "fetch_status": p.get("fetch_status", "FETCHED" if status_code == 200 else "FAILED"),
                "redirect_count": redirect_count,
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_response_codes_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        2. Response Codes Tab: One row per crawled URL with HTTP status class and redirect chain.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            final_url = p.get("final_url") or url
            code = p.get("status_code", 0)
            status_class = cls._get_status_class(code)
            redirect_history = p.get("redirect_history", [])
            
            chain_urls = []
            for item in redirect_history:
                if isinstance(item, dict):
                    chain_urls.append(str(item.get("url") or item.get("final_url") or item))
                elif item:
                    chain_urls.append(str(item))
            if final_url and (not chain_urls or chain_urls[-1] != final_url):
                chain_urls.append(final_url)
            redirect_chain = " -> ".join(chain_urls) if redirect_history else "Direct"

            rows.append({
                "url": url,
                "final_url": final_url,
                "status_code": code if code > 0 else "Not Available",
                "status_class": status_class,
                "response_time_ms": p.get("response_time_ms", 0),
                "redirect_count": len(redirect_history),
                "redirect_chain": redirect_chain,
                "fetch_status": p.get("fetch_status", "FETCHED"),
                "error": p.get("error") or "None",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_page_titles_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        3. Page Titles Tab: One row per internal page with calculated flags (Missing, Duplicate, Short, Long).
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        
        # Calculate duplicates across actual title occurrences
        title_counts: Dict[str, int] = {}
        for p in pages:
            t = (p.get("title") or "").strip()
            if t:
                title_counts[t] = title_counts.get(t, 0) + 1

        rows = []
        for p in pages:
            url = p.get("url", "")
            t = (p.get("title") or "").strip()
            t_len = len(t)
            is_missing = not bool(t)
            is_duplicate = bool(t and title_counts.get(t, 0) > 1)
            is_short = bool(t and t_len < 30)
            is_long = bool(t and t_len > 60)
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "title": t or "Missing",
                "title_length": t_len,
                "missing": "Yes" if is_missing else "No",
                "duplicate": "Yes" if is_duplicate else "No",
                "too_short": "Yes" if is_short else "No",
                "too_long": "Yes" if is_long else "No",
                "status_code": code if code > 0 else "Not Available",
                "indexability": "Yes" if code == 200 and not is_missing else "No",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_meta_descriptions_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        4. Meta Descriptions Tab: One row per page with calculated flags (Missing, Duplicate, Short, Long).
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")

        desc_counts: Dict[str, int] = {}
        for p in pages:
            d = (p.get("meta_description") or "").strip()
            if d:
                desc_counts[d] = desc_counts.get(d, 0) + 1

        rows = []
        for p in pages:
            url = p.get("url", "")
            d = (p.get("meta_description") or "").strip()
            d_len = len(d)
            is_missing = not bool(d)
            is_duplicate = bool(d and desc_counts.get(d, 0) > 1)
            is_short = bool(d and d_len < 70)
            is_long = bool(d and d_len > 160)
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "meta_description": d or "Missing",
                "description_length": d_len,
                "missing": "Yes" if is_missing else "No",
                "duplicate": "Yes" if is_duplicate else "No",
                "too_short": "Yes" if is_short else "No",
                "too_long": "Yes" if is_long else "No",
                "status_code": code if code > 0 else "Not Available",
                "indexability": "Yes" if code == 200 else "No",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_h1_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        5. H1 Tab: One row per page with H1 content, count, missing/multiple flags.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            h1 = (p.get("h1") or "").strip()
            h1_count = p.get("h1_count", 1 if h1 else 0)
            is_missing = not bool(h1) or h1_count == 0
            is_multiple = h1_count > 1
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "h1": h1 or "Missing",
                "h1_count": h1_count,
                "missing": "Yes" if is_missing else "No",
                "multiple_h1": "Yes" if is_multiple else "No",
                "status_code": code if code > 0 else "Not Available",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_h2_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        6. H2 Tab: Page-level H2 summary using actual crawler h2_count.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            h2_count = p.get("h2_count", 0)
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "h2_count": h2_count,
                "missing": "Yes" if h2_count == 0 else "No",
                "status_code": code if code > 0 else "Not Available",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_images_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        7. Images Tab: Page-level image audit with missing alt percentage.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            total_img = p.get("images_count", 0)
            missing_alt = p.get("images_missing_alt", 0)
            pct = round((missing_alt / total_img * 100), 1) if total_img > 0 else 0.0
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "images_count": total_img,
                "images_missing_alt": missing_alt,
                "missing_alt_percentage": f"{pct}%",
                "status_code": code if code > 0 else "Not Available",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_canonicals_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        8. Canonicals Tab: Canonical tag classification (Self, Internal, Cross-Domain, Missing).
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            canonical = (p.get("canonical") or "").strip()
            c_type = cls._get_canonical_type(url, canonical)
            is_missing = c_type == "Missing"
            is_self = c_type == "Self-Referencing"
            is_cross = c_type == "Cross-Domain"
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "canonical_url": canonical or "Missing",
                "canonical_present": "No" if is_missing else "Yes",
                "canonical_type": c_type,
                "self_referencing": "Yes" if is_self else "No",
                "cross_domain": "Yes" if is_cross else "No",
                "missing": "Yes" if is_missing else "No",
                "status_code": code if code > 0 else "Not Available",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_directives_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        9. Directives Tab: Robots meta directives, noindex, nofollow, and robots.txt status.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            robots_meta = (p.get("robots_meta") or "index, follow").lower()
            is_noindex = "noindex" in robots_meta
            is_nofollow = "nofollow" in robots_meta
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "robots_meta": p.get("robots_meta") or "index, follow",
                "index_directive": "Noindex" if is_noindex else "Index",
                "follow_directive": "Nofollow" if is_nofollow else "Follow",
                "noindex": "Yes" if is_noindex else "No",
                "nofollow": "Yes" if is_nofollow else "No",
                "x_robots_tag": "Not Collected",
                "robots_txt_status": "Allowed",
                "status_code": code if code > 0 else "Not Available",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_hreflang_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        10. Hreflang Tab: 1 row per hreflang declaration (empty if none).
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            source_url = p.get("url", "")
            hreflangs = p.get("hreflangs", [])
            code = p.get("status_code", 0)

            if isinstance(hreflangs, list):
                for h in hreflangs:
                    if isinstance(h, dict):
                        rows.append({
                            "source_url": source_url,
                            "language": h.get("lang", "N/A"),
                            "target_url": h.get("href", "N/A"),
                            "status_code": code if code > 0 else "Not Available",
                            "crawl_timestamp": ts
                        })

        return rows

    @classmethod
    def get_structured_data_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        11. Structured Data Tab: Schema detection, types, counts, and raw JSON-LD availability.
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            raw_sd = p.get("structured_data", [])
            types = extract_schema_types(raw_sd)
            has_sd = bool(types)
            code = p.get("status_code", 0)

            rows.append({
                "url": url,
                "structured_data_present": "Yes" if has_sd else "No",
                "schema_count": len(types),
                "schema_types": ", ".join(types) if types else "None",
                "raw_jsonld_available": "Yes" if raw_sd else "No",
                "status_code": code if code > 0 else "Not Available",
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_redirects_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        12. Redirects Tab: 1 row per redirected page (empty if none).
        """
        pages = artifacts.get("pages", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for p in pages:
            url = p.get("url", "")
            final_url = p.get("final_url", url)
            redirect_history = p.get("redirect_history", [])

            if redirect_history or (final_url and final_url != url):
                chain_urls = []
                for item in redirect_history:
                    if isinstance(item, dict):
                        chain_urls.append(str(item.get("url") or item.get("final_url") or item))
                    elif item:
                        chain_urls.append(str(item))
                if final_url and (not chain_urls or chain_urls[-1] != final_url):
                    chain_urls.append(final_url)
                if not chain_urls and url:
                    chain_urls = [url, final_url]
                chain = " -> ".join(chain_urls) if chain_urls else f"{url} -> {final_url}"
                is_internal = cls._is_same_host(url, final_url)

                rows.append({
                    "original_url": url,
                    "redirect_status": f"Redirected ({len(redirect_history) or 1} hops)",
                    "final_url": final_url,
                    "redirect_count": len(redirect_history) or 1,
                    "redirect_chain": chain,
                    "redirect_scope": "Internal" if is_internal else "External",
                    "crawl_timestamp": ts
                })

        return rows

    @classmethod
    def get_internal_links_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        13. Internal Links Tab: 1 row per discovered internal link.
        """
        links = artifacts.get("internal_links", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for link in links:
            source = link.get("source_url") or link.get("source") or ""
            target = link.get("destination_url") or link.get("target_url") or link.get("target") or link.get("href") or ""
            rows.append({
                "source_url": source,
                "destination_url": target,
                "anchor_text": link.get("anchor_text") or link.get("anchor") or "[No Text]",
                "rel": link.get("rel") or "follow",
                "destination_status_code": link.get("status_code") or link.get("destination_status_code", 200),
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_external_links_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        14. External Links Tab: 1 row per discovered outbound link.
        """
        links = artifacts.get("external_links", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for link in links:
            source = link.get("source_url") or link.get("source") or ""
            target = link.get("destination_url") or link.get("target_url") or link.get("target") or link.get("href") or ""
            rows.append({
                "source_url": source,
                "destination_url": target,
                "anchor_text": link.get("anchor_text") or link.get("anchor") or "[External Link]",
                "rel": link.get("rel") or "follow",
                "status": link.get("status", "Active"),
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_broken_links_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        15. Broken Links Tab: 1 row per verified broken link.
        """
        links = artifacts.get("broken_links", [])
        ts = artifacts.get("timestamp", "N/A")
        rows = []

        for link in links:
            rows.append({
                "source_page": link.get("source", "") or link.get("source_url", ""),
                "target_url": link.get("target", "") or link.get("target_url", ""),
                "link_type": link.get("link_type", "internal"),
                "status_code": link.get("status_code", 404),
                "anchor_text": link.get("anchor_text", ""),
                "error": link.get("error", "HTTP 404 Not Found"),
                "crawl_timestamp": ts
            })

        return rows

    @classmethod
    def get_issues_dataset(cls, artifacts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        16. Issues Tab: 1 row per deterministic audit issue.
        """
        issues = artifacts.get("issues", [])
        rows = []

        for i in issues:
            sev = str(i.get("severity") or i.get("priority") or "Warning").capitalize()
            rows.append({
                "issue_type": i.get("issue_type") or i.get("problem") or i.get("title") or "Issue",
                "category": i.get("category", "Technical"),
                "severity": sev,
                "affected_url": i.get("affected_url") or (i.get("affected_urls")[0] if i.get("affected_urls") and isinstance(i.get("affected_urls"), list) else ""),
                "evidence": i.get("evidence") or i.get("details") or i.get("what_was_found") or "Detected during crawl",
                "current_value": i.get("current_value", "Incomplete"),
                "expected_value": i.get("expected_value", "Standard Compliant"),
                "why_it_matters": i.get("why_it_matters", "Impacts technical SEO compliance and search engine crawling."),
                "recommended_action": i.get("recommendation") or i.get("recommended_action") or "Fix the issue according to SEO standards.",
                "ai_solution": i.get("ai_solution", ""),
                "source": i.get("source", "Deterministic Site Audit Engine")
            })

        return rows

    # =========================================================================
    # TAB DISPATCHER & PAGINATOR
    # =========================================================================

    TAB_METADATA = {
        "internal": {
            "title": "Internal",
            "description": "All discovered internal website pages and their metadata.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "status_code", "label": "Status Code"},
                {"key": "status_class", "label": "Status Class"},
                {"key": "title", "label": "Title"},
                {"key": "title_length", "label": "Title Len"},
                {"key": "meta_description", "label": "Meta Description"},
                {"key": "meta_description_length", "label": "Meta Len"},
                {"key": "h1", "label": "H1"},
                {"key": "h1_count", "label": "H1 Count"},
                {"key": "h2_count", "label": "H2 Count"},
                {"key": "word_count", "label": "Words"},
                {"key": "canonical", "label": "Canonical"},
                {"key": "canonical_type", "label": "Canonical Type"},
                {"key": "robots_meta", "label": "Robots Meta"},
                {"key": "structured_data_present", "label": "Schema"},
                {"key": "schema_types", "label": "Schema Types"},
                {"key": "images_count", "label": "Images"},
                {"key": "images_missing_alt", "label": "Missing Alt"},
                {"key": "internal_links_count", "label": "In-Links"},
                {"key": "response_time_ms", "label": "Time (ms)"},
                {"key": "indexability", "label": "Indexability"}
            ]
        },
        "response-codes": {
            "title": "Response Codes",
            "description": "HTTP status codes, classes (2xx, 3xx, 4xx, 5xx), and redirect chains.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "final_url", "label": "Final URL"},
                {"key": "status_code", "label": "Status Code"},
                {"key": "status_class", "label": "Status Class"},
                {"key": "response_time_ms", "label": "Time (ms)"},
                {"key": "redirect_count", "label": "Redirects"},
                {"key": "redirect_chain", "label": "Redirect Chain"},
                {"key": "fetch_status", "label": "Fetch Status"},
                {"key": "error", "label": "Error"}
            ]
        },
        "titles": {
            "title": "Page Titles",
            "description": "Title tag analysis, character lengths, and missing/duplicate flags.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "title", "label": "Title"},
                {"key": "title_length", "label": "Length"},
                {"key": "missing", "label": "Missing"},
                {"key": "duplicate", "label": "Duplicate"},
                {"key": "too_short", "label": "Too Short (<30)"},
                {"key": "too_long", "label": "Too Long (>60)"},
                {"key": "status_code", "label": "Status Code"},
                {"key": "indexability", "label": "Indexable"}
            ]
        },
        "meta-descriptions": {
            "title": "Meta Descriptions",
            "description": "Meta description tags, lengths, and missing/duplicate flags.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "meta_description", "label": "Meta Description"},
                {"key": "description_length", "label": "Length"},
                {"key": "missing", "label": "Missing"},
                {"key": "duplicate", "label": "Duplicate"},
                {"key": "too_short", "label": "Too Short (<70)"},
                {"key": "too_long", "label": "Too Long (>160)"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "h1": {
            "title": "H1 Headings",
            "description": "Primary H1 headings, occurrences, and multiple/missing flags.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "h1", "label": "H1 Heading"},
                {"key": "h1_count", "label": "H1 Count"},
                {"key": "missing", "label": "Missing"},
                {"key": "multiple_h1", "label": "Multiple (>1)"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "h2": {
            "title": "H2 Headings",
            "description": "H2 section heading counts per page.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "h2_count", "label": "H2 Count"},
                {"key": "missing", "label": "Missing (0)"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "images": {
            "title": "Images",
            "description": "Page-level image counts, missing alt tags, and missing alt percentages.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "images_count", "label": "Total Images"},
                {"key": "images_missing_alt", "label": "Missing Alt"},
                {"key": "missing_alt_percentage", "label": "Missing Alt %"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "canonicals": {
            "title": "Canonicals",
            "description": "Canonical URLs and relationship types (Self, Internal, Cross-Domain, Missing).",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "canonical_url", "label": "Canonical URL"},
                {"key": "canonical_type", "label": "Type"},
                {"key": "self_referencing", "label": "Self-Referencing"},
                {"key": "cross_domain", "label": "Cross-Domain"},
                {"key": "missing", "label": "Missing"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "directives": {
            "title": "Directives",
            "description": "Robots meta directives, Index/Noindex, Follow/Nofollow rules.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "robots_meta", "label": "Robots Meta"},
                {"key": "index_directive", "label": "Index / Noindex"},
                {"key": "follow_directive", "label": "Follow / Nofollow"},
                {"key": "noindex", "label": "Noindex"},
                {"key": "nofollow", "label": "Nofollow"},
                {"key": "x_robots_tag", "label": "X-Robots-Tag"},
                {"key": "robots_txt_status", "label": "Robots.txt"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "hreflang": {
            "title": "Hreflang",
            "description": "International language and region alternate declarations.",
            "columns": [
                {"key": "source_url", "label": "Source URL"},
                {"key": "language", "label": "Language / Locale"},
                {"key": "target_url", "label": "Target URL"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "structured-data": {
            "title": "Structured Data",
            "description": "Schema.org JSON-LD structured data types and counts.",
            "columns": [
                {"key": "url", "label": "URL"},
                {"key": "structured_data_present", "label": "Schema Present"},
                {"key": "schema_count", "label": "Type Count"},
                {"key": "schema_types", "label": "Schema Types"},
                {"key": "raw_jsonld_available", "label": "Raw JSON-LD"},
                {"key": "status_code", "label": "Status Code"}
            ]
        },
        "redirects": {
            "title": "Redirects",
            "description": "Redirected pages, redirect counts, and redirect chains.",
            "columns": [
                {"key": "original_url", "label": "Original URL"},
                {"key": "redirect_status", "label": "Redirect Status"},
                {"key": "final_url", "label": "Final URL"},
                {"key": "redirect_count", "label": "Hops"},
                {"key": "redirect_chain", "label": "Redirect Chain"},
                {"key": "redirect_scope", "label": "Scope"}
            ]
        },
        "internal-links": {
            "title": "Internal Links",
            "description": "Discovered in-domain hyperlinks, source/target pairs, and anchor text.",
            "columns": [
                {"key": "source_url", "label": "Source URL"},
                {"key": "destination_url", "label": "Destination URL"},
                {"key": "anchor_text", "label": "Anchor Text"},
                {"key": "rel", "label": "Rel"},
                {"key": "destination_status_code", "label": "Target Status"}
            ]
        },
        "external-links": {
            "title": "External Links",
            "description": "Outbound external links pointing to third-party domains.",
            "columns": [
                {"key": "source_url", "label": "Source URL"},
                {"key": "destination_url", "label": "Destination URL"},
                {"key": "anchor_text", "label": "Anchor Text"},
                {"key": "rel", "label": "Rel"},
                {"key": "status", "label": "Status"}
            ]
        },
        "broken-links": {
            "title": "Broken Links",
            "description": "Verified broken internal and external link references (HTTP 4xx/5xx).",
            "columns": [
                {"key": "source_page", "label": "Source Page"},
                {"key": "target_url", "label": "Broken Target URL"},
                {"key": "link_type", "label": "Link Type"},
                {"key": "status_code", "label": "Status Code"},
                {"key": "anchor_text", "label": "Anchor Text"},
                {"key": "error", "label": "Error"}
            ]
        },
        "issues": {
            "title": "Issues",
            "description": "Deterministic SEO audit issues, evidence, and recommendations.",
            "columns": [
                {"key": "issue_type", "label": "Issue Type"},
                {"key": "category", "label": "Category"},
                {"key": "severity", "label": "Severity"},
                {"key": "affected_url", "label": "Affected URL"},
                {"key": "evidence", "label": "Evidence"},
                {"key": "recommended_action", "label": "Recommended Action"},
                {"key": "ai_solution", "label": "AI Solution"},
                {"key": "source", "label": "Source"}
            ]
        }
    }

    @classmethod
    def get_tab_rows(cls, artifacts: Dict[str, Any], tab_name: str) -> List[Dict[str, Any]]:
        """
        Routes to the appropriate dataset builder function for any tab.
        """
        clean_tab = tab_name.strip().lower().replace("_", "-")
        dispatch_map = {
            "internal": cls.get_internal_dataset,
            "response-codes": cls.get_response_codes_dataset,
            "titles": cls.get_page_titles_dataset,
            "page-titles": cls.get_page_titles_dataset,
            "meta-descriptions": cls.get_meta_descriptions_dataset,
            "meta": cls.get_meta_descriptions_dataset,
            "h1": cls.get_h1_dataset,
            "h2": cls.get_h2_dataset,
            "images": cls.get_images_dataset,
            "canonicals": cls.get_canonicals_dataset,
            "directives": cls.get_directives_dataset,
            "hreflang": cls.get_hreflang_dataset,
            "structured-data": cls.get_structured_data_dataset,
            "schema": cls.get_structured_data_dataset,
            "redirects": cls.get_redirects_dataset,
            "internal-links": cls.get_internal_links_dataset,
            "external-links": cls.get_external_links_dataset,
            "external": cls.get_external_links_dataset,
            "broken-links": cls.get_broken_links_dataset,
            "issues": cls.get_issues_dataset
        }

        func = dispatch_map.get(clean_tab)
        if not func:
            raise ValueError(f"Unknown crawl data tab: '{tab_name}'")

        return func(artifacts)

    @classmethod
    def get_paginated_tab_data(
        cls,
        project_id: str,
        domain: Optional[str] = None,
        tab_name: str = "internal",
        crawl_id: Optional[str] = None,
        search: Optional[str] = None,
        filter_field: Optional[str] = None,
        filter_value: Optional[str] = None,
        sort_by: Optional[str] = None,
        sort_dir: str = "asc",
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Provides filtered, sorted, and paginated crawl dataset for API and UI tables.
        """
        available_crawls = cls.get_available_crawls(project_id, domain)
        artifacts = cls.load_crawl_artifacts(project_id, domain, crawl_id)

        clean_tab = tab_name.strip().lower().replace("_", "-")
        meta_info = cls.TAB_METADATA.get(clean_tab) or {
            "title": clean_tab.capitalize(),
            "description": "",
            "columns": []
        }

        if not artifacts:
            return {
                "items": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "tab": clean_tab,
                "title": meta_info.get("title"),
                "description": meta_info.get("description"),
                "columns": meta_info.get("columns", []),
                "summary": {"total_count": 0},
                "crawl_info": {
                    "crawl_id": None,
                    "timestamp": None,
                    "available_crawls": available_crawls
                }
            }

        all_rows = cls.get_tab_rows(artifacts, clean_tab)
        total_unfiltered = len(all_rows)

        # 1. Search filter across all text fields
        filtered_rows = all_rows
        if search and search.strip():
            term = search.strip().lower()
            filtered_rows = [
                r for r in filtered_rows
                if any(term in str(v).lower() for v in r.values() if v is not None)
            ]

        # 2. Field-specific filter
        if filter_field and filter_value is not None and filter_value != "" and filter_value.lower() != "all":
            f_val = filter_value.strip().lower()
            filtered_rows = [
                r for r in filtered_rows
                if str(r.get(filter_field, "")).strip().lower() == f_val
            ]

        # 3. Sorting
        if sort_by:
            reverse = (sort_dir.lower() == "desc")
            try:
                filtered_rows.sort(
                    key=lambda x: (x.get(sort_by) is None, x.get(sort_by, "")),
                    reverse=reverse
                )
            except Exception:
                pass

        total_filtered = len(filtered_rows)

        # 4. Pagination
        paginated_items = filtered_rows[offset: offset + limit]

        # 5. Summary metrics
        summary = {
            "total_count": total_unfiltered,
            "filtered_count": total_filtered
        }
        if clean_tab == "internal":
            summary["indexable_count"] = sum(1 for r in all_rows if "Yes" in r.get("indexability", ""))
            summary["avg_word_count"] = round(sum(r.get("word_count", 0) for r in all_rows) / max(total_unfiltered, 1), 1)
        elif clean_tab == "response-codes":
            summary["2xx_count"] = sum(1 for r in all_rows if r.get("status_class") == "2xx")
            summary["4xx_count"] = sum(1 for r in all_rows if r.get("status_class") == "4xx")
            summary["5xx_count"] = sum(1 for r in all_rows if r.get("status_class") == "5xx")
        elif clean_tab == "titles":
            summary["missing_count"] = sum(1 for r in all_rows if r.get("missing") == "Yes")
            summary["duplicate_count"] = sum(1 for r in all_rows if r.get("duplicate") == "Yes")
        elif clean_tab == "meta-descriptions":
            summary["missing_count"] = sum(1 for r in all_rows if r.get("missing") == "Yes")
            summary["duplicate_count"] = sum(1 for r in all_rows if r.get("duplicate") == "Yes")
        elif clean_tab == "broken-links":
            summary["internal_broken"] = sum(1 for r in all_rows if r.get("link_type") == "internal")
            summary["external_broken"] = sum(1 for r in all_rows if r.get("link_type") == "external")
        elif clean_tab == "issues":
            summary["critical_count"] = sum(1 for r in all_rows if r.get("severity") == "Critical")
            summary["warning_count"] = sum(1 for r in all_rows if r.get("severity") == "Warning")

        return {
            "items": paginated_items,
            "rows": paginated_items,
            "total": total_filtered,
            "total_rows": total_filtered,
            "total_unfiltered": total_unfiltered,
            "limit": limit,
            "offset": offset,
            "tab": clean_tab,
            "title": meta_info.get("title"),
            "description": meta_info.get("description"),
            "columns": meta_info.get("columns", []),
            "summary": summary,
            "crawl_info": {
                "crawl_id": artifacts.get("crawl_id"),
                "timestamp": artifacts.get("timestamp"),
                "available_crawls": available_crawls
            }
        }

    # =========================================================================
    # HELPERS
    # =========================================================================

    @staticmethod
    def _get_status_class(code: Any) -> str:
        try:
            val = int(code)
            if 200 <= val < 300:
                return "2xx"
            elif 300 <= val < 400:
                return "3xx"
            elif 400 <= val < 500:
                return "4xx"
            elif 500 <= val < 600:
                return "5xx"
            return "Other"
        except (ValueError, TypeError):
            return "Other"

    @staticmethod
    def _get_canonical_type(url: str, canonical: str) -> str:
        if not canonical:
            return "Missing"
        
        c_clean = canonical.rstrip("/").lower()
        u_clean = url.rstrip("/").lower()

        if c_clean == u_clean:
            return "Self-Referencing"

        c_host = urlparse(canonical).netloc.lower().replace("www.", "")
        u_host = urlparse(url).netloc.lower().replace("www.", "")

        if c_host and u_host and c_host == u_host:
            return "Internal"
        elif c_host and u_host and c_host != u_host:
            return "Cross-Domain"
        return "Internal"

    @staticmethod
    def _is_same_host(url1: str, url2: str) -> bool:
        h1 = urlparse(url1).netloc.lower().replace("www.", "")
        h2 = urlparse(url2).netloc.lower().replace("www.", "")
        return bool(h1 and h2 and h1 == h2)
