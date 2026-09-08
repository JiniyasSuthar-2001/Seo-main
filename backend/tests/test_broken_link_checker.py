import unittest
import asyncio
import uuid
import os
import sys
import json
import httpx
from unittest.mock import patch, MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.config.settings import settings
from app.crawler.broken_link_checker import (
    BrokenLinkChecker,
    check_links_status,
    check_single_link,
    normalize_link_url,
    is_private_ip
)
from app.crawler.crawler import SEOCrawler
from app.services.crawl_storage import CrawlStorage


class TestBrokenLinkChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_email = f"bl_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="Broken Link Tester")
        cls.db.add(cls.user)
        cls.db.commit()

        cls.token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

        cls.project = Project(
            id=str(uuid.uuid4()),
            name="Broken Link Project",
            url="https://example-broken.com",
            domain="example-broken.com"
        )
        cls.db.add(cls.project)
        cls.db.commit()

        cls.membership = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user.id,
            project_id=cls.project.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_url_normalization_and_ssrf_detection(self):
        """Test URL normalization handles fragments and casing, and SSRF blocks private IPs."""
        self.assertEqual(
            normalize_link_url("https://Example.COM/Page-1#Section-A"),
            "https://example.com/Page-1"
        )
        self.assertEqual(
            normalize_link_url("https://example.com/test/?utm_source=seo"),
            "https://example.com/test?utm_source=seo"
        )
        self.assertEqual(
            normalize_link_url("https://example.com/"),
            "https://example.com/"
        )

        # SSRF checks
        self.assertTrue(is_private_ip("127.0.0.1"))
        self.assertTrue(is_private_ip("localhost"))
        self.assertTrue(is_private_ip("169.254.169.254"))
        self.assertTrue(is_private_ip("10.0.0.1"))
        self.assertTrue(is_private_ip("192.168.1.1"))
        self.assertTrue(is_private_ip("172.16.0.1"))
        self.assertTrue(is_private_ip("::1"))
        self.assertFalse(is_private_ip("8.8.8.8"))

    def test_02_internal_links_reuse_crawled_status_without_network_request(self):
        """Internal URLs that were already crawled must reuse their existing status without new network requests."""
        checker = BrokenLinkChecker()

        crawled_pages = [
            {
                "url": "https://example.com/",
                "status_code": 200,
                "is_success": True,
                "fetch_status": "CRAWLED"
            },
            {
                "url": "https://example.com/about",
                "status_code": 200,
                "is_success": True,
                "fetch_status": "CRAWLED"
            },
            {
                "url": "https://example.com/missing-internal",
                "status_code": 404,
                "is_success": False,
                "fetch_status": "FAILED",
                "error": "HTTP 404 Not Found"
            },
            {
                "url": "https://example.com/server-error",
                "status_code": 500,
                "is_success": False,
                "fetch_status": "FAILED",
                "error": "HTTP 500 Internal Server Error"
            }
        ]

        internal_links = [
            {"source": "https://example.com/", "target": "https://example.com/about", "anchor_text": "About Us"},
            {"source": "https://example.com/", "target": "https://example.com/missing-internal", "anchor_text": "Missing Page"},
            {"source": "https://example.com/about", "target": "https://example.com/server-error", "anchor_text": "Broken Feature"}
        ]

        # check_all_links should run with 0 external links
        broken = asyncio.run(checker.check_all_links(
            internal_links=internal_links,
            external_links=[],
            crawled_pages=crawled_pages
        ))

        # Only 2 broken links should be found: /missing-internal and /server-error
        self.assertEqual(len(broken), 2)
        
        targets = [b["target"] for b in broken]
        self.assertIn("https://example.com/missing-internal", targets)
        self.assertIn("https://example.com/server-error", targets)
        self.assertNotIn("https://example.com/about", targets)

        for b in broken:
            self.assertEqual(b["link_type"], "internal")
            self.assertTrue(b["is_broken"])
            self.assertIsNotNone(b["error"])

    def test_03_external_links_deduplication_and_relationship_preservation(self):
        """
        Duplicate external URLs referenced across multiple pages must be requested ONCE,
        but each source relationship must appear in broken_links.
        """
        checker = BrokenLinkChecker()

        external_links = [
            {"source": "https://example.com/page-1", "target": "https://dead-external.com/api", "anchor_text": "Resource 1"},
            {"source": "https://example.com/page-2", "target": "https://dead-external.com/api", "anchor_text": "Resource 2"},
            {"source": "https://example.com/page-3", "target": "https://dead-external.com/api", "anchor_text": "Resource 3"},
            {"source": "https://example.com/page-1", "target": "https://healthy-external.com/docs", "anchor_text": "Docs"}
        ]

        request_counts = {}

        async def mock_check_single(client, url, timeout=10.0, headers=None):
            request_counts[url] = request_counts.get(url, 0) + 1
            if "dead-external" in url:
                return {"url": url, "status_code": 404, "is_broken": True, "error": "HTTP 404 Not Found", "final_url": url}
            else:
                return {"url": url, "status_code": 200, "is_broken": False, "error": None, "final_url": url}

        with patch("app.crawler.broken_link_checker.check_single_link", side_effect=mock_check_single):
            broken = asyncio.run(checker.check_all_links(
                internal_links=[],
                external_links=external_links,
                crawled_pages=[]
            ))

        # The dead external URL should only have been requested ONCE
        self.assertEqual(request_counts.get("https://dead-external.com/api"), 1)
        self.assertEqual(request_counts.get("https://healthy-external.com/docs"), 1)

        # But all 3 source relationships must appear in the final broken links list
        self.assertEqual(len(broken), 3)
        sources = [b["source"] for b in broken]
        self.assertIn("https://example.com/page-1", sources)
        self.assertIn("https://example.com/page-2", sources)
        self.assertIn("https://example.com/page-3", sources)

        for b in broken:
            self.assertEqual(b["target"], "https://dead-external.com/api")
            self.assertEqual(b["link_type"], "external")
            self.assertEqual(b["status_code"], 404)
            self.assertTrue(b["is_broken"])

    def test_04_no_300_url_cap_checks_over_350_external_urls(self):
        """
        CRITICAL TEST: Over 350 unique external URLs must ALL be checked without any 300 cap.
        """
        checker = BrokenLinkChecker(concurrency=20)

        # Generate 450 unique external URLs
        total_test_urls = 450
        external_links = []
        for i in range(1, total_test_urls + 1):
            external_links.append({
                "source": f"https://example.com/page-{i % 10}",
                "target": f"https://external-site-{i}.com/resource",
                "anchor_text": f"External Link {i}"
            })

        checked_urls = set()

        async def mock_check_single(client, url, timeout=10.0, headers=None):
            checked_urls.add(url)
            # Mark every 10th URL as broken 404
            is_dead = ("-10." in url or "-50." in url or "-100." in url or "-350." in url or "-400." in url)
            if is_dead:
                return {"url": url, "status_code": 404, "is_broken": True, "error": "HTTP 404 Not Found", "final_url": url}
            return {"url": url, "status_code": 200, "is_broken": False, "error": None, "final_url": url}

        progress_calls = []
        def on_progress(current, total, msg):
            progress_calls.append((current, total, msg))

        with patch("app.crawler.broken_link_checker.check_single_link", side_effect=mock_check_single):
            broken = asyncio.run(checker.check_all_links(
                internal_links=[],
                external_links=external_links,
                crawled_pages=[],
                progress_callback=on_progress
            ))

        # Confirm ALL 450 unique external URLs were checked (> 300 limit verified!)
        self.assertEqual(len(checked_urls), total_test_urls)
        self.assertGreater(len(checked_urls), 300)
        self.assertGreater(len(broken), 0)
        self.assertGreater(len(progress_calls), 0)

    def test_05_error_handling_timeout_dns_500_redirects(self):
        """Test status code and network exception handling across various scenarios."""
        async def run_scenario_tests():
            async with httpx.AsyncClient() as client:
                # 1. Timeout
                with patch.object(client, "head", side_effect=httpx.TimeoutException("Read timed out")):
                    res = await check_single_link(client, "https://timeout-domain.com/slow")
                    self.assertTrue(res["is_broken"])
                    self.assertEqual(res["status_code"], 0)
                    self.assertIn("Timed Out", res["error"])

                # 2. DNS failure
                with patch.object(client, "head", side_effect=httpx.ConnectError("getaddrinfo failed [Errno 11001]")):
                    res = await check_single_link(client, "https://nonexistent-dns-domain.xyz")
                    self.assertTrue(res["is_broken"])
                    self.assertEqual(res["status_code"], 0)
                    self.assertIn("DNS", res["error"])

                # 3. HTTP 500 Internal Server Error
                mock_500 = MagicMock(status_code=500, url=httpx.URL("https://server-error.com"), reason_phrase="Internal Server Error")
                with patch.object(client, "head", return_value=mock_500):
                    res = await check_single_link(client, "https://server-error.com")
                    self.assertTrue(res["is_broken"])
                    self.assertEqual(res["status_code"], 500)

                # 4. Valid redirect resolving to 200 OK (Healthy)
                mock_200 = MagicMock(status_code=200, url=httpx.URL("https://destination.com/final"), reason_phrase="OK")
                with patch.object(client, "head", return_value=mock_200):
                    res = await check_single_link(client, "https://source.com/redirect")
                    self.assertFalse(res["is_broken"])
                    self.assertEqual(res["status_code"], 200)

                # 5. Redirect resolving to 404 (Broken)
                mock_404 = MagicMock(status_code=404, url=httpx.URL("https://destination.com/missing"), reason_phrase="Not Found")
                with patch.object(client, "head", return_value=mock_404):
                    res = await check_single_link(client, "https://source.com/broken-redirect")
                    self.assertTrue(res["is_broken"])
                    self.assertEqual(res["status_code"], 404)

        asyncio.run(run_scenario_tests())

    def test_06_zero_broken_links_produces_empty_list(self):
        """When all links are healthy, broken_links list is [] without error."""
        checker = BrokenLinkChecker()
        crawled_pages = [
            {"url": "https://example.com/", "status_code": 200, "is_success": True, "fetch_status": "CRAWLED"},
            {"url": "https://example.com/about", "status_code": 200, "is_success": True, "fetch_status": "CRAWLED"}
        ]
        internal_links = [{"source": "https://example.com/", "target": "https://example.com/about", "anchor_text": "About"}]

        async def mock_healthy(client, url, timeout=10.0, headers=None):
            return {"url": url, "status_code": 200, "is_broken": False, "error": None, "final_url": url}

        with patch("app.crawler.broken_link_checker.check_single_link", side_effect=mock_healthy):
            broken = asyncio.run(checker.check_all_links(
                internal_links=internal_links,
                external_links=[{"source": "https://example.com/", "target": "https://google.com", "anchor_text": "Google"}],
                crawled_pages=crawled_pages
            ))

        self.assertEqual(broken, [])

    def test_07_storage_snapshot_and_api_integration(self):
        """Test crawl storage snapshot saving broken_links.json and API retrieval endpoints."""
        storage = CrawlStorage()
        session_id = f"test_bl_sess_{uuid.uuid4().hex[:6]}"

        mock_results = {
            "status": "completed",
            "max_pages": 5000,
            "successful_pages_count": 2,
            "failed_pages_count": 0,
            "pages": [
                {"url": f"https://{self.project.domain}/", "status_code": 200, "is_success": True},
                {"url": f"https://{self.project.domain}/page1", "status_code": 200, "is_success": True}
            ],
            "issues": [],
            "internal_links": [
                {"source": f"https://{self.project.domain}/", "target": f"https://{self.project.domain}/dead", "anchor_text": "Dead Link"}
            ],
            "external_links": [
                {"source": f"https://{self.project.domain}/", "target": "https://dead-ext.com/404", "anchor_text": "Dead Ext"}
            ],
            "broken_links": [
                {
                    "source": f"https://{self.project.domain}/",
                    "target": f"https://{self.project.domain}/dead",
                    "anchor_text": "Dead Link",
                    "link_type": "internal",
                    "status_code": 404,
                    "is_broken": True,
                    "error": "HTTP 404 Not Found"
                },
                {
                    "source": f"https://{self.project.domain}/",
                    "target": "https://dead-ext.com/404",
                    "anchor_text": "Dead Ext",
                    "link_type": "external",
                    "status_code": 404,
                    "is_broken": True,
                    "error": "HTTP 404 Not Found"
                }
            ]
        }

        crawl_dir = storage.save_crawl_snapshot(
            key=self.project.domain,
            session_id=session_id,
            results=mock_results,
            domain=self.project.domain,
            project_id=self.project.id
        )

        # 1. Verify broken_links.json was created
        bl_path = os.path.join(crawl_dir, "broken_links.json")
        self.assertTrue(os.path.exists(bl_path))

        with open(bl_path, "r") as f:
            saved_bl = json.load(f)
        self.assertEqual(len(saved_bl), 2)

        # 2. Test GET /api/projects/{project_id}/internal-links/broken
        res = self.client.get(f"/api/projects/{self.project.id}/internal-links/broken", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(data["internal_count"], 1)
        self.assertEqual(data["external_count"], 1)

        # Test filter type=internal
        res_int = self.client.get(f"/api/projects/{self.project.id}/internal-links/broken?type=internal", headers=self.headers)
        self.assertEqual(res_int.status_code, 200)
        self.assertEqual(len(res_int.json()["broken_links"]), 1)
        self.assertEqual(res_int.json()["broken_links"][0]["link_type"], "internal")

        # Test filter type=external
        res_ext = self.client.get(f"/api/projects/{self.project.id}/internal-links/broken?type=external", headers=self.headers)
        self.assertEqual(res_ext.status_code, 200)
        self.assertEqual(len(res_ext.json()["broken_links"]), 1)
        self.assertEqual(res_ext.json()["broken_links"][0]["link_type"], "external")

        # 3. Test CSV export endpoint
        res_csv = self.client.get(f"/api/projects/{self.project.id}/internal-links/broken/export.csv", headers=self.headers)
        self.assertEqual(res_csv.status_code, 200)
        self.assertIn("Source Page,Broken URL,Link Type,Status Code,Link Text,Error", res_csv.text)
        self.assertIn("https://dead-ext.com/404", res_csv.text)

    def test_08_crawler_integration_broken_links(self):
        """Test SEOCrawler produces broken_links in its results."""
        crawler = SEOCrawler(start_url="https://example-broken.com/")
        
        crawler.pages = [
            {"url": "https://example-broken.com/", "status_code": 200, "is_success": True, "fetch_status": "CRAWLED"},
            {"url": "https://example-broken.com/dead", "status_code": 404, "is_success": False, "fetch_status": "FAILED", "error": "HTTP 404 Error"}
        ]
        crawler.internal_links = [
            {"source": "https://example-broken.com/", "target": "https://example-broken.com/dead", "anchor_text": "Dead Link"}
        ]
        crawler.external_links = [
            {"source": "https://example-broken.com/", "target": "https://ext-error.com/error", "anchor_text": "Ext Error"}
        ]

        async def mock_check_single(client, url, timeout=10.0, headers=None):
            return {"url": url, "status_code": 500, "is_broken": True, "error": "HTTP 500 Internal Server Error", "final_url": url}

        with patch("app.crawler.broken_link_checker.check_single_link", side_effect=mock_check_single):
            checker = BrokenLinkChecker()
            broken = asyncio.run(checker.check_all_links(
                internal_links=crawler.internal_links,
                external_links=crawler.external_links,
                crawled_pages=crawler.pages
            ))

        self.assertEqual(len(broken), 2)
        int_b = [b for b in broken if b["link_type"] == "internal"]
        ext_b = [b for b in broken if b["link_type"] == "external"]
        self.assertEqual(len(int_b), 1)
        self.assertEqual(len(ext_b), 1)
        self.assertEqual(int_b[0]["status_code"], 404)
        self.assertEqual(ext_b[0]["status_code"], 500)


if __name__ == '__main__':
    unittest.main()
