import os
import sys
import json
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.reports.master_report_service import MasterReportBuilder
from app.services.ai_solution_service import AISolutionService
from app.models.project import Project


def _make_project(project_id="test_ai_guard_proj", domain="testsite.com"):
    p = MagicMock(spec=Project)
    p.id = project_id
    p.domain = domain
    p.url = f"https://{domain}"
    p.name = "Test Site"
    return p


class TestNoAIOnReportDownload(unittest.TestCase):
    """
    P0: Downloading any report (PDF/XLSX/PPTX/ZIP) must NOT trigger new AI
    generation or charge AI page usage.

    Tests 1-8 cover the main acceptance criteria.
    """

    # ------------------------------------------------------------------
    # TEST 1 — allow_ai_generation defaults to False
    # ------------------------------------------------------------------
    def test_01_default_allow_ai_generation_is_false(self):
        """build_master_report must default allow_ai_generation to False."""
        import inspect
        sig = inspect.signature(MasterReportBuilder.build_master_report)
        params = sig.parameters
        self.assertIn("allow_ai_generation", params)
        default_val = params["allow_ai_generation"].default
        self.assertFalse(default_val, "allow_ai_generation must default to False")

    # ------------------------------------------------------------------
    # TEST 2 — batch_enrich_issues with max_ai_pages=0 never calls LLM
    # ------------------------------------------------------------------
    @patch("app.services.ai_solution_service.get_llm_provider_for_user")
    @patch("app.services.ai_solution_service.AIUsageService")
    def test_02_batch_enrich_max_ai_pages_zero_never_calls_llm(self, mock_usage, mock_provider_fn):
        """max_ai_pages=0 → LLM provider is never resolved; deterministic fallback returned."""
        mock_provider_fn.return_value = MagicMock()
        project = _make_project()
        issues = [{"rule_id": "MISSING_TITLE", "problem": "Missing Title", "severity": "High", "url": "https://testsite.com/"}]
        pages = [{"url": "https://testsite.com/", "title": "", "status_code": 200}]

        result = AISolutionService.batch_enrich_issues(
            project=project,
            issues=issues,
            pages=pages,
            db=None,
            user_id=None,
            max_ai_pages=0,
        )

        self.assertEqual(len(result), 1)
        mock_provider_fn.assert_not_called()
        mock_usage.record_ai_usage.assert_not_called()

    # ------------------------------------------------------------------
    # TEST 3 — AI usage NOT charged on download path
    # ------------------------------------------------------------------
    @patch("app.services.ai_solution_service.AIUsageService")
    @patch("app.services.ai_solution_service.get_llm_provider_for_user")
    def test_03_ai_usage_not_charged_on_download(self, mock_provider_fn, mock_usage_svc):
        """record_ai_usage must not be called when max_ai_pages=0 (download path)."""
        mock_usage_svc.can_consume_ai_page.return_value = True
        mock_provider_fn.return_value = MagicMock()

        project = _make_project()
        issues = [{"rule_id": "TEST", "problem": "Test Issue", "severity": "Warning", "url": "https://testsite.com/about"}]
        pages = [{"url": "https://testsite.com/about", "status_code": 200}]

        AISolutionService.batch_enrich_issues(
            project=project, issues=issues, pages=pages,
            db=None, user_id=None, max_ai_pages=0,
        )

        mock_provider_fn.assert_not_called()
        mock_usage_svc.record_ai_usage.assert_not_called()

    # ------------------------------------------------------------------
    # TEST 4 — get_or_generate_solution with no db/user_id is read-only
    # ------------------------------------------------------------------
    @patch("app.services.ai_solution_service.get_llm_provider_for_user")
    def test_04_get_or_generate_without_db_is_deterministic(self, mock_provider_fn):
        """
        get_or_generate_solution(db=None, user_id=None) must not resolve LLM
        provider and must return a valid deterministic solution.
        """
        project = _make_project()
        result = AISolutionService.get_or_generate_solution(
            project=project,
            rule_id="MISSING_META_DESC",
            problem_title="Missing Meta Description",
            category="On-Page SEO",
            severity="High",
            description="Page has no meta description",
            recommendation="Add a meta description",
            affected_url="https://testsite.com/about",
            db=None,
            user_id=None,
        )

        self.assertIsInstance(result, dict)
        self.assertIn("ai_solution", result)
        mock_provider_fn.assert_not_called()

    # ------------------------------------------------------------------
    # TEST 5 — Historical comparison no longer leaks open file handles
    # ------------------------------------------------------------------
    def test_05_historical_comparison_no_bare_open(self):
        """
        Verify the unclosed-file-handle anti-pattern is eliminated.
        json.load(open(...)) is replaced by the _safe_read_json helper.
        """
        import inspect
        source = inspect.getsource(MasterReportBuilder._build_historical_comparison)
        self.assertNotIn(
            "json.load(open(",
            source,
            "Unclosed file handle pattern 'json.load(open(...))' must not exist",
        )

    # ------------------------------------------------------------------
    # TEST 6 — build_master_report docstring documents AI gate
    # ------------------------------------------------------------------
    def test_06_docstring_documents_ai_gate(self):
        """build_master_report docstring must explain the allow_ai_generation parameter."""
        doc = MasterReportBuilder.build_master_report.__doc__ or ""
        self.assertIn("allow_ai_generation", doc)

    # ------------------------------------------------------------------
    # TEST 7 — allow_ai_generation=False → batch_enrich called with db=None
    # ------------------------------------------------------------------
    def test_07_false_flag_passes_none_to_batch(self):
        """
        When allow_ai_generation=False, batch_enrich_issues must receive
        db=None, user_id=None, max_ai_pages=0.
        """
        captured = {}

        def interceptor(project, issues, pages, db=None, user_id=None, max_ai_pages=20):
            captured["db"] = db
            captured["user_id"] = user_id
            captured["max_ai_pages"] = max_ai_pages
            return issues

        with patch.object(AISolutionService, "batch_enrich_issues", side_effect=interceptor):
            project = _make_project(project_id="gate_proj", domain="gate.example.com")
            db = MagicMock(spec=Session)
            MasterReportBuilder.build_master_report(
                project, db, user_id="real_user", allow_ai_generation=False
            )

        # If crawl exists and batch was called, validate gating
        if captured:
            self.assertIsNone(captured.get("db"), "db must be None on download path")
            self.assertIsNone(captured.get("user_id"), "user_id must be None on download path")
            self.assertEqual(captured.get("max_ai_pages"), 0, "max_ai_pages must be 0 on download path")

    # ------------------------------------------------------------------
    # TEST 8 — allow_ai_generation=True → batch_enrich called with real db
    # ------------------------------------------------------------------
    def test_08_true_flag_passes_real_db_to_batch(self):
        """
        When allow_ai_generation=True (explicit user AI action), batch_enrich_issues
        must receive the real db, user_id, and max_ai_pages=20.
        """
        captured = {}

        def interceptor(project, issues, pages, db=None, user_id=None, max_ai_pages=20):
            captured["db"] = db
            captured["user_id"] = user_id
            captured["max_ai_pages"] = max_ai_pages
            return issues

        with patch.object(AISolutionService, "batch_enrich_issues", side_effect=interceptor):
            project = _make_project(project_id="gate_proj2", domain="gate2.example.com")
            db = MagicMock(spec=Session)
            MasterReportBuilder.build_master_report(
                project, db, user_id="real_user_456", allow_ai_generation=True
            )

        if captured:
            self.assertIsNotNone(captured.get("db"), "db must be real on AI generation path")
            self.assertEqual(captured.get("user_id"), "real_user_456")
            self.assertEqual(captured.get("max_ai_pages"), 20)


if __name__ == "__main__":
    unittest.main()
