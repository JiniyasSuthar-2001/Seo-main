import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

# Ensure backend path is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.config.utils import get_sanitized_domain, get_project_storage_key, get_project_storage_dir
from app.services.crawl_storage import CrawlStorage
from app.services.backlink_service import BacklinkDataService
from app.models.project import Project

class TestMultiTenantStorageIsolation(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="seo_isolation_test_")
        self.domain = "example.com"
        self.proj_a_id = "proj_user_A_123"
        self.proj_b_id = "proj_user_B_456"

        self.project_a = Project(
            id=self.proj_a_id,
            name="Project A",
            domain=self.domain,
            url=f"https://{self.domain}"
        )

        self.project_b = Project(
            id=self.proj_b_id,
            name="Project B",
            domain=self.domain,
            url=f"https://{self.domain}"
        )

    def tearDown(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_1_storage_key_isolation(self):
        """Verify storage keys for two projects sharing the same domain are unique."""
        key_a = get_project_storage_key(self.domain, self.proj_a_id)
        key_b = get_project_storage_key(self.domain, self.proj_b_id)

        self.assertEqual(key_a, f"{get_sanitized_domain(self.domain)}__{self.proj_a_id}")
        self.assertEqual(key_b, f"{get_sanitized_domain(self.domain)}__{self.proj_b_id}")
        self.assertNotEqual(key_a, key_b)

    def test_2_storage_dir_isolation(self):
        """Verify storage directories for Project A and Project B are isolated."""
        dir_a = get_project_storage_dir(self.temp_dir, self.domain, self.proj_a_id)
        dir_b = get_project_storage_dir(self.temp_dir, self.domain, self.proj_b_id)

        self.assertEqual(os.path.basename(dir_a), f"{get_sanitized_domain(self.domain)}__{self.proj_a_id}")
        self.assertEqual(os.path.basename(dir_b), f"{get_sanitized_domain(self.domain)}__{self.proj_b_id}")
        self.assertNotEqual(dir_a, dir_b)

    def test_3_crawl_snapshot_isolation(self):
        """Verify crawl snapshot saved for Project A is not accessible by Project B."""
        storage = CrawlStorage(base_dir=self.temp_dir)
        mock_results = {
            "status": "completed",
            "pages": [{"url": "https://example.com/page1", "status_code": 200}],
            "issues": [{"issue_type": "missing_h1", "affected_url": "https://example.com/page1", "severity": "Warning"}],
            "internal_links": [],
            "external_links": []
        }

        # Save snapshot for Project A
        crawl_dir_a = storage.save_crawl_snapshot(self.domain, "session_A", mock_results, domain=self.domain, project_id=self.proj_a_id)
        
        # Verify Project A history contains snapshot
        history_a = storage.get_crawl_history(self.domain, domain=self.domain, project_id=self.proj_a_id)
        self.assertEqual(len(history_a), 1)

        # Verify Project B history remains 100% empty
        history_b = storage.get_crawl_history(self.domain, domain=self.domain, project_id=self.proj_b_id)
        self.assertEqual(len(history_b), 0)

    def test_4_shared_domain_prevents_legacy_fallback(self):
        """Verify multiple projects sharing a domain prevents legacy directory fallback."""
        # Create legacy folder
        legacy_dir = os.path.join(self.temp_dir, get_sanitized_domain(self.domain))
        os.makedirs(legacy_dir, exist_ok=True)
        with open(os.path.join(legacy_dir, "latest.json"), "w") as f:
            f.write('{"path": "legacy"}')

        # Mock DB with 2 projects sharing domain
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_filter = MagicMock()
        mock_filter.count = MagicMock(return_value=2)
        mock_query.filter.return_value = mock_filter
        mock_db.query.return_value = mock_query

        # Resolving storage for Project B with shared DB count > 1 must NOT return legacy_dir
        dir_b = get_project_storage_dir(self.temp_dir, self.domain, self.proj_b_id, db=mock_db)
        self.assertNotEqual(dir_b, legacy_dir)
        self.assertEqual(os.path.basename(dir_b), f"{get_sanitized_domain(self.domain)}__{self.proj_b_id}")

if __name__ == "__main__":
    unittest.main()
