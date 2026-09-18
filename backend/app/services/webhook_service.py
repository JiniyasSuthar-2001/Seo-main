import json
import logging
import asyncio
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger("webhook_service")

class WebhookService:
    """
    Production-grade, safe Webhook Delivery Engine.
    Handles secure HTTP POST delivery for platform events (crawl_completed, crawl_failed, seo_alert, audit_completed).
    Includes SSRF validation, non-blocking async execution, 5-second timeouts, and secret-safe logging.
    """

    @classmethod
    async def dispatch_webhook_async(cls, webhook_url: str, event_type: str, payload: Dict[str, Any]):
        """Executes non-blocking HTTP POST webhook delivery safely."""
        from app.crawler.ssrf_protection import validate_url_ssrf

        if not webhook_url or not webhook_url.strip():
            return {"status": "skipped", "reason": "No webhook URL configured."}

        # 1. Validate destination against SSRF security policies
        is_safe, error_reason = validate_url_ssrf(webhook_url, allow_local_dev=False)
        if not is_safe:
            logger.warning(f"[WEBHOOK BLOCKED] Blocked webhook delivery to '{webhook_url}': {error_reason}")
            return {"status": "blocked", "reason": f"SSRF security policy blocked destination: {error_reason}"}

        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SEO-Intelligence-Webhook/1.0",
            "X-SEO-Event": event_type
        }

        body = {
            "event": event_type,
            "timestamp": payload.get("timestamp"),
            "project_id": payload.get("project_id"),
            "domain": payload.get("domain"),
            "data": payload.get("data", {})
        }

        # 2. Execute HTTP POST request with strict 5.0 second timeout
        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=False) as client:
                response = await client.post(webhook_url, json=body, headers=headers)
                if response.is_success:
                    logger.info(f"[WEBHOOK SUCCESS] Delivered '{event_type}' to {webhook_url} (HTTP {response.status_code})")
                    return {"status": "success", "http_status": response.status_code}
                else:
                    logger.warning(f"[WEBHOOK FAILED] Destination returned HTTP {response.status_code} for '{event_type}'")
                    return {"status": "failed", "http_status": response.status_code, "reason": f"HTTP {response.status_code}"}
        except httpx.TimeoutException:
            logger.warning(f"[WEBHOOK TIMEOUT] Webhook request to {webhook_url} timed out after 5.0s.")
            return {"status": "failed", "reason": "Request timed out after 5.0s."}
        except Exception as e:
            logger.error(f"[WEBHOOK ERROR] Failed to deliver webhook to {webhook_url}: {str(e)[:150]}")
            return {"status": "failed", "reason": str(e)[:150]}

    @classmethod
    def send_event(cls, project: Any, event_type: str, data: Optional[Dict[str, Any]] = None, payload: Optional[Dict[str, Any]] = None):
        """
        Public trigger entry point.
        Checks if project has a configured webhook URL and if the event is enabled.
        Spawns async delivery task safely without blocking caller thread.
        """
        event_data = data if data is not None else (payload or {})
        webhook_url = getattr(project, "webhook_url", None)
        if not webhook_url or not webhook_url.strip():
            return

        # Check configured events
        events_json = getattr(project, "webhook_events", None)
        enabled_events: List[str] = []
        if events_json:
            try:
                if isinstance(events_json, list):
                    enabled_events = events_json
                elif events_json.startswith("["):
                    enabled_events = json.loads(events_json)
                else:
                    enabled_events = [e.strip() for e in events_json.split(",") if e.strip()]
            except Exception:
                enabled_events = []

        # Standardize event names (e.g. crawl_completed, crawl.completed)
        normalized_event = event_type.replace("_", ".")
        normalized_enabled = [e.replace("_", ".") for e in enabled_events]

        if enabled_events and normalized_event not in normalized_enabled:
            return

        payload_data = {
            "timestamp": event_data.get("timestamp"),
            "project_id": project.id,
            "domain": getattr(project, "domain", None) or getattr(project, "url", None),
            "data": event_data
        }

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(cls.dispatch_webhook_async(webhook_url, event_type, payload_data))
            else:
                asyncio.run(cls.dispatch_webhook_async(webhook_url, event_type, payload_data))
        except Exception as ex:
            print(f"[WEBHOOK TRIGGER ERROR] Could not schedule webhook dispatch: {ex}", flush=True)
