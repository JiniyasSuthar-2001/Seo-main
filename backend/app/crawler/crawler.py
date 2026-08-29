import httpx
import asyncio
import time
import re
import ssl
import json
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from typing import Set, Dict, Any, List, Optional, Callable

STATIC_ASSET_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".tar", ".gz", ".rar",
    ".mp4", ".avi", ".mov", ".mp3", ".wav", ".css", ".js", ".woff", ".woff2", ".ttf", ".eot"
)

class SEOCrawler:
    def __init__(
        self, 
        start_url: str, 
        max_pages: int = 5000, 
        request_timeout: float = 20.0,
        scope_type: str = "entire_domain",
        max_depth: int = 0,
        respect_robots_txt: bool = True,
        crawl_delay_ms: int = 500,
        user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        ignore_utm_params: bool = True,
        follow_redirects: bool = True,
        target_countries: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int]], None] = None,
        cancellation_checker: Optional[Callable[[], bool]] = None
    ):
        if not start_url or not start_url.startswith(("http://", "https://")):
            raise ValueError("Crawler requires a valid HTTP or HTTPS start URL.")

        self.raw_start_url = start_url
        self.ignore_utm_params = ignore_utm_params
        self.start_url = self.normalize_url(start_url, start_url)
        
        # Handle 5000+ Large-Site Mode (unlimited pages within scope)
        if max_pages == "5000+" or max_pages == 0 or max_pages is None or str(max_pages).strip() == "5000+":
            self.max_pages = 0
            self.is_unlimited_scope = True
        else:
            try:
                val = int(max_pages)
                if val <= 0:
                    self.max_pages = 0
                    self.is_unlimited_scope = True
                else:
                    self.max_pages = val
                    self.is_unlimited_scope = False
            except (ValueError, TypeError):
                self.max_pages = 5000
                self.is_unlimited_scope = False

        self.request_timeout = request_timeout
        self.scope_type = scope_type
        self.max_depth = max_depth
        self.respect_robots_txt = respect_robots_txt
        self.crawl_delay_ms = crawl_delay_ms
        self.user_agent = user_agent
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.follow_redirects = follow_redirects
        self.target_countries = target_countries or []
        self.progress_callback = progress_callback
        self.cancellation_checker = cancellation_checker
        self.is_cancelled = False

        parsed_url = urlparse(self.start_url)
        self.domain = parsed_url.netloc.lower()
        self.scheme = parsed_url.scheme
        self.start_path = parsed_url.path or "/"
        
        # Track depth per URL
        self.url_depths: Dict[str, int] = {self.start_url: 0}
        
        # Queue state tracking: PENDING, CRAWLING, CRAWLED, FAILED, BLOCKED, SKIPPED
        self.queue_status: Dict[str, str] = {self.start_url: "PENDING"}
        self.visited: Set[str] = set()
        self.to_visit: List[str] = [self.start_url]
        
        self.disallowed_paths: List[str] = []
        self.sitemap_urls: List[str] = []
        
        # Results collections
        self.pages: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
        self.internal_links: List[Dict[str, Any]] = []
        self.external_links: List[Dict[str, Any]] = []
        self.asset_checks: List[Dict[str, Any]] = []
        
        self.is_running = False
        self.seed_status_code = None

    def is_same_domain(self, url: str) -> bool:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        dom = self.domain.lower()
        clean_netloc = netloc.replace("www.", "")
        clean_dom = dom.replace("www.", "")
        return clean_netloc == clean_dom

    def is_static_asset(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        return path.endswith(STATIC_ASSET_EXTENSIONS)

    def normalize_url(self, url: str, base_url: str) -> str:
        full_url = urljoin(base_url, url)
        parsed = urlparse(full_url)
        path = parsed.path
        if not path:
            path = "/"
        elif path != "/" and path.endswith("/"):
            path = path.rstrip("/")

        query_str = ""
        if parsed.query:
            if self.ignore_utm_params:
                q_params = [q for q in parsed.query.split("&") if q and not q.startswith(("utm_", "fbclid=", "gclid=", "mc_cid=", "mc_eid="))]
                if q_params:
                    query_str = "?" + "&".join(q_params)
            else:
                query_str = "?" + parsed.query

        return f"{parsed.scheme}://{parsed.netloc}{path}{query_str}".lower()

    async def fetch_robots_txt(self, client: httpx.AsyncClient):
        robots_url = f"{self.scheme}://{self.domain}/robots.txt"
        print(f"[ROBOTS] Requesting {robots_url}", flush=True)
        try:
            resp = await client.get(robots_url, timeout=10.0, follow_redirects=True)
            if resp.status_code == 200:
                print(f"[ROBOTS] Found robots.txt ({len(resp.text)} bytes)", flush=True)
                for line in resp.text.splitlines():
                    line = line.strip()
                    if line.lower().startswith("disallow:"):
                        path = line.split(":", 1)[1].strip()
                        if path:
                            self.disallowed_paths.append(path)
                    elif line.lower().startswith("sitemap:"):
                        s_url = line.split(":", 1)[1].strip()
                        if s_url:
                            self.sitemap_urls.append(s_url)
        except Exception as e:
            print(f"[ROBOTS] Optional robots.txt fetch error: {e}", flush=True)

    async def fetch_sitemap_xml(self, client: httpx.AsyncClient):
        sitemap_candidates = list(self.sitemap_urls) or [f"{self.scheme}://{self.domain}/sitemap.xml"]
        for sm_url in sitemap_candidates[:3]:
            try:
                resp = await client.get(sm_url, timeout=10.0, follow_redirects=True)
                if resp.status_code == 200:
                    found_locs = re.findall(r"<loc>(.*?)</loc>", resp.text, re.I)
                    print(f"[SITEMAP] Discovered {len(found_locs)} URLs from {sm_url}", flush=True)
                    for loc in found_locs[:100]:
                        norm = self.normalize_url(loc.strip(), sm_url)
                        if self.is_same_domain(norm) and not self.is_static_asset(norm) and norm not in self.queue_status:
                            self.queue_status[norm] = "PENDING"
                            self.to_visit.append(norm)
            except Exception as e:
                print(f"[SITEMAP] Optional sitemap fetch error for {sm_url}: {e}", flush=True)

    def is_disallowed(self, url: str) -> bool:
        if not self.respect_robots_txt or not self.disallowed_paths:
            return False
        parsed = urlparse(url)
        path = parsed.path or "/"
        for dis in self.disallowed_paths:
            if dis == "/":
                return True
            if path.startswith(dis):
                return True
        return False

    def is_within_scope(self, url: str) -> bool:
        if not self.is_same_domain(url):
            return False

        if self.is_static_asset(url):
            return False

        if self.max_depth > 0:
            depth = self.url_depths.get(url, 999)
            if depth >= self.max_depth:
                return False

        parsed = urlparse(url)
        path = parsed.path or "/"

        if self.scope_type == "subfolder_only":
            if not path.startswith(self.start_path):
                return False

        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                clean_pat = pattern.strip().lower()
                if clean_pat and (clean_pat in path or clean_pat in url):
                    return False

        if self.include_patterns:
            matched = False
            for pattern in self.include_patterns:
                clean_pat = pattern.strip().lower()
                if clean_pat and (clean_pat in path or clean_pat in url):
                    matched = True
                    break
            if not matched:
                return False

        return True

    def evaluate_page_issues(self, page_data: Dict[str, Any]):
        url = page_data["url"]
        status = page_data.get("status_code", 0)
        fetch_st = page_data.get("fetch_status") or "FAILED"
        
        source_links = [l for l in self.internal_links if l.get("target") == url]
        source_url = source_links[0]["source"] if source_links else page_data.get("source_url") or "Start URL"

        if status in (403, 401) or fetch_st == "BLOCKED":
            self.issues.append({
                "rule_id": "CRAWL_002",
                "category": "Crawlability",
                "severity": "Critical",
                "issue_type": "Access Denied / Forbidden",
                "affected_url": url,
                "source_url": source_url,
                "details": f"URL '{url}' returned HTTP status {status} (Access Denied / Forbidden). Crawling blocked.",
                "recommendation": "Verify firewall policies, server permissions, or user-agent access controls."
            })
            return

        if status >= 400 or status == 0 or not page_data.get("is_success", True):
            err_msg = page_data.get("error") or f"HTTP {status}"
            is_internal = (url != self.start_url)
            self.issues.append({
                "rule_id": "LINK_002" if is_internal else "CRAWL_001",
                "category": "Internal Links" if is_internal else "Crawlability",
                "severity": "Critical",
                "issue_type": "Internal Broken Link" if is_internal else "HTTP Error / Broken Page",
                "affected_url": url,
                "source_url": source_url,
                "details": f"Page request failed ({err_msg}). Discovered on '{source_url}'.",
                "recommendation": "Fix broken URL or update internal link anchor targets."
            })
            return

        if not page_data.get("title"):
            self.issues.append({
                "severity": "Critical",
                "issue_type": "Missing Title",
                "affected_url": url,
                "details": "Page does not have a <title> tag.",
                "recommendation": "Add a descriptive <title> tag containing primary target keywords (50-60 characters)."
            })

        if not page_data.get("meta_description"):
            self.issues.append({
                "severity": "Warning",
                "issue_type": "Missing Meta Description",
                "affected_url": url,
                "details": "Page is missing a meta description tag.",
                "recommendation": "Add a compelling meta description (150-160 characters) to improve CTR."
            })

        if not page_data.get("h1"):
            self.issues.append({
                "severity": "Warning",
                "issue_type": "Missing H1 Heading",
                "affected_url": url,
                "details": "Page is missing a main <h1> heading tag.",
                "recommendation": "Include a single <h1> heading representing the page topic."
            })
        elif page_data.get("h1_count", 0) > 1:
            self.issues.append({
                "severity": "Notice",
                "issue_type": "Multiple H1 Headings",
                "affected_url": url,
                "details": f"Page contains {page_data['h1_count']} <h1> tags.",
                "recommendation": "Use only one primary <h1> heading per page for clean structural hierarchy."
            })

        if not page_data.get("canonical"):
            self.issues.append({
                "severity": "Notice",
                "issue_type": "Missing Canonical Tag",
                "affected_url": url,
                "details": "Page does not declare a canonical URL tag.",
                "recommendation": "Add <link rel='canonical' href='...'> to prevent duplicate content issues."
            })

        if page_data.get("word_count", 0) < 150:
            self.issues.append({
                "severity": "Notice",
                "issue_type": "Thin Content",
                "affected_url": url,
                "details": f"Page text content is low ({page_data['word_count']} words).",
                "recommendation": "Expand body text to provide substantial value for visitors and search crawlers."
            })

        if page_data.get("images_missing_alt", 0) > 0:
            self.issues.append({
                "severity": "Notice",
                "issue_type": "Missing Image Alt Text",
                "affected_url": url,
                "details": f"{page_data['images_missing_alt']} image(s) on this page lack alt attributes.",
                "recommendation": "Add descriptive alt attributes to all content images for accessibility and image SEO."
            })

    async def crawl_page(self, client: httpx.AsyncClient, url: str):
        if url in self.visited or len(self.visited) >= self.max_pages:
            return
            
        if self.is_disallowed(url):
            print(f"[ROBOTS] Skipping disallowed URL: {url}", flush=True)
            self.queue_status[url] = "SKIPPED"
            return

        self.visited.add(url)
        self.queue_status[url] = "CRAWLING"
        print(f"[CRAWL HTTP] GET {url}", flush=True)

        start_time = time.time()
        
        try:
            # Enforce strict 20.0 second max timeout per individual page operation
            await asyncio.wait_for(
                self._fetch_and_process_page(client, url, start_time),
                timeout=self.request_timeout
            )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            err_msg = f"Page crawl timed out after {self.request_timeout} seconds."
            print(f"[CRAWL TIMEOUT] {url} ({err_msg})", flush=True)
            self.queue_status[url] = "TIMEOUT"
            page_record = {
                "url": url,
                "status_code": 0,
                "response_time_ms": elapsed_ms,
                "error": err_msg,
                "is_success": False,
                "fetch_status": "TIMEOUT",
                "content_available": False,
                "word_count": 0,
                "internal_links_count": 0,
                "action": "Skipped and crawl continued."
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
        except Exception as unhandled_err:
            elapsed_ms = int((time.time() - start_time) * 1000)
            err_msg = f"Page processing exception: {str(unhandled_err)[:120]}"
            print(f"[CRAWL PAGE ERROR] {url} ({err_msg})", flush=True)
            self.queue_status[url] = "FAILED"
            page_record = {
                "url": url,
                "status_code": 0,
                "response_time_ms": elapsed_ms,
                "error": err_msg,
                "is_success": False,
                "fetch_status": "FAILED",
                "content_available": False,
                "word_count": 0,
                "internal_links_count": 0,
                "action": "Skipped and crawl continued."
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
        finally:
            if self.progress_callback:
                try:
                    self.progress_callback(len(self.visited), len(self.queue_status))
                except Exception:
                    pass

    async def _fetch_and_process_page(self, client: httpx.AsyncClient, url: str, start_time: float):
        attempt = 0
        max_attempts = 1  # 1 attempt per page bounded strictly by 20s
        response = None
        elapsed_ms = 0
        fetch_error = None
        fetch_status = "FAILED"

        while attempt < max_attempts:
            attempt += 1
            try:
                headers = {
                    "User-Agent": self.user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Upgrade-Insecure-Requests": "1"
                }
                response = await client.get(url, headers=headers, timeout=self.request_timeout, follow_redirects=True)
                elapsed_ms = int((time.time() - start_time) * 1000)
                break
            except httpx.TimeoutException:
                elapsed_ms = int((time.time() - start_time) * 1000)
                fetch_status = "TIMEOUT"
                fetch_error = f"Request timed out after {self.request_timeout}s"
            except httpx.ConnectError as ce:
                elapsed_ms = int((time.time() - start_time) * 1000)
                err_str = str(ce)
                if "name" in err_str.lower() or "dns" in err_str.lower() or "getaddrinfo" in err_str.lower():
                    fetch_status = "DNS_ERROR"
                    fetch_error = "DNS resolution failed"
                else:
                    fetch_status = "CONNECTION_REFUSED"
                    fetch_error = "Connection refused"
            except Exception as e:
                elapsed_ms = int((time.time() - start_time) * 1000)
                fetch_status = "NETWORK_ERROR"
                fetch_error = f"Network request error: {str(e)[:120]}"

        if not response:
            print(f"[CRAWL FAILED] {fetch_status} for {url} ({fetch_error})", flush=True)
            self.queue_status[url] = fetch_status if fetch_status == "TIMEOUT" else "FAILED"
            page_record = {
                "url": url,
                "status_code": 0,
                "response_time_ms": elapsed_ms,
                "error": fetch_error,
                "is_success": False,
                "fetch_status": fetch_status,
                "content_available": False,
                "word_count": 0,
                "internal_links_count": 0,
                "action": "Skipped and crawl continued."
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
            return

        if url == self.start_url:
            self.seed_status_code = response.status_code

        print(f"[CRAWL HTTP] {response.status_code} {url} ({elapsed_ms}ms)", flush=True)
        
        if response.status_code in (403, 401):
            self.queue_status[url] = "BLOCKED"
            page_record = {
                "url": url,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "error": f"HTTP {response.status_code} Access Denied",
                "is_success": False,
                "fetch_status": "BLOCKED",
                "content_available": False,
                "word_count": 0,
                "internal_links_count": 0,
                "action": "Skipped and crawl continued."
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
            return

        if response.status_code >= 400:
            self.queue_status[url] = "FAILED"
            page_record = {
                "url": url,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "error": f"HTTP {response.status_code} Error",
                "is_success": False,
                "fetch_status": "FAILED",
                "content_available": False,
                "word_count": 0,
                "internal_links_count": 0,
                "action": "Skipped and crawl continued."
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
            return

        self.queue_status[url] = "CRAWLED"
        
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            self.asset_checks.append({
                "url": url,
                "status_code": response.status_code,
                "content_type": content_type
            })
            return

        try:
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            title_tag = soup.title.string.strip() if soup.title and soup.title.string else None
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_description = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else None
            
            canonical_tag = soup.find("link", attrs={"rel": "canonical"})
            canonical = canonical_tag["href"].strip() if canonical_tag and canonical_tag.get("href") else None
            
            robots_tag = soup.find("meta", attrs={"name": "robots"})
            robots_meta = robots_tag["content"].strip() if robots_tag and robots_tag.get("content") else "index, follow"

            html_lang = soup.html.get("lang").strip() if soup.html and soup.html.get("lang") else None
            viewport_tag = soup.find("meta", attrs={"name": "viewport"})
            viewport = viewport_tag["content"].strip() if viewport_tag and viewport_tag.get("content") else None

            hreflangs = []
            for link in soup.find_all("link", attrs={"rel": re.compile(r"alternate", re.I)}):
                if link.get("hreflang"):
                    hreflangs.append({
                        "lang": link.get("hreflang").strip(),
                        "href": link.get("href", "").strip()
                    })

            structured_data = []
            for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
                if script.string:
                    try:
                        structured_data.append(json.loads(script.string.strip()))
                    except Exception:
                        pass

            h1_tags = [h.get_text().strip() for h in soup.find_all("h1") if h.get_text()]
            h2_tags = [h.get_text().strip() for h in soup.find_all("h2") if h.get_text()]
            h3_tags = [h.get_text().strip() for h in soup.find_all("h3") if h.get_text()]
            h1 = h1_tags[0] if h1_tags else None

            text = soup.get_text(separator=" ")
            words = [w for w in text.split() if len(w) > 1]
            word_count = len(words)

            images = soup.find_all("img")
            images_missing_alt = sum(1 for img in images if not img.get("alt"))

            current_depth = self.url_depths.get(url, 0)
            discovered_internal = []

            for a_tag in soup.find_all("a", href=True):
                raw_href = a_tag["href"].strip()
                if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue
                
                normalized = self.normalize_url(raw_href, url)

                if self.is_same_domain(normalized):
                    discovered_internal.append(normalized)
                    self.internal_links.append({
                        "source": url,
                        "target": normalized,
                        "anchor_text": a_tag.get_text().strip() or "[Image/No Text]",
                        "rel": a_tag.get("rel", "")
                    })
                    
                    if normalized not in self.queue_status and self.is_within_scope(normalized):
                        self.queue_status[normalized] = "PENDING"
                        self.url_depths[normalized] = current_depth + 1
                        self.to_visit.append(normalized)
                else:
                    self.external_links.append({
                        "source": url,
                        "target": normalized,
                        "anchor_text": a_tag.get_text().strip() or "[External Link]",
                        "rel": a_tag.get("rel", "")
                    })

            page_record = {
                "url": url,
                "final_url": str(response.url),
                "redirect_history": [str(r.url) for r in response.history],
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "is_success": True,
                "fetch_status": "FETCHED",
                "content_available": True,
                "title": title_tag,
                "meta_description": meta_description,
                "canonical": canonical,
                "robots_meta": robots_meta,
                "html_lang": html_lang,
                "viewport": viewport,
                "hreflangs": hreflangs,
                "structured_data": structured_data,
                "h1": h1,
                "h1_count": len(h1_tags),
                "h2_count": len(h2_tags),
                "h3_count": len(h3_tags),
                "word_count": word_count,
                "images_count": len(images),
                "images_missing_alt": images_missing_alt,
                "internal_links_count": len(discovered_internal)
            }
            
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
        except Exception as parse_err:
            print(f"[PARSE ERROR] Failed to parse HTML for {url}: {parse_err}", flush=True)
            page_record = {
                "url": url,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "error": f"HTML parsing error: {parse_err}",
                "is_success": False,
                "fetch_status": "PARSE_ERROR",
                "content_available": False,
                "word_count": 0,
                "internal_links_count": 0,
                "action": "Skipped and crawl continued."
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)

    async def start(self) -> Dict[str, Any]:
        self.is_running = True
        print(f"[CRAWL] Starting real Internet crawl for {self.start_url}", flush=True)
        
        async with httpx.AsyncClient(verify=False) as client:
            await self.fetch_robots_txt(client)
            await self.fetch_sitemap_xml(client)

            while self.to_visit and (self.is_unlimited_scope or len(self.visited) < self.max_pages):
                if self.cancellation_checker and self.cancellation_checker():
                    print(f"[CRAWL CANCELLED] Session cancellation requested by user. Halting crawler loop.", flush=True)
                    self.is_cancelled = True
                    break

                batch = self.to_visit[:5] 
                self.to_visit = self.to_visit[5:]
                
                tasks = [self.crawl_page(client, url) for url in batch]
                await asyncio.gather(*tasks, return_exceptions=True)
                await asyncio.sleep(0.2)

        self.is_running = False

        successful_pages = [p for p in self.pages if p.get("is_success") and p.get("status_code") == 200]
        failed_pages = [p for p in self.pages if not p.get("is_success") or (p.get("status_code") or 0) >= 400]
        
        is_access_denied = (self.seed_status_code in (403, 401))
        
        if self.is_cancelled:
            overall_status = "cancelled"
        elif is_access_denied:
            overall_status = "access_denied"
        elif len(successful_pages) > 0 and len(failed_pages) > 0:
            overall_status = "completed_with_errors"
        elif len(successful_pages) > 0 and len(failed_pages) == 0:
            overall_status = "completed"
        elif len(self.pages) > 0:
            overall_status = "completed_with_errors"
        else:
            overall_status = "failed"

        print(f"[CRAWL FINISHED] Status: '{overall_status}'. Total Pages Saved: {len(self.pages)}, Successful: {len(successful_pages)}, Failed/Blocked: {len(failed_pages)}, Issues: {len(self.issues)}", flush=True)
        
        return {
            "status": overall_status,
            "max_pages": "5000+" if self.is_unlimited_scope else self.max_pages,
            "seed_status_code": self.seed_status_code,
            "successful_pages_count": len(successful_pages),
            "failed_pages_count": len(failed_pages),
            "pages": self.pages,
            "issues": self.issues,
            "internal_links": self.internal_links,
            "external_links": self.external_links,
            "asset_checks": self.asset_checks
        }
