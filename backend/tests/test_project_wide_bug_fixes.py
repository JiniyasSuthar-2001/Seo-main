import unittest
import os
import sys
import uuid
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from app.main import app
from app.config.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.models.keyword import Keyword
from app.models.keyword_group import KeywordGroup
from app.models.action_opportunity import ActionOpportunity
from app.models.competitor import Competitor
from app.models.external_connection import ExternalConnection
from app.config.auth import create_access_token
from app.routers.internal_links import normalize_link_url


class TestProjectWideBugFixes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.db = SessionLocal()

        # Create test users
        cls.user_a_email = f"user_a_{uuid.uuid4().hex[:6]}@example.com"
        cls.user_b_email = f"user_b_{uuid.uuid4().hex[:6]}@example.com"

        cls.user_a = User(id=cls.user_a_email, email=cls.user_a_email, name="User A")
        cls.user_b = User(id=cls.user_b_email, email=cls.user_b_email, name="User B")

        cls.db.add(cls.user_a)
        cls.db.add(cls.user_b)

        # Create project for User A
        cls.proj_a = Project(
            id=str(uuid.uuid4()),
            name="User A Website",
            domain="usera-domain.com",
            url="https://usera-domain.com",
            description="Project owned by User A"
        )
        cls.db.add(cls.proj_a)

        cls.mem_a = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_a_email,
            project_id=cls.proj_a.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_a)

        # Create project for User B
        cls.proj_b = Project(
            id=str(uuid.uuid4()),
            name="User B Website",
            domain="userb-domain.com",
            url="https://userb-domain.com",
            description="Project owned by User B"
        )
        cls.db.add(cls.proj_b)

        cls.mem_b = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_b_email,
            project_id=cls.proj_b.id,
            role="OWNER",
            status="ACTIVE"
        )
        cls.db.add(cls.mem_b)

        # Create sample keywords for Project A
        cls.kw_a1 = Keyword(
            id=str(uuid.uuid4()),
            project_id=cls.proj_a.id,
            keyword="solar panel installation",
            position=12,
            source="Crawled Data"
        )
        cls.kw_a2 = Keyword(
            id=str(uuid.uuid4()),
            project_id=cls.proj_a.id,
            keyword="solar panel repair",
            position=15,
            source="Crawled Data"
        )
        cls.db.add(cls.kw_a1)
        cls.db.add(cls.kw_a2)

        # Create sample keyword group for Project B
        cls.kw_group_b = KeywordGroup(
            id=str(uuid.uuid4()),
            project_id=cls.proj_b.id,
            name="Secret Topic B"
        )
        cls.db.add(cls.kw_group_b)

        # Create keyword for Project B
        cls.kw_b = Keyword(
            id=str(uuid.uuid4()),
            project_id=cls.proj_b.id,
            keyword="private keyword b",
            group_id=cls.kw_group_b.id
        )
        cls.db.add(cls.kw_b)

        cls.db.commit()

        # Generate JWT tokens
        cls.token_a = create_access_token(user_id=cls.user_a_email)
        cls.headers_a = {"Authorization": f"Bearer {cls.token_a}"}

        cls.token_b = create_access_token(user_id=cls.user_b_email)
        cls.headers_b = {"Authorization": f"Bearer {cls.token_b}"}

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ActionOpportunity).filter(
                ActionOpportunity.project_id.in_([cls.proj_a.id, cls.proj_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(ExternalConnection).filter(
                ExternalConnection.user_id.in_([cls.user_a_email, cls.user_b_email])
            ).delete(synchronize_session=False)
            cls.db.query(Competitor).filter(
                Competitor.project_id.in_([cls.proj_a.id, cls.proj_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(Keyword).filter(
                Keyword.project_id.in_([cls.proj_a.id, cls.proj_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(KeywordGroup).filter(
                KeywordGroup.project_id.in_([cls.proj_a.id, cls.proj_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(ProjectMembership).filter(
                ProjectMembership.user_id.in_([cls.user_a_email, cls.user_b_email])
            ).delete(synchronize_session=False)
            cls.db.query(Project).filter(
                Project.id.in_([cls.proj_a.id, cls.proj_b.id])
            ).delete(synchronize_session=False)
            cls.db.query(User).filter(
                (User.id.in_([cls.user_a_email, cls.user_b_email])) | (User.email.in_([cls.user_a_email, cls.user_b_email]))
            ).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            cls.db.rollback()
        finally:
            cls.db.close()

    # 1. KEYWORDS
    def test_01_keywords_auto_cluster_endpoint(self):
        """Test auto-cluster endpoint executes on actual route /keywords/groups/auto-cluster"""
        res = self.client.post(
            f"/api/projects/{self.proj_a.id}/keywords/groups/auto-cluster",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("clusters_created", data)
        self.assertIn("keywords_clustered", data)

    def test_02_keyword_research_contract(self):
        """Test keyword research supports query param and returns results array"""
        res = self.client.get(
            f"/api/projects/{self.proj_a.id}/keywords/research?q=solar",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("results", data)
        self.assertIn("suggestions", data)
        self.assertIsInstance(data["results"], list)

    def test_03_keyword_endpoint_authorization(self):
        """Test cross-tenant access to keyword opportunities and groups is denied (403)"""
        # User A querying User B's opportunities
        res_opp = self.client.get(
            f"/api/projects/{self.proj_b.id}/keywords/opportunities",
            headers=self.headers_a
        )
        self.assertEqual(res_opp.status_code, 403)

        # User A trying to rename User B's keyword group
        res_rename = self.client.put(
            f"/api/projects/{self.proj_b.id}/keywords/groups/{self.kw_group_b.id}",
            json={"name": "Hacked Group"},
            headers=self.headers_a
        )
        self.assertEqual(res_rename.status_code, 403)

        # User A trying to assign User B's keyword
        res_assign = self.client.put(
            f"/api/projects/{self.proj_b.id}/keywords/{self.kw_b.id}/group",
            json={"group_id": None},
            headers=self.headers_a
        )
        self.assertEqual(res_assign.status_code, 403)

        # User A trying to delete User B's keyword group
        res_del = self.client.delete(
            f"/api/projects/{self.proj_b.id}/keywords/groups/{self.kw_group_b.id}",
            headers=self.headers_a
        )
        self.assertEqual(res_del.status_code, 403)

    # 2. SEARCH RANKINGS
    def test_04_rankings_authorization_and_winners_losers(self):
        """Test rankings tracking overview enforces auth and winners-losers returns structure"""
        # Cross-account tracking overview denied
        res_track = self.client.get(
            f"/api/projects/{self.proj_b.id}/rankings/tracking",
            headers=self.headers_a
        )
        self.assertEqual(res_track.status_code, 403)

        # Authorized winners-losers returns contract
        res_wl = self.client.get(
            f"/api/projects/{self.proj_a.id}/rankings/winners-losers",
            headers=self.headers_a
        )
        self.assertEqual(res_wl.status_code, 200)
        data = res_wl.json()
        self.assertIn("has_comparison", data)
        self.assertIn("improved", data)
        self.assertIn("declined", data)

    # 3. BACKLINKS
    def test_05_backlink_gap_authorization_and_contract(self):
        """Test backlink gap analysis enforces auth and returns structure"""
        # Cross-account backlink gap denied
        res_gap_denied = self.client.get(
            f"/api/projects/{self.proj_b.id}/backlinks/gap-analysis",
            headers=self.headers_a
        )
        self.assertEqual(res_gap_denied.status_code, 403)

        # Authorized backlink gap
        res_gap = self.client.get(
            f"/api/projects/{self.proj_a.id}/backlinks/gap-analysis",
            headers=self.headers_a
        )
        self.assertEqual(res_gap.status_code, 200)
        data = res_gap.json()
        self.assertIn("confirmed_competitors_count", data)
        self.assertIn("backlink_gap", data)

    # 4. INTERNAL LINKS
    def test_06_internal_links_authorization_and_url_normalization(self):
        """Test internal links opportunities auth and consistent URL normalization"""
        # Cross-account opportunities denied
        res_opp_denied = self.client.get(
            f"/api/projects/{self.proj_b.id}/internal-links/opportunities",
            headers=self.headers_a
        )
        self.assertEqual(res_opp_denied.status_code, 403)

        # URL normalization consistency
        url1 = "https://example.com/about/"
        url2 = "https://example.com/about"
        url3 = "https://example.com/about#team"
        self.assertEqual(normalize_link_url(url1), "https://example.com/about")
        self.assertEqual(normalize_link_url(url2), "https://example.com/about")
        self.assertEqual(normalize_link_url(url3), "https://example.com/about")

    # 5. OPPORTUNITIES PERSISTENCE
    def test_07_opportunities_persistence_and_status_update(self):
        """Verify GET /opportunities does NOT delete or reset existing opportunity statuses"""
        # 1. Create an opportunity for Project A
        opp = ActionOpportunity(
            id=str(uuid.uuid4()),
            project_id=self.proj_a.id,
            title="Fix Missing Meta Descriptions",
            category="On-Page SEO",
            priority_score=85,
            priority_level="HIGH",
            impact="High Impact",
            evidence="3 pages missing meta description",
            affected_urls_json=json.dumps(["https://usera-domain.com/page1"]),
            affected_count=1,
            recommendation="Add descriptive meta tags",
            status="In Progress"
        )
        self.db.add(opp)
        self.db.commit()

        # 2. Call GET /opportunities - status must remain "In Progress"
        res_get = self.client.get(
            f"/api/projects/{self.proj_a.id}/opportunities",
            headers=self.headers_a
        )
        self.assertEqual(res_get.status_code, 200)
        opps = res_get.json().get("opportunities", [])
        found = next((o for o in opps if o["id"] == opp.id), None)
        self.assertIsNotNone(found, "Opportunity should not be deleted on GET request")
        self.assertEqual(found["status"], "In Progress", "Opportunity status must persist across GET requests")

        # 3. Unauthorized status update denied
        res_unauth_put = self.client.put(
            f"/api/projects/{self.proj_a.id}/opportunities/{opp.id}/status",
            json={"status": "Resolved"},
            headers=self.headers_b
        )
        self.assertEqual(res_unauth_put.status_code, 403)

        # 4. Authorized status update persists
        res_auth_put = self.client.put(
            f"/api/projects/{self.proj_a.id}/opportunities/{opp.id}/status",
            json={"status": "Resolved"},
            headers=self.headers_a
        )
        self.assertEqual(res_auth_put.status_code, 200)
        self.assertEqual(res_auth_put.json()["status"], "Resolved")

    # 6. ALERTS
    def test_08_alerts_preserve_affected_urls(self):
        """Test alerts endpoint preserves affected_urls list in output"""
        res = self.client.get(
            f"/api/projects/{self.proj_a.id}/alerts",
            headers=self.headers_a
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("alerts", data)
        for alert in data.get("alerts", []):
            self.assertIn("affected_urls", alert)
            self.assertIsInstance(alert["affected_urls"], list)

    # 7. IMPORTS COMPETITORS
    def test_09_competitor_import_support(self):
        """Test importer supports data_type='competitors' without 400 error"""
        from app.routers.imports import get_importer
        from app.importers.competitor_importer import CompetitorImporter
        importer = get_importer("competitors", self.db, self.proj_a.id, "test_competitors.csv", "Test Upload")
        self.assertIsInstance(importer, CompetitorImporter)

        # Test processing a valid record
        records = [
            {
                "Competitor Name": "Acme Solar",
                "Competitor Domain": "acmesolar.com",
                "Location": "Sydney",
                "Relevance Score": "85.5",
                "Keyword Overlap": "12"
            }
        ]
        importer.start_import("competitors")
        success, errors = importer.process_records(records)
        importer.finish_import()
        self.assertEqual(success, 1)
        self.assertEqual(errors, 0)

        # Verify competitor was stored in DB
        comp = self.db.query(Competitor).filter(
            Competitor.project_id == self.proj_a.id,
            Competitor.domain == "acmesolar.com"
        ).first()
        self.assertIsNotNone(comp)
        self.assertEqual(comp.status, "Confirmed")
        self.assertEqual(comp.relevance_score, 85.5)

    # 8. INTEGRATIONS DISCONNECT
    def test_10_integrations_disconnect_and_revoke_alias(self):
        """Test provider disconnect and revoke alias endpoint"""
        # Create external connection for user A
        conn = ExternalConnection(
            id=str(uuid.uuid4()),
            user_id=self.user_a_email,
            provider="google",
            provider_account_id="google_12345",
            provider_email="testgoogle@example.com",
            status="CONNECTED"
        )
        self.db.add(conn)
        self.db.commit()

        # Disconnect via /api/integrations/google/disconnect
        res_disc = self.client.post(
            "/api/integrations/google/disconnect",
            headers=self.headers_a
        )
        self.assertEqual(res_disc.status_code, 200)

        # Verify record is deleted
        found = self.db.query(ExternalConnection).filter(
            ExternalConnection.user_id == self.user_a_email,
            ExternalConnection.provider == "google"
        ).first()
        self.assertIsNone(found)


if __name__ == '__main__':
    unittest.main()
