import unittest
import os
import sys
import tempfile
import json
from app.config.utils import sanitize_csv_cell, get_sanitized_domain
from app.services.reports.export_service import CSVExportService

class TestActionCenterAndExportSystem(unittest.TestCase):
    def test_csv_formula_injection_protection(self):
        dangerous_values = [
            ("=1+1", "'=1+1"),
            ("+cmd|' /C calc'!A0", "'+cmd|' /C calc'!A0"),
            ("-100", "'-100"),
            ("@SUM(A1:A10)", "'@SUM(A1:A10)"),
            ("\tTAB", "'\tTAB"),
            ("\rCARRIAGE", "'\rCARRIAGE"),
            ("Normal Text", "Normal Text"),
            ("123", "123"),
            (None, "")
        ]

        for val, expected in dangerous_values:
            sanitized = sanitize_csv_cell(val)
            self.assertEqual(sanitized, expected, f"Failed formula injection escaping for input '{val}'")

    def test_pages_csv_generation(self):
        sample_pages = [
            {
                "url": "https://example.com/page1",
                "status_code": 200,
                "title": "Example Title 1",
                "meta_description": "=1+1 Formula Injection Attempt",
                "canonical": "https://example.com/page1",
                "word_count": 450,
                "h1": "Main Heading",
                "h2": ["Subheading 1", "Subheading 2"],
                "internal_links_count": 12,
                "external_links_count": 3
            }
        ]

        csv_out = CSVExportService.generate_pages_csv(sample_pages)
        self.assertIn("https://example.com/page1", csv_out)
        self.assertIn("'=1+1 Formula Injection Attempt", csv_out, "Formula injection trigger was not escaped in pages CSV output!")
        self.assertIn("URL,Status Code", csv_out)

    def test_opportunities_csv_generation(self):
        sample_opps = [
            {
                "priority": "HIGH",
                "category": "Technical",
                "title": "Fix Missing Meta Descriptions",
                "description": "18 pages affected",
                "affected_urls": "https://example.com/service-a",
                "provenance": "Crawled Data"
            }
        ]

        csv_out = CSVExportService.generate_opportunities_csv(sample_opps)
        self.assertIn("Fix Missing Meta Descriptions", csv_out)
        self.assertTrue("Crawled Data" in csv_out or "Website Scan" in csv_out)
        self.assertIn("HIGH", csv_out)

    def test_domain_sanitization(self):
        urls = [
            ("https://www.queenshine.com.au/", "queenshine.com.au"),
            ("http://example.com:8080/path?query=1#sec", "example.com"),
            ("CON", "site_con")
        ]
        for url, expected in urls:
            self.assertEqual(get_sanitized_domain(url), expected)

if __name__ == "__main__":
    unittest.main()
