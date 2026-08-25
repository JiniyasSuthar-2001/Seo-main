import unittest
import os
import json
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.audit_rules import evaluate_site_audit_rules

class TestAuditEngineIntegrity(unittest.TestCase):

    def test_403_crawl_blocked_handling(self):
        """
        Test 2: A 403 page produces 'Crawl Blocked / Access Denied (HTTP 403)'
        and does NOT produce 'Missing Title', 'Missing H1', 'Missing Canonical'.
        """
        blocked_page = [{
            "url": "https://example.com/",
            "status_code": 403,
            "response_time_ms": 100,
            "error": "HTTP 403 Access Denied",
            "is_success": False,
            "word_count": 0,
            "internal_links_count": 0
        }]
        
        res = evaluate_site_audit_rules(blocked_page)
        
        self.assertEqual(res["total_audited_pages"], 1)
        self.assertEqual(res["successful_html_pages_count"], 0)
        self.assertEqual(res["blocked_pages_count"], 1)
        
        issue_titles = [i["title"] for i in res["issues"]]
        
        # Must produce Crawl Blocked issue
        self.assertIn("Crawl Blocked / Access Denied (HTTP 403)", issue_titles)
        
        # Must NOT produce false HTML metadata issues
        self.assertNotIn("Pages Missing HTML Title Tags", issue_titles)
        self.assertNotIn("Pages Missing Meta Descriptions", issue_titles)
        self.assertNotIn("Pages Missing Main H1 Heading", issue_titles)
        self.assertNotIn("Pages Missing Self-Referential Canonical Tag", issue_titles)

    def test_200_html_missing_title(self):
        """
        Test 3: A real 200 HTML page with missing title produces 'Pages Missing HTML Title Tags'.
        """
        page_no_title = [{
            "url": "https://example.com/page1",
            "status_code": 200,
            "is_success": True,
            "title": "",
            "meta_description": "Valid description",
            "h1": "Valid Heading",
            "canonical": "https://example.com/page1",
            "word_count": 500,
            "internal_links_count": 5
        }]
        
        res = evaluate_site_audit_rules(page_no_title)
        issue_titles = [i["title"] for i in res["issues"]]
        
        self.assertIn("Pages Missing HTML Title Tags", issue_titles)

    def test_200_html_valid_title(self):
        """
        Test 4: A real 200 HTML page with a valid title does NOT produce 'Pages Missing HTML Title Tags'.
        """
        valid_page = [{
            "url": "https://example.com/page1",
            "status_code": 200,
            "is_success": True,
            "title": "Complete Page Title Here",
            "meta_description": "Valid meta description text",
            "h1": "Main H1 Heading",
            "canonical": "https://example.com/page1",
            "word_count": 500,
            "internal_links_count": 5
        }]
        
        res = evaluate_site_audit_rules(valid_page)
        issue_titles = [i["title"] for i in res["issues"]]
        
        self.assertNotIn("Pages Missing HTML Title Tags", issue_titles)

    def test_no_fake_pass_on_blocked_pages(self):
        """
        Test 6: A category that cannot be evaluated on blocked pages must be marked 'Not Evaluated'.
        """
        blocked_page = [{
            "url": "https://example.com/",
            "status_code": 403,
            "is_success": False
        }]
        
        res = evaluate_site_audit_rules(blocked_page)
        categories = res["category_breakdown"]
        
        self.assertEqual(categories["Metadata"]["status"], "Not Evaluated")
        self.assertFalse(categories["Metadata"]["evaluated"])
        self.assertEqual(categories["Headings"]["status"], "Not Evaluated")
        self.assertFalse(categories["Headings"]["evaluated"])
        self.assertEqual(categories["Canonicals"]["status"], "Not Evaluated")
        self.assertFalse(categories["Canonicals"]["evaluated"])

    def test_different_projects_independent_results(self):
        """
        Test 5: Two projects with different crawl data produce independently calculated audit results.
        """
        project_a_data = [
            {"url": "https://site-a.com/", "status_code": 200, "is_success": True, "title": "Site A", "h1": "Welcome", "meta_description": "Desc A", "canonical": "https://site-a.com/", "word_count": 300, "internal_links_count": 2}
        ]
        
        project_b_data = [
            {"url": "https://site-b.com/", "status_code": 200, "is_success": True, "title": "", "h1": "", "meta_description": "", "canonical": "", "word_count": 50, "internal_links_count": 0}
        ]
        
        res_a = evaluate_site_audit_rules(project_a_data)
        res_b = evaluate_site_audit_rules(project_b_data)
        
        self.assertEqual(res_a["health_score"], 100)
        self.assertEqual(len(res_a["issues"]), 0)
        
        self.assertLess(res_b["health_score"], 100)
        self.assertGreater(len(res_b["issues"]), 0)

if __name__ == "__main__":
    unittest.main()
