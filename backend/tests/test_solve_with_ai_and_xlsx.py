import os
import json
import uuid
import unittest
import openpyxl
import io
from datetime import datetime

from app.config.database import SessionLocal, Base, engine
from app.models.user import User
from app.models.project import Project
from app.models.project_membership import ProjectMembership
from app.services.ai_solution_service import AISolutionService
from app.services.reports.master_report_service import MasterReportBuilder
from app.services.reports.xlsx_service import XLSXExportService
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, get_project_storage_dir

class TestSolveWithAIAndMasterXLSX(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)
        cls.db = SessionLocal()
        cls.user_id = str(uuid.uuid4())
        cls.user = User(
            id=cls.user_id,
            email=f"solve_ai_{uuid.uuid4().hex[:6]}@example.com",
            name="Solve AI Tester"
        )
        cls.db.add(cls.user)
        cls.db.commit()

        cls.project_id = str(uuid.uuid4())
        cls.domain = f"solar-install-{uuid.uuid4().hex[:6]}.com"
        cls.project = Project(
            id=cls.project_id,
            name="Apex Solar Energy",
            domain=cls.domain,
            target_country="Australia",
            industry="Renewable Energy & Solar Installation",
            services="Solar Panel Installation, Commercial Solar, Battery Storage",
            service_areas="Brisbane, Gold Coast, Queensland"
        )
        cls.db.add(cls.project)
        cls.db.commit()

        cls.membership = ProjectMembership(
            id=str(uuid.uuid4()),
            user_id=cls.user_id,
            project_id=cls.project_id,
            role="owner"
        )
        cls.db.add(cls.membership)
        cls.db.commit()

        # Prepare mock crawl data
        cls.proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, cls.domain, cls.project_id)
        cls.crawl_id = "crawl_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        cls.crawl_dir = os.path.join(cls.proj_dir, "crawls", cls.crawl_id)
        os.makedirs(cls.crawl_dir, exist_ok=True)

        cls.pages = [
            {
                "url": f"https://{cls.domain}/",
                "title": "Home - Apex Solar Energy Systems Brisbane",
                "meta_description": "We are a full service solar energy provider specializing in high-grade solar panels and residential storage solutions for all homeowners across the entire Queensland region.",
                "h1": "Top Rated Solar Panel Installers Brisbane",
                "status_code": 200,
                "word_count": 850,
                "canonical": f"https://{cls.domain}/"
            },
            {
                "url": f"https://{cls.domain}/services/commercial-solar/",
                "title": "Commercial Solar Power Installations and Energy Storage - Apex Solar Brisbane Queensland Australia Wide",
                "meta_description": "Commercial Solar Solutions by Apex Solar Energy Brisbane Australia providing enterprise rooftop solar installations, battery storage integration, commercial power savings audits, zero down commercial financing, ongoing monitoring, and full manufacturer warranty support.", # 275 chars (too long)
                "h1": "Commercial Solar Power Systems",
                "status_code": 200,
                "word_count": 1200,
                "canonical": f"https://{cls.domain}/services/commercial-solar/"
            },
            {
                "url": f"https://{cls.domain}/battery-storage/",
                "title": "", # Missing title
                "meta_description": "", # Missing meta description
                "h1": "", # Missing H1
                "status_code": 200,
                "word_count": 450,
                "canonical": f"https://{cls.domain}/battery-storage/"
            },
            {
                "url": f"https://{cls.domain}/broken-page-test/",
                "title": "Page Not Found",
                "meta_description": "",
                "status_code": 404,
                "word_count": 50,
                "canonical": ""
            }
        ]

        with open(os.path.join(cls.crawl_dir, "pages.json"), "w", encoding="utf-8") as f:
            json.dump(cls.pages, f)

        with open(os.path.join(cls.proj_dir, "latest.json"), "w", encoding="utf-8") as f:
            json.dump({
                "crawl_id": cls.crawl_id,
                "path": cls.crawl_dir,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }, f)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.db.query(ProjectMembership).filter(ProjectMembership.project_id == cls.project_id).delete()
            cls.db.query(Project).filter(Project.id == cls.project_id).delete()
            cls.db.query(User).filter(User.id == cls.user_id).delete()
            cls.db.commit()
            cls.db.close()
        except Exception:
            pass

    def test_01_meta_description_too_long_generates_actionable_fix(self):
        """Scenario 1: Meta Description Too Long gives exact replacement, char count, and HTML tag."""
        target_url = f"https://{self.domain}/services/commercial-solar/"
        sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="META_DESCRIPTION_TOO_LONG",
            problem_title="Meta Description Too Long",
            category="On-Page",
            severity="High",
            description="The meta description is 275 characters, which exceeds the 160 character limit.",
            recommendation="Shorten meta description to 150-160 characters.",
            affected_url=target_url,
            pages=self.pages
        )

        self.assertIsNotNone(sol)
        self.assertEqual(sol["affected_url"], target_url)
        self.assertIn("what_is_wrong", sol)
        self.assertIn("why_it_matters", sol)
        self.assertIn("what_should_change", sol)
        self.assertIn("current_value", sol)
        self.assertIn("recommended_replacement", sol)
        self.assertTrue(len(sol["recommended_replacement"]) > 0)
        self.assertTrue(100 <= sol["character_count"] <= 165)
        self.assertIn("<meta name=\"description\"", sol["implementation"])
        self.assertIn("where_to_change", sol)
        self.assertIn("why_this_version_is_better", sol)
        self.assertIn("verification", sol)
        self.assertEqual(sol["status"], "Open")

    def test_02_missing_title_tag_generates_replacement_and_tag(self):
        """Scenario 2: Missing title tag generates concise replacement and <title> tag."""
        target_url = f"https://{self.domain}/battery-storage/"
        sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="MISSING_TITLE_TAG",
            problem_title="Missing Title Tag",
            category="On-Page",
            severity="High",
            description="Page is missing a title tag.",
            recommendation="Add a descriptive title tag between 50-60 characters.",
            affected_url=target_url,
            pages=self.pages
        )

        self.assertIsNotNone(sol)
        self.assertIn("Battery Storage", sol["recommended_replacement"])
        self.assertIn("<title>", sol["implementation"])
        self.assertTrue(len(sol["recommended_replacement"]) <= 65)
        self.assertIn("where_to_change", sol)
        self.assertIn("verification", sol)

    def test_03_missing_h1_generates_concrete_h1_heading(self):
        """Scenario 3: Missing H1 heading generates <h1> tag grounded in page URL."""
        target_url = f"https://{self.domain}/battery-storage/"
        sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="MISSING_H1_HEADING",
            problem_title="Missing H1 Heading",
            category="Content Structure",
            severity="High",
            description="Page does not have an H1 heading.",
            recommendation="Add a single descriptive H1 tag.",
            affected_url=target_url,
            pages=self.pages
        )

        self.assertIsNotNone(sol)
        self.assertIn("<h1>", sol["implementation"])
        self.assertIn("</h1>", sol["implementation"])
        self.assertIn("where_to_change", sol)

    def test_04_broken_link_404_generates_status_and_redirect_fix(self):
        """Scenario 4: Broken 404 URL generates 301 redirect instruction."""
        target_url = f"https://{self.domain}/broken-page-test/"
        sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="BROKEN_PAGE_404",
            problem_title="Page Returns HTTP 404 Not Found",
            category="Technical",
            severity="Critical",
            description="URL returns HTTP 404 status code.",
            recommendation="Restore page or configure 301 redirect.",
            affected_url=target_url,
            pages=self.pages
        )

        self.assertIsNotNone(sol)
        self.assertEqual(sol["severity"], "Critical")
        self.assertIn("404", sol["what_is_wrong"])
        self.assertIn("301", sol["recommended_replacement"])
        self.assertIn("where_to_change", sol)

    def test_05_missing_schema_generates_valid_json_ld(self):
        """Scenario 5: Missing Schema generates valid JSON-LD schema snippet."""
        target_url = f"https://{self.domain}/"
        sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="MISSING_SCHEMA_MARKUP",
            problem_title="Missing Schema Markup",
            category="Structured Data",
            severity="Medium",
            description="Page is missing structured data.",
            recommendation="Add Schema.org JSON-LD markup.",
            affected_url=target_url,
            pages=self.pages
        )

        self.assertIsNotNone(sol)
        self.assertIn("application/ld+json", sol["implementation"])
        self.assertIn("schema.org", sol["recommended_replacement"])

    def test_06_insufficient_crawl_data_does_not_fabricate(self):
        """Scenario 6: Missing page crawl data explicitly reports Insufficient crawl data without fake info."""
        sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="UNKNOWN_UNSCANNED_RULE",
            problem_title="Unscanned Rule Finding",
            category="Technical",
            severity="Medium",
            description="No data available",
            recommendation="Run scan",
            affected_url="",
            pages=[]
        )

        self.assertIn("The required information was not available in the crawl data, so an exact replacement cannot be generated safely.", sol["recommended_replacement"])

    def test_07_master_report_and_xlsx_automatically_contain_ai_solutions(self):
        """Scenario 7: Master Report and Master XLSX automatically contain all solution fields without user clicking Solve button."""
        from app.routers.reports import get_shared_project_report_data
        report_data = get_shared_project_report_data(self.project, self.db, self.user_id)
        problems = report_data.get("issues", [])

        self.assertTrue(len(problems) > 0)
        sample_prob = problems[0]

        # Verify standard fields are present in normalized problems
        required_fields = [
            "issue_id", "category", "severity", "affected_url", "what_is_wrong",
            "current_value", "ai_solution", "recommended_fix", "recommended_replacement",
            "implementation", "why_this_version_is_better", "verification", "priority", "crawl_date", "status"
        ]
        for field in required_fields:
            self.assertIn(field, sample_prob, f"Field '{field}' missing from Master Report problem")

        # Generate Master XLSX
        xlsx_bytes = XLSXExportService.generate_full_project_xlsx(
            project_name=self.project.name,
            project_url=self.project.domain,
            metadata=report_data["metadata"],
            pages=report_data["pages"],
            keywords=report_data["keywords"],
            issues=problems,
            opportunities=report_data["opportunities"],
            ai_insights=report_data["ai_insights"],
            internal_links=[],
            outbound_links=[],
            competitors=[],
            backlinks=[],
            master_report=report_data.get("master_report")
        )

        self.assertTrue(len(xlsx_bytes) > 0)

        # Validate Technical XLSX contains required columns
        tech_xlsx_bytes = XLSXExportService.generate_technical_xlsx(issues=problems, domain=self.domain)
        wb = openpyxl.load_workbook(io.BytesIO(tech_xlsx_bytes))
        ws = wb.active

        headers = [cell.value for cell in ws[1]]
        self.assertIn("Priority", headers)
        self.assertIn("Category", headers)
        self.assertIn("Problem", headers)
        self.assertIn("Affected Pages", headers)
        self.assertIn("What We Found", headers)
        self.assertIn("Current Value", headers)
        self.assertIn("Recommended Action", headers)
        self.assertIn("AI Solution", headers)
        self.assertIn("Implementation / Code", headers)
        self.assertIn("Expected Improvement", headers)
        self.assertIn("Verification", headers)
        self.assertIn("Status", headers)
        self.assertIn("Crawl Date", headers)

    def test_08_ui_and_xlsx_consistency_and_caching(self):
        """Scenario 8: Solve with AI and Master XLSX retrieve identical solution from snapshot cache."""
        target_url = f"https://{self.domain}/services/commercial-solar/"
        
        # Step A: UI Solve with AI invocation
        ui_sol = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="META_DESCRIPTION_TOO_LONG",
            problem_title="Meta Description Too Long",
            category="On-Page",
            severity="High",
            description="The meta description is 275 characters.",
            recommendation="Shorten meta description.",
            affected_url=target_url,
            pages=self.pages,
            db=self.db,
            user_id=self.user_id
        )

        # Step B: Repeated UI Solve with AI invocation (retrieves cached solution)
        ui_sol_cached = AISolutionService.get_or_generate_solution(
            project=self.project,
            rule_id="META_DESCRIPTION_TOO_LONG",
            problem_title="Meta Description Too Long",
            category="On-Page",
            severity="High",
            description="The meta description is 275 characters.",
            recommendation="Shorten meta description.",
            affected_url=target_url,
            pages=self.pages,
            db=self.db,
            user_id=self.user_id
        )

        self.assertEqual(ui_sol["recommended_replacement"], ui_sol_cached["recommended_replacement"])
        self.assertEqual(ui_sol["character_count"], ui_sol_cached["character_count"])

        # Step C: Master Report generation uses the exact same stored solution
        enriched = AISolutionService.batch_enrich_issues(
            project=self.project,
            issues=[{
                "rule_id": "META_DESCRIPTION_TOO_LONG",
                "title": "Meta Description Too Long",
                "category": "On-Page",
                "severity": "High",
                "affected_url": target_url
            }],
            pages=self.pages,
            db=self.db,
            user_id=self.user_id
        )

        self.assertEqual(len(enriched), 1)
        self.assertEqual(enriched[0]["recommended_replacement"], ui_sol["recommended_replacement"])
        self.assertEqual(enriched[0]["implementation"], ui_sol["implementation"])

if __name__ == "__main__":
    unittest.main()
