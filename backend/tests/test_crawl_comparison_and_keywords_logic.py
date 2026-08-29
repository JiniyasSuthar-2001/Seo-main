import os
import sys
import unittest
import shutil
import tempfile
import json
from datetime import datetime
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.keyword import Keyword
from app.models.competitor import Competitor
from app.config.auth import create_access_token
from app.config.settings import settings
from app.config.utils import get_project_storage_dir

class TestCrawlComparisonAndKeywordsLogic(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        self.user_email = "usr_comp_test@example.com"

        user = self.db.query(User).filter(User.email == self.user_email).first()
        if not user:
            user = User(id="usr_comp_test_id", email=self.user_email, name="Comparison User")
            self.db.add(user)
            self.db.commit()

        self.proj_id = "proj_comp_test_999"
        self.domain = "comparisontest.com"
        proj = self.db.query(Project).filter(Project.id == self.proj_id).first()
        if not proj:
            proj = Project(id=self.proj_id, name="Comparison Test Site", domain=self.domain, url=f"https://{self.domain}")
            self.db.add(proj)
            self.db.commit()

        mem = self.db.query(ProjectMembership).filter(
            ProjectMembership.user_id == self.user_email,
            ProjectMembership.project_id == self.proj_id
        ).first()
        if not mem:
            mem = ProjectMembership(id="mem_comp_test", user_id=self.user_email, project_id=self.proj_id, role="OWNER", status="ACTIVE")
            self.db.add(mem)
            self.db.commit()

        # Clean up existing test keywords for clean rerun
        self.db.query(Keyword).filter(Keyword.project_id == self.proj_id).delete()
        self.db.commit()

        token = create_access_token(user_id=self.user_email)
        self.headers = {"Authorization": f"Bearer {token}"}

        # Setup temp storage directory for project crawls
        self.proj_storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, self.domain, self.proj_id)
        self.crawls_dir = os.path.join(self.proj_storage_dir, "crawls")
        if os.path.exists(self.crawls_dir):
            shutil.rmtree(self.crawls_dir)
        os.makedirs(self.crawls_dir, exist_ok=True)

    def tearDown(self):
        self.db.close()

    def test_1_issue_history_single_crawl(self):
        """Test issue history when only 1 crawl snapshot exists."""
        c1 = os.path.join(self.crawls_dir, "2026-08-29_100000")
        os.makedirs(c1, exist_ok=True)
        pages1 = [
            {"url": "https://comparisontest.com/", "title": "Home", "h1": None} # Missing H1
        ]
        with open(os.path.join(c1, "pages.json"), "w") as f:
            json.dump(pages1, f)

        res = self.client.get(f"/api/projects/{self.proj_id}/technical/issue-history", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertFalse(data["has_history"])
        self.assertIn("first crawl", data["message"])

    def test_2_issue_history_two_crawls_delta(self):
        """Test issue history delta classification (RESOLVED, NEW, IMPROVED, WORSENED, STILL OPEN)."""
        c1 = os.path.join(self.crawls_dir, "2026-08-29_100000")
        c2 = os.path.join(self.crawls_dir, "2026-08-29_120000")
        os.makedirs(c1, exist_ok=True)
        os.makedirs(c2, exist_ok=True)

        # Crawl 1: missing title on /about, missing H1 on /services, broken link on /old
        pages1 = [
            {"url": "https://comparisontest.com/about", "title": None, "h1": "About Us"},
            {"url": "https://comparisontest.com/services", "title": "Services", "h1": None},
            {"url": "https://comparisontest.com/old", "title": "Old Page", "status_code": 404}
        ]
        with open(os.path.join(c1, "pages.json"), "w") as f:
            json.dump(pages1, f)

        # Crawl 2: missing title fixed on /about, missing H1 still on /services, new missing description on /contact
        pages2 = [
            {"url": "https://comparisontest.com/about", "title": "About Us - Company", "h1": "About Us"},
            {"url": "https://comparisontest.com/services", "title": "Services", "h1": None},
            {"url": "https://comparisontest.com/contact", "title": "Contact", "meta_description": None}
        ]
        with open(os.path.join(c2, "pages.json"), "w") as f:
            json.dump(pages2, f)

        res = self.client.get(f"/api/projects/{self.proj_id}/technical/issue-history", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["has_history"])
        self.assertIn("comparison_items", data)
        self.assertGreater(len(data["comparison_items"]), 0)

        statuses = [item["status"] for item in data["comparison_items"]]
        self.assertTrue(any(s in ("RESOLVED", "NEW", "IMPROVED", "WORSENED", "STILL OPEN") for s in statuses))

    def test_3_keywords_pipeline_and_endpoints(self):
        """Test Keywords API pipeline returns frequency, pages_found, opportunities, and competitor gap."""
        kw = Keyword(
            id=f"kw_test_{json.dumps(datetime.now().isoformat())}",
            project_id=self.proj_id,
            keyword="solar panel installation",
            position=14, # Striking distance
            frequency=12,
            pages_found=4,
            source="Crawled Data"
        )
        self.db.add(kw)
        self.db.commit()

        # Keywords main list
        res = self.client.get(f"/api/projects/{self.proj_id}/keywords", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        kws = res.json().get("keywords", [])
        self.assertGreater(len(kws), 0)
        self.assertEqual(kws[0]["frequency"], 12)
        self.assertEqual(kws[0]["pages_found"], 4)
        self.assertEqual(kws[0]["position_display"], "#14")

        # Opportunities
        opp_res = self.client.get(f"/api/projects/{self.proj_id}/keywords/opportunities", headers=self.headers)
        self.assertEqual(opp_res.status_code, 200)
        opps = opp_res.json().get("opportunities", [])
        self.assertGreater(len(opps), 0)
        self.assertEqual(opps[0]["category"], "Striking Distance")

        # Competitor Gap without competitors
        gap_res = self.client.get(f"/api/projects/{self.proj_id}/keywords/competitor-gap", headers=self.headers)
        self.assertEqual(gap_res.status_code, 200)
        self.assertFalse(gap_res.json()["has_competitors"])
        self.assertIn("Competitor data unavailable", gap_res.json()["message"])

if __name__ == "__main__":
    unittest.main()
