import unittest
import os
import sys
from app.services.audit_rules import evaluate_site_audit_rules

class TestAuditEvidenceRedesign(unittest.TestCase):
    def test_evaluate_site_audit_rules_checks_breakdown(self):
        sample_pages = [
            {
                "url": "https://example.com/",
                "status_code": 200,
                "is_success": True,
                "title": "Home Page",
                "meta_description": "Welcome to our website",
                "canonical": "https://example.com/",
                "word_count": 450,
                "h1": "Welcome",
                "robots_meta": "index, follow"
            },
            {
                "url": "https://example.com/about",
                "status_code": 200,
                "is_success": True,
                "title": "", # Missing title (issue)
                "meta_description": "", # Missing meta description (issue)
                "canonical": "",
                "word_count": 80, # Thin content (issue)
                "h1": "", # Missing H1 (issue)
                "robots_meta": "index, follow"
            },
            {
                "url": "https://example.com/blocked",
                "status_code": 403,
                "is_success": False,
                "fetch_status": "BLOCKED"
            }
        ]

        res = evaluate_site_audit_rules(sample_pages)

        # 1. Audited pages count
        self.assertEqual(res["total_audited_pages"], 3)
        self.assertEqual(res["successful_html_pages_count"], 2)
        self.assertEqual(res["blocked_pages_count"], 1)

        # 2. Total evaluated checks & rules count
        self.assertIn("total_evaluated_checks", res)
        self.assertIn("evaluated_rules_count", res)
        self.assertIn("checks_explanation", res)
        self.assertGreater(res["total_evaluated_checks"], 0)

        # 3. Category Checks Table
        cat_table = res.get("category_checks_table", [])
        self.assertTrue(len(cat_table) >= 15, "Category checks table must contain at least 15 technical categories")

        # Performance category must NOT be marked Passed
        perf_cat = next((c for c in cat_table if c["category"] == "Performance"), None)
        self.assertIsNotNone(perf_cat)
        self.assertFalse(perf_cat["evaluated"])
        self.assertNotEqual(perf_cat["status"], "Passed", "Unevaluated Performance category must never be marked 'Passed'!")

        # Metadata category must report issues found
        meta_cat = next((c for c in cat_table if c["category"] == "Metadata"), None)
        self.assertIsNotNone(meta_cat)
        self.assertTrue(meta_cat["evaluated"])
        self.assertGreater(meta_cat["issues_count"], 0)
        self.assertEqual(meta_cat["status"], "Issues Found")

if __name__ == "__main__":
    unittest.main()
