import httpx
import asyncio
import time
import re
import ssl
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from typing import Set, Dict, Any, List, Optional


STATIC_ASSET_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".tar", ".gz", ".rar",
    ".mp4", ".avi", ".mov", ".mp3", ".wav", ".css", ".js", ".woff", ".woff2", ".ttf", ".eot"
)

class SEOCrawler:
    def __init__(self, start_url: str, max_pages: int = 1000, request_timeout: float = 20.0):
        if not start_url or not start_url.startswith(("http://", "https://")):
            raise ValueError("Crawler requires a valid HTTP or HTTPS start URL.")

        self.start_url = self.normalize_url(start_url, start_url)
        self.max_pages = max_pages
        self.request_timeout = request_timeout
        
        parsed_url = urlparse(self.start_url)
        self.domain = parsed_url.netloc.lower()
        self.scheme = parsed_url.scheme
        
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
        self.user_agent = "SEO-Intelligence-Platform/1.0 (Mozilla/5.0 Compatible)"

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
            
        return f"{parsed.scheme}://{parsed.netloc}{path}".lower()

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
                        sm_url = line.split(":", 1)[1].strip()
                        if sm_url:
                            self.sitemap_urls.append(sm_url)
        except Exception as e:
            print(f"[ROBOTS] robots.txt not available: {e}", flush=True)

    async def fetch_sitemap_xml(self, client: httpx.AsyncClient):
        sitemaps_to_check = self.sitemap_urls if self.sitemap_urls else [f"{self.scheme}://{self.domain}/sitemap.xml"]
        for sm_url in sitemaps_to_check:
            print(f"[SITEMAP] Inspecting sitemap {sm_url}", flush=True)
            try:
                resp = await client.get(sm_url, timeout=10.0, follow_redirects=True)
                if resp.status_code == 200 and "xml" in resp.headers.get("content-type", ""):
                    soup = BeautifulSoup(resp.text, "xml")
                    locs = [loc.text.strip() for loc in soup.find_all("loc") if loc.text.strip()]
                    discovered_count = 0
                    for loc in locs:
                        norm = self.normalize_url(loc, sm_url)
                        if self.is_same_domain(norm) and not self.is_static_asset(norm) and norm not in self.queue_status:
                            self.queue_status[norm] = "PENDING"
                            self.to_visit.append(norm)
                            discovered_count += 1
                    print(f"[SITEMAP] Discovered {discovered_count} HTML URLs from {sm_url}", flush=True)
            except Exception as e:
                print(f"[SITEMAP] Failed to parse sitemap {sm_url}: {e}", flush=True)

    def is_disallowed(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path
        for dis in self.disallowed_paths:
            if dis == "/" or path.startswith(dis):
                return True
        return False

    def evaluate_page_issues(self, page_data: Dict[str, Any]):
        url = page_data["url"]
        status = page_data.get("status_code", 0)
        
        if status == 403 or status == 401:
            self.issues.append({
                "severity": "Critical",
                "issue_type": "Access Denied / Forbidden",
                "affected_url": url,
                "details": f"Server returned HTTP status {status} (Access Denied / Forbidden). Crawling blocked.",
                "recommendation": "Verify firewall policies, server permissions, or user-agent access controls."
            })
            return

        if status >= 400 or status == 0:
            self.issues.append({
                "severity": "Critical",
                "issue_type": "HTTP Error",
                "affected_url": url,
                "details": f"Page returned HTTP status code {status}",
                "recommendation": "Investigate server errors or update broken internal links."
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
        print(f"[HTTP] GET {url}", flush=True)
        
        start_time = time.time()
        try:
            headers = {"User-Agent": self.user_agent}
            response = await client.get(url, headers=headers, timeout=self.request_timeout, follow_redirects=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            if url == self.start_url:
                self.seed_status_code = response.status_code

            print(f"[HTTP] {response.status_code} {url} ({elapsed_ms}ms)", flush=True)
            
            # Handle HTTP Access Denied (403, 401) or HTTP Errors (5xx, 4xx)
            if response.status_code in (403, 401):
                self.queue_status[url] = "BLOCKED"
                page_record = {
                    "url": url,
                    "status_code": response.status_code,
                    "response_time_ms": elapsed_ms,
                    "error": f"HTTP {response.status_code} Access Denied",
                    "is_success": False,
                    "word_count": 0,
                    "internal_links_count": 0
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
                    "word_count": 0,
                    "internal_links_count": 0
                }
                self.pages.append(page_record)
                self.evaluate_page_issues(page_record)
                return

            self.queue_status[url] = "CRAWLED"
            
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                # Store as static resource check rather than HTML page
                self.asset_checks.append({
                    "url": url,
                    "status_code": response.status_code,
                    "content_type": content_type
                })
                return

            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            
            # Metadata Extraction
            title_tag = soup.title.string.strip() if soup.title and soup.title.string else None
            
            meta_desc_tag = soup.find("meta", attrs={"name": "description"})
            meta_description = meta_desc_tag["content"].strip() if meta_desc_tag and meta_desc_tag.get("content") else None
            
            canonical_tag = soup.find("link", attrs={"rel": "canonical"})
            canonical = canonical_tag["href"].strip() if canonical_tag and canonical_tag.get("href") else None
            
            robots_tag = soup.find("meta", attrs={"name": "robots"})
            robots_meta = robots_tag["content"].strip() if robots_tag and robots_tag.get("content") else "index, follow"

            # Headings
            h1_tags = [h.text.strip() for h in soup.find_all("h1") if h.text.strip()]
            h1 = h1_tags[0] if h1_tags else None
            
            h2_tags = soup.find_all("h2")
            h3_tags = soup.find_all("h3")

            # Word Count
            body_text = soup.body.get_text(separator=" ", strip=True) if soup.body else ""
            words = body_text.split()
            word_count = len(words)

            # Images
            images = soup.find_all("img")
            images_missing_alt = sum(1 for img in images if not img.get("alt") or not img["alt"].strip())

            # Extract Links & Separate HTML pages from Static Asset URLs
            discovered_internal = set()
            a_tags = soup.find_all("a", href=True)
            
            for a_tag in a_tags:
                href = a_tag["href"].strip()
                anchor_text = a_tag.text.strip()
                
                if not href or href.startswith(("mailto:", "tel:", "javascript:", "#")):
                    continue
                    
                normalized = self.normalize_url(href, url)
                
                # Check if target is a static image or asset file vs HTML page
                if self.is_static_asset(normalized):
                    self.asset_checks.append({
                        "url": normalized,
                        "found_on": url,
                        "type": "static_asset"
                    })
                    continue

                if self.is_same_domain(normalized):
                    discovered_internal.add(normalized)
                    self.internal_links.append({
                        "source": url,
                        "target": normalized,
                        "anchor_text": anchor_text
                    })
                    if normalized not in self.visited and normalized not in self.to_visit and len(self.visited) + len(self.to_visit) < self.max_pages:
                        self.queue_status[normalized] = "PENDING"
                        self.to_visit.append(normalized)
                else:
                    self.external_links.append({
                        "source": url,
                        "target": normalized,
                        "anchor_text": anchor_text
                    })

            print(f"[PARSE] Extracted {len(discovered_internal)} internal HTML links from {url}", flush=True)

            page_record = {
                "url": url,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "is_success": True,
                "title": title_tag,
                "meta_description": meta_description,
                "canonical": canonical,
                "robots_meta": robots_meta,
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

        except (httpx.SSLError, ssl.SSLError) as ssl_err:
            elapsed_ms = int((time.time() - start_time) * 1000)
            print(f"[SSL ERROR] TLS verification failed for {url}: {ssl_err}", flush=True)
            self.queue_status[url] = "FAILED"
            page_record = {
                "url": url,
                "status_code": 0,
                "response_time_ms": elapsed_ms,
                "is_success": False,
                "error": "SSL/TLS certificate validation failed — HTTPS connection could not be securely established",
                "word_count": 0,
                "internal_links_count": 0
            }
            self.pages.append(page_record)
            self.issues.append({
                "severity": "Critical",
                "issue_type": "SSL / TLS Certificate Validation Failed",
                "affected_url": url,
                "details": f"HTTPS request failed certificate verification: {ssl_err}",
                "recommendation": "Renew expired SSL certificate, configure valid CA chain, or resolve hostname mismatch."
            })
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            print(f"[ERROR] Failed to fetch {url}: {e}", flush=True)
            self.queue_status[url] = "FAILED"
            page_record = {
                "url": url,
                "status_code": 0,
                "response_time_ms": elapsed_ms,
                "is_success": False,
                "error": str(e),
                "word_count": 0,
                "internal_links_count": 0
            }
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)

    async def start(self) -> Dict[str, Any]:
        self.is_running = True
        print(f"[CRAWL] Starting real Internet crawl for {self.start_url}", flush=True)
        
        async with httpx.AsyncClient(verify=True) as client:

            # 1. Fetch robots.txt and sitemap.xml first
            await self.fetch_robots_txt(client)
            await self.fetch_sitemap_xml(client)

            # 2. Main Crawl Queue Loop
            while self.to_visit and len(self.visited) < self.max_pages:
                batch = self.to_visit[:5] 
                self.to_visit = self.to_visit[5:]
                
                tasks = [self.crawl_page(client, url) for url in batch]
                await asyncio.gather(*tasks)
                await asyncio.sleep(0.5)

        self.is_running = False

        successful_pages = [p for p in self.pages if p.get("is_success") and p.get("status_code") == 200]
        failed_pages = [p for p in self.pages if not p.get("is_success") or (p.get("status_code") or 0) >= 400]
        
        # Check if seed or entire site was access denied (e.g. 403 Forbidden)
        is_access_denied = (self.seed_status_code in (403, 401)) or (len(successful_pages) == 0 and len(failed_pages) > 0)
        overall_status = "access_denied" if is_access_denied else ("completed" if successful_pages else "failed")

        print(f"[CRAWL FINISHED] Status: {overall_status}. Successful Pages: {len(successful_pages)}, Failed/Blocked: {len(failed_pages)}, Issues: {len(self.issues)}", flush=True)
        
        return {
            "status": overall_status,
            "seed_status_code": self.seed_status_code,
            "successful_pages_count": len(successful_pages),
            "failed_pages_count": len(failed_pages),
            "pages": self.pages,
            "issues": self.issues,
            "internal_links": self.internal_links,
            "external_links": self.external_links,
            "asset_checks": self.asset_checks
        }
