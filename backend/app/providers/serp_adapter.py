"""
serp_adapter.py
================
Pluggable SERP provider abstraction layer.

Architecture:
  BaseSERPAdapter (ABC)
       │
  ┌────┴────────────┐
  │                 │
  SerpApiAdapter    OpenSERPAdapter
  │                 │
  └────┬────────────┘
       │
  SERPAdapterFactory.get(provider_name, api_key)
       │
  NormalizedSERPResult  <── common output format regardless of provider

Adding a new provider:
  1. Subclass BaseSERPAdapter
  2. Implement search() and test_connection()
  3. Register in SERPAdapterFactory.REGISTRY
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from app.config.logger import get_logger

logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# NORMALIZED DATA MODELS
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class NormalizedSERPResult:
    """Common SERP result format regardless of which provider produced it."""
    keyword: str
    domain: str
    position: Optional[int]        # 1-indexed; None = not found in top N
    ranking_url: Optional[str]
    title: Optional[str]
    snippet: Optional[str]
    search_engine: str             # "Google", "Bing", etc.
    country: str
    language: str
    device: str                    # "Desktop" | "Mobile"
    source: str                    # provider id: "serpapi", "openserp"
    checked_at: str                # ISO 8601
    status: str                    # "ranked" | "not_ranked" | "error"
    serp_features: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ──────────────────────────────────────────────────────────────────────────────
# ABSTRACT BASE
# ──────────────────────────────────────────────────────────────────────────────

class BaseSERPAdapter(ABC):
    """
    All SERP provider adapters must implement this interface.
    The rest of the application should only interact with BaseSERPAdapter.
    """
    provider_id: str = "unknown"
    provider_name: str = "Unknown SERP Provider"

    @abstractmethod
    def search(
        self,
        keyword: str,
        domain: str,
        country: str = "us",
        language: str = "en",
        device: str = "Desktop",
        num_results: int = 100,
    ) -> NormalizedSERPResult:
        """Perform a SERP check for one keyword + domain. Returns a normalized result."""
        ...

    @abstractmethod
    def test_connection(self) -> Dict[str, Any]:
        """Verify the API key is valid and the provider is reachable."""
        ...

    def check_rankings(
        self,
        keywords: List[str],
        domain: str,
        country: str = "us",
        language: str = "en",
        device: str = "Desktop",
    ) -> List[NormalizedSERPResult]:
        """
        Convenience method: checks all keywords and returns a list of results.
        Existing code that uses SERPRankTrackerProvider.check_rankings() should
        call this method through the adapter.
        """
        results = []
        for kw in keywords:
            try:
                results.append(
                    self.search(kw, domain, country=country, language=language, device=device)
                )
            except Exception as e:
                ts = datetime.utcnow().isoformat()
                results.append(NormalizedSERPResult(
                    keyword=kw,
                    domain=domain,
                    position=None,
                    ranking_url=None,
                    title=None,
                    snippet=None,
                    search_engine="Google",
                    country=country,
                    language=language,
                    device=device,
                    source=self.provider_id,
                    checked_at=ts,
                    status="error",
                    error=str(e)[:200],
                ))
        return results


# ──────────────────────────────────────────────────────────────────────────────
# SERPAPI ADAPTER
# ──────────────────────────────────────────────────────────────────────────────

class SerpApiAdapter(BaseSERPAdapter):
    """
    SerpApi (serpapi.com) adapter.
    Documentation: https://serpapi.com/search-api
    """
    provider_id = "serpapi"
    provider_name = "SerpApi"
    BASE_URL = "https://serpapi.com/search.json"

    def __init__(self, api_key: str):
        if not api_key or not api_key.strip():
            raise ValueError("SerpApi API key is required.")
        self.api_key = api_key.strip()

    def search(
        self,
        keyword: str,
        domain: str,
        country: str = "us",
        language: str = "en",
        device: str = "Desktop",
        num_results: int = 100,
    ) -> NormalizedSERPResult:
        ts = datetime.utcnow().isoformat()
        clean_domain = domain.lower().replace("https://", "").replace("http://", "").rstrip("/")

        params = {
            "engine": "google",
            "q": keyword,
            "api_key": self.api_key,
            "gl": country.lower()[:2],
            "hl": language.lower()[:2],
            "num": str(num_results),
            "device": device.lower(),
        }
        url = self.BASE_URL + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": "SEO-Intelligence-Platform/1.0"}, method="GET")

        try:
            with urllib.request.urlopen(req, timeout=20.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code == 401 or "Invalid API" in body:
                raise ValueError("SerpApi key is invalid or unauthorized.")
            raise ValueError(f"SerpApi HTTP {e.code}: {body[:200]}")
        except Exception as e:
            raise ValueError(f"SerpApi connection error: {e}")

        # Parse organic results to find the domain's position
        organic = data.get("organic_results", [])
        position = None
        ranking_url = None
        title = None
        snippet = None

        for idx, result in enumerate(organic, start=1):
            result_domain = result.get("displayed_link", result.get("link", "")).lower()
            result_url = result.get("link", "")
            if clean_domain in result_domain or clean_domain in result_url.lower():
                position = idx
                ranking_url = result_url
                title = result.get("title")
                snippet = result.get("snippet")
                break

        # Detect SERP features
        features = []
        if data.get("answer_box"):
            features.append("featured_snippet")
        if data.get("related_questions"):
            features.append("people_also_ask")
        if data.get("local_results"):
            features.append("local_pack")
        if data.get("shopping_results"):
            features.append("shopping")

        return NormalizedSERPResult(
            keyword=keyword,
            domain=clean_domain,
            position=position,
            ranking_url=ranking_url,
            title=title,
            snippet=snippet,
            search_engine="Google",
            country=country,
            language=language,
            device=device,
            source=self.provider_id,
            checked_at=ts,
            status="ranked" if position else "not_ranked",
            serp_features=features,
        )

    def test_connection(self) -> Dict[str, Any]:
        """Test by fetching account info endpoint."""
        url = f"https://serpapi.com/account?api_key={urllib.parse.quote(self.api_key)}"
        req = urllib.request.Request(url, headers={"User-Agent": "SEO-Intelligence-Platform/1.0"}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "status": "connected",
                    "provider": self.provider_id,
                    "provider_name": self.provider_name,
                    "searches_this_month": data.get("this_month_usage", {}).get("searches", None),
                    "plan": data.get("plan_name", "Unknown"),
                    "message": "SerpApi connected successfully.",
                }
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ValueError("SerpApi key is invalid or unauthorized.")
            raise ValueError(f"SerpApi test failed (HTTP {e.code}).")
        except Exception as e:
            raise ValueError(f"SerpApi connection test failed: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# OPENSERP ADAPTER
# ──────────────────────────────────────────────────────────────────────────────

class OpenSERPAdapter(BaseSERPAdapter):
    """
    OpenSERP Cloud adapter (openserp.org).
    OpenSERP is an open-source SERP scraper with a managed cloud API.
    Endpoint: POST https://api.openserp.org/api/v1/search  (Cloud)
    Self-hosted: configurable BASE_URL via OPENSERP_BASE_URL env var.
    """
    provider_id = "openserp"
    provider_name = "OpenSERP"
    DEFAULT_BASE_URL = "https://api.openserp.org"

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").strip().rstrip("/") or self.DEFAULT_BASE_URL

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SEO-Intelligence-Platform/1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def search(
        self,
        keyword: str,
        domain: str,
        country: str = "us",
        language: str = "en",
        device: str = "Desktop",
        num_results: int = 100,
    ) -> NormalizedSERPResult:
        ts = datetime.utcnow().isoformat()
        clean_domain = domain.lower().replace("https://", "").replace("http://", "").rstrip("/")

        # OpenSERP v1 search endpoint
        endpoint = f"{self.base_url}/api/v1/google/search"
        payload = {
            "query": keyword,
            "country": country.lower()[:2],
            "language": language.lower()[:2],
            "limit": num_results,
        }

        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers=self._get_headers(),
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=25.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            if e.code in (401, 403):
                raise ValueError("OpenSERP API key is invalid or unauthorized.")
            raise ValueError(f"OpenSERP HTTP {e.code}: {body[:200]}")
        except Exception as e:
            raise ValueError(f"OpenSERP connection error: {e}")

        # Parse OpenSERP response — results are in data["results"] or data["organic"]
        organic = data.get("results") or data.get("organic") or []
        position = None
        ranking_url = None
        title = None
        snippet = None

        for idx, result in enumerate(organic, start=1):
            result_url = result.get("url") or result.get("link") or ""
            if clean_domain in result_url.lower():
                position = idx
                ranking_url = result_url
                title = result.get("title") or result.get("name")
                snippet = result.get("description") or result.get("snippet")
                break

        return NormalizedSERPResult(
            keyword=keyword,
            domain=clean_domain,
            position=position,
            ranking_url=ranking_url,
            title=title,
            snippet=snippet,
            search_engine="Google",
            country=country,
            language=language,
            device=device,
            source=self.provider_id,
            checked_at=ts,
            status="ranked" if position else "not_ranked",
            serp_features=[],
        )

    def test_connection(self) -> Dict[str, Any]:
        """Test by hitting the health/ping endpoint."""
        endpoint = f"{self.base_url}/api/v1/health"
        req = urllib.request.Request(
            endpoint,
            headers=self._get_headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                return {
                    "status": "connected",
                    "provider": self.provider_id,
                    "provider_name": self.provider_name,
                    "base_url": self.base_url,
                    "message": "OpenSERP connected successfully.",
                }
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise ValueError("OpenSERP API key is invalid or unauthorized.")
            # Try the root endpoint as fallback
            try:
                req2 = urllib.request.Request(f"{self.base_url}/", headers=self._get_headers(), method="GET")
                with urllib.request.urlopen(req2, timeout=5.0) as r2:
                    return {
                        "status": "connected",
                        "provider": self.provider_id,
                        "provider_name": self.provider_name,
                        "base_url": self.base_url,
                        "message": "OpenSERP reachable.",
                    }
            except Exception:
                pass
            raise ValueError(f"OpenSERP test failed (HTTP {e.code}).")
        except Exception as e:
            raise ValueError(f"OpenSERP connection test failed: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# FACTORY
# ──────────────────────────────────────────────────────────────────────────────

class SERPAdapterFactory:
    """
    Instantiate the correct SERP adapter by provider name.
    New providers: add to REGISTRY.
    """
    REGISTRY: Dict[str, type] = {
        "serpapi": SerpApiAdapter,
        "openserp": OpenSERPAdapter,
    }

    PROVIDER_DISPLAY_NAMES = {
        "serpapi": "SerpApi",
        "openserp": "OpenSERP",
    }

    @classmethod
    def get(cls, provider_name: str, api_key: str, **kwargs) -> BaseSERPAdapter:
        provider_key = (provider_name or "serpapi").lower().strip()
        adapter_cls = cls.REGISTRY.get(provider_key)
        if not adapter_cls:
            raise ValueError(f"Unknown SERP provider '{provider_name}'. Supported: {list(cls.REGISTRY.keys())}")
        return adapter_cls(api_key=api_key, **kwargs)

    @classmethod
    def list_providers(cls) -> List[Dict[str, str]]:
        return [
            {"id": pid, "name": cls.PROVIDER_DISPLAY_NAMES.get(pid, pid.title())}
            for pid in cls.REGISTRY
        ]
