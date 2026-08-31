import pytest
from unittest.mock import MagicMock
from app.services.audit_rules import evaluate_site_audit_rules
from app.routers.projects import get_project_metrics
from app.services.reports.master_report_service import MasterReportBuilder

def test_uncrawled_site_audit_rules_health_score_and_category_status():
    """
    Verify that when 0 pages are audited (uncrawled or unanalyzed):
    1. health_score is None (null in JSON)
    2. score_available is False
    3. Every category in category_breakdown and category_checks_table has evaluated == False and status == 'Not Evaluated'
    4. NEVER has evaluated == False and status == 'Passed'
    """
    res = evaluate_site_audit_rules([])
    assert res["health_score"] is None
    assert res["score_available"] is False
    assert res["total_audited_pages"] == 0

    breakdown = res["category_breakdown"]
    for cat_name, details in breakdown.items():
        assert details["evaluated"] is False, f"Category {cat_name} should have evaluated=False"
        assert details["status"] == "Not Evaluated", f"Category {cat_name} should have status='Not Evaluated'"
        assert not (details["evaluated"] is False and details["status"] == "Passed"), f"Forbidden combination in {cat_name}"

    table = res["category_checks_table"]
    for row in table:
        assert row["evaluated"] is False
        assert row["status"] == "Not Evaluated"
        assert not (row["evaluated"] is False and row["status"] == "Passed")

def test_crawled_site_audit_rules_evaluated_vs_unevaluated_categories():
    """
    Verify that with crawled HTML pages:
    1. health_score is a numeric integer between 0 and 100
    2. Evaluated categories have evaluated == True and status == 'Passed' or 'Issues Found'
    3. Unevaluated categories (e.g. Performance without API key) have evaluated == False and status == 'Not Evaluated'
    4. NEVER has evaluated == False and status == 'Passed'
    """
    mock_pages = [
        {
            "url": "https://example.com/",
            "status_code": 200,
            "content_type": "text/html",
            "title": "Example Home Page Title That Is Optimal Length",
            "meta_description": "This is a valid meta description that is between 70 and 160 characters in length.",
            "h1": ["Example Main Heading"],
            "canonical": "https://example.com/",
            "is_canonical": True,
            "is_indexable": True,
            "internal_links": ["https://example.com/about"],
            "external_links": ["https://google.com"],
            "images_missing_alt": 0,
            "word_count": 500,
            "has_structured_data": True,
            "is_https": True,
            "is_mobile_responsive": True,
            "has_hreflang": True
        }
    ]
    res = evaluate_site_audit_rules(mock_pages)
    assert res["health_score"] is not None
    assert isinstance(res["health_score"], (int, float))
    assert 0 <= res["health_score"] <= 100
    assert res["score_available"] is True

    table = res["category_checks_table"]
    for row in table:
        if row["evaluated"]:
            assert row["status"] in ["Passed", "Issues Found"]
        else:
            assert row["status"] == "Not Evaluated"
        assert not (row["evaluated"] is False and row["status"] == "Passed"), f"Forbidden combination in {row['category']}"

def test_crawled_site_with_issues_marks_issues_found():
    """
    Verify that when issues exist in 200 HTML pages, evaluated categories are marked as 'Issues Found'.
    """
    mock_pages = [
        {
            "url": "http://example.com/", # Insecure HTTP -> HTTPS issue
            "status_code": 200,
            "content_type": "text/html",
            "title": "", # Missing title -> Metadata issue
            "meta_description": "", # Missing meta description -> Metadata issue
            "h1": [], # Missing H1 -> Headings issue
            "canonical": "",
            "is_canonical": False,
            "is_indexable": True,
            "internal_links": [],
            "external_links": [],
            "images_missing_alt": 2, # Missing Alt -> Images issue
            "word_count": 10, # Thin content -> Content issue
            "has_structured_data": False,
            "is_mobile_responsive": False, # Mobile issue
            "has_hreflang": False
        }
    ]
    res = evaluate_site_audit_rules(mock_pages)
    assert res["health_score"] is not None
    assert res["health_score"] < 100
    assert len(res["issues"]) > 0

    table = {r["category"]: r for r in res["category_checks_table"]}
    assert table["Metadata"]["status"] == "Issues Found"
    assert table["Headings"]["status"] == "Issues Found"
    assert table["Images"]["status"] == "Issues Found"
    assert table["Content"]["status"] == "Issues Found"
    assert table["HTTPS"]["status"] == "Issues Found"
    assert table["Performance"]["status"] == "Not Evaluated"
    assert table["Performance"]["evaluated"] is False

def test_get_project_metrics_uncrawled_project():
    """
    Verify get_project_metrics returns health_score: None for an uncrawled domain.
    """
    metrics = get_project_metrics("non_existent_domain_test_xyz.com")
    assert metrics["health_score"] is None
    assert metrics["crawl_status"] == "Not Crawled"
    assert metrics["pages_count"] == 0
    assert metrics["has_crawled"] is False

def test_master_report_builder_empty_project_health_score():
    """
    Verify master report builder returns health_score: None for unscored/uncrawled project.
    """
    mock_proj = MagicMock()
    mock_proj.id = "uncrawled-test-uuid-999"
    mock_proj.domain = "uncrawled-test-domain.org"
    mock_proj.name = "Uncrawled Test Project"
    mock_proj.url = "https://uncrawled-test-domain.org"

    report = MasterReportBuilder.build_master_report(
        project=mock_proj,
        db=None,
        user_id="test_user"
    )
    assert report["health"]["health_score"] is None
    assert report["ai_analysis"]["health_score"] is None
    assert report["crawl"]["has_crawl"] is False
