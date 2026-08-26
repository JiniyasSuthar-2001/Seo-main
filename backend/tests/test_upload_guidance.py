import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.services.reports.guideline_service import GuidelineReportService, BACKEND_GUIDELINES

class TestUploadGuidance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_guidelines_pdf_generation(self):
        for gid in ["keywords", "rankings", "backlinks", "competitors"]:
            resp = self.client.get(f"/api/guidelines/{gid}/pdf")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("application/pdf", resp.headers.get("content-type"))
            disp = resp.headers.get("content-disposition", "")
            self.assertIn(f"SEO_Platform_{gid.capitalize()}_Upload_Guidelines.pdf", disp)

    def test_02_guidelines_csv_template_generation(self):
        for gid in ["keywords", "rankings", "backlinks", "competitors"]:
            resp = self.client.get(f"/api/guidelines/{gid}/template.csv")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/csv", resp.headers.get("content-type"))
            csv_text = resp.text
            self.assertGreater(len(csv_text), 0)
            info = BACKEND_GUIDELINES[gid]
            first_header = info["synthetic_headers"][0]
            self.assertIn(first_header, csv_text)

    def test_03_synthetic_data_integrity(self):
        for gid, info in BACKEND_GUIDELINES.items():
            self.assertTrue(len(info["synthetic_rows"]) > 0)
            for row in info["synthetic_rows"]:
                for cell in row:
                    # Synthetic data should contain example.com or synthetic names
                    self.assertFalse("api_key" in str(cell).lower())
                    self.assertFalse("bearer" in str(cell).lower())

if __name__ == "__main__":
    unittest.main()
