import unittest
from app.crawler.crawler import SEOCrawler

class TestDepthAndScope(unittest.TestCase):
    def test_01_level_1_depth_calculation(self):
        # Level 1 = starting page only
        crawler = SEOCrawler(start_url="https://example.com/", max_depth=1)
        
        # Start URL (depth 0) is within scope
        self.assertTrue(crawler.is_within_scope("https://example.com/"))

        # Link found on start_url (assigned depth 1) must NOT be within scope for max_depth = 1
        crawler.url_depths["https://example.com/services"] = 1
        self.assertFalse(crawler.is_within_scope("https://example.com/services"))

    def test_02_level_2_depth_calculation(self):
        # Level 2 = starting page + pages 1 hop away
        crawler = SEOCrawler(start_url="https://example.com/", max_depth=2)
        
        # Start URL (depth 0)
        self.assertTrue(crawler.is_within_scope("https://example.com/"))

        # Direct link (depth 1) is allowed
        crawler.url_depths["https://example.com/services"] = 1
        self.assertTrue(crawler.is_within_scope("https://example.com/services"))

        # 2nd tier link (depth 2) is blocked
        crawler.url_depths["https://example.com/services/seo"] = 2
        self.assertFalse(crawler.is_within_scope("https://example.com/services/seo"))

    def test_03_scope_independent_of_depth(self):
        # Subfolder scope restricts URLs outside /services/ even if max_depth is 10
        crawler = SEOCrawler(
            start_url="https://example.com/services/",
            scope_type="subfolder_only",
            max_depth=10
        )
        
        # URL inside /services/ is allowed
        crawler.url_depths["https://example.com/services/seo"] = 1
        self.assertTrue(crawler.is_within_scope("https://example.com/services/seo"))

        # URL outside /services/ is blocked despite high max_depth
        crawler.url_depths["https://example.com/about"] = 1
        self.assertFalse(crawler.is_within_scope("https://example.com/about"))

if __name__ == '__main__':
    unittest.main()
