import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def test_phase3_audit_rules():
    from app.services.audit_rules import evaluate_site_audit_rules
    from app.services.opportunity_engine import generate_central_opportunities, compute_priority_score
    from app.services.report_builder_service import generate_custom_pdf_report, generate_csv_report_package

    mock_pages = [
        {"url": "https://example.com/", "status_code": 200, "title": "", "meta_description": "", "h1": [], "canonical": "https://example.com/other", "load_time_ms": 4500, "is_https": False, "is_indexable": False},
        {"url": "https://example.com/about", "status_code": 404, "title": "About Us", "meta_description": "Short", "h1": ["About"], "canonical": None, "load_time_ms": 800, "is_https": True, "is_indexable": True}
    ]

    audit_res = evaluate_site_audit_rules(mock_pages)
    assert "health_score" in audit_res
    assert len(audit_res["category_breakdown"]) == 15

    priority_info = compute_priority_score("critical", 20, 90.0)
    assert priority_info["level"] == "CRITICAL"


    opps = generate_central_opportunities(audit_res, [], mock_pages)
    assert len(opps) > 0

    pdf_bytes = generate_custom_pdf_report("Audit Test Project", "example.com", mock_pages, audit_res["category_breakdown"], opps)
    assert len(pdf_bytes) > 0

    zip_bytes = generate_csv_report_package("Audit Test Project", "example.com", mock_pages, audit_res["category_breakdown"], opps)
    assert len(zip_bytes) > 0

if __name__ == "__main__":
    test_phase3_audit_rules()
