import unittest
import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.crawler.crawler import SEOCrawler

class TestCrawlerTimeoutAndResilience(unittest.TestCase):
    def test_01_crawler_status_classification(self):
        crawler = SEOCrawler(start_url="https://example.com/", request_timeout=20.0)
        
        # Case A / B: Partial success with 1 timeout page
        crawler.pages = [
            {"url": "https://example.com/", "status_code": 200, "is_success": True},
            {"url": "https://example.com/page-2", "status_code": 200, "is_success": True},
            {"url": "https://example.com/slow-page", "status_code": 0, "is_success": False, "fetch_status": "TIMEOUT", "error": "Page crawl timed out after 20.0 seconds"}
        ]
        crawler.seed_status_code = 200

        succ = [p for p in crawler.pages if p.get("is_success") and p.get("status_code") == 200]
        fail = [p for p in crawler.pages if not p.get("is_success") or (p.get("status_code") or 0) >= 400]
        
        is_access_denied = (crawler.seed_status_code in (403, 401))
        if is_access_denied:
            status = "access_denied"
        elif len(succ) > 0 and len(fail) > 0:
            status = "completed_with_errors"
        elif len(succ) > 0 and len(fail) == 0:
            status = "completed"
        else:
            status = "failed"

        self.assertEqual(status, "completed_with_errors")
        self.assertEqual(len(succ), 2)
        self.assertEqual(len(fail), 1)

    def test_02_all_pages_failed_status(self):
        crawler = SEOCrawler(start_url="https://unreachable-domain-12345.com/", request_timeout=20.0)
        crawler.pages = [
            {"url": "https://unreachable-domain-12345.com/", "status_code": 0, "is_success": False, "fetch_status": "DNS_ERROR", "error": "DNS resolution failed"}
        ]
        crawler.seed_status_code = 0

        succ = [p for p in crawler.pages if p.get("is_success") and p.get("status_code") == 200]
        fail = [p for p in crawler.pages if not p.get("is_success") or (p.get("status_code") or 0) >= 400]
        
        is_access_denied = (crawler.seed_status_code in (403, 401))
        if is_access_denied:
            status = "access_denied"
        elif len(succ) > 0 and len(fail) > 0:
            status = "completed_with_errors"
        elif len(succ) > 0 and len(fail) == 0:
            status = "completed"
        else:
            status = "failed"

        self.assertEqual(status, "failed")

if __name__ == '__main__':
    unittest.main()
