import os
import sys
import unittest
import asyncio

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.crawler.crawler import (
    SEOCrawler,
    canonicalize_url,
    RobotsDirectiveEngine,
    STATIC_ASSET_EXTENSIONS
)

class TestCrawlerPipelineFixes(unittest.TestCase):
    def test_01_canonicalize_url(self):
        # 1. Strips fragments
        self.assertEqual(
            canonicalize_url("https://example.com/about#team"),
            "https://example.com/about"
        )
        # 2. Removes default ports
        self.assertEqual(
            canonicalize_url("http://example.com:80/services"),
            "http://example.com/services"
        )
        self.assertEqual(
            canonicalize_url("https://example.com:443/services"),
            "https://example.com/services"
        )
        # 3. Strips tracking params & sorts remaining params
        self.assertEqual(
            canonicalize_url("https://example.com/shop?utm_source=google&b=2&a=1&gclid=123"),
            "https://example.com/shop?a=1&b=2"
        )
        # 4. Resolves relative URLs
        self.assertEqual(
            canonicalize_url("/about/contact/", base_url="https://example.com/services/"),
            "https://example.com/about/contact"
        )
        # 5. Normalizes multi-slashes
        self.assertEqual(
            canonicalize_url("https://example.com//products///item-1/"),
            "https://example.com/products/item-1"
        )

    def test_02_domain_and_subdomain_detection(self):
        crawler_strict = SEOCrawler(start_url="https://example.com/", allow_subdomains=False)
        self.assertTrue(crawler_strict.is_same_domain("https://example.com/about"))
        self.assertTrue(crawler_strict.is_same_domain("https://www.example.com/about"))
        self.assertFalse(crawler_strict.is_same_domain("https://blog.example.com/post"))
        self.assertFalse(crawler_strict.is_same_domain("https://google.com"))

        crawler_subs = SEOCrawler(start_url="https://example.com/", allow_subdomains=True)
        self.assertTrue(crawler_subs.is_same_domain("https://example.com/about"))
        self.assertTrue(crawler_subs.is_same_domain("https://blog.example.com/post"))
        self.assertTrue(crawler_subs.is_same_domain("https://app.example.com/dashboard"))
        self.assertFalse(crawler_subs.is_same_domain("https://otherdomain.com"))

    def test_03_local_development_host_normalization(self):
        crawler_dev = SEOCrawler(
            start_url="http://localhost:8030/",
            allow_local_dev=True
        )
        self.assertTrue(crawler_dev.is_same_domain("http://127.0.0.1:8030/about"))
        self.assertTrue(crawler_dev.is_same_domain("http://localhost:8030/contact"))
        self.assertFalse(crawler_dev.is_same_domain("http://127.0.0.1:9000/contact"))  # different port

    def test_04_robots_directive_engine(self):
        robots_txt = """
User-agent: *
Disallow: /admin/
Disallow: /private/*
Allow: /private/public-doc
Disallow: /api/*.json$

User-agent: Googlebot
Disallow: /google-blocked/
"""
        engine = RobotsDirectiveEngine(robots_txt, "SEO-Intelligence-Bot/1.0")
        
        self.assertTrue(engine.is_disallowed("/admin/users"))
        self.assertTrue(engine.is_disallowed("/private/secret-data"))
        self.assertFalse(engine.is_disallowed("/private/public-doc"))  # explicit Allow rule overrides
        self.assertTrue(engine.is_disallowed("/api/data.json"))
        self.assertFalse(engine.is_disallowed("/api/data.xml"))
        self.assertFalse(engine.is_disallowed("/about"))
        self.assertFalse(engine.is_disallowed("/google-blocked/"))  # user-agent specific to Googlebot

    def test_05_spa_route_extraction(self):
        crawler = SEOCrawler(start_url="https://example.com/")
        
        # Next.js hydration payload
        nextjs_html = """
        <html>
        <head><title>SPA App</title></head>
        <body>
            <div id="__next"></div>
            <script id="__NEXT_DATA__" type="application/json">
            {"props":{"pageProps":{}},"page":"/","query":{},"buildId":"xyz","runtimeConfig":{},"routes":["/features","/pricing","/company/about"]}
            </script>
        </body>
        </html>
        """
        extracted = crawler.extract_spa_links_from_html(nextjs_html, "https://example.com/")
        self.assertIn("/features", extracted)
        self.assertIn("/pricing", extracted)
        self.assertIn("/company/about", extracted)

    def test_06_subfolder_scope_root_vs_path(self):
        # Root path "/" does not restrict sub-paths
        crawler_root = SEOCrawler(start_url="https://example.com/", scope_type="subfolder_only")
        crawler_root.url_depths["https://example.com/about"] = 1
        is_scope, _ = crawler_root.is_within_scope("https://example.com/about")
        self.assertTrue(is_scope)

        # Explicit subfolder "/blog/" restricts to /blog/*
        crawler_blog = SEOCrawler(start_url="https://example.com/blog/", scope_type="subfolder_only")
        crawler_blog.url_depths["https://example.com/blog/article-1"] = 1
        is_scope, _ = crawler_blog.is_within_scope("https://example.com/blog/article-1")
        self.assertTrue(is_scope)

        crawler_blog.url_depths["https://example.com/blog-posts"] = 1
        is_scope, reason = crawler_blog.is_within_scope("https://example.com/blog-posts")
        self.assertFalse(is_scope)
        self.assertEqual(reason, "OUT_OF_SUBFOLDER_SCOPE")

    def test_07_page_ceiling_unlimited_mode(self):
        crawler_unlimited = SEOCrawler(start_url="https://example.com/", max_pages="5000+")
        self.assertTrue(crawler_unlimited.is_unlimited_scope)
        self.assertEqual(crawler_unlimited.max_pages, 0)

        crawler_exact = SEOCrawler(start_url="https://example.com/", max_pages=500)
        self.assertFalse(crawler_exact.is_unlimited_scope)
        self.assertEqual(crawler_exact.max_pages, 500)

if __name__ == '__main__':
    unittest.main()
