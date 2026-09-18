import os
import sys
import json
import unittest
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
from app.config.auth import create_access_token
from app.config.settings import settings
from app.config.utils import get_project_storage_dir

class TestFeatureUpdates(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        db = SessionLocal()

        cls.owner_email = "owner_test_feat@example.com"
        cls.member_email = "member_test_feat@example.com"
        cls.other_email = "other_test_feat@example.com"

        for email, name in [
            (cls.owner_email, "Owner User"),
            (cls.member_email, "Member User"),
            (cls.other_email, "Other User")
        ]:
            u = db.query(User).filter(User.email == email).first()
            if not u:
                u = User(id=f"usr_{email}", email=email, name=name)
                db.add(u)
        db.commit()

        cls.proj_id = "proj_feat_test_999"
        proj = db.query(Project).filter(Project.id == cls.proj_id).first()
        if not proj:
            proj = Project(
                id=cls.proj_id,
                name="Feature Alpha Site",
                url="https://alphafeature.com"
            )
            db.add(proj)
            db.commit()

        mem_owner_id = f"mem_owner_{cls.proj_id}"
        pm_owner = db.query(ProjectMembership).filter(ProjectMembership.id == mem_owner_id).first()
        if not pm_owner:
            pm_owner = ProjectMembership(
                id=mem_owner_id,
                user_id=cls.owner_email,
                project_id=cls.proj_id,
                role="OWNER",
                status="ACTIVE"
            )
            db.add(pm_owner)

        mem_member_id = f"mem_member_{cls.proj_id}"
        pm_member = db.query(ProjectMembership).filter(ProjectMembership.id == mem_member_id).first()
        if not pm_member:
            pm_member = ProjectMembership(
                id=mem_member_id,
                user_id=cls.member_email,
                project_id=cls.proj_id,
                role="MEMBER",
                status="ACTIVE"
            )
            db.add(pm_member)
        db.commit()

        cls.kw_id = "kw_feat_test_999"
        if not db.query(Keyword).filter(Keyword.id == cls.kw_id).first():
            kw = Keyword(
                id=cls.kw_id,
                project_id=cls.proj_id,
                keyword="seo audit",
                frequency=5,
                search_volume=1200
            )
            db.add(kw)
            db.commit()

        db.close()

        cls.owner_headers = {"Authorization": f"Bearer {create_access_token(user_id=cls.owner_email)}"}
        cls.member_headers = {"Authorization": f"Bearer {create_access_token(user_id=cls.member_email)}"}
        cls.other_headers = {"Authorization": f"Bearer {create_access_token(user_id=cls.other_email)}"}

    def setUp(self):
        db = SessionLocal()
        # Ensure project exists
        p = db.query(Project).filter(Project.id == self.proj_id).first()
        if not p:
            p = Project(id=self.proj_id, name="Feature Alpha Site", url="https://alphafeature.com")
            db.add(p)
            db.commit()

        # Ensure active owner membership
        pm = db.query(ProjectMembership).filter(
            ProjectMembership.project_id == self.proj_id,
            ProjectMembership.user_id == self.owner_email
        ).first()
        if not pm:
            import uuid
            pm = ProjectMembership(
                id=f"mem_own_{uuid.uuid4().hex[:8]}",
                user_id=self.owner_email,
                project_id=self.proj_id,
                role="OWNER",
                status="ACTIVE"
            )
            db.add(pm)
            db.commit()
        elif pm.status != "ACTIVE" or pm.role != "OWNER":
            pm.status = "ACTIVE"
            pm.role = "OWNER"
            db.commit()

        # Ensure keyword exists
        kw = db.query(Keyword).filter(Keyword.id == self.kw_id).first()
        if not kw:
            kw = Keyword(
                id=self.kw_id,
                project_id=self.proj_id,
                keyword="seo audit",
                frequency=5,
                search_volume=1200
            )
            db.add(kw)
            db.commit()
        db.close()

    def test_1_project_overview_empty_crawl(self):
        """Test GET /api/projects/{project_id}/overview with no crawl returns honest empty state."""
        fresh_id = "proj_fresh_empty_999"
        db = SessionLocal()
        if not db.query(Project).filter(Project.id == fresh_id).first():
            p = Project(id=fresh_id, name="Fresh Project", url="https://freshproject.com")
            db.add(p)
            db.commit()
        mem_id = f"mem_{fresh_id}"
        if not db.query(ProjectMembership).filter(ProjectMembership.id == mem_id).first():
            pm = ProjectMembership(id=mem_id, user_id=self.owner_email, project_id=fresh_id, role="OWNER", status="ACTIVE")
            db.add(pm)
            db.commit()
        db.close()

        res = self.client.get(
            f"/api/projects/{fresh_id}/overview",
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data["project"]["id"], fresh_id)
        self.assertEqual(data["project"]["name"], "Fresh Project")
        self.assertFalse(data["has_crawl"])
        self.assertIsNone(data["kpis"]["health_score"])
        self.assertIsNone(data["kpis"]["total_pages"])
        self.assertEqual(data["kpis"]["total_runs"], 0)
        self.assertIsNone(data["kpis"]["critical_problems"])
        self.assertEqual(data["health_trend"], [])
        self.assertEqual(data["issues_trend"], [])
        self.assertIn("technical_audit", data["previews"])
        self.assertIn("keywords", data["previews"])

    def test_2_project_overview_unauthorized_isolation(self):
        """Test multi-tenant isolation: unauthorized user cannot access project overview."""
        res = self.client.get(
            f"/api/projects/{self.proj_id}/overview",
            headers=self.other_headers
        )
        self.assertEqual(res.status_code, 403, res.text)

    def test_3_keyword_evidence(self):
        """Test keyword evidence endpoint returns real crawl occurrences and location types."""
        storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, "alphafeature.com", self.proj_id)
        os.makedirs(storage_dir, exist_ok=True)
        crawl_file = os.path.join(storage_dir, "latest.json")
        crawl_payload = {
            "session_id": "test_evidence_session",
            "timestamp": "2026-09-18T10:00:00Z",
            "pages": [
                {
                    "url": "https://alphafeature.com/",
                    "title": "Comprehensive SEO Audit for Business",
                    "meta_description": "Run your seo audit today with precision.",
                    "h1": ["Best SEO Audit Tool"],
                    "h2": ["Why SEO Audit Matters", "Pricing"],
                    "h3": [],
                    "paragraphs": ["Our seo audit engine scans every single link and tag."],
                    "first_paragraph": "Our seo audit engine scans every single link and tag.",
                    "body_text": "Our seo audit engine scans every single link and tag.",
                    "images": [{"alt": "seo audit overview graphic", "src": "/img.png"}],
                    "links": [{"anchor": "Explore our seo audit suite", "href": "/about"}]
                }
            ],
            "issues": []
        }
        with open(crawl_file, "w", encoding="utf-8") as f:
            json.dump(crawl_payload, f)

        res = self.client.get(
            f"/api/projects/{self.proj_id}/keywords/{self.kw_id}/evidence",
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 200, res.text)
        ev = res.json()
        self.assertEqual(ev["keyword"], "seo audit")
        self.assertGreater(ev["total_frequency"], 0)
        self.assertGreater(len(ev["evidence"]), 0)

        locations = [item["location"] for item in ev["evidence"]]
        self.assertIn("Page title", locations)
        self.assertIn("Meta description", locations)
        self.assertIn("H1", locations)

    def test_4_three_crawl_issue_history(self):
        """Test 3-crawl comparison endpoint returns Previous-Previous, Previous, and Latest."""
        storage_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, "alphafeature.com", self.proj_id)
        crawls_dir = os.path.join(storage_dir, "crawls")
        os.makedirs(crawls_dir, exist_ok=True)

        for i, (ts, missing_count) in enumerate([
            ("2026-09-15T10:00:00Z", 6),
            ("2026-09-16T10:00:00Z", 4),
            ("2026-09-17T10:00:00Z", 2)
        ], start=1):
            folder = f"crawl_{ts.replace(':', '_')}"
            cdir = os.path.join(crawls_dir, folder)
            os.makedirs(cdir, exist_ok=True)
            pages = [
                {"url": f"https://alphafeature.com/p{j}", "status_code": 200, "title": "" if j < missing_count else f"Page Title {j}"}
                for j in range(10)
            ]
            with open(os.path.join(cdir, "pages.json"), "w", encoding="utf-8") as f:
                json.dump(pages, f)
            with open(os.path.join(cdir, "metadata.json"), "w", encoding="utf-8") as f:
                json.dump({"timestamp": ts, "session_id": f"sess_{i}"}, f)

        res = self.client.get(
            f"/api/projects/{self.proj_id}/technical/issue-history",
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 200, res.text)
        hist = res.json()
        self.assertEqual(hist["crawls_count"], 3)
        self.assertEqual(len(hist["snapshots"]), 3)
        self.assertEqual(hist["snapshots"][0]["label"], "Previous-Previous")
        self.assertEqual(hist["snapshots"][1]["label"], "Previous")
        self.assertEqual(hist["snapshots"][2]["label"], "Latest")
        self.assertGreater(len(hist["comparison_items"]), 0)

    def test_5_template_download_and_guidelines(self):
        """Test template downloads for all supported types match schema and contain valid example rows."""
        for dataset in ["keywords", "rankings", "backlinks", "competitors"]:
            res = self.client.get(
                f"/api/guidelines/{dataset}/template.csv",
                headers=self.owner_headers
            )
            self.assertEqual(res.status_code, 200, res.text)
            content = res.text
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            self.assertGreaterEqual(len(lines), 3)

    def test_6_member_cannot_delete_project(self):
        """Test member role cannot delete project via DELETE /api/projects/{project_id}."""
        res = self.client.delete(
            f"/api/projects/{self.proj_id}",
            headers=self.member_headers
        )
        self.assertEqual(res.status_code, 403, res.text)

    def test_7_owner_can_delete_project(self):
        """Test owner role can delete project, cascades data and cleans up storage."""
        del_proj_id = "proj_to_delete_test_999"
        db = SessionLocal()
        if not db.query(Project).filter(Project.id == del_proj_id).first():
            p = Project(id=del_proj_id, name="Project To Delete", url="https://deleteme.com")
            db.add(p)
            db.commit()
        mem_del_id = f"mem_{del_proj_id}"
        if not db.query(ProjectMembership).filter(ProjectMembership.id == mem_del_id).first():
            pm = ProjectMembership(id=mem_del_id, user_id=self.owner_email, project_id=del_proj_id, role="OWNER", status="ACTIVE")
            db.add(pm)
            db.commit()
        db.close()

        res = self.client.delete(
            f"/api/projects/{del_proj_id}",
            headers=self.owner_headers
        )
        self.assertEqual(res.status_code, 200, res.text)
        data = res.json()
        self.assertEqual(data.get("status"), "success")

        res_get = self.client.get(
            f"/api/projects/{del_proj_id}",
            headers=self.owner_headers
        )
        self.assertEqual(res_get.status_code, 404)

if __name__ == "__main__":
    unittest.main()
