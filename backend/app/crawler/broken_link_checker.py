import asyncio
import httpx
import ipaddress
import socket
from urllib.parse import urlparse, urljoin
from typing import List, Dict, Any, Optional, Callable, Set

from app.crawler.ssrf_protection import validate_url_ssrf, create_ssrf_safe_client, SSRFBlockedError

STATIC_OR_SPECIAL_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "#")

def is_private_ip(hostname: str) -> bool:
    """
    SSRF Protection: Checks whether a hostname or IP address resolves to a
    loopback, private, link-local, or cloud metadata address.
    """
    if not hostname:
        return True
    is_safe, _ = validate_url_ssrf(f"http://{hostname}")
    return not is_safe


def normalize_link_url(url: Optional[str]) -> str:
    """
    Normalizes URLs for deduplication: strips fragment (#...), lowercases scheme and netloc,
    strips trailing slash on non-root paths.
    """
    if not url:
        return ""
    clean = url.split('#')[0].strip()
    if not clean:
        return ""
    parsed = urlparse(clean)
    if not parsed.scheme or not parsed.netloc:
        return clean
    path = parsed.path
    if not path:
        path = "/"
    elif path != "/" and path.endswith("/"):
        path = path.rstrip("/")
    
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}{query}"


async def check_single_link(
    client: httpx.AsyncClient, 
    url: str, 
    timeout: float = 10.0,
    headers: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Checks the status of a single URL via HTTP HEAD with fallback to GET.
    Captures status_code, status label, Content-Type response header, final_url,
    redirect chain, is_broken, and error.
    """
    if not url or not url.startswith(("http://", "https://")):
        return {
            "url": url,
            "status_code": 0,
            "status": "Invalid URL",
            "content_type": "N/A",
            "is_broken": True,
            "error": "Invalid or Unsupported URL scheme",
            "error_type": "invalid_url",
            "final_url": url,
            "redirect_chain": []
        }

    is_safe, ssrf_reason = validate_url_ssrf(url)
    if not is_safe:
        return {
            "url": url,
            "status_code": 0,
            "status": "Blocked",
            "content_type": "N/A",
            "is_broken": True,
            "error": f"Blocked (SSRF Protection: {ssrf_reason})",
            "error_type": "blocked",
            "final_url": url,
            "redirect_chain": []
        }

    req_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "*/*"
    }
    if headers:
        req_headers.update(headers)

    # 1. Try HEAD request first for efficiency
    try:
        resp = await client.head(url, headers=req_headers, timeout=timeout, follow_redirects=True)
        
        # If HEAD returned Method Not Allowed (405) or Forbidden (403), fallback to GET
        if resp.status_code in (405, 403, 501):
            try:
                resp = await client.get(url, headers=req_headers, timeout=timeout, follow_redirects=True)
            except Exception:
                pass

        status_code = resp.status_code
        final_url = str(resp.url)
        
        # Extract Content-Type header from actual HTTP response
        raw_ct = resp.headers.get("content-type") or ""
        content_type = raw_ct.split(";")[0].strip().lower() if raw_ct else "text/html"
        
        # Extract redirect history
        redirect_chain = []
        if getattr(resp, "history", None):
            for r in resp.history:
                redirect_chain.append({
                    "url": str(r.url),
                    "status_code": r.status_code
                })
        redirect_chain.append({
            "url": final_url,
            "status_code": status_code
        })

        has_redirect = len(resp.history) > 0 if getattr(resp, "history", None) else False
        initial_status = resp.history[0].status_code if has_redirect else status_code

        if status_code == 200:
            status_label = f"{initial_status} Redirect" if has_redirect else "200 OK"
        elif 200 <= status_code < 300:
            status_label = f"{initial_status} Redirect" if has_redirect else f"{status_code} OK"
        elif 300 <= status_code < 400:
            status_label = f"{status_code} Redirect"
        elif status_code == 404:
            status_label = "404 Not Found"
        elif status_code == 410:
            status_label = "410 Gone"
        elif status_code in (401, 403):
            status_label = f"{status_code} Forbidden"
        elif 400 <= status_code < 500:
            status_label = f"{status_code} Client Error"
        elif 500 <= status_code < 600:
            status_label = f"{status_code} Server Error"
        else:
            status_label = f"HTTP {status_code}"
        
        # Determine if healthy (2xx, 3xx followed to 2xx)
        if status_code < 400 and status_code != 0:
            return {
                "url": url,
                "status_code": status_code,
                "status": status_label,
                "content_type": content_type,
                "is_broken": False,
                "error": None,
                "error_type": None,
                "final_url": final_url,
                "redirect_chain": redirect_chain
            }
        else:
            err_type = "not_found" if status_code == 404 else ("gone" if status_code == 410 else "http_error")
            return {
                "url": url,
                "status_code": status_code,
                "status": status_label,
                "content_type": content_type,
                "is_broken": True,
                "error": f"HTTP {status_code} {getattr(resp, 'reason_phrase', 'Error') or 'Error'}",
                "error_type": err_type,
                "final_url": final_url,
                "redirect_chain": redirect_chain
            }

    except httpx.TimeoutException:
        return {
            "url": url,
            "status_code": 0,
            "status": "Timeout",
            "content_type": "N/A",
            "is_broken": True,
            "error": f"Request Timed Out ({timeout}s)",
            "error_type": "timeout",
            "final_url": url,
            "redirect_chain": []
        }
    except httpx.ConnectError as ce:
        err_s = str(ce)
        if any(k in err_s.lower() for k in ("name", "dns", "getaddrinfo", "nodename")):
            err_msg = "DNS Resolution Failed"
            err_type = "dns_error"
            status_label = "DNS Error"
        else:
            err_msg = "Connection Refused"
            err_type = "connection_error"
            status_label = "Connection Error"
        return {
            "url": url,
            "status_code": 0,
            "status": status_label,
            "content_type": "N/A",
            "is_broken": True,
            "error": err_msg,
            "error_type": err_type,
            "final_url": url,
            "redirect_chain": []
        }
    except httpx.InvalidURL:
        return {
            "url": url,
            "status_code": 0,
            "status": "Malformed URL",
            "content_type": "N/A",
            "is_broken": True,
            "error": "Malformed URL",
            "error_type": "invalid_url",
            "final_url": url,
            "redirect_chain": []
        }
    except Exception as exc:
        err_text = str(exc)[:100] or type(exc).__name__
        return {
            "url": url,
            "status_code": 0,
            "status": "Network Error",
            "content_type": "N/A",
            "is_broken": True,
            "error": f"Network Error ({err_text})",
            "error_type": "network_error",
            "final_url": url,
            "redirect_chain": []
        }


async def check_links_status(
    urls: List[str],
    concurrency: int = 20,
    timeout: float = 10.0,
    user_agent: Optional[str] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    cancellation_checker: Optional[Callable[[], bool]] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Checks HTTP status for ALL unique URLs concurrently using bounded concurrency.
    There is NO arbitrary limit on the number of URLs.
    """
    unique_urls = list(dict.fromkeys(urls))
    total_count = len(unique_urls)
    results: Dict[str, Dict[str, Any]] = {}

    if total_count == 0:
        return results

    sem = asyncio.Semaphore(concurrency)
    completed_count = 0
    headers = {"User-Agent": user_agent} if user_agent else None

    # Use an SSRF-protected shared AsyncClient
    async with create_ssrf_safe_client(verify=False, timeout=timeout) as client:
        
        async def _worker(url: str):
            nonlocal completed_count
            if cancellation_checker and cancellation_checker():
                return
            async with sem:
                res = await check_single_link(client, url, timeout=timeout, headers=headers)
                results[url] = res
                completed_count += 1
                
                if progress_callback:
                    try:
                        # Report progress periodically or at milestones
                        msg = f"Checking external links: {completed_count}/{total_count}"
                        progress_callback(completed_count, total_count, msg)
                    except Exception:
                        pass

        tasks = [_worker(u) for u in unique_urls]
        await asyncio.gather(*tasks, return_exceptions=True)

    return results


class BrokenLinkChecker:
    """
    High-performance broken-link checking coordinator.
    Evaluates both internal and external links discovered during crawling.
    """

    def __init__(
        self,
        concurrency: int = 20,
        request_timeout: float = 10.0,
        user_agent: Optional[str] = None
    ):
        self.concurrency = concurrency
        self.request_timeout = request_timeout
        self.user_agent = user_agent

    async def check_all_links(
        self,
        internal_links: List[Dict[str, Any]],
        external_links: List[Dict[str, Any]],
        crawled_pages: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancellation_checker: Optional[Callable[[], bool]] = None
    ) -> List[Dict[str, Any]]:
        """
        Runs comprehensive broken-link analysis:
        1. For internal links: reuses already crawled page status without network requests.
        2. For uncrawled internal targets: runs status check.
        3. For external links: checks ALL unique targets concurrently (no cap).
        4. Enriches external_links with verified HTTP status and Content-Type.
        5. Reconstructs all source->target relationships for broken links only.
        """
        # Map of crawled pages by normalized URL
        crawled_page_map: Dict[str, Dict[str, Any]] = {}
        for p in crawled_pages:
            p_url = p.get("url")
            if p_url:
                crawled_page_map[normalize_link_url(p_url)] = p
                crawled_page_map[p_url] = p

        # Cache of evaluated status by normalized target URL
        target_status_cache: Dict[str, Dict[str, Any]] = {}

        # -------------------------------------------------------------
        # Phase 1: Internal Links
        # -------------------------------------------------------------
        if progress_callback:
            try:
                progress_callback(0, max(len(external_links), 1), "Checking internal links...")
            except Exception:
                pass

        uncrawled_internal_targets: Set[str] = set()

        for link in internal_links:
            target = link.get("target") or link.get("target_url") or link.get("destination_url") or link.get("href") or ""
            if not target or target.startswith(STATIC_OR_SPECIAL_SCHEMES):
                continue
            
            norm_target = normalize_link_url(target)
            
            # Check if target was already crawled
            matched_page = crawled_page_map.get(norm_target) or crawled_page_map.get(target)
            if matched_page:
                status_code = matched_page.get("status_code", 0)
                is_success = matched_page.get("is_success", True)
                fetch_status = matched_page.get("fetch_status", "")
                content_type = matched_page.get("content_type", "text/html")
                final_url = matched_page.get("final_url") or target
                
                is_broken = False
                err_msg = None
                status_label = "200 OK" if status_code == 200 else (f"{status_code} OK" if 200 <= status_code < 300 else f"HTTP {status_code}")

                if status_code in (403, 401) or fetch_status == "BLOCKED":
                    is_broken = True
                    err_msg = f"HTTP {status_code} Access Denied"
                    status_label = f"{status_code} Forbidden"
                elif status_code >= 400 or status_code == 0 or not is_success or fetch_status in ("FAILED", "TIMEOUT", "DNS_ERROR", "CONNECTION_REFUSED"):
                    is_broken = True
                    err_msg = matched_page.get("error") or f"HTTP {status_code} Error"
                    status_label = "404 Not Found" if status_code == 404 else f"{status_code} Error"
                
                target_status_cache[norm_target] = {
                    "status_code": status_code,
                    "status": status_label,
                    "content_type": content_type,
                    "is_broken": is_broken,
                    "error": err_msg,
                    "final_url": final_url,
                    "redirect_chain": []
                }
            else:
                uncrawled_internal_targets.add(target)

        # Check any uncrawled internal targets (e.g. assets, out of depth)
        if uncrawled_internal_targets:
            uncrawled_results = await check_links_status(
                urls=list(uncrawled_internal_targets),
                concurrency=self.concurrency,
                timeout=self.request_timeout,
                user_agent=self.user_agent,
                cancellation_checker=cancellation_checker
            )
            for u, res in uncrawled_results.items():
                target_status_cache[normalize_link_url(u)] = res
                target_status_cache[u] = res

        # -------------------------------------------------------------
        # Phase 2: External Links
        # -------------------------------------------------------------
        unique_external_targets: List[str] = []
        for link in external_links:
            target = link.get("target") or link.get("target_url") or link.get("destination_url") or link.get("href") or ""
            if not target or target.startswith(STATIC_OR_SPECIAL_SCHEMES):
                continue
            norm_target = normalize_link_url(target)
            if norm_target not in target_status_cache and target not in target_status_cache:
                unique_external_targets.append(target)

        # Deduplicate while preserving order
        unique_external_targets = list(dict.fromkeys(unique_external_targets))
        total_external = len(unique_external_targets)

        if total_external > 0:
            if progress_callback:
                try:
                    progress_callback(0, total_external, f"Checking external links: 0/{total_external}")
                except Exception:
                    pass

            external_results = await check_links_status(
                urls=unique_external_targets,
                concurrency=self.concurrency,
                timeout=self.request_timeout,
                user_agent=self.user_agent,
                progress_callback=progress_callback,
                cancellation_checker=cancellation_checker
            )
            for u, res in external_results.items():
                target_status_cache[normalize_link_url(u)] = res
                target_status_cache[u] = res

        # Annotate external_links in-place with verified status and Content-Type
        for link in external_links:
            target = link.get("target") or link.get("target_url") or link.get("destination_url") or link.get("href") or ""
            if not target:
                continue
            norm_target = normalize_link_url(target)
            status_info = target_status_cache.get(norm_target) or target_status_cache.get(target)
            if status_info:
                link["status_code"] = status_info.get("status_code", 0)
                link["status"] = status_info.get("status") or "Not Checked"
                link["content_type"] = status_info.get("content_type") or "Not Checked"
                link["final_url"] = status_info.get("final_url", target)
                link["redirect_chain"] = status_info.get("redirect_chain", [])
                link["is_broken"] = status_info.get("is_broken", False)
                link["error"] = status_info.get("error")
            else:
                link["status"] = "Not Checked"
                link["content_type"] = "Not Checked"

        if progress_callback:
            try:
                progress_callback(total_external, total_external, "Broken link checking complete")
            except Exception:
                pass

        # -------------------------------------------------------------
        # Phase 3: Construct Combined Broken Links Dataset
        # -------------------------------------------------------------
        broken_links: List[Dict[str, Any]] = []

        # Internal broken links
        for link in internal_links:
            target = link.get("target") or link.get("target_url") or link.get("destination_url") or link.get("href") or ""
            norm_target = normalize_link_url(target)
            status_info = target_status_cache.get(norm_target) or target_status_cache.get(target)
            
            if status_info and status_info.get("is_broken"):
                broken_links.append({
                    "source": link.get("source") or link.get("source_url", ""),
                    "target": target,
                    "anchor_text": link.get("anchor_text") or link.get("anchor", "") or "[No Anchor Text]",
                    "link_type": "internal",
                    "status_code": status_info.get("status_code", 0),
                    "status": status_info.get("status") or f"HTTP {status_info.get('status_code', 0)}",
                    "content_type": status_info.get("content_type", "text/html"),
                    "is_broken": True,
                    "error": status_info.get("error"),
                    "error_type": status_info.get("error_type", "http_error"),
                    "final_url": status_info.get("final_url", target),
                    "redirect_chain": status_info.get("redirect_chain", []),
                    "rel": link.get("rel", "follow"),
                    "source_section": link.get("source_section", "other"),
                    "nearest_heading": link.get("nearest_heading"),
                    "heading_level": link.get("heading_level"),
                    "paragraph_index": link.get("paragraph_index"),
                    "sentence_index": link.get("sentence_index"),
                    "context_before": link.get("context_before", ""),
                    "context_text": link.get("context_text", ""),
                    "context_after": link.get("context_after", ""),
                    "html_snippet": link.get("html_snippet", "")
                })

        # External broken links
        for link in external_links:
            target = link.get("target") or link.get("target_url") or link.get("destination_url") or link.get("href") or ""
            norm_target = normalize_link_url(target)
            status_info = target_status_cache.get(norm_target) or target_status_cache.get(target)
            
            if status_info and status_info.get("is_broken"):
                broken_links.append({
                    "source": link.get("source") or link.get("source_url", ""),
                    "target": target,
                    "anchor_text": link.get("anchor_text") or link.get("anchor", "") or "[External Link]",
                    "link_type": "external",
                    "status_code": status_info.get("status_code", 0),
                    "status": status_info.get("status") or f"HTTP {status_info.get('status_code', 0)}",
                    "content_type": status_info.get("content_type", "text/html"),
                    "is_broken": True,
                    "error": status_info.get("error"),
                    "error_type": status_info.get("error_type", "http_error"),
                    "final_url": status_info.get("final_url", target),
                    "redirect_chain": status_info.get("redirect_chain", []),
                    "rel": link.get("rel", "follow"),
                    "source_section": link.get("source_section", "other"),
                    "nearest_heading": link.get("nearest_heading"),
                    "heading_level": link.get("heading_level"),
                    "paragraph_index": link.get("paragraph_index"),
                    "sentence_index": link.get("sentence_index"),
                    "context_before": link.get("context_before", ""),
                    "context_text": link.get("context_text", ""),
                    "context_after": link.get("context_after", ""),
                    "html_snippet": link.get("html_snippet", "")
                })

        return broken_links
