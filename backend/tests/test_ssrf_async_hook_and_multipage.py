import os
import sys
import unittest
import asyncio

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
from unittest.mock import patch
from app.crawler.crawler import SEOCrawler
from app.crawler.ssrf_protection import (
    validate_url_ssrf,
    create_ssrf_safe_client,
    SSRFBlockedError,
    create_ssrf_request_hook,
    create_ssrf_response_hook
)

class TestSSRFAsyncHookAndMultiPage(unittest.IsolatedAsyncioTestCase):

    async def test_01_ssrf_async_hooks_are_coroutines(self):
        """
        Verifies that create_ssrf_request_hook and create_ssrf_response_hook
        return async coroutine functions that can be awaited by httpx.AsyncClient.
        """
        req_hook = create_ssrf_request_hook(allow_local_dev=True)
        resp_hook = create_ssrf_response_hook(allow_local_dev=True)

        self.assertTrue(asyncio.iscoroutinefunction(req_hook))
        self.assertTrue(asyncio.iscoroutinefunction(resp_hook))

        # Awaiting valid request hook does not raise TypeError
        request = httpx.Request("GET", "http://localhost:8030/about")
        await req_hook(request)

        # Awaiting response hook does not raise TypeError
        response = httpx.Response(200, request=request)
        await resp_hook(response)

    async def test_02_ssrf_protection_blocks_unsafe_destinations(self):
        """
        Verifies SSRF protection continues to strictly block private IPs, metadata endpoints, and loopback in normal mode.
        """
        # Blocked in normal mode (allow_local_dev=False)
        is_safe, reason = validate_url_ssrf("http://127.0.0.1:8000/admin", allow_local_dev=False)
        self.assertFalse(is_safe)

        is_safe, reason = validate_url_ssrf("http://localhost:8030/dashboard", allow_local_dev=False)
        self.assertFalse(is_safe)

        is_safe, reason = validate_url_ssrf("http://169.254.169.254/latest/meta-data/", allow_local_dev=False)
        self.assertFalse(is_safe)

        is_safe, reason = validate_url_ssrf("http://10.0.0.1/internal", allow_local_dev=False)
        self.assertFalse(is_safe)

        is_safe, reason = validate_url_ssrf("http://192.168.1.1/router", allow_local_dev=False)
        self.assertFalse(is_safe)

        # Request hook raises SSRFBlockedError on blocked URL
        req_hook = create_ssrf_request_hook(allow_local_dev=False)
        with self.assertRaises(SSRFBlockedError):
            await req_hook(httpx.Request("GET", "http://169.254.169.254/secret"))

    async def test_03_multipage_crawl_pipeline_success(self):
        """
        Simulates a real multi-page website with 6 pages:
        / -> links to /about, /services, /contact, /pricing, /blog
        Verifies all 6 pages are discovered and crawled without transport-level hook failures.
        """
        site_pages = {
            "https://mysite.com/": """
                <html><head><title>Home</title></head><body>
                    <h1>Welcome</h1>
                    <a href="/about">About Us</a>
                    <a href="/services">Our Services</a>
                    <a href="/contact">Contact</a>
                    <a href="/pricing">Pricing Plans</a>
                    <a href="/blog">Blog</a>
                </body></html>
            """,
            "https://mysite.com/about": """
                <html><head><title>About</title></head><body><h1>About Us</h1><a href="/">Home</a></body></html>
            """,
            "https://mysite.com/services": """
                <html><head><title>Services</title></head><body><h1>Services</h1><a href="/">Home</a></body></html>
            """,
            "https://mysite.com/contact": """
                <html><head><title>Contact</title></head><body><h1>Contact Us</h1><a href="/">Home</a></body></html>
            """,
            "https://mysite.com/pricing": """
                <html><head><title>Pricing</title></head><body><h1>Pricing</h1><a href="/">Home</a></body></html>
            """,
            "https://mysite.com/blog": """
                <html><head><title>Blog</title></head><body><h1>Latest News</h1><a href="/">Home</a></body></html>
            """,
            "https://mysite.com/robots.txt": "User-agent: *\nAllow: /\n"
        }

        def mock_handler(request: httpx.Request) -> httpx.Response:
            url_str = str(request.url).rstrip("/") if str(request.url).endswith("/") and str(request.url) != "https://mysite.com/" else str(request.url)
            # Match against site_pages
            for target_url, content in site_pages.items():
                norm_target = target_url.rstrip("/") if target_url.endswith("/") and target_url != "https://mysite.com/" else target_url
                if url_str == norm_target:
                    content_type = "text/plain" if "robots.txt" in url_str else "text/html"
                    return httpx.Response(200, content=content.encode("utf-8"), headers={"content-type": content_type}, request=request)
            return httpx.Response(404, content=b"Not Found", request=request)

        mock_transport = httpx.MockTransport(mock_handler)

        def mock_create_safe_client(**kwargs):
            return httpx.AsyncClient(
                transport=mock_transport,
                event_hooks={
                    "request": [create_ssrf_request_hook(allow_local_dev=True)],
                    "response": [create_ssrf_response_hook(allow_local_dev=True)]
                }
            )

        with patch("app.crawler.crawler.create_ssrf_safe_client", side_effect=mock_create_safe_client):
            crawler = SEOCrawler(
                start_url="https://mysite.com/",
                max_pages=5000,
                max_depth=3,
                allow_local_dev=True
            )
            results = await crawler.start()

            # Verify crawl statistics
            self.assertEqual(results["status"], "completed")
            self.assertEqual(results["successful_pages_count"], 6)
            self.assertEqual(results["failed_pages_count"], 0)
            self.assertEqual(len(results["pages"]), 6)
            self.assertGreaterEqual(len(results["internal_links"]), 5)

            # Verify all expected URLs were crawled
            crawled_urls = {p["url"] for p in results["pages"]}
            expected_urls = {
                "https://mysite.com/",
                "https://mysite.com/about",
                "https://mysite.com/services",
                "https://mysite.com/contact",
                "https://mysite.com/pricing",
                "https://mysite.com/blog"
            }
            self.assertEqual(crawled_urls, expected_urls)

if __name__ == '__main__':
    unittest.main()
