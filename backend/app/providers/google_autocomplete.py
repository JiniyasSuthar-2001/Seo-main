import urllib.request
import urllib.parse
import urllib.error
import json
import time
import threading
from typing import List, Dict, Any, Optional
from app.providers.base import BaseAutocompleteProvider
from app.config.settings import settings
from app.config.logger import get_logger

logger = get_logger(__name__)

class AutocompleteStatus:
    SUCCESS = "SUCCESS"
    NO_RESULTS = "NO_RESULTS"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    TIMEOUT = "TIMEOUT"
    UPSTREAM_ERROR = "UPSTREAM_ERROR"

# Thread-safe in-memory LRU/TTL Cache (Max 500 entries, TTL 3600s)
_cache_lock = threading.Lock()
_autocomplete_cache: Dict[str, Dict[str, Any]] = {}
MAX_CACHE_ENTRIES = 500
CACHE_TTL_SECONDS = 3600

def _get_from_cache(query: str) -> Optional[Dict[str, Any]]:
    clean_q = query.strip().lower()
    with _cache_lock:
        entry = _autocomplete_cache.get(clean_q)
        if entry:
            if time.time() - entry["timestamp"] < CACHE_TTL_SECONDS:
                return entry["result"]
            else:
                del _autocomplete_cache[clean_q]
    return None

def _put_in_cache(query: str, result: Dict[str, Any]):
    clean_q = query.strip().lower()
    with _cache_lock:
        if len(_autocomplete_cache) >= MAX_CACHE_ENTRIES:
            # Remove oldest entry
            oldest_key = min(_autocomplete_cache.keys(), key=lambda k: _autocomplete_cache[k]["timestamp"])
            del _autocomplete_cache[oldest_key]
        _autocomplete_cache[clean_q] = {
            "timestamp": time.time(),
            "result": result
        }

class GoogleAutocompleteProvider(BaseAutocompleteProvider):
    def get_suggestions_detailed(self, query: str, timeout: float = 5.0) -> Dict[str, Any]:
        if not query or not query.strip():
            return {
                "query": query,
                "suggestions": [],
                "status": AutocompleteStatus.NO_RESULTS,
                "message": "Empty query string."
            }

        clean_q = query.strip()
        
        # Check cache
        cached = _get_from_cache(clean_q)
        if cached:
            logger.info(f"[AUTOCOMPLETE CACHE HIT] Query '{clean_q}' served from cache.")
            return cached

        encoded_q = urllib.parse.quote(clean_q)
        endpoint_base = settings.AUTOCOMPLETE_ENDPOINT_URL
        url = f"{endpoint_base}?client=chrome&q={encoded_q}"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "SEO-Intelligence-Platform/1.0 (Mozilla/5.0 Compatible)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    raw_body = response.read().decode("utf-8")
                    data = json.loads(raw_body)
                    suggestions = []
                    if isinstance(data, list) and len(data) > 1 and isinstance(data[1], list):
                        suggestions = [str(s).strip() for s in data[1] if str(s).strip()]

                    status = AutocompleteStatus.SUCCESS if suggestions else AutocompleteStatus.NO_RESULTS
                    result = {
                        "query": clean_q,
                        "suggestions": suggestions,
                        "status": status,
                        "message": None if suggestions else "No suggestions returned by provider."
                    }
                    _put_in_cache(clean_q, result)
                    return result
        except urllib.error.HTTPError as e:
            logger.warning(f"[AUTOCOMPLETE HTTP ERROR] Upstream HTTP {e.code} for query '{clean_q}'")
            if e.code == 429:
                return {
                    "query": clean_q,
                    "suggestions": [],
                    "status": AutocompleteStatus.RATE_LIMITED,
                    "message": "Autocomplete provider rate limited request."
                }
            return {
                "query": clean_q,
                "suggestions": [],
                "status": AutocompleteStatus.UPSTREAM_ERROR,
                "message": f"Upstream provider returned HTTP {e.code}."
            }
        except Exception as e:
            logger.warning(f"[AUTOCOMPLETE ERROR] Provider failure for query '{clean_q}': {e}")
            return {
                "query": clean_q,
                "suggestions": [],
                "status": AutocompleteStatus.PROVIDER_UNAVAILABLE,
                "message": f"Autocomplete provider unavailable: {e}"
            }

    def get_suggestions(self, query: str) -> List[str]:
        res = self.get_suggestions_detailed(query)
        return res.get("suggestions", [])
