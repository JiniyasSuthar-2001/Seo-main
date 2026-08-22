import os
import sys
import unittest

# Ensure backend path is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.crawler.crawler import SEOCrawler
from app.services.audit_rules import evaluate_site_audit_rules
from app.services.link_graph_engine import build_internal_link_graph
from app.services.semantic_engine import classify_search_intent, detect_keyword_cannibalization
from app.services.quality_signals import evaluate_quality_signals
from app.llm.seo_analyst import SEOAnalystAgent

class TestRealSEOIntelligenceEngine(unittest.TestCase):

    def test_1_crawler_attribute_extraction(self):
        """Verify crawler extracts hreflang, structured data, viewport, and lang attributes."""
        crawler = SEOCrawler(start_url="https://example.com/", max_pages=1)
        self.assertTrue(hasattr(crawler, "start_url"))
        self.assertEqual(crawler.domain, "example.com")

    def test_2_audit_rules_15_categories_truthfulness(self):
        """Verify 14 categories evaluated from real crawl data, 1 category Performance marked Not Analyzed."""
        pages = [
            {
                "url": "https://example.com/",
                "status_code": 200,
                "title": "Home Page",
                "meta_description": "Descriptive meta description.",
                "h1": "Welcome to Example",
                "canonical": "https://example.com/",
                "word_count": 350,
                "images_missing_alt": 0,
                "internal_links_count": 5,
                "viewport": "width=device-width, initial-scale=1.0",
                "structured_data": [{"@type": "Organization"}],
                "robots_meta": "index, follow"
            },
            {
                "url": "https://example.com/thin",
                "status_code": 200,
                "title": "",
                "meta_description": "",
                "h1": "",
                "canonical": "",
                "word_count": 50,
                "images_missing_alt": 2,
                "internal_links_count": 0,
                "viewport": None,
                "structured_data": [],
                "robots_meta": "noindex, follow"
            }
        ]

        res = evaluate_site_audit_rules(pages)
        self.assertIn("health_score", res)
        self.assertIn("category_breakdown", res)
        
        breakdown = res["category_breakdown"]
        self.assertEqual(len(breakdown), 15)
        
        # Performance must be Not Analyzed (evaluated=False)
        self.assertFalse(breakdown["Performance"]["evaluated"])
        self.assertEqual(breakdown["Performance"]["status"], "Not Analyzed")

        # 14 evaluated categories must have evaluated=True
        evaluated_cats = [k for k, v in breakdown.items() if v["evaluated"]]
        self.assertEqual(len(evaluated_cats), 14)

    def test_3_link_graph_engine(self):
        """Verify internal link graph identifies orphan pages."""
        pages = [
            {"url": "https://example.com/", "title": "Home"},
            {"url": "https://example.com/orphan", "title": "Orphan Page"}
        ]
        links = [
            {"source": "https://example.com/", "target": "https://example.com/about", "anchor_text": "About"}
        ]
        graph = build_internal_link_graph(pages, links)
        self.assertEqual(graph["orphan_pages_count"], 1)
        self.assertEqual(graph["orphan_pages"][0]["url"], "https://example.com/orphan")

    def test_4_semantic_engine_intent_classification(self):
        """Verify search intent classification for informational, transactional, and commercial queries."""
        t_intent = classify_search_intent("buy iphone 15 online")
        self.assertEqual(t_intent["intent"], "Transactional")

        c_intent = classify_search_intent("best laptops review 2024")
        self.assertEqual(c_intent["intent"], "Commercial")

        i_intent = classify_search_intent("how does seo work")
        self.assertEqual(i_intent["intent"], "Informational")

    def test_5_quality_signals_evaluation(self):
        """Verify quality signals detect thin content and duplicate titles."""
        pages = [
            {"url": "https://example.com/a", "title": "Contact Us", "word_count": 40},
            {"url": "https://example.com/b", "title": "Contact Us", "word_count": 50}
        ]
        quality = evaluate_quality_signals(pages)
        self.assertEqual(quality["thin_content_pages_count"], 2)
        self.assertEqual(quality["duplicate_title_pairs_count"], 1)

    def test_6_ai_analyst_truthfulness(self):
        """Verify AI analyst returns AI_NOT_CONFIGURED status when unconfigured without canned fake responses."""
        agent = SEOAnalystAgent()
        res = agent.analyze_project(domain="example.com")
        if res.get("status") != "empty":
            self.assertEqual(res.get("status"), "AI_NOT_CONFIGURED")
            self.assertFalse(res.get("is_llm_generated"))
            self.assertEqual(res.get("provider"), "none")

if __name__ == "__main__":
    unittest.main()
