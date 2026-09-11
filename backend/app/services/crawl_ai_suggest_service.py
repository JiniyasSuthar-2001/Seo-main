"""
crawl_ai_suggest_service.py
============================
Multi-provider AI suggestion orchestrator for crawl data SEO page content.

Supports task types:
  - meta_description      (missing / duplicate)
  - meta_title            (missing / duplicate)
  - hreflang              (detected issue on page)
  - image_alt             (missing / generic / poor alt text for page images)

Architecture:
  1. Gather focused page-level context from real crawl snapshot
  2. Query all enabled providers in parallel (ThreadPoolExecutor)
  3. Evaluate each response for quality (SEO criteria per task type)
  4. Synthesize: pick winner or blend best parts if multiple providers agree
  5. Return structured result with per-provider transparency
"""

import os
import json
import time
import concurrent.futures
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.config.settings import settings, get_active_groq_key
from app.config.utils import normalize_stored_path, get_project_storage_dir
from app.config.logger import get_logger
from app.llm.llm_provider import (
    LLMProvider,
    GroqProviderAdapter,
    OpenAIProviderAdapter,
    AnthropicProviderAdapter,
    GeminiProviderAdapter,
    AIProviderException,
)
from app.llm.ollama_adapter import OllamaProviderAdapter
from app.models.external_connection import ExternalConnection

logger = get_logger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# TASK-TYPE QUALITY METRICS
# ──────────────────────────────────────────────────────────────────────────────

TASK_QUALITY_RULES = {
    "meta_description": {
        "min_chars": 70,
        "max_chars": 160,
        "good_range": (120, 158),
        "forbidden": ["click here", "read more", "lorem ipsum"],
    },
    "meta_title": {
        "min_chars": 20,
        "max_chars": 70,
        "good_range": (30, 60),
        "forbidden": ["untitled", "page title", "lorem ipsum"],
    },
    "image_alt": {
        "min_chars": 5,
        "max_chars": 120,
        "good_range": (10, 100),
        "forbidden": ["image", "photo", "picture", "img", "logo", "icon", "click"],
    },
    "hreflang": {
        "min_chars": 10,
        "max_chars": 2000,
        "good_range": (20, 1000),
        "forbidden": [],
    },
}

TASK_SYSTEM_PROMPTS = {
    "meta_description": (
        "You are an expert SEO content specialist. Generate a single, compelling meta description "
        "for the provided web page based exclusively on the crawled page data given. "
        "Requirements: 120-158 characters, naturally include the primary keyword, describe actual page content, "
        "no keyword stuffing, written in the same language as the page title/H1. "
        "Return ONLY valid JSON: {\"suggestion\": \"...\", \"char_count\": 0, \"reason\": \"...\"}"
    ),
    "meta_title": (
        "You are an expert SEO content specialist. Generate a single, compelling page title (title tag) "
        "for the provided web page based exclusively on the crawled page data. "
        "Requirements: 30-60 characters, naturally include the primary keyword near the start, "
        "describe the actual content, no keyword stuffing. "
        "Return ONLY valid JSON: {\"suggestion\": \"...\", \"char_count\": 0, \"reason\": \"...\"}"
    ),
    "image_alt": (
        "You are an expert web accessibility and SEO specialist. Analyze the image information and page context provided. "
        "For each image: generate descriptive alt text based on its filename, surrounding content, and page context. "
        "Requirements: descriptive (not generic like 'image' or 'photo'), 5-100 characters, accessible, relevant to the page. "
        "If existing alt text is already appropriate, say so. "
        "Return ONLY valid JSON: {\"images\": [{\"src\": \"...\", \"suggestion\": \"...\", \"char_count\": 0, "
        "\"existing_alt\": \"...\", \"verdict\": \"appropriate|improve|missing\", \"reason\": \"...\"}]}"
    ),
    "hreflang": (
        "You are an international SEO expert. Analyze the hreflang configuration on this page based solely on the provided crawl data. "
        "Identify genuine issues (missing x-default, incorrect language codes, mismatched URLs, incomplete reciprocal links). "
        "Do NOT invent alternate language pages that don't appear in the crawl data. "
        "Return ONLY valid JSON: {\"issues\": [{\"issue\": \"...\", \"recommendation\": \"...\"}], "
        "\"summary\": \"...\", \"valid_entries\": 0, \"problematic_entries\": 0}"
    ),
}

TASK_USER_PROMPTS = {
    "meta_description": "Generate a meta description for this web page based on the provided crawl data.",
    "meta_title": "Generate an SEO-optimized page title for this web page based on the provided crawl data.",
    "image_alt": "Analyze the images on this page and suggest appropriate alt text based on the page context.",
    "hreflang": "Analyze the hreflang configuration on this page and identify any genuine issues or improvements needed.",
}


# ──────────────────────────────────────────────────────────────────────────────
# CONTEXT BUILDER
# ──────────────────────────────────────────────────────────────────────────────

class CrawlPageContextBuilder:
    """
    Extracts focused, minimal page-level context from real crawl snapshot files.
    Never sends the entire dataset — only what is relevant to the task.
    """

    @classmethod
    def build(
        cls,
        project_id: str,
        domain: Optional[str],
        page_url: str,
        task_type: str,
    ) -> Dict[str, Any]:
        """Load specific page data from the latest crawl snapshot."""
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
        latest_path = os.path.join(proj_dir, "latest.json")

        if not os.path.exists(latest_path):
            return {
                "task_type": task_type,
                "page_url": page_url,
                "error": "No crawl snapshot found for this project.",
            }

        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if not os.path.exists(pages_file):
                return {"task_type": task_type, "page_url": page_url, "error": "pages.json not found."}

            with open(pages_file, "r", encoding="utf-8") as pf:
                pages = json.load(pf)

        except Exception as e:
            logger.error(f"[CrawlPageContextBuilder] Failed to load pages: {e}")
            return {"task_type": task_type, "page_url": page_url, "error": str(e)}

        # Find the exact page
        page_data = None
        page_url_norm = page_url.strip().rstrip("/").lower()
        for p in pages:
            if isinstance(p, dict):
                p_url = (p.get("url") or "").strip().rstrip("/").lower()
                if p_url == page_url_norm:
                    page_data = p
                    break

        if not page_data:
            # Fallback: find by partial URL
            for p in pages:
                if isinstance(p, dict):
                    p_url = (p.get("url") or "").strip().lower()
                    if page_url_norm in p_url or p_url in page_url_norm:
                        page_data = p
                        break

        if not page_data:
            return {
                "task_type": task_type,
                "page_url": page_url,
                "error": f"Page '{page_url}' not found in crawl data. Cannot generate context-grounded suggestion.",
            }

        return cls._extract_task_context(page_data, task_type)

    @classmethod
    def _extract_task_context(cls, page: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """Extract only the fields relevant to the specific task type."""
        base = {
            "task_type": task_type,
            "page_url": page.get("url", ""),
            "page_title": page.get("title") or "",
            "h1": page.get("h1") or "",
            "status_code": page.get("status_code", 200),
        }

        if task_type in ("meta_description", "duplicate_meta_description"):
            base.update({
                "current_meta_description": page.get("meta_description") or "",
                "meta_description_length": len(page.get("meta_description") or ""),
                "h2_headings": page.get("h2_tags", [])[:5] if page.get("h2_tags") else [],
                "word_count": page.get("word_count", 0),
                "robots_meta": page.get("robots_meta") or "index, follow",
                "canonical": page.get("canonical") or "",
                "issue": "Missing" if not page.get("meta_description") else "Duplicate",
            })

        elif task_type in ("meta_title", "duplicate_meta_title"):
            base.update({
                "current_title": page.get("title") or "",
                "title_length": len(page.get("title") or ""),
                "h2_headings": page.get("h2_tags", [])[:3] if page.get("h2_tags") else [],
                "meta_description": page.get("meta_description") or "",
                "word_count": page.get("word_count", 0),
                "issue": "Missing" if not page.get("title") else "Duplicate",
            })

        elif task_type == "image_alt":
            images = page.get("images", [])
            if not isinstance(images, list):
                images = []
            # Send compact image data — src, filename, current alt, position context
            image_items = []
            for img in images[:20]:  # Cap at 20 images per page
                if isinstance(img, dict):
                    src = img.get("src") or img.get("url") or ""
                    filename = src.split("/")[-1].split("?")[0] if src else ""
                    image_items.append({
                        "src": src,
                        "filename": filename,
                        "alt": img.get("alt") or "",
                        "missing_alt": not bool(img.get("alt")),
                        "title_attr": img.get("title") or "",
                        "width": img.get("width"),
                        "height": img.get("height"),
                    })
            # If page has no structured image data, build from image_inventory
            if not image_items:
                inv = page.get("image_inventory", [])
                if isinstance(inv, list):
                    for img in inv[:20]:
                        if isinstance(img, dict):
                            src = img.get("src") or img.get("url") or ""
                            filename = src.split("/")[-1].split("?")[0] if src else ""
                            image_items.append({
                                "src": src,
                                "filename": filename,
                                "alt": img.get("alt") or "",
                                "missing_alt": not bool(img.get("alt")),
                            })

            base.update({
                "images_count": page.get("images_count", len(image_items)),
                "images_missing_alt": page.get("images_missing_alt", sum(1 for i in image_items if i.get("missing_alt"))),
                "images": image_items,
                "word_count": page.get("word_count", 0),
            })

        elif task_type == "hreflang":
            hreflangs = page.get("hreflangs", [])
            if not isinstance(hreflangs, list):
                hreflangs = []
            base.update({
                "hreflang_entries": hreflangs,
                "hreflang_count": len(hreflangs),
                "html_lang": page.get("html_lang") or "",
                "canonical": page.get("canonical") or "",
            })

        return base


# ──────────────────────────────────────────────────────────────────────────────
# RESPONSE QUALITY EVALUATOR
# ──────────────────────────────────────────────────────────────────────────────

class SuggestionEvaluator:
    @staticmethod
    def score(response: Dict[str, Any], task_type: str) -> float:
        """Score a parsed provider response 0.0 – 1.0."""
        rules = TASK_QUALITY_RULES.get(task_type, {})
        if not rules:
            return 0.5

        suggestion = ""
        if task_type == "image_alt":
            # Score based on average image suggestion quality
            images = response.get("images", [])
            if not images:
                return 0.0
            scores = []
            for img in images:
                s = img.get("suggestion") or img.get("alt") or ""
                scores.append(SuggestionEvaluator._score_text(s, rules))
            return sum(scores) / len(scores) if scores else 0.0
        elif task_type == "hreflang":
            summary = response.get("summary", "")
            issues = response.get("issues", [])
            if summary or issues:
                return 0.75  # Hreflang responses are hard to score mechanically
            return 0.2
        else:
            suggestion = response.get("suggestion") or ""
            return SuggestionEvaluator._score_text(suggestion, rules)

    @staticmethod
    def _score_text(text: str, rules: Dict) -> float:
        if not text or not text.strip():
            return 0.0
        length = len(text.strip())
        min_c = rules.get("min_chars", 0)
        max_c = rules.get("max_chars", 9999)
        good_min, good_max = rules.get("good_range", (min_c, max_c))
        forbidden = rules.get("forbidden", [])

        # Length score (0.6 weight)
        if length < min_c or length > max_c:
            length_score = 0.2
        elif good_min <= length <= good_max:
            length_score = 1.0
        else:
            length_score = 0.6

        # Forbidden terms penalty (0.4 weight)
        text_lower = text.lower()
        for term in forbidden:
            if term in text_lower:
                return max(0.0, length_score * 0.3)

        return length_score


# ──────────────────────────────────────────────────────────────────────────────
# MULTI-PROVIDER ORCHESTRATOR
# ──────────────────────────────────────────────────────────────────────────────

class CrawlSuggestOrchestrator:
    """
    Queries all enabled AI providers in parallel for a page-level SEO suggestion.
    Evaluates each response. If multiple providers respond, synthesizes the best result.
    Individual provider responses remain accessible for transparency.
    """

    PROVIDER_TIMEOUT = 30.0  # seconds per provider

    @classmethod
    def suggest(
        cls,
        task_type: str,
        context: Dict[str, Any],
        user_id: Optional[str] = None,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """Entry point. Returns orchestrated suggestion."""
        providers = cls._get_enabled_providers(user_id, db)
        if not providers:
            raise AIProviderException(
                "No AI provider is available. Configure Groq, OpenAI, Gemini, or Claude in Integrations.",
                status_code=503,
                code="NO_PROVIDER_AVAILABLE",
            )

        system_prompt = TASK_SYSTEM_PROMPTS.get(task_type, TASK_SYSTEM_PROMPTS["meta_description"])
        user_prompt = TASK_USER_PROMPTS.get(task_type, "Generate an SEO suggestion.")

        provider_results = cls._call_providers_parallel(providers, system_prompt, user_prompt, context)

        # Evaluate
        evaluated = []
        for pr in provider_results:
            if pr.get("success") and pr.get("parsed"):
                score = SuggestionEvaluator.score(pr["parsed"], task_type)
                evaluated.append({**pr, "score": score})
            else:
                evaluated.append({**pr, "score": 0.0})

        successful = [r for r in evaluated if r.get("success") and r.get("score", 0) > 0.0]

        if not successful:
            errors = [r.get("error", "Unknown error") for r in evaluated]
            raise AIProviderException(
                f"All AI providers failed to generate a suggestion: {'; '.join(set(errors))}",
                status_code=502,
                code="ALL_PROVIDERS_FAILED",
            )

        # Sort by score
        successful.sort(key=lambda x: x["score"], reverse=True)
        winner = successful[0]

        # Synthesize if multiple providers responded well
        if len(successful) >= 2 and task_type not in ("hreflang",):
            final_parsed = cls._synthesize(successful, task_type)
        else:
            final_parsed = winner["parsed"]

        # Build final response
        result = cls._format_result(final_parsed, task_type)
        result["provider_used"] = winner["provider_name"]
        result["providers_queried"] = len(providers)
        result["providers_succeeded"] = len(successful)
        result["provider_responses"] = [
            {
                "provider": r["provider_name"],
                "success": r["success"],
                "score": round(r.get("score", 0), 2),
                "response": r.get("parsed") if r.get("success") else None,
                "error": r.get("error") if not r.get("success") else None,
            }
            for r in evaluated
        ]
        return result

    @classmethod
    def _get_enabled_providers(
        cls,
        user_id: Optional[str],
        db: Optional[Session],
    ) -> List[Dict[str, Any]]:
        """Returns list of {name, adapter} dicts for all available providers."""
        providers = []

        # 1. Platform Groq (always first if configured)
        groq_key = get_active_groq_key()
        if groq_key:
            try:
                providers.append({
                    "provider_name": "groq",
                    "adapter": GroqProviderAdapter(api_key=groq_key),
                })
            except Exception as e:
                logger.warning(f"[CrawlSuggest] Groq init failed: {e}")

        # 2. Customer BYO connections
        if user_id and db:
            try:
                conns = (
                    db.query(ExternalConnection)
                    .filter(
                        ExternalConnection.user_id == user_id,
                        ExternalConnection.provider.in_(["openai", "claude", "anthropic", "gemini"]),
                        ExternalConnection.status == "CONNECTED",
                    )
                    .all()
                )
                for conn in conns:
                    api_key = conn.get_api_key()
                    if not api_key:
                        continue
                    p = conn.provider.lower()
                    try:
                        if p == "openai":
                            providers.append({"provider_name": "openai", "adapter": OpenAIProviderAdapter(api_key=api_key)})
                        elif p in ("claude", "anthropic"):
                            providers.append({"provider_name": "claude", "adapter": AnthropicProviderAdapter(api_key=api_key)})
                        elif p == "gemini":
                            providers.append({"provider_name": "gemini", "adapter": GeminiProviderAdapter(api_key=api_key)})
                    except Exception as e:
                        logger.warning(f"[CrawlSuggest] Provider '{p}' init failed: {e}")
            except Exception as e:
                logger.warning(f"[CrawlSuggest] Failed to load customer connections: {e}")

        # 3. Ollama local as last fallback
        if not providers:
            try:
                ollama = OllamaProviderAdapter()
                ollama.test_connection(timeout=2.0)
                providers.append({"provider_name": "ollama", "adapter": ollama})
            except Exception:
                pass

        return providers

    @classmethod
    def _call_providers_parallel(
        cls,
        providers: List[Dict],
        system_prompt: str,
        user_prompt: str,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Call all providers concurrently with individual timeout protection."""
        results = []

        def call_one(prov_info: Dict) -> Dict[str, Any]:
            name = prov_info["provider_name"]
            adapter: LLMProvider = prov_info["adapter"]
            t0 = time.time()
            try:
                parsed = adapter.analyze(
                    system_instructions=system_prompt,
                    user_prompt=user_prompt,
                    context_data=context,
                    timeout=cls.PROVIDER_TIMEOUT,
                )
                duration = time.time() - t0
                logger.info(f"[CrawlSuggest] Provider '{name}' succeeded in {duration:.2f}s")
                return {
                    "provider_name": name,
                    "success": True,
                    "parsed": parsed,
                    "duration": round(duration, 2),
                    "error": None,
                }
            except Exception as e:
                duration = time.time() - t0
                msg = e.message if isinstance(e, AIProviderException) else str(e)
                logger.warning(f"[CrawlSuggest] Provider '{name}' failed after {duration:.2f}s: {msg}")
                return {
                    "provider_name": name,
                    "success": False,
                    "parsed": None,
                    "duration": round(duration, 2),
                    "error": msg[:200],
                }

        # Parallel execution with a global wall-clock timeout
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(providers), 4)) as executor:
            futures = {executor.submit(call_one, p): p for p in providers}
            done, not_done = concurrent.futures.wait(
                futures,
                timeout=cls.PROVIDER_TIMEOUT + 5,
                return_when=concurrent.futures.ALL_COMPLETED,
            )
            for future in done:
                results.append(future.result())
            for future in not_done:
                future.cancel()
                prov = futures[future]
                results.append({
                    "provider_name": prov["provider_name"],
                    "success": False,
                    "parsed": None,
                    "duration": cls.PROVIDER_TIMEOUT + 5,
                    "error": "Provider timed out.",
                })

        return results

    @classmethod
    def _synthesize(cls, evaluated: List[Dict], task_type: str) -> Dict[str, Any]:
        """
        Synthesize best response from top providers.
        Strategy: take the highest-scored response as winner.
        If top-2 scores are within 0.1 of each other, prefer the longer suggestion
        in the valid range (for text tasks) or the winner directly.
        """
        winner = evaluated[0]
        runner_up = evaluated[1] if len(evaluated) >= 2 else None

        if task_type in ("meta_description", "meta_title"):
            rules = TASK_QUALITY_RULES.get(task_type, {})
            good_min, good_max = rules.get("good_range", (0, 9999))
            w_sugg = winner["parsed"].get("suggestion", "")
            r_sugg = runner_up["parsed"].get("suggestion", "") if runner_up else ""

            # If scores are close, prefer the suggestion that's in the good character range
            if runner_up and abs(winner["score"] - runner_up["score"]) < 0.12:
                w_len = len(w_sugg)
                r_len = len(r_sugg)
                w_in_range = good_min <= w_len <= good_max
                r_in_range = good_min <= r_len <= good_max
                if r_in_range and not w_in_range:
                    return runner_up["parsed"]

        return winner["parsed"]

    @classmethod
    def _format_result(cls, parsed: Dict[str, Any], task_type: str) -> Dict[str, Any]:
        """Normalize parsed AI response into consistent API output format."""
        if task_type == "image_alt":
            return {
                "task_type": task_type,
                "images": parsed.get("images", []),
                "summary": parsed.get("summary", ""),
            }
        elif task_type == "hreflang":
            return {
                "task_type": task_type,
                "issues": parsed.get("issues", []),
                "summary": parsed.get("summary", ""),
                "valid_entries": parsed.get("valid_entries", 0),
                "problematic_entries": parsed.get("problematic_entries", 0),
            }
        else:
            suggestion = parsed.get("suggestion") or ""
            return {
                "task_type": task_type,
                "suggestion": suggestion,
                "char_count": len(suggestion),
                "reason": parsed.get("reason") or "",
            }
