import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.models.project import Project
from app.services.backlink_service import BacklinkDataService
from app.services.competitor_service import check_serp_provider_status, discover_competitors_for_project

class TestBacklinksAndCompetitors(unittest.TestCase):

    def test_outbound_links_service_metrics(self):
        project = MagicMock(spec=Project)
        project.id = "test_project_id"
        project.domain = "example.com"

        data = BacklinkDataService.get_project_backlink_data(project=project)
        
        self.assertIn("outbound_links", data)
        self.assertIn("outbound_summary", data)
        self.assertIn("provenance", data)
        
        # Verify provenance badges and distinction
        self.assertEqual(data["provenance"]["outbound_label"], "Crawled Data — Outbound")
        self.assertEqual(data["summary"]["inbound_backlinks"], 0)
        self.assertEqual(data["provenance"]["source_label"], "Unavailable")
        
        # Verify summary dictionary keys
        summary = data["outbound_summary"]
        self.assertIn("total_outbound_links", summary)
        self.assertIn("unique_external_urls", summary)
        self.assertIn("unique_external_domains", summary)
        self.assertIn("nofollow_count", summary)
        self.assertIn("sponsored_count", summary)
        self.assertIn("ugc_count", summary)
        self.assertIn("broken_count", summary)

    def test_competitor_serp_provider_status(self):
        project = MagicMock(spec=Project)
        project.id = "test_project_id"
        project.domain = "testdomain12345.com"

        serp_status = check_serp_provider_status(project)
        self.assertIn("has_serp_provider", serp_status)
        
        # Groq/AI alone is not a SERP data provider, so has_serp_provider must be False when no SERP provider/imported dataset exists
        self.assertFalse(serp_status["has_serp_provider"])
        self.assertIn("Competitor discovery requires search-result data", serp_status["message"])

        # discover_competitors_for_project must return honest status
        db_mock = MagicMock()
        db_mock.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        disc = discover_competitors_for_project(project, db_mock)
        self.assertFalse(disc["has_serp_provider"])
        self.assertEqual(len(disc["suggested_competitors"]), 0)

if __name__ == '__main__':
    unittest.main()
