import pytest
import io
from app.services.reports.pdf_framework import (
    PDFColors, NumberedCanvas, EnterprisePDFTheme, PDFComponentBuilder
)
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.report_builder_service import generate_custom_pdf_report
from app.services.reports.guideline_service import GuidelineReportService


def test_enterprise_pdf_theme_and_colors():
    theme = EnterprisePDFTheme()
    assert theme.cover_title is not None
    assert theme.section_title is not None
    assert theme.kpi_value is not None
    assert PDFColors.PRIMARY_DARK is not None
    assert PDFColors.BRAND_BLUE is not None
    assert PDFColors.SUCCESS_GREEN is not None
    assert PDFColors.CRITICAL_RED is not None


def test_generate_full_project_pdf_master_report():
    pdf_gen = PDFReportGenerator()
    master_report = {
        "project": {"name": "Solar Pro Australia", "domain": "solarpro.com.au"},
        "crawl": {"timestamp": "2026-09-10 14:00:00", "pages_crawled": 5},
        "health": {
            "health_score": 92,
            "category_breakdown": [
                {"category": "Crawlability", "score": 100, "status": "Passed"},
                {"category": "Content & Metadata", "score": 88, "status": "Audited"}
            ]
        },
        "checks": {"evaluated_rules_count": 14},
        "affected_pages": [
            {"url": "https://solarpro.com.au", "status_code": 200, "title": "Home - Solar Pro", "word_count": 850},
            {"url": "https://solarpro.com.au/about", "status_code": 200, "title": "About Us", "word_count": 420},
            {"url": "https://solarpro.com.au/broken", "status_code": 404, "title": "Not Found", "word_count": 0}
        ],
        "problems": [
            {
                "severity": "Critical",
                "problem": "Broken 404 URL Discovered",
                "affected_url": "https://solarpro.com.au/broken",
                "what_was_found": "HTTP response 404 Not Found",
                "why_it_matters": "Search crawlers waste budget and users encounter dead ends.",
                "recommended_action": "Fix internal link or redirect to /services",
                "ai_solution": "Redirect broken URL to relevant category page."
            },
            {
                "severity": "Warning",
                "problem": "Short Meta Description",
                "affected_url": "https://solarpro.com.au/about",
                "what_was_found": "Length is 35 chars (recommended 70-160)",
                "why_it_matters": "Low snippet CTR in search results.",
                "recommended_action": "Expand meta description to 120 chars.",
                "ai_solution": "Craft high-converting copy including brand benefits."
            }
        ],
        "opportunities": [
            {
                "priority": "High",
                "title": "Add Internal Links to Key Product Pages",
                "url": "https://solarpro.com.au/services",
                "recommended_action": "Link from blog posts to main service page.",
                "ai_solution": "Insert 3 contextual links with descriptive anchors."
            }
        ],
        "keywords": [
            {"keyword": "commercial solar sydney", "frequency": 8, "target_url": "https://solarpro.com.au"},
            {"keyword": "solar rebate nsw", "frequency": 4, "target_url": "https://solarpro.com.au/rebates"}
        ],
        "content_and_links": {
            "internal_links": [{"source": "https://solarpro.com.au", "target": "https://solarpro.com.au/about"}],
            "outbound_links": [{"source": "https://solarpro.com.au", "target": "https://energy.gov.au"}]
        },
        "backlinks": {
            "inbound_backlinks": [{"source_url": "https://industrynews.com/solar", "target_url": "https://solarpro.com.au"}]
        },
        "competitors": [{"domain": "competitor.com.au", "rank": 3}],
        "ai_analysis": {
            "executive_assessment": "Solar Pro displays strong technical compliance with a 92/100 score.",
            "status": "ready"
        },
        "historical_comparison": {
            "has_previous_crawl": True,
            "previous_score": 85,
            "score_delta": 7,
            "problems_fixed_count": 3,
            "new_problems_count": 1,
            "ai_trend_summary": "Overall technical health improved by 7 points after repairing broken headers."
        }
    }

    pdf_bytes = pdf_gen.generate_full_project_pdf(master_report=master_report)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 2000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_full_project_pdf_legacy_parameters():
    pdf_gen = PDFReportGenerator()
    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name="Legacy Project",
        project_url="https://legacy-domain.com",
        metadata={"health_score": 78, "website": "legacy-domain.com", "timestamp": "2026-09-10"},
        pages=[{"url": "https://legacy-domain.com", "status_code": 200}],
        issues=[{"severity": "Warning", "title": "Missing H1", "affected_url": "https://legacy-domain.com"}],
        keywords=[{"keyword": "seo tools", "frequency": 5}],
        internal_links=[{"source": "https://legacy-domain.com", "target": "https://legacy-domain.com/docs"}]
    )
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")


def test_generate_simple_table_pdf_modules():
    pdf_gen = PDFReportGenerator()
    
    # 1. Pages Report
    pages_headers = ["URL", "Status Code", "Title", "Word Count"]
    pages_rows = [
        ["https://example.com", "200", "Home Page", "1200"],
        ["https://example.com/about", "200", "About", "450"],
        ["https://example.com/contact", "200", "Contact Us", "200"]
    ]
    pages_pdf = pdf_gen.generate_simple_table_pdf(
        title="Pages Inventory Report",
        subtitle="Complete crawl catalog of discovered website URLs.",
        headers=pages_headers,
        rows_data=pages_rows,
        col_widths=[220, 60, 200, 60],
        domain="example.com",
        project_name="Example Site"
    )
    assert isinstance(pages_pdf, bytes)
    assert len(pages_pdf) > 1000
    assert pages_pdf.startswith(b"%PDF-")

    # 2. Keywords Report
    kw_headers = ["Keyword", "Frequency", "Target URL", "SERP Position"]
    kw_rows = [
        ["commercial electricians", "14", "https://example.com/services", "#4"],
        ["emergency repairs sydney", "6", "https://example.com/emergency", "#1"]
    ]
    kw_pdf = pdf_gen.generate_simple_table_pdf(
        title="Extracted Keywords & Rankings",
        subtitle="On-page content keyword frequencies and tracked search rankings.",
        headers=kw_headers,
        rows_data=kw_rows,
        col_widths=[160, 80, 200, 100],
        domain="example.com",
        project_name="Example Site"
    )
    assert isinstance(kw_pdf, bytes)
    assert len(kw_pdf) > 1000
    assert kw_pdf.startswith(b"%PDF-")


def test_generate_custom_pdf_report_various_sections():
    audit_summary = {
        "health_score": 88,
        "total_audited_pages": 12,
        "summary": {"critical_errors": 1, "warnings": 4},
        "category_checks_table": [
            {"category": "Crawlability", "checks_performed": 12, "passed": 11, "issues_count": 1},
            {"category": "Metadata", "checks_performed": 24, "passed": 20, "issues_count": 4}
        ]
    }
    pages = [{"url": "https://mysite.com", "status_code": 200, "title": "My Site Home", "word_count": 600}]
    issues = [{"severity": "Critical", "title": "Broken Link", "affected_url": "https://mysite.com"}]
    keywords = [{"keyword": "growth marketing", "frequency": 10, "pages_found": 3, "position": 5}]
    internal_links = [{"source": "https://mysite.com", "target": "https://mysite.com/blog", "anchor_text": "Blog"}]
    opportunities = [{"priority_level": "High", "title": "Optimize Meta Titles", "recommendation": "Rewrite short titles"}]
    ai_insights = {
        "summary": "Solid foundation with growth potential in metadata.",
        "findings": [{"title": "Title Optimization", "recommendation": "Expand titles", "severity": "High"}]
    }

    custom_pdf = generate_custom_pdf_report(
        project_name="My Growth Project",
        domain="mysite.com",
        sections=["Executive Summary", "SEO Health", "Technical Audit", "Pages", "Keywords", "Internal Links", "Opportunities", "AI Insights"],
        audit_summary=audit_summary,
        brand_name="Executive SEO Consultants",
        report_title="Quarterly SEO Strategy Report",
        pages=pages,
        issues=issues,
        keywords=keywords,
        internal_links=internal_links,
        opportunities=opportunities,
        ai_insights=ai_insights
    )
    assert isinstance(custom_pdf, bytes)
    assert len(custom_pdf) > 2000
    assert custom_pdf.startswith(b"%PDF-")


def test_generate_guideline_pdf():
    for guideline_id in ["keywords", "rankings", "backlinks", "competitors"]:
        pdf_bytes = GuidelineReportService.generate_guideline_pdf(guideline_id)
        assert isinstance(pdf_bytes, bytes)
        assert len(pdf_bytes) > 1000
        assert pdf_bytes.startswith(b"%PDF-")
