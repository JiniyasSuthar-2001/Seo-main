import os
import sys

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath("backend"))

from app.services.audit_rules import evaluate_site_audit_rules
from app.services.opportunity_engine import compute_priority_score, generate_central_opportunities
from app.services.report_builder_service import generate_custom_pdf_report, generate_csv_report_package

def verify_phase3_implementation():
    print("============================================================", flush=True)
    print(" PHASE 3 — SITE AUDIT, OPPORTUNITIES & REPORTING AUDIT", flush=True)
    print("============================================================\n", flush=True)

    # 1. Test 15-Category Site Audit Engine & Deterministic Health Score
    mock_pages = [
        {"url": "https://example.com/", "status_code": 200, "title": "Example Home", "meta_description": "Descriptive meta description.", "h1": "Main Heading", "word_count": 500, "canonical": "https://example.com/", "indexability": "index"},
        {"url": "https://example.com/broken", "status_code": 404, "title": "", "meta_description": "", "h1": "", "word_count": 0, "canonical": "", "indexability": ""},
        {"url": "http://example.com/insecure", "status_code": 200, "title": "Insecure Page", "meta_description": "", "h1": "Insecure", "word_count": 50, "canonical": "", "indexability": "noindex"}
    ]

    audit_res = evaluate_site_audit_rules(mock_pages)
    print(f"[1/5] Testing 15-Category Site Audit Rule Engine...", flush=True)
    assert "health_score" in audit_res, "Audit evaluation missing health_score"
    assert audit_res["health_score"] >= 0 and audit_res["health_score"] <= 100, "Health score out of range 0-100"
    assert len(audit_res["category_breakdown"]) == 15, f"Expected 15 categories, got {len(audit_res['category_breakdown'])}"
    print(f"      [PASS] Calculated Health Score: {audit_res['health_score']}/100 across 15 Audit Categories.", flush=True)

    # 2. Test Priority Score Calculation Formula
    print(f"\n[2/5] Testing Deterministic Priority Score Formula...", flush=True)
    calc_crit = compute_priority_score("critical", 10, 100.0)
    assert calc_crit["level"] == "CRITICAL", f"Expected CRITICAL level, got {calc_crit['level']}"
    assert calc_crit["score"] >= 80.0, f"Expected score >= 80, got {calc_crit['score']}"
    print(f"      [PASS] Critical priority calculation: Score={calc_crit['score']}, Level={calc_crit['level']}", flush=True)

    # 3. Test Central Opportunities Generator
    print(f"\n[3/5] Testing Central Action Center Opportunities Engine...", flush=True)
    opps = generate_central_opportunities(audit_res, [], mock_pages)
    assert len(opps) > 0, "Opportunities generator returned empty list"
    assert "priority_score" in opps[0], "Opportunity missing priority_score"
    print(f"      [PASS] Generated {len(opps)} prioritized growth opportunities.", flush=True)

    # 4. Test PDF Report Generation
    print(f"\n[4/5] Testing Custom Executive PDF Report Generation...", flush=True)
    pdf_bytes = generate_custom_pdf_report(
        "Audit Test Project",
        "example.com",
        ["Executive Summary", "Technical Audit"],
        audit_res,
        "SEO Intelligence Agency",
        "Executive Audit Report"
    )
    assert len(pdf_bytes) > 100, "PDF report bytes empty or corrupted"
    print(f"      [PASS] Generated PDF Report: {len(pdf_bytes)} bytes.", flush=True)

    # 5. Test CSV Package Export
    print(f"\n[5/5] Testing CSV Package ZIP Generation...", flush=True)
    zip_bytes = generate_csv_report_package("Audit Test Project", "example.com", mock_pages, [], [])
    assert len(zip_bytes) > 50, "ZIP package bytes empty"
    print(f"      [PASS] Generated CSV ZIP Package: {len(zip_bytes)} bytes.", flush=True)

    print("\n============================================================", flush=True)
    print(" ALL 5 PHASE 3 AUDIT TESTS PASSED SUCCESSFULLY!", flush=True)
    print("============================================================", flush=True)

if __name__ == "__main__":
    verify_phase3_implementation()
