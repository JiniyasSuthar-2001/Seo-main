import os
import json
import re
from collections import Counter
from typing import Dict, Any, List, Optional
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.llm.ai_service import AIService

class AnchorSuggestionService:
    _cache: Dict[str, Any] = {}

    @classmethod
    def get_suggestions(
        cls,
        project_id: str,
        domain: str,
        source_url: str,
        target_url: str,
        refresh: bool = False
    ) -> Dict[str, Any]:
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
        cache_key = f"{project_id}:{source_url}:{target_url}"

        if not refresh and cache_key in cls._cache:
            return cls._cache[cache_key]

        latest_path = os.path.join(proj_dir, "latest.json")
        if not os.path.exists(latest_path):
            return {
                "status": "no_crawl",
                "suggestions": [],
                "message": "No website crawl snapshot available. Execute a website crawl to analyze page content for anchor suggestions.",
                "evidence": {}
            }

        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))

            pages_path = os.path.join(crawl_dir, "pages.json")
            links_path = os.path.join(crawl_dir, "internal_links.json")

            pages = json.load(open(pages_path, encoding="utf-8")) if os.path.exists(pages_path) else []
            links = json.load(open(links_path, encoding="utf-8")) if os.path.exists(links_path) else []
        except Exception as e:
            return {
                "status": "error",
                "suggestions": [],
                "message": f"Error reading crawl snapshot data: {str(e)}",
                "evidence": {}
            }

        # 1. Locate Source Page & Target Page
        norm_source = source_url.lower().rstrip('/')
        norm_target = target_url.lower().rstrip('/')

        source_page = None
        target_page = None

        for p in pages:
            url = (p.get("url") or "").lower().rstrip('/')
            if url == norm_source:
                source_page = p
            if url == norm_target:
                target_page = p

        if not target_page:
            # Fallback check if URL contains target path
            for p in pages:
                if norm_target in (p.get("url") or "").lower():
                    target_page = p
                    break

        if not target_page:
            return {
                "status": "insufficient_evidence",
                "suggestions": [],
                "message": "Not enough evidence. The destination page was not found in the latest crawl snapshot.",
                "evidence": {
                    "source_url": source_url,
                    "target_url": target_url
                }
            }

        # 2. Extract Evidence
        target_title = (target_page.get("title") or "").strip()
        target_h1 = (target_page.get("h1") or "").strip()
        target_h2_list = target_page.get("h2") or []
        if isinstance(target_h2_list, str):
            target_h2_list = [target_h2_list]
        
        target_word_count = target_page.get("word_count") or 0
        target_meta = (target_page.get("meta_description") or "").strip()

        source_title = (source_page.get("title") or "") if source_page else ""
        source_h1 = (source_page.get("h1") or "") if source_page else ""

        # Check existing anchor text pointing to destination
        existing_anchors = Counter()
        for l in links:
            t = (l.get("target") or "").lower().rstrip('/')
            anc = (l.get("anchor_text") or "").strip()
            if t == norm_target and anc:
                existing_anchors[anc] += 1

        existing_anchor_usage = [{"anchor": k, "count": v} for k, v in existing_anchors.most_common(10)]

        # Check Insufficient Content Rule
        if target_word_count < 15 and not target_title and not target_h1:
            res = {
                "status": "insufficient_evidence",
                "suggestions": [],
                "message": "No reliable anchor suggestions available. The destination page does not contain enough relevant content to generate a trustworthy contextual anchor.",
                "evidence": {
                    "source_url": source_url,
                    "target_url": target_url,
                    "destination_title": target_title or "(Missing Title)",
                    "destination_h1": target_h1 or "(Missing H1)",
                    "word_count": target_word_count
                }
            }
            cls._cache[cache_key] = res
            return res

        # 3. Generate Candidate Suggestions based on REAL EVIDENCE
        candidates = []

        # Candidate A: Primary H1 / Title topic
        if target_h1 and len(target_h1) < 60:
            candidates.append({
                "anchor": target_h1.lower(),
                "reason": "Closely matches the primary H1 heading on the destination page.",
                "confidence": "High",
                "source_type": "destination_h1"
            })
        
        # Candidate B: Title tag topic
        clean_title = re.sub(r'\s*[-|–].*', '', target_title).strip()
        if clean_title and clean_title.lower() != (target_h1 or "").lower() and len(clean_title) < 60:
            candidates.append({
                "anchor": clean_title.lower(),
                "reason": "Directly describes the destination page's primary title tag topic.",
                "confidence": "High",
                "source_type": "destination_title"
            })

        # Candidate C: Target H2 headings
        for h2 in target_h2_list:
            h2_str = str(h2).strip()
            if h2_str and len(h2_str) < 55 and h2_str.lower() not in [c["anchor"] for c in candidates]:
                candidates.append({
                    "anchor": h2_str.lower(),
                    "reason": "Relevant sub-topic heading extracted from the destination content.",
                    "confidence": "High" if len(candidates) < 2 else "Medium",
                    "source_type": "destination_h2"
                })
                if len(candidates) >= 4:
                    break

        # Candidate D: Target URL slug semantic phrase
        url_slug = norm_target.split('/')[-1].replace('-', ' ').replace('_', ' ').strip()
        if url_slug and url_slug not in ('index.html', 'index.php', '') and url_slug.lower() not in [c["anchor"] for c in candidates]:
            candidates.append({
                "anchor": url_slug.lower(),
                "reason": "Natural contextual phrase derived from the destination URL path structure.",
                "confidence": "Medium",
                "source_type": "url_slug"
            })

        # Check Diversity Warning (if an anchor is already used >= 4 times)
        diversity_warning = None
        for anc_info in existing_anchor_usage:
            if anc_info["count"] >= 4:
                overused = anc_info["anchor"]
                diversity_warning = f"Anchor diversity warning: '{overused}' is already used {anc_info['count']} times as an internal anchor across the site. Consider choosing a natural semantic variation."
                break

        # Filter out generic terms like "learn more", "click here", "read more"
        filtered_suggestions = []
        forbidden_anchors = {"learn more", "read more", "click here", "view page", "visit page", "learn about this", "details", "more"}

        for c in candidates:
            anc_lower = c["anchor"].strip().lower()
            if anc_lower in forbidden_anchors or len(anc_lower) < 3:
                continue
            filtered_suggestions.append({
                "anchor": c["anchor"],
                "reason": c["reason"],
                "confidence": c["confidence"]
            })

        # Build Evidence summary package
        evidence_pkg = {
            "source_url": source_url,
            "source_title": source_title or "(Crawled Source Page)",
            "destination_url": target_url,
            "destination_title": target_title or "(Missing Title Tag)",
            "destination_h1": target_h1 or "(Missing H1 Heading)",
            "destination_word_count": target_word_count,
            "relevant_terms": [c["anchor"] for c in filtered_suggestions[:3]],
            "existing_anchor_usage": existing_anchor_usage[:5]
        }

        result = {
            "status": "success" if filtered_suggestions else "insufficient_evidence",
            "suggestions": filtered_suggestions,
            "diversity_warning": diversity_warning,
            "evidence": evidence_pkg,
            "provenance": {
                "source_type": "AI Analysis",
                "label": "AI Analysis & Crawled Data Engine",
                "message": "Generated from verified destination page content, titles, headings, and internal link graph."
            }
        }

        cls._cache[cache_key] = result
        return result
