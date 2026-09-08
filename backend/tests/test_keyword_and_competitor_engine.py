import unittest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from app.config.database import Base, engine, SessionLocal
from app.models.user import User
from app.models.project import Project
from app.models.page import Page
from app.models.competitor import Competitor
from app.models.project_membership import ProjectMembership
from app.config.auth import create_access_token
from app.services.keyword_discovery import KeywordDiscoveryService
from app.services.competitor_engine import CompetitorEngineService

client = TestClient(app)


class TestKeywordAndCompetitorEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()

        cls.user_email = f"engine_user_{uuid.uuid4().hex[:6]}@example.com"
        cls.user = User(id=cls.user_email, email=cls.user_email, name="Engine Test User")
        cls.db.add(cls.user)

        cls.proj = Project(
            id=f"proj_{uuid.uuid4().hex[:8]}",
            name="Keyword Test Project",
            domain="example.com"
        )
        cls.db.add(cls.proj)

        cls.pm = ProjectMembership(user_id=cls.user.id, project_id=cls.proj.id, role="owner")
        cls.db.add(cls.pm)

        # Add sample crawled page
        cls.page = Page(
            id=f"page_{uuid.uuid4().hex[:8]}",
            project_id=cls.proj.id,
            url="https://example.com/services/occupational-therapy",
            status_code=200,
            title="Occupational Therapy Services in Vadodara",
            h1="Professional Occupational Therapy Services",
            meta_description='Comprehensive occupational therapy treatments. Learn more at href="https://rehabclinicvadodara.com/info" for rehab details.'
        )
        cls.db.add(cls.page)

        # Add sample registered competitor
        cls.competitor = Competitor(
            id=f"comp_{uuid.uuid4().hex[:8]}",
            project_id=cls.proj.id,
            domain="vadodara-seo-competitor.com",
            url="https://vadodara-seo-competitor.com",
            name="Vadodara Competitor"
        )
        cls.db.add(cls.competitor)

        cls.db.commit()

        cls.token = create_access_token(cls.user.id)
        cls.headers = {"Authorization": f"Bearer {cls.token}"}

    @classmethod
    def tearDownClass(cls):
        cls.db.close()

    def test_01_keyword_candidate_extraction(self):
        res = KeywordDiscoveryService.discover_candidate_keywords(self.proj.id, self.db)
        self.assertEqual(res["status"], "SUCCESS")
        candidates = res["candidate_keywords"]
        self.assertGreater(len(candidates), 0)
        
        for cand in candidates:
            self.assertTrue(cand["is_ai_suggested"])
            self.assertEqual(cand["source_label"], "AI Suggested / Content Extracted")
            self.assertIsNone(cand["ranking_position"])
            self.assertIsNone(cand["search_volume"])

    def test_02_keyword_discovery_endpoint(self):
        res = client.post(f"/api/projects/{self.proj.id}/keywords/discover", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "SUCCESS")

    def test_03_competitor_discovery_from_evidence(self):
        res = CompetitorEngineService.discover_competitors_from_evidence(self.proj.id, self.db)
        self.assertGreaterEqual(len(res["competitors"]), 1)
        domains = [c["domain"] for c in res["competitors"]]
        self.assertIn("vadodara-seo-competitor.com", domains)

    def test_04_competitor_discovery_endpoint(self):
        res = client.get(f"/api/projects/{self.proj.id}/competitors/discover", headers=self.headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("competitors", data)

    def test_05_competitor_comparison_excludes_fabricated_metrics(self):
        res = CompetitorEngineService.compare_competitor(self.proj.id, "vadodara-seo-competitor.com", self.db)
        self.assertIn("Data unavailable", res["comparison"]["measured_traffic"])
        self.assertIn("Data unavailable", res["comparison"]["measured_backlinks"])

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(Page).filter(Page.project_id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(Competitor).filter(Competitor.project_id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(Project).filter(Project.id == cls.proj.id).delete(synchronize_session=False)
            cls.db.query(User).filter(User.id == cls.user.id).delete(synchronize_session=False)
            cls.db.commit()
        except Exception:
            pass
        cls.db.close()

if __name__ == '__main__':
    unittest.main()
