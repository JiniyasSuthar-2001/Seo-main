import os
import shutil
import tempfile
import unittest
from app.config.utils import get_sanitized_domain
from app.services.crawl_storage import CrawlStorage

class TestCrawlPathRegression(unittest.TestCase):
    def test_url_sanitization(self):
        test_cases = [
            ("https://www.queenshine.com.au/", "queenshine.com.au"),
            ("http://www.queenshine.com.au/cdn-cgi/l/email-protection", "queenshine.com.au"),
            ("https://www.queenshine.com.au:8080/services/?test=1#sec", "queenshine.com.au"),
            ("https://example.com/page?test=1", "example.com"),
            ("https://example.com/page#section", "example.com"),
            ("https:", "https"),
            ("http://", "unknown_domain"),
            ("CON", "site_con"),
            ("AUX", "site_aux"),
            ("NUL", "site_nul"),
            ("http://192.168.1.13:8020/api", "192.168.1.13"),
        ]

        for input_url, expected in test_cases:
            sanitized = get_sanitized_domain(input_url)
            self.assertNotIn(":", sanitized, f"Colon found in sanitized path: {sanitized}")
            self.assertNotIn("\\", sanitized, f"Backslash found in sanitized path: {sanitized}")
            self.assertNotIn("/", sanitized, f"Forward slash found in sanitized path: {sanitized}")
            self.assertEqual(sanitized, expected, f"Expected '{expected}', got '{sanitized}' for input '{input_url}'")

    def test_crawl_storage_path_safety(self):
        temp_dir = tempfile.mkdtemp(prefix="test_crawl_storage_")
        try:
            storage = CrawlStorage(base_dir=temp_dir)
            problem_urls = [
                "https://www.queenshine.com.au/",
                "http://www.queenshine.com.au/cdn-cgi/l/email-protection",
                "https://example.com/page?test=1#section",
                "https:",
                "http://"
            ]

            for raw_url in problem_urls:
                folder = storage._get_website_folder(key=raw_url, domain=raw_url)
                
                # Regression check: folder path must NOT contain "https:" or illegal colons
                self.assertNotIn("https:", folder.replace(":\\", "___DRIVE___"), f"Regression bug detected! Folder path contains 'https:': {folder}")
                
                # Try creating directory on Windows OS
                crawl_dir = os.path.join(folder, "crawls", "2026-08-26_120000")
                os.makedirs(crawl_dir, exist_ok=True)
                self.assertTrue(os.path.exists(crawl_dir), f"Directory creation failed for {crawl_dir}")
                
                # Write a dummy snapshot file to verify write access
                dummy_file = os.path.join(crawl_dir, "metadata.json")
                with open(dummy_file, "w") as f:
                    f.write('{"status": "ok"}')
                self.assertTrue(os.path.exists(dummy_file), f"File creation failed for {dummy_file}")

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
