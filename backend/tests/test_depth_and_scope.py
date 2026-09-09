import unittest
from app.crawler.crawler import SEOCrawler

class TestDepthAndScope(unittest.TestCase):
    def test_01_level_1_depth_calculation(self):
        # max_depth = 1 means seed (depth 0) + direct 1-hop links (depth 1) are allowed
        crawler = SEOCrawler(start_url="https://example.com/", max_depth=1)
        
        # Start URL (depth 0) is within scope
        is_scope, _ = crawler.is_within_scope("https://example.com/")
        self.assertTrue(is_scope)

        # Direct link found on start_url (assigned depth 1) IS within scope for max_depth = 1
        crawler.url_depths["https://example.com/services"] = 1
        is_scope, _ = crawler.is_within_scope("https://example.com/services")
        self.assertTrue(is_scope)

        # 2nd tier link (depth 2) is blocked for max_depth = 1
        crawler.url_depths["https://example.com/services/seo"] = 2
        is_scope, reason = crawler.is_within_scope("https://example.com/services/seo")
        self.assertFalse(is_scope)
        self.assertEqual(reason, "MAX_DEPTH_EXCEEDED")

    def test_02_level_2_depth_calculation(self):
        # max_depth = 2 means seed (depth 0) + depth 1 + depth 2 are allowed
        crawler = SEOCrawler(start_url="https://example.com/", max_depth=2)
        
        # Start URL (depth 0)
        is_scope, _ = crawler.is_within_scope("https://example.com/")
        self.assertTrue(is_scope)

        # Direct link (depth 1) is allowed
        crawler.url_depths["https://example.com/services"] = 1
        is_scope, _ = crawler.is_within_scope("https://example.com/services")
        self.assertTrue(is_scope)

        # 2nd tier link (depth 2) is allowed
        crawler.url_depths["https://example.com/services/seo"] = 2
        is_scope, _ = crawler.is_within_scope("https://example.com/services/seo")
        self.assertTrue(is_scope)

        # 3rd tier link (depth 3) is blocked
        crawler.url_depths["https://example.com/services/seo/pricing"] = 3
        is_scope, reason = crawler.is_within_scope("https://example.com/services/seo/pricing")
        self.assertFalse(is_scope)
        self.assertEqual(reason, "MAX_DEPTH_EXCEEDED")

    def test_03_scope_independent_of_depth(self):
        # Subfolder scope restricts URLs outside /services/ even if max_depth is 10
        crawler = SEOCrawler(
            start_url="https://example.com/services/",
            scope_type="subfolder_only",
            max_depth=10
        )
        
        # URL inside /services/ is allowed
        crawler.url_depths["https://example.com/services/seo"] = 1
        is_scope, _ = crawler.is_within_scope("https://example.com/services/seo")
        self.assertTrue(is_scope)

        # URL outside /services/ is blocked despite high max_depth
        crawler.url_depths["https://example.com/about"] = 1
        is_scope, reason = crawler.is_within_scope("https://example.com/about")
        self.assertFalse(is_scope)
        self.assertEqual(reason, "OUT_OF_SUBFOLDER_SCOPE")

    def test_04_subfolder_segment_matching(self):
        # Subfolder /services/ must NOT match /services-old/
        crawler = SEOCrawler(
            start_url="https://example.com/services/",
            scope_type="subfolder_only",
            max_depth=5
        )
        crawler.url_depths["https://example.com/services-old"] = 1
        is_scope, reason = crawler.is_within_scope("https://example.com/services-old")
        self.assertFalse(is_scope)
        self.assertEqual(reason, "OUT_OF_SUBFOLDER_SCOPE")

        crawler.url_depths["https://example.com/services/web-design"] = 1
        is_scope, _ = crawler.is_within_scope("https://example.com/services/web-design")
        self.assertTrue(is_scope)

if __name__ == '__main__':
    unittest.main()
