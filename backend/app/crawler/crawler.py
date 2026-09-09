import httpx
import asyncio
import time
import re
import ssl
import json
import uuid
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlunparse, parse_qsl, urlencode
from bs4 import BeautifulSoup
from typing import Set, Dict, Any, List, Optional, Callable, Tuple
from app.crawler.broken_link_checker import BrokenLinkChecker
from app.crawler.ssrf_protection import validate_url_ssrf, create_ssrf_safe_client, SSRFBlockedError

STATIC_ASSET_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp", ".tiff",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".tar", ".gz", ".rar",
    ".mp4", ".avi", ".mov", ".mp3", ".wav", ".css", ".js", ".woff", ".woff2", ".ttf", ".eot"
)

BOT_PROTECTION_KEYWORDS = (
    "just a moment...", "verify you are human", "checking your browser",
    "cf-browser-verification", "turnstile", "ddos-guard", "cloudflare ray id",
    "security verification", "attention required! | cloudflare", "access denied"
)

def canonicalize_url(url: str, base_url: str = "", ignore_utm_params: bool = True) -> str:
    """
    Centralized canonical URL normalizer:
    1. Resolves relative and protocol-relative URLs against base_url.
    2. Strips URL fragments (#section).
    3. Normalizes scheme and host to lowercase.
    4. Removes default ports (:80 on http, :443 on https).
    5. Normalizes path (normalizes multi-slashes, standardizes trailing slashes).
    6. Filters tracking parameters (utm_*, gclid, fbclid, etc.) and sorts query parameters for deduplication.
    """
    if not url or not isinstance(url, str):
        return ""

    url = url.strip()
    if not url or url.startswith(("#", "javascript:", "mailto:", "tel:")):
        return ""

    if base_url:
        full_url = urljoin(base_url, url)
    else:
        full_url = url

    parsed = urlparse(full_url)
    scheme = (parsed.scheme or "http").lower()
    if scheme not in ("http", "https"):
        return ""

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return ""

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = f"{hostname}:{port}" if port else hostname

    # Path normalization
    raw_path = parsed.path or "/"
    # Collapse multiple consecutive slashes
    raw_path = re.sub(r"/+", "/", raw_path)
    if not raw_path:
        raw_path = "/"
    elif raw_path != "/" and raw_path.endswith("/"):
        raw_path = raw_path.rstrip("/")

    # Query parameters normalization
    query_str = ""
    if parsed.query:
        try:
            params = parse_qsl(parsed.query, keep_blank_values=True)
            filtered_params = []
            for k, v in params:
                k_lower = k.lower()
                if ignore_utm_params and (
                    k_lower.startswith("utm_") or
                    k_lower in ("fbclid", "gclid", "mc_cid", "mc_eid", "_ga", "_gl", "msclkid")
                ):
                    continue
                filtered_params.append((k, v))
            if filtered_params:
                filtered_params.sort(key=lambda x: x[0])
                query_str = urlencode(filtered_params)
        except Exception:
            query_str = parsed.query

    return urlunparse((scheme, netloc, raw_path, "", query_str, ""))

from app.models.link_record import LinkRecord

def extract_link_semantic_location_and_context(a_tag: Any, soup: BeautifulSoup) -> Dict[str, Any]:
    """
    Extracts semantic DOM section, nearest heading (H1/H2/H3), paragraph index,
    sentence index, surrounding context, and exact HTML snippet for an anchor tag.
    """
    # 1. Semantic DOM section
    section = "other"
    curr = a_tag.parent
    while curr and getattr(curr, "name", None) != "[document]":
        name = getattr(curr, "name", "").lower() if getattr(curr, "name", None) else ""
        classes = " ".join(curr.get("class", [])).lower() if isinstance(curr.get("class"), list) else str(curr.get("class") or "").lower()
        elem_id = str(curr.get("id") or "").lower()
        role = str(curr.get("role") or "").lower()

        if name == "nav" or role == "navigation" or "nav" in classes or "menu" in classes or "nav" in elem_id:
            section = "navigation"
            break
        elif name == "header" or role == "banner" or "header" in classes or "head" in classes:
            section = "header"
            break
        elif name == "footer" or role == "contentinfo" or "footer" in classes:
            section = "footer"
            break
        elif name == "aside" or role == "complementary" or "sidebar" in classes or "aside" in classes:
            section = "sidebar"
            break
        elif name == "article" or role == "article":
            section = "article"
            break
        elif name == "main" or role == "main" or "content" in classes or "main" in classes:
            section = "main"
            break
        curr = curr.parent

    # 2. Nearest Heading (preceding H1, H2, H3, H4)
    nearest_heading = None
    heading_level = None
    prev_h = a_tag.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
    if prev_h:
        h_text = prev_h.get_text().strip()
        if h_text:
            nearest_heading = h_text
            try:
                heading_level = int(prev_h.name[1])
            except (ValueError, IndexError):
                heading_level = None

    # 3. Parent paragraph and surrounding context
    parent_p = a_tag.find_parent("p") or a_tag.find_parent(["li", "div", "section", "td"])
    p_text = parent_p.get_text(separator=" ").strip() if parent_p else ""
    anc_text = a_tag.get_text().strip()

    context_before = ""
    context_after = ""
    context_text = p_text
    paragraph_index = None
    sentence_index = None

    if parent_p:
        container = parent_p.parent or soup
        p_siblings = container.find_all("p") if container else []
        if parent_p in p_siblings:
            paragraph_index = p_siblings.index(parent_p) + 1

        if anc_text and anc_text in p_text:
            pos = p_text.find(anc_text)
            context_before = p_text[:pos].strip()[-100:]
            context_after = p_text[pos + len(anc_text):].strip()[:100]

            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', p_text) if s.strip()]
            for s_idx, sent in enumerate(sentences, 1):
                if anc_text in sent:
                    sentence_index = s_idx
                    context_text = sent
                    break

    html_snippet = str(a_tag)[:300]

    return {
        "source_section": section,
        "nearest_heading": nearest_heading,
        "heading_level": heading_level,
        "paragraph_index": paragraph_index,
        "sentence_index": sentence_index,
        "context_before": context_before,
        "context_text": context_text or anc_text,
        "context_after": context_after,
        "html_snippet": html_snippet
    }


class RobotsDirectiveEngine:

    """
    Robust robots.txt parser supporting User-agent matching, Allow/Disallow,
    wildcards (*), and end-of-path anchors ($).
    """
    def __init__(self, robots_txt: str = "", user_agent: str = ""):
        self.disallowed_patterns: List[str] = []
        self.allowed_patterns: List[str] = []
        self.sitemaps: List[str] = []
        self._parse(robots_txt, user_agent)

    def _parse(self, content: str, target_ua: str):
        if not content:
            return

        current_applies = False
        target_ua_lower = target_ua.lower()

        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" not in line:
                continue

            field, val = line.split(":", 1)
            field = field.strip().lower()
            val = val.strip()

            if field == "user-agent":
                ua_val = val.lower()
                if ua_val == "*" or ua_val in target_ua_lower or target_ua_lower in ua_val:
                    current_applies = True
                else:
                    current_applies = False
            elif current_applies:
                if field == "disallow":
                    if val:
                        self.disallowed_patterns.append(val)
                elif field == "allow":
                    if val:
                        self.allowed_patterns.append(val)
                elif field == "sitemap":
                    if val and val not in self.sitemaps:
                        self.sitemaps.append(val)

    def is_disallowed(self, path: str) -> bool:
        """
        Checks if a URL path is blocked by parsed robots directives.
        Allow directives take precedence over Disallow if they match more specifically.
        """
        if not path:
            path = "/"

        # Check explicit Allow rules first
        for allow_pat in self.allowed_patterns:
            if self._matches_pattern(path, allow_pat):
                return False

        for dis_pat in self.disallowed_patterns:
            if self._matches_pattern(path, dis_pat):
                return True

        return False

    @staticmethod
    def _matches_pattern(path: str, pattern: str) -> bool:
        if pattern == "/":
            return True
        regex_pat = "^" + re.escape(pattern).replace(r"\*", ".*")
        if regex_pat.endswith(r"\$"):
            regex_pat = regex_pat[:-2] + "$"
        try:
            return bool(re.search(regex_pat, path))
        except re.error:
            return path.startswith(pattern)


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
        allow_subdomains: bool = False,
        allow_local_dev: bool = False,
        js_rendering: str = "auto",
        progress_callback: Optional[Callable[[int, int, Optional[str]], None]] = None,
        cancellation_checker: Optional[Callable[[], bool]] = None
    ):
        if not start_url or not start_url.startswith(("http://", "https://")):
            raise ValueError("Crawler requires a valid HTTP or HTTPS start URL.")

        self.allow_local_dev = allow_local_dev
        is_safe, ssrf_err = validate_url_ssrf(start_url, allow_local_dev=self.allow_local_dev)
        if not is_safe:
            raise ValueError(f"Prohibited crawl start URL (SSRF Protection): {ssrf_err}")

        self.raw_start_url = start_url
        self.ignore_utm_params = ignore_utm_params
        self.start_url = canonicalize_url(start_url, ignore_utm_params=ignore_utm_params)
        
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
        self.max_depth = max(0, int(max_depth or 0))
        self.respect_robots_txt = respect_robots_txt
        self.crawl_delay_ms = crawl_delay_ms
        self.user_agent = user_agent
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.follow_redirects = follow_redirects
        self.target_countries = target_countries or []
        self.allow_subdomains = allow_subdomains
        self.js_rendering = (js_rendering or "auto").lower()
        self.progress_callback = progress_callback
        self.cancellation_checker = cancellation_checker
        self.is_cancelled = False
        self.verify_ssl = True

        parsed_url = urlparse(self.start_url)
        self.domain = (parsed_url.hostname or "").lower()
        self.port = parsed_url.port
        self.netloc = (parsed_url.netloc or "").lower()
        self.scheme = parsed_url.scheme
        self.start_path = parsed_url.path or "/"
        
        # Base subfolder calculation for subfolder_only scope
        if self.start_path and self.start_path != "/":
            self.subfolder_prefix = self.start_path.rstrip("/")
        else:
            self.subfolder_prefix = ""

        # Depth tracking: start URL is at depth 0
        self.url_depths: Dict[str, int] = {self.start_url: 0}
        
        # Queue state tracking: PENDING, CRAWLING, CRAWLED, FAILED, BLOCKED, SKIPPED, BOT_PROTECTION
        self.queue_status: Dict[str, str] = {self.start_url: "PENDING"}
        self.visited: Set[str] = set()
        self.to_visit: List[str] = [self.start_url]
        
        # Rejection registry for diagnostics
        self.rejection_log: List[Dict[str, str]] = []
        
        # Observability counters
        self.metrics = {
            "pages_discovered": 1,
            "pages_crawled": 0,
            "pages_failed": 0,
            "pages_blocked": 0,
            "pages_skipped": 0,
            "pages_out_of_scope": 0,
            "pages_blocked_by_robots": 0,
            "pages_blocked_by_ssrf": 0,
            "pages_blocked_by_bot_protection": 0,
            "pages_js_rendered": 0
        }
        
        self.robots_engine: Optional[RobotsDirectiveEngine] = None
        self.robots_blocked_seed = False
        self.bot_protection_blocked_seed = False
        
        # Results collections
        self.pages: List[Dict[str, Any]] = []
        self.issues: List[Dict[str, Any]] = []
        self.internal_links: List[Dict[str, Any]] = []
        self.external_links: List[Dict[str, Any]] = []
        self.link_records: List[Dict[str, Any]] = []
        self.broken_links: List[Dict[str, Any]] = []
        self.asset_checks: List[Dict[str, Any]] = []
        
        self.is_running = False
        self.seed_status_code = None

    def is_same_domain(self, url: str) -> bool:
        """
        Determines if a URL belongs to the internal crawl target domain.
        - Handles www vs non-www
        - Respects allow_subdomains setting
        - Supports local dev equivalence (localhost <-> 127.0.0.1 on identical port) when allow_local_dev is active
        """
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if not host:
            return False

        # Local development equivalence
        if self.allow_local_dev:
            target_is_local = self.domain in ("localhost", "127.0.0.1")
            url_is_local = host in ("localhost", "127.0.0.1")
            if target_is_local and url_is_local:
                return (parsed.port or 80) == (self.port or 80)

        clean_host = host.replace("www.", "")
        clean_target = self.domain.replace("www.", "")

        if clean_host == clean_target:
            return True

        if self.allow_subdomains:
            if clean_host.endswith("." + clean_target):
                return True

        return False

    def is_static_asset(self, url: str) -> bool:
        parsed = urlparse(url)
        path = parsed.path.lower()
        return path.endswith(STATIC_ASSET_EXTENSIONS)

    def is_disallowed(self, url: str) -> bool:
        if not self.respect_robots_txt or not self.robots_engine:
            return False
        parsed = urlparse(url)
        path = parsed.path or "/"
        return self.robots_engine.is_disallowed(path)

    def is_within_scope(self, url: str) -> Tuple[bool, str]:
        """
        Comprehensive crawl scope evaluation:
        1. Domain validation
        2. Static asset filtering
        3. Depth ceiling evaluation (depth > max_depth rejected for max_depth > 0)
        4. Subfolder path-segment matching
        5. Exclude / include regex patterns
        Returns (is_valid, rejection_reason).
        """
        if not self.is_same_domain(url):
            return False, "EXTERNAL_DOMAIN"

        if self.is_static_asset(url):
            return False, "STATIC_ASSET"

        # Correct depth semantics: max_depth = 1 allows depth 0 (seed) and depth 1 (direct links)
        if self.max_depth > 0:
            depth = self.url_depths.get(url, 999)
            if depth > self.max_depth:
                return False, "MAX_DEPTH_EXCEEDED"

        parsed = urlparse(url)
        path = parsed.path or "/"

        # Path-segment subfolder validation
        if self.scope_type == "subfolder_only" and self.subfolder_prefix:
            prefix = self.subfolder_prefix
            if path != prefix and not path.startswith(prefix + "/"):
                return False, "OUT_OF_SUBFOLDER_SCOPE"

        if self.exclude_patterns:
            for pattern in self.exclude_patterns:
                clean_pat = pattern.strip().lower()
                if clean_pat and (clean_pat in path or clean_pat in url):
                    return False, "EXCLUDE_PATTERN_MATCH"

        if self.include_patterns:
            matched = False
            for pattern in self.include_patterns:
                clean_pat = pattern.strip().lower()
                if clean_pat and (clean_pat in path or clean_pat in url):
                    matched = True
                    break
            if not matched:
                return False, "INCLUDE_PATTERN_MISMATCH"

        return True, "OK"

    async def fetch_robots_txt(self, client: httpx.AsyncClient):
        robots_url = f"{self.scheme}://{self.netloc}/robots.txt"
        print(f"[ROBOTS] Requesting {robots_url}", flush=True)
        try:
            resp = await client.get(robots_url, timeout=10.0, follow_redirects=True)
            if resp.status_code == 200:
                self.robots_engine = RobotsDirectiveEngine(resp.text, self.user_agent)
                print(f"[ROBOTS] Parsed robots.txt ({len(resp.text)} bytes)", flush=True)
                
                # Check if seed URL is disallowed
                if self.respect_robots_txt and self.robots_engine.is_disallowed(self.start_path):
                    print(f"[ROBOTS] Seed URL '{self.start_url}' is DISALLOWED by robots.txt", flush=True)
                    self.robots_blocked_seed = True
        except Exception as e:
            print(f"[ROBOTS] Optional robots.txt fetch error: {e}", flush=True)

    async def fetch_sitemap_xml(self, client: httpx.AsyncClient):
        candidates = []
        if self.robots_engine and self.robots_engine.sitemaps:
            candidates.extend(self.robots_engine.sitemaps)
        candidates.append(f"{self.scheme}://{self.netloc}/sitemap.xml")

        max_entries = 5000 if not self.is_unlimited_scope else 20000
        for sm_url in candidates[:5]:
            try:
                resp = await client.get(sm_url, timeout=10.0, follow_redirects=True)
                if resp.status_code == 200:
                    found_locs = re.findall(r"<loc>(.*?)</loc>", resp.text, re.I)
                    print(f"[SITEMAP] Discovered {len(found_locs)} URLs from {sm_url}", flush=True)
                    for loc in found_locs[:max_entries]:
                        norm = canonicalize_url(loc.strip(), sm_url, self.ignore_utm_params)
                        if norm and norm not in self.queue_status:
                            is_scope, reason = self.is_within_scope(norm)
                            if is_scope:
                                is_safe, _ = validate_url_ssrf(norm, allow_local_dev=self.allow_local_dev)
                                if is_safe and not self.is_disallowed(norm):
                                    self.queue_status[norm] = "PENDING"
                                    self.url_depths[norm] = 1
                                    self.to_visit.append(norm)
                                    self.metrics["pages_discovered"] += 1
            except Exception as e:
                print(f"[SITEMAP] Optional sitemap fetch error for {sm_url}: {e}", flush=True)

    def extract_spa_links_from_html(self, html: str, current_url: str) -> List[str]:
        """
        Inspects static HTML for Single Page Application routing payloads
        (Next.js __NEXT_DATA__, Nuxt __NUXT__, Remix/SvelteKit data, React Router links).
        """
        discovered: List[str] = []
        try:
            # 1. Next.js __NEXT_DATA__
            if "__NEXT_DATA__" in html:
                match = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(1).strip())
                        # Check buildManifest or page paths
                        props = data.get("props", {})
                        # Extract any strings formatted like URL paths
                        json_str = json.dumps(data)
                        paths = re.findall(r'\"(/[a-zA-Z0-9_\-\./]+)\"', json_str)
                        for p in paths:
                            if not p.endswith(STATIC_ASSET_EXTENSIONS) and not p.startswith("/_next"):
                                discovered.append(p)
                    except Exception:
                        pass

            # 2. Nuxt __NUXT__ or payload scripts
            if "__NUXT__" in html:
                paths = re.findall(r'routePath:\s*[\'"](/[\w\-/]+)[\'"]', html)
                discovered.extend(paths)

            # 3. Harvest root-relative links from client JS chunks
            routes = re.findall(r'href:\s*[\'"](/[\w\-/]+)[\'"]', html)
            discovered.extend(routes)

        except Exception:
            pass

        return discovered

    async def render_with_browser_fallback(self, url: str) -> Optional[Tuple[str, List[str]]]:
        """
        Optional headless browser rendering fallback for SPA / JavaScript-rendered websites.
        Attempts to use Playwright if available in the environment.
        Returns (rendered_html, extracted_links) or None if unavailable.
        """
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(user_agent=self.user_agent)
                await page.goto(url, timeout=int(self.request_timeout * 1000), wait_until="domcontentloaded")
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except Exception:
                    pass
                
                rendered_html = await page.content()
                hrefs = await page.eval_on_selector_all("a[href]", "elements => elements.map(el => el.getAttribute('href'))")
                await browser.close()
                self.metrics["pages_js_rendered"] += 1
                return rendered_html, [h for h in hrefs if h]
        except ImportError:
            # Playwright is not installed; static parsing & SPA route harvesting handles SPA data
            return None
        except Exception as e:
            print(f"[BROWSER RENDER] Headless fallback skipped for {url}: {e}", flush=True)
            return None

    def extract_page_data_from_html(self, url: str, html: str) -> Dict[str, Any]:
        """
        Parses HTML content and extracts comprehensive SEO page attributes,
        headings, structured data, image inventory, open graph, and twitter cards.
        """
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
        image_inventory = []
        for img in images:
            src = img.get("src") or img.get("data-src") or ""
            if src:
                img_url = canonicalize_url(src.strip(), url, self.ignore_utm_params)
                alt = img.get("alt", None)
                has_alt = alt is not None and len(str(alt).strip()) > 0
                image_inventory.append({
                    "image_url": img_url or src,
                    "source_page": url,
                    "alt_text": str(alt).strip() if alt else "",
                    "alt_missing": not has_alt,
                    "width": img.get("width"),
                    "height": img.get("height"),
                    "loading": img.get("loading")
                })
        images_missing_alt = sum(1 for img in image_inventory if img["alt_missing"]) if image_inventory else sum(1 for img in images if not img.get("alt"))

        open_graph = {}
        for meta_tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:", re.I)}):
            prop = meta_tag.get("property", "").lower()
            c_val = meta_tag.get("content", "").strip()
            if prop and c_val:
                open_graph[prop] = c_val

        twitter_cards = {}
        for meta_tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
            name = meta_tag.get("name", "").lower()
            c_val = meta_tag.get("content", "").strip()
            if name and c_val:
                twitter_cards[name] = c_val

        links = []
        link_records = []
        for idx, a_tag in enumerate(soup.find_all("a", href=True), 1):
            raw_href = a_tag["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            normalized = canonicalize_url(raw_href, url, self.ignore_utm_params)
            if not normalized:
                continue
            
            anc_txt = a_tag.get_text().strip()
            rel_val = a_tag.get("rel", "")
            if isinstance(rel_val, list):
                rel_val = " ".join(rel_val)
            elif not isinstance(rel_val, str):
                rel_val = str(rel_val or "")

            has_img = a_tag.find("img") is not None
            l_type = "image_link" if has_img else "hyperlink"
            if not anc_txt and has_img:
                img_child = a_tag.find("img")
                anc_txt = str(img_child.get("alt", "")).strip() if img_child else "[Image Link]"
                if not anc_txt:
                    anc_txt = "[Image Link]"
            elif not anc_txt:
                anc_txt = "[No Anchor Text]"

            loc_info = extract_link_semantic_location_and_context(a_tag, soup)
            loc_info["link_index_on_page"] = idx

            is_int = self.is_same_domain(normalized)
            rel_lower = (rel_val or "").lower()

            rec = {
                "id": str(uuid.uuid4()),
                "source_url": url,
                "target_url": normalized,
                "normalized_source_url": canonicalize_url(url),
                "normalized_target_url": normalized,
                "link_scope": "internal" if is_int else "external",
                "link_type": l_type,
                "anchor_text": anc_txt,
                "rel": rel_val or "follow",
                "is_internal": is_int,
                "is_external": not is_int,
                "is_nofollow": "nofollow" in rel_lower,
                "is_sponsored": "sponsored" in rel_lower,
                "is_ugc": "ugc" in rel_lower,
                "source_section": loc_info.get("source_section", "other"),
                "nearest_heading": loc_info.get("nearest_heading"),
                "heading_level": loc_info.get("heading_level"),
                "paragraph_index": loc_info.get("paragraph_index"),
                "sentence_index": loc_info.get("sentence_index"),
                "link_index_on_page": loc_info.get("link_index_on_page"),
                "context_before": loc_info.get("context_before", ""),
                "context_text": loc_info.get("context_text", ""),
                "context_after": loc_info.get("context_after", ""),
                "html_snippet": loc_info.get("html_snippet", ""),
                "discovered_at": datetime.utcnow().isoformat()
            }
            link_records.append(rec)
            links.append({
                "source": url,
                "target": normalized,
                "anchor_text": anc_txt,
                "rel": rel_val,
                "is_internal": is_int,
                "source_section": loc_info.get("source_section", "other"),
                "nearest_heading": loc_info.get("nearest_heading"),
                "heading_level": loc_info.get("heading_level"),
                "paragraph_index": loc_info.get("paragraph_index"),
                "sentence_index": loc_info.get("sentence_index"),
                "context_before": loc_info.get("context_before", ""),
                "context_text": loc_info.get("context_text", ""),
                "context_after": loc_info.get("context_after", ""),
                "html_snippet": loc_info.get("html_snippet", "")
            })

        return {
            "url": url,
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
            "h1_tags": h1_tags,
            "h2": h2_tags,
            "h2_count": len(h2_tags),
            "h3": h3_tags,
            "h3_count": len(h3_tags),
            "word_count": word_count,
            "images": [img.get("src") for img in images if img.get("src")],
            "image_inventory": image_inventory,
            "images_missing_alt": images_missing_alt,
            "open_graph": open_graph,
            "twitter_cards": twitter_cards,
            "og_title": open_graph.get("og:title"),
            "og_description": open_graph.get("og:description"),
            "twitter_card": twitter_cards.get("twitter:card"),
            "links": links,
            "link_records": link_records
        }

    def evaluate_page_issues(self, page_data: Dict[str, Any]):
        url = page_data["url"]
        status = page_data.get("status_code", 0)
        fetch_st = page_data.get("fetch_status") or "FAILED"
        
        source_links = [l for l in self.internal_links if l.get("target") == url]
        source_url = source_links[0]["source"] if source_links else page_data.get("source_url") or "Start URL"

        if fetch_st == "BOT_PROTECTION" or status in (403, 401) or "Access Denied" in (page_data.get("error") or ""):
            self.issues.append({
                "rule_id": "CRAWL_002",
                "category": "Crawlability",
                "severity": "Critical",
                "issue_type": "Access Denied / Bot Protection",
                "affected_url": url,
                "source_url": source_url,
                "details": f"URL '{url}' encountered bot protection or access control (HTTP {status}).",
                "recommendation": "Configure user-agent whitelisting, firewall rules, or disable anti-bot challenges for crawler IP."
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
        if url in self.visited or (not self.is_unlimited_scope and self.max_pages > 0 and len(self.visited) >= self.max_pages):
            return
            
        if self.is_disallowed(url):
            print(f"[ROBOTS] Skipping disallowed URL: {url}", flush=True)
            self.queue_status[url] = "SKIPPED"
            self.metrics["pages_blocked_by_robots"] += 1
            self.metrics["pages_skipped"] += 1
            return

        self.visited.add(url)
        self.queue_status[url] = "CRAWLING"
        self.metrics["pages_crawled"] += 1
        print(f"[CRAWL HTTP] GET {url}", flush=True)

        start_time = time.time()
        
        try:
            await asyncio.wait_for(
                self._fetch_and_process_page(client, url, start_time),
                timeout=self.request_timeout
            )
        except asyncio.TimeoutError:
            elapsed_ms = int((time.time() - start_time) * 1000)
            err_msg = f"Page crawl timed out after {self.request_timeout} seconds."
            print(f"[CRAWL TIMEOUT] {url} ({err_msg})", flush=True)
            self.queue_status[url] = "TIMEOUT"
            self.metrics["pages_failed"] += 1
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
            self.metrics["pages_failed"] += 1
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
                    self.progress_callback(len(self.visited), max(len(self.queue_status), len(self.visited)), f"Crawled {len(self.visited)} pages...")
                except Exception:
                    pass

    async def _fetch_and_process_page(self, client: httpx.AsyncClient, url: str, start_time: float):
        response = None
        elapsed_ms = 0
        fetch_error = None
        fetch_status = "FAILED"

        try:
            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Upgrade-Insecure-Requests": "1"
            }
            response = await client.get(url, headers=headers, timeout=self.request_timeout, follow_redirects=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
        except SSRFBlockedError as sbe:
            elapsed_ms = int((time.time() - start_time) * 1000)
            fetch_status = "BLOCKED"
            fetch_error = f"SSRF Protection: {str(sbe)}"
            self.metrics["pages_blocked_by_ssrf"] += 1
        except httpx.TimeoutException:
            elapsed_ms = int((time.time() - start_time) * 1000)
            fetch_status = "TIMEOUT"
            fetch_error = f"Request timed out after {self.request_timeout}s"
            self.metrics["pages_failed"] += 1
        except httpx.ConnectError as ce:
            elapsed_ms = int((time.time() - start_time) * 1000)
            err_str = str(ce)
            fetch_status = "DNS_ERROR" if ("dns" in err_str.lower() or "getaddrinfo" in err_str.lower()) else "CONNECTION_REFUSED"
            fetch_error = "DNS resolution failed" if fetch_status == "DNS_ERROR" else "Connection refused"
            self.metrics["pages_failed"] += 1
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            fetch_status = "NETWORK_ERROR"
            fetch_error = f"Network request error: {str(e)[:120]}"
            self.metrics["pages_failed"] += 1

        if not response:
            print(f"[CRAWL FAILED] {fetch_status} for {url} ({fetch_error})", flush=True)
            self.queue_status[url] = fetch_status
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
        
        # Detect Bot Protection / Cloudflare Challenges
        resp_text_preview = (response.text or "")[:4000].lower()
        is_bot_challenge = any(kw in resp_text_preview for kw in BOT_PROTECTION_KEYWORDS)
        
        if (response.status_code in (403, 503) and is_bot_challenge) or (response.status_code == 403):
            self.queue_status[url] = "BOT_PROTECTION"
            self.metrics["pages_blocked_by_bot_protection"] += 1
            self.metrics["pages_blocked"] += 1
            if url == self.start_url:
                self.bot_protection_blocked_seed = True
            page_record = {
                "url": url,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "error": f"HTTP {response.status_code} Bot Protection / Access Denied",
                "is_success": False,
                "fetch_status": "BOT_PROTECTION",
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
            self.metrics["pages_failed"] += 1
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
            image_inventory = []
            for img in images:
                src = img.get("src") or img.get("data-src") or ""
                if src:
                    img_url = canonicalize_url(src.strip(), url, self.ignore_utm_params)
                    alt = img.get("alt", None)
                    has_alt = alt is not None and len(str(alt).strip()) > 0
                    image_inventory.append({
                        "image_url": img_url or src,
                        "source_page": url,
                        "alt_text": str(alt).strip() if alt else "",
                        "alt_missing": not has_alt,
                        "width": img.get("width"),
                        "height": img.get("height"),
                        "loading": img.get("loading")
                    })
            images_missing_alt = sum(1 for img in image_inventory if img["alt_missing"]) if image_inventory else sum(1 for img in images if not img.get("alt"))

            # Social metadata: Open Graph & Twitter Cards
            open_graph = {}
            for meta_tag in soup.find_all("meta", attrs={"property": re.compile(r"^og:", re.I)}):
                prop = meta_tag.get("property", "").lower()
                c_val = meta_tag.get("content", "").strip()
                if prop and c_val:
                    open_graph[prop] = c_val

            twitter_cards = {}
            for meta_tag in soup.find_all("meta", attrs={"name": re.compile(r"^twitter:", re.I)}):
                name = meta_tag.get("name", "").lower()
                c_val = meta_tag.get("content", "").strip()
                if name and c_val:
                    twitter_cards[name] = c_val

            current_depth = self.url_depths.get(url, 0)
            discovered_internal = []
            raw_hrefs_to_process: List[Tuple[str, str, str, str, Dict[str, Any]]] = []  # (href, anchor_text, rel, link_type, loc_info)

            # 1. Harvest traditional anchor links from HTML with full semantic location & context
            for idx, a_tag in enumerate(soup.find_all("a", href=True), 1):
                raw_href = a_tag["href"].strip()
                if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    continue

                anc_txt = a_tag.get_text().strip()
                rel_val = a_tag.get("rel", "")
                if isinstance(rel_val, list):
                    rel_val = " ".join(rel_val)
                elif not isinstance(rel_val, str):
                    rel_val = str(rel_val or "")

                has_img = a_tag.find("img") is not None
                l_type = "image_link" if has_img else "hyperlink"
                if not anc_txt and has_img:
                    img_child = a_tag.find("img")
                    anc_txt = str(img_child.get("alt", "")).strip() if img_child else "[Image Link]"
                    if not anc_txt:
                        anc_txt = "[Image Link]"
                elif not anc_txt:
                    anc_txt = "[No Anchor Text]"

                loc_info = extract_link_semantic_location_and_context(a_tag, soup)
                loc_info["link_index_on_page"] = idx

                raw_hrefs_to_process.append((
                    raw_href,
                    anc_txt,
                    rel_val,
                    l_type,
                    loc_info
                ))

            # 2. Check SPA Route Discovery if static links are sparse
            spa_routes = self.extract_spa_links_from_html(html, url)
            for sr in spa_routes:
                raw_hrefs_to_process.append((
                    sr,
                    "[SPA Navigation Route]",
                    "",
                    "nav_link",
                    {
                        "source_section": "navigation",
                        "nearest_heading": None,
                        "heading_level": None,
                        "paragraph_index": None,
                        "sentence_index": None,
                        "context_before": "",
                        "context_text": "[SPA Route]",
                        "context_after": "",
                        "html_snippet": f'<a href="{sr}">SPA Route</a>',
                        "link_index_on_page": None
                    }
                ))

            # 3. Optional Headless Browser Rendering Fallback for SPA shells with 0 static links
            if len(raw_hrefs_to_process) == 0 and (self.js_rendering in ("auto", "enabled")):
                browser_result = await self.render_with_browser_fallback(url)
                if browser_result:
                    rendered_html, rendered_hrefs = browser_result
                    for rh in rendered_hrefs:
                        raw_hrefs_to_process.append((
                            rh,
                            "[JS Rendered Link]",
                            "",
                            "nav_link",
                            {
                                "source_section": "navigation",
                                "nearest_heading": None,
                                "heading_level": None,
                                "paragraph_index": None,
                                "sentence_index": None,
                                "context_before": "",
                                "context_text": "[JS Rendered Link]",
                                "context_after": "",
                                "html_snippet": f'<a href="{rh}">JS Rendered Link</a>',
                                "link_index_on_page": None
                            }
                        ))

            # Process all discovered candidate links and build canonical LinkRecords
            for raw_href, anchor_txt, rel_val, l_type, loc_info in raw_hrefs_to_process:
                normalized = canonicalize_url(raw_href, url, self.ignore_utm_params)
                if not normalized:
                    continue

                is_internal_link = self.is_same_domain(normalized)
                rel_lower = (rel_val or "").lower()

                link_rec = {
                    "id": str(uuid.uuid4()),
                    "source_url": url,
                    "target_url": normalized,
                    "normalized_source_url": canonicalize_url(url),
                    "normalized_target_url": normalized,
                    "link_scope": "internal" if is_internal_link else "external",
                    "link_type": l_type,
                    "anchor_text": anchor_txt,
                    "rel": rel_val or "follow",
                    "is_internal": is_internal_link,
                    "is_external": not is_internal_link,
                    "is_nofollow": "nofollow" in rel_lower,
                    "is_sponsored": "sponsored" in rel_lower,
                    "is_ugc": "ugc" in rel_lower,
                    "source_section": loc_info.get("source_section", "other"),
                    "nearest_heading": loc_info.get("nearest_heading"),
                    "heading_level": loc_info.get("heading_level"),
                    "paragraph_index": loc_info.get("paragraph_index"),
                    "sentence_index": loc_info.get("sentence_index"),
                    "link_index_on_page": loc_info.get("link_index_on_page"),
                    "context_before": loc_info.get("context_before", ""),
                    "context_text": loc_info.get("context_text", ""),
                    "context_after": loc_info.get("context_after", ""),
                    "html_snippet": loc_info.get("html_snippet", ""),
                    "discovered_at": datetime.utcnow().isoformat()
                }
                self.link_records.append(link_rec)

                if is_internal_link:
                    discovered_internal.append(normalized)
                    self.internal_links.append({
                        "source": url,
                        "target": normalized,
                        "anchor_text": anchor_txt,
                        "rel": rel_val,
                        "source_section": loc_info.get("source_section", "other"),
                        "nearest_heading": loc_info.get("nearest_heading"),
                        "heading_level": loc_info.get("heading_level"),
                        "paragraph_index": loc_info.get("paragraph_index"),
                        "sentence_index": loc_info.get("sentence_index"),
                        "context_before": loc_info.get("context_before", ""),
                        "context_text": loc_info.get("context_text", ""),
                        "context_after": loc_info.get("context_after", ""),
                        "html_snippet": loc_info.get("html_snippet", "")
                    })
                    
                    if normalized not in self.queue_status:
                        # Queue assignment depth: child links are depth + 1
                        assigned_depth = current_depth + 1
                        self.url_depths[normalized] = assigned_depth
                        
                        is_scope, reason = self.is_within_scope(normalized)
                        if is_scope:
                            is_safe, ssrf_reason = validate_url_ssrf(normalized, allow_local_dev=self.allow_local_dev)
                            if is_safe:
                                if not self.is_disallowed(normalized):
                                    self.queue_status[normalized] = "PENDING"
                                    self.to_visit.append(normalized)
                                    self.metrics["pages_discovered"] += 1
                                else:
                                    self.queue_status[normalized] = "SKIPPED"
                                    self.metrics["pages_blocked_by_robots"] += 1
                                    self.metrics["pages_skipped"] += 1
                                    self.rejection_log.append({"url": normalized, "reason": "ROBOTS_DISALLOWED"})
                            else:
                                self.queue_status[normalized] = "BLOCKED"
                                self.metrics["pages_blocked_by_ssrf"] += 1
                                self.rejection_log.append({"url": normalized, "reason": f"SSRF_BLOCKED: {ssrf_reason}"})
                        else:
                            self.queue_status[normalized] = "SKIPPED"
                            self.metrics["pages_out_of_scope"] += 1
                            self.rejection_log.append({"url": normalized, "reason": reason})
                else:
                    self.external_links.append({
                        "source": url,
                        "target": normalized,
                        "anchor_text": anchor_txt,
                        "rel": rel_val,
                        "source_section": loc_info.get("source_section", "other"),
                        "nearest_heading": loc_info.get("nearest_heading"),
                        "heading_level": loc_info.get("heading_level"),
                        "paragraph_index": loc_info.get("paragraph_index"),
                        "sentence_index": loc_info.get("sentence_index"),
                        "context_before": loc_info.get("context_before", ""),
                        "context_text": loc_info.get("context_text", ""),
                        "context_after": loc_info.get("context_after", ""),
                        "html_snippet": loc_info.get("html_snippet", "")
                    })
                    self.rejection_log.append({"url": normalized, "reason": "EXTERNAL_DOMAIN"})

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
                "open_graph": open_graph,
                "twitter_cards": twitter_cards,
                "h1": h1,
                "h1_count": len(h1_tags),
                "h2_count": len(h2_tags),
                "h3_count": len(h3_tags),
                "word_count": word_count,
                "images_count": len(image_inventory) if image_inventory else len(images),
                "images_missing_alt": images_missing_alt,
                "image_inventory": image_inventory,
                "internal_links_count": len(discovered_internal)
            }
            
            self.pages.append(page_record)
            self.evaluate_page_issues(page_record)
        except Exception as parse_err:
            print(f"[PARSE ERROR] Failed to parse HTML for {url}: {parse_err}", flush=True)
            self.metrics["pages_failed"] += 1
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
        print(f"[CRAWL] Starting real Internet crawl for {self.start_url} (Max Depth: {self.max_depth}, Scope: {self.scope_type}, Max Pages: {'5000+' if self.is_unlimited_scope else self.max_pages})", flush=True)
        
        async with create_ssrf_safe_client(
            verify=self.verify_ssl,
            timeout=self.request_timeout,
            allow_local_dev=self.allow_local_dev
        ) as client:
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
                await asyncio.sleep(0.1)

        self.is_running = False

        # Run Broken-Link Checking on all discovered internal and external links
        if not self.is_cancelled:
            print(f"[CRAWL] Checking broken links for {len(self.internal_links)} internal and {len(self.external_links)} external link references...", flush=True)
            link_checker = BrokenLinkChecker(
                concurrency=20,
                request_timeout=10.0,
                user_agent=self.user_agent
            )
            
            def _link_progress(current: int, total: int, msg: str = ""):
                if self.progress_callback:
                    try:
                        self.progress_callback(len(self.visited), max(len(self.queue_status), len(self.visited)), msg)
                    except Exception:
                        pass

            try:
                self.broken_links = await link_checker.check_all_links(
                    internal_links=self.internal_links,
                    external_links=self.external_links,
                    crawled_pages=self.pages,
                    progress_callback=_link_progress,
                    cancellation_checker=self.cancellation_checker
                )
                print(f"[CRAWL] Broken-link verification complete: Found {len(self.broken_links)} broken links.", flush=True)
            except Exception as link_err:
                print(f"[CRAWL] Optional broken-link check error: {link_err}", flush=True)
                self.broken_links = []

        successful_pages = [p for p in self.pages if p.get("is_success") and p.get("status_code") == 200]
        failed_pages = [p for p in self.pages if not p.get("is_success") or (p.get("status_code") or 0) >= 400]
        
        is_access_denied = (self.seed_status_code in (403, 401))
        
        if self.is_cancelled:
            overall_status = "cancelled"
            status_message = "Crawl was cancelled by user."
        elif self.robots_blocked_seed:
            overall_status = "blocked_by_robots"
            status_message = "Crawl blocked by robots.txt (Disallow directive)."
        elif self.bot_protection_blocked_seed or (is_access_denied and len(successful_pages) == 0):
            overall_status = "blocked_by_protection"
            status_message = "Crawl could not continue because the website returned a bot-protection challenge (Cloudflare/CAPTCHA)."
        elif len(successful_pages) > 0 and len(failed_pages) > 0:
            overall_status = "completed_with_errors"
            status_message = f"Crawl completed with {len(successful_pages)} pages crawled and {len(failed_pages)} errors."
        elif len(successful_pages) > 0 and len(failed_pages) == 0:
            overall_status = "completed"
            status_message = f"Crawl successfully completed ({len(successful_pages)} pages crawled)."
        elif len(self.pages) > 0:
            overall_status = "completed_with_errors"
            status_message = "Crawl completed with issues."
        else:
            overall_status = "failed"
            status_message = "Crawl failed to reach destination server."

        print(f"[CRAWL FINISHED] Status: '{overall_status}'. Total Pages Saved: {len(self.pages)}, Successful: {len(successful_pages)}, Failed/Blocked: {len(failed_pages)}, Broken Links: {len(self.broken_links)}, Issues: {len(self.issues)}", flush=True)
        
        return {
            "status": overall_status,
            "status_message": status_message,
            "max_pages": "5000+" if self.is_unlimited_scope else self.max_pages,
            "seed_status_code": self.seed_status_code,
            "successful_pages_count": len(successful_pages),
            "failed_pages_count": len(failed_pages),
            "pages": self.pages,
            "issues": self.issues,
            "internal_links": self.internal_links,
            "external_links": self.external_links,
            "link_records": self.link_records,
            "broken_links": self.broken_links,
            "asset_checks": self.asset_checks,
            "metrics": self.metrics,
            "rejections_sample": self.rejection_log[:100]
        }
