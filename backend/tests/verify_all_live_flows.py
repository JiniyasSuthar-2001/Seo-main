import unittest
import os
import sys
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.keyword import Keyword
from app.models.action_opportunity import ActionOpportunity
from app.models.competitor import Competitor
from app.models.external_connection import ExternalConnection
from app.config.auth import create_access_token
from app.routers.projects import get_project_metrics
from app.services.audit_rules import evaluate_site_audit_rules
from app.routers.internal_links import normalize_link_url


class TestLiveVerificationFlows(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        cls.user_email = f"verified_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="Verified User")
        cls.db.add(cls.user)

        cls.proj = Project(
            id=str(uuid.uuid4()),
            name="Live Verification Project",
            domain="live-verify.com",
            url="https://live-verify.com",
            description="End to end test project"
        )
        cls.db.add(cls.proj)

        cls.mem = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_email,
            project_id=cls.proj.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem)
        cls.db.commit()

        cls.token = create_access_token(user_id=cls.user_email)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ActionOpportunity).filter(ActionOpportunity.project_id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(Competitor).filter(Competitor.project_id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(ExternalConnection).filter(ExternalConnection.user_id == cls.user_email).delete(synchronize_session=False)
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id == cls.user_email).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    def test_01_uncrawled_project_health_score_null(self):
        """1. Health score must be null for uncrawled project."""
        metrics = get_project_metrics(self.proj.domain, self.proj.id)
        self.assertIsNone(metrics["health_score"], "Uncrawled project must return health_score: null")
        self.assertFalse(metrics["has_crawled"])

        res = self.client.get(f"/api/projects/{self.proj.id}/technical", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        tech = res.json()
        self.assertIsNone(tech["health_score"])
        self.assertFalse(tech["score_available"])
        for cat_name, cat in tech["category_breakdown"].items():
            self.assertFalse(cat["evaluated"])
            self.assertEqual(cat["status"], "Not Evaluated")

    def test_02_audit_rules_after_crawl_evaluation(self):
        """2. Evaluated categories must be 'Passed' or 'Issues Found', never 'Passed' when unevaluated."""
        pages = [
            {
                "url": "https://live-verify.com/",
                "status_code": 200,
                "title": "Home Page With Sufficient Length For SEO Evaluation",
                "meta_description": "This is a valid meta description for testing.",
                "h1": ["Welcome to Live Verify Website"],
                "word_count": 450,
                "canonical": "https://live-verify.com/",
                "images": [{"src": "logo.png", "alt": "Logo"}],
                "inlinks": ["https://live-verify.com/about"],
                "outlinks": ["https://live-verify.com/about"]
            }
        ]
        res = evaluate_site_audit_rules(pages)
        self.assertIsNotNone(res["health_score"])
        self.assertGreater(res["health_score"], 0)
        self.assertTrue(res["category_breakdown"]["Metadata"]["evaluated"])
        self.assertEqual(res["category_breakdown"]["Metadata"]["status"], "Passed")

    def test_03_competitor_data_no_fabrication(self):
        """3. Missing metrics must stay null."""
        from app.importers.competitor_importer import CompetitorImporter
        importer = CompetitorImporter(self.db, self.proj.id, "sparse_competitors.csv", "Direct Test")
        records = [
            {
                "name": "Sparse Competitor",
                "domain": "sparsecompetitor.com"
                # relevance_score, keyword_overlap, search_appearances intentionally missing
            }
        ]
        importer.start_import("competitors")
        importer.process_records(records)
        importer.finish_import()

        comp = self.db.query(Competitor).filter(
            Competitor.project_id == self.proj.id,
            Competitor.domain == "sparsecompetitor.com"
        ).first()
        self.assertIsNotNone(comp)
        self.assertIsNone(comp.relevance_score, "Missing relevance score must remain null, never default to 75.0")
        self.assertIsNone(comp.keyword_overlap, "Missing keyword overlap must remain null, never default to 5")
        self.assertIsNone(comp.search_appearances, "Missing search appearances must remain null, never default to 3")

    def test_04_keywords_contract_and_clustering(self):
        """4. Auto-clustering route and search suggestions parsing."""
        res_cluster = self.client.post(
            f"/api/projects/{self.proj.id}/keywords/groups/auto-cluster",
            headers=self.headers
        )
        self.assertEqual(res_cluster.status_code, 200)

        res_research = self.client.get(
            f"/api/projects/{self.proj.id}/keywords/research?q=digital+marketing",
            headers=self.headers
        )
        self.assertEqual(res_research.status_code, 200)
        data = res_research.json()
        self.assertIn("results", data)
        self.assertIn("suggestions", data)

    def test_05_rankings_winners_losers(self):
        """5. Winners and losers endpoint."""
        res = self.client.get(
            f"/api/projects/{self.proj.id}/rankings/winners-losers",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("has_comparison", data)
        self.assertIn("improved", data)
        self.assertIn("declined", data)

    def test_06_backlinks_gap_analysis(self):
        """6. Backlink gap analysis."""
        res = self.client.get(
            f"/api/projects/{self.proj.id}/backlinks/gap-analysis",
            headers=self.headers
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("confirmed_competitors_count", data)
        self.assertIn("backlink_gap", data)

    def test_07_internal_links_normalization(self):
        """7. Normalization consistency."""
        u1 = "https://live-verify.com/products/"
        u2 = "https://live-verify.com/products"
        u3 = "https://live-verify.com/products#details"
        self.assertEqual(normalize_link_url(u1), "https://live-verify.com/products")
        self.assertEqual(normalize_link_url(u2), "https://live-verify.com/products")
        self.assertEqual(normalize_link_url(u3), "https://live-verify.com/products")

    def test_08_opportunities_persistence(self):
        """8. Opportunities must persist status and not be recreated on GET."""
        opp = ActionOpportunity(
            id=str(uuid.uuid4()),
            project_id=self.proj.id,
            title="Optimise Page Headings",
            category="Content",
            priority_score=90,
            priority_level="HIGH",
            impact="High Impact",
            evidence="Headings evidence",
            status="In Progress"
        )
        self.db.add(opp)
        self.db.commit()

        # Multiple consecutive GETs
        for _ in range(3):
            res = self.client.get(f"/api/projects/{self.proj.id}/opportunities", headers=self.headers)
            self.assertEqual(res.status_code, 200)
            items = res.json().get("opportunities", [])
            matched = next((o for o in items if o["id"] == opp.id), None)
            self.assertIsNotNone(matched)
            self.assertEqual(matched["status"], "In Progress", "Status must not revert to Open")

    def test_09_alerts_preserve_affected_urls(self):
        """9. Alerts must preserve affected_urls list."""
        res = self.client.get(f"/api/projects/{self.proj.id}/alerts", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        for a in data.get("alerts", []):
            self.assertIn("affected_urls", a)
            self.assertIsInstance(a["affected_urls"], list)

    def test_10_import_upload_and_integrations_disconnect(self):
        """10. Import upload route and Integrations disconnect."""
        res_import = self.client.post(
            f"/api/projects/{self.proj.id}/import/upload",
            data={"data_type": "keywords"},
            files={"file": ("test.csv", b"keyword,position\nseo tool,5\n", "text/csv")},
            headers=self.headers
        )
        self.assertEqual(res_import.status_code, 200)

        conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=self.user_email,
            provider="google",
            provider_account_id="g_111",
            provider_email="verify@gmail.com",
            status="CONNECTED"
        )
        self.db.add(conn)
        self.db.commit()

        res_disc = self.client.post("/api/integrations/google/disconnect", headers=self.headers)
        self.assertEqual(res_disc.status_code, 200)
        self.assertIsNone(self.db.query(ExternalConnection).filter(ExternalConnection.user_id == self.user_email, ExternalConnection.provider == "google").first())


    def test_11_project_team_and_search(self):
        """11. Project team retrieval, user search, and invitation management."""
        # 1. Fetch team
        res = self.client.get(f"/api/projects/{self.proj.id}/team", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["project_id"], self.proj.id)
        self.assertTrue(data["is_owner"])
        self.assertEqual(data["caller_role"], "OWNER")
        self.assertEqual(len(data["members"]), 1)
        self.assertEqual(data["members"][0]["email"], self.user_email)

        # 2. Search users
        res_search = self.client.get(f"/api/projects/users/search?q={self.user_email[:6]}", headers=self.headers)
        self.assertEqual(res_search.status_code, 200)
        search_data = res_search.json()
        self.assertTrue(len(search_data["users"]) >= 1)

        # 3. Create second user and invite
        invitee_email = f"teammate_{uuid.uuid4().hex[:6]}@example.com"
        invitee = User(id=invitee_email, email=invitee_email, name="Teammate User")
        self.db.add(invitee)
        self.db.commit()

        res_invite = self.client.post(
            f"/api/projects/{self.proj.id}/team/invite",
            json={"email": invitee_email, "role": "MEMBER", "permissions": {"can_view": True, "can_edit": True, "can_crawl": False}},
            headers=self.headers
        )
        self.assertEqual(res_invite.status_code, 200)
        inv_id = res_invite.json().get("invitation", {}).get("id")

        # 4. Check team pending invitations
        res_team_after = self.client.get(f"/api/projects/{self.proj.id}/team", headers=self.headers)
        self.assertEqual(res_team_after.status_code, 200)
        self.assertEqual(len(res_team_after.json()["pending_invitations"]), 1)

        # 5. Cancel invitation
        res_cancel = self.client.post(
            f"/api/projects/{self.proj.id}/team/cancel-invite",
            json={"invitation_id": inv_id},
            headers=self.headers
        )
        self.assertEqual(res_cancel.status_code, 200)


if __name__ == '__main__':
    unittest.main()

