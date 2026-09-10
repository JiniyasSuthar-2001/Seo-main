import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime
from app.providers.base import BasePageSpeedProvider
from app.config.settings import settings

class GooglePageSpeedProvider(BasePageSpeedProvider):
    """
    Production-grade Google PageSpeed Insights Provider.
    Calls Google PageSpeed API v5 to extract authentic Core Web Vitals and Lighthouse lab diagnostics.
    Never fabricates metrics. Returns explicit error details if API key is invalid or rate limited.
    """
    PAGESPEED_API_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("PAGESPEED_API_KEY") or os.environ.get("GOOGLE_PAGESPEED_API_KEY") or getattr(settings, "PAGESPEED_API_KEY", "")
        self.timeout = timeout

    def analyze_url(self, url: str, strategy: str = "mobile", api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous URL performance analysis.
        """
        key = api_key or self.api_key
        params = {
            "url": url,
            "strategy": strategy.lower() if strategy in ("mobile", "desktop") else "mobile",
            "category": "performance"
        }
        if key and key.strip():
            params["key"] = key.strip()

        timestamp = datetime.utcnow().isoformat()

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.PAGESPEED_API_ENDPOINT, params=params)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_pagespeed_response(url, strategy, data, timestamp)
                elif response.status_code in (429, 403):
                    err_msg = "Google PageSpeed API quota limit exceeded or key unauthorized."
                    return self._build_error_response(url, strategy, response.status_code, err_msg, timestamp)
                elif response.status_code == 400:
                    err_data = response.json().get("error", {})
                    err_msg = err_data.get("message", "Invalid URL or request parameter for PageSpeed API.")
                    return self._build_error_response(url, strategy, 400, err_msg, timestamp)
                else:
                    return self._build_error_response(url, strategy, response.status_code, f"PageSpeed API returned HTTP {response.status_code}", timestamp)

        except httpx.TimeoutException:
            return self._build_error_response(url, strategy, 408, "PageSpeed analysis request timed out.", timestamp)
        except Exception as e:
            return self._build_error_response(url, strategy, 500, f"PageSpeed execution error: {str(e)}", timestamp)

    async def analyze_url_async(self, url: str, strategy: str = "mobile", api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Asynchronous URL performance analysis.
        """
        key = api_key or self.api_key
        params = {
            "url": url,
            "strategy": strategy.lower() if strategy in ("mobile", "desktop") else "mobile",
            "category": "performance"
        }
        if key and key.strip():
            params["key"] = key.strip()

        timestamp = datetime.utcnow().isoformat()

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(self.PAGESPEED_API_ENDPOINT, params=params)

                if response.status_code == 200:
                    data = response.json()
                    return self._parse_pagespeed_response(url, strategy, data, timestamp)
                elif response.status_code in (429, 403):
                    err_msg = "Google PageSpeed API quota limit exceeded or key unauthorized."
                    return self._build_error_response(url, strategy, response.status_code, err_msg, timestamp)
                else:
                    return self._build_error_response(url, strategy, response.status_code, f"PageSpeed API returned HTTP {response.status_code}", timestamp)

        except httpx.TimeoutException:
            return self._build_error_response(url, strategy, 408, "PageSpeed analysis request timed out.", timestamp)
        except Exception as e:
            return self._build_error_response(url, strategy, 500, f"PageSpeed execution error: {str(e)}", timestamp)

    def _parse_pagespeed_response(self, url: str, strategy: str, data: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        perf_cat = categories.get("performance", {})
        score_val = perf_cat.get("score")
        score = int(round(score_val * 100)) if score_val is not None else None

        audits = lighthouse.get("audits", {})

        def _get_metric(audit_key: str):
            a = audits.get(audit_key, {})
            return {
                "value": a.get("numericValue"),
                "display_value": a.get("displayValue", ""),
                "score": a.get("score")
            }

        fcp = _get_metric("first-contentful-paint")
        lcp = _get_metric("largest-contentful-paint")
        cls = _get_metric("cumulative-layout-shift")
        tbt = _get_metric("total-blocking-time")
        si = _get_metric("speed-index")
        ttfb = _get_metric("server-response-time")
        inp = _get_metric("interaction-to-next-paint")

        # Extract Core Web Vitals assessment
        cwv_passed = True
        if lcp["value"] and lcp["value"] > 2500:
            cwv_passed = False
        if cls["value"] and cls["value"] > 0.1:
            cwv_passed = False
        if inp["value"] and inp["value"] > 200:
            cwv_passed = False

        return {
            "status": "success",
            "url": url,
            "strategy": strategy,
            "timestamp": timestamp,
            "performance_score": score,
            "core_web_vitals": {
                "assessment": "PASSED" if cwv_passed else "POOR",
                "lcp": {
                    "name": "Largest Contentful Paint (LCP)",
                    "value_ms": round(lcp["value"], 1) if lcp["value"] is not None else None,
                    "display": lcp["display_value"],
                    "rating": "GOOD" if lcp["value"] and lcp["value"] <= 2500 else ("NEEDS_IMPROVEMENT" if lcp["value"] and lcp["value"] <= 4000 else "POOR")
                },
                "cls": {
                    "name": "Cumulative Layout Shift (CLS)",
                    "value": round(cls["value"], 3) if cls["value"] is not None else None,
                    "display": cls["display_value"],
                    "rating": "GOOD" if cls["value"] is not None and cls["value"] <= 0.1 else ("NEEDS_IMPROVEMENT" if cls["value"] is not None and cls["value"] <= 0.25 else "POOR")
                },
                "fcp": {
                    "name": "First Contentful Paint (FCP)",
                    "value_ms": round(fcp["value"], 1) if fcp["value"] is not None else None,
                    "display": fcp["display_value"],
                    "rating": "GOOD" if fcp["value"] and fcp["value"] <= 1800 else ("NEEDS_IMPROVEMENT" if fcp["value"] and fcp["value"] <= 3000 else "POOR")
                },
                "tbt": {
                    "name": "Total Blocking Time (TBT)",
                    "value_ms": round(tbt["value"], 1) if tbt["value"] is not None else None,
                    "display": tbt["display_value"],
                    "rating": "GOOD" if tbt["value"] is not None and tbt["value"] <= 200 else ("NEEDS_IMPROVEMENT" if tbt["value"] is not None and tbt["value"] <= 600 else "POOR")
                },
                "ttfb": {
                    "name": "Time to First Byte (TTFB)",
                    "value_ms": round(ttfb["value"], 1) if ttfb["value"] is not None else None,
                    "display": ttfb["display_value"],
                    "rating": "GOOD" if ttfb["value"] and ttfb["value"] <= 800 else ("NEEDS_IMPROVEMENT" if ttfb["value"] and ttfb["value"] <= 1800 else "POOR")
                },
                "speed_index": {
                    "name": "Speed Index",
                    "value_ms": round(si["value"], 1) if si["value"] is not None else None,
                    "display": si["display_value"]
                }
            },
            "provenance": {
                "source": "Google PageSpeed Insights API v5",
                "engine": "Lighthouse Lab & Crux Data"
            }
        }

    def _build_error_response(self, url: str, strategy: str, status_code: int, message: str, timestamp: str) -> Dict[str, Any]:
        return {
            "status": "error",
            "url": url,
            "strategy": strategy,
            "timestamp": timestamp,
            "http_status": status_code,
            "error_message": message,
            "performance_score": None,
            "core_web_vitals": None,
            "provenance": {
                "source": "Google PageSpeed Insights API v5",
                "message": message
            }
        }
