import unittest
import uuid
import json
from datetime import datetime, timedelta
from app.config.database import SessionLocal
from app.models.project import Project
from app.models.crawl_session import CrawlSession

class TestCrawlCompletionUXAndAPI(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        self.project_id = f"test-proj-ux-{uuid.uuid4().hex[:8]}"
        self.project = Project(
            id=self.project_id,
            name="Crawl UX Test Site",
            url="https://example-ux-test.com",
            domain="example-ux-test.com",
            crawl_config=json.dumps({"max_pages": 500})
        )
        self.db.add(self.project)
        self.db.commit()

    def tearDown(self):
        self.db.query(CrawlSession).filter(CrawlSession.project_id == self.project_id).delete()
        self.db.query(Project).filter(Project.id == self.project_id).delete()
        self.db.commit()
        self.db.close()

    def test_01_crawl_session_duration_and_metrics_calculation(self):
        start_time = datetime.utcnow() - timedelta(seconds=134)
        comp_time = datetime.utcnow()
        session = CrawlSession(
            id=str(uuid.uuid4()),
            project_id=self.project_id,
            status="completed",
            pages_discovered=1248,
            pages_crawled=1231,
            issues_found=17,
            started_at=start_time,
            completed_at=comp_time,
            status_message="Crawl completed successfully"
        )
        self.db.add(session)
        self.db.commit()

        # Verify DB values
        fetched = self.db.query(CrawlSession).filter(CrawlSession.id == session.id).first()
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.pages_discovered, 1248)
        self.assertEqual(fetched.pages_crawled, 1231)
        self.assertEqual(fetched.issues_found, 17)
        self.assertIsNotNone(fetched.completed_at)

        # Calculate duration
        duration = int((fetched.completed_at - fetched.started_at).total_seconds())
        self.assertGreaterEqual(duration, 130)
        self.assertLessEqual(duration, 140)

    def test_02_crawl_cancellation_preserves_status(self):
        session = CrawlSession(
            id=str(uuid.uuid4()),
            project_id=self.project_id,
            status="cancelling",
            pages_discovered=25,
            pages_crawled=10,
            started_at=datetime.utcnow()
        )
        self.db.add(session)
        self.db.commit()

        session.status = "cancelled"
        session.status_message = "Crawl cancelled by user."
        session.completed_at = datetime.utcnow()
        self.db.commit()

        fetched = self.db.query(CrawlSession).filter(CrawlSession.id == session.id).first()
        self.assertEqual(fetched.status, "cancelled")
        self.assertNotEqual(fetched.status, "completed")

    def test_03_crawl_failure_status_integrity(self):
        session = CrawlSession(
            id=str(uuid.uuid4()),
            project_id=self.project_id,
            status="failed",
            pages_discovered=1,
            pages_crawled=0,
            issues_found=0,
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            status_message="Crawl failed to reach destination server."
        )
        self.db.add(session)
        self.db.commit()

        fetched = self.db.query(CrawlSession).filter(CrawlSession.id == session.id).first()
        self.assertEqual(fetched.status, "failed")
        self.assertEqual(fetched.pages_crawled, 0)

if __name__ == "__main__":
    unittest.main()
