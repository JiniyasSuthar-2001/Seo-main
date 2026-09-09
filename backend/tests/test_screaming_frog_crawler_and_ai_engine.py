import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.crawler.crawler import SEOCrawler
from app.services.link_graph_engine import build_internal_link_graph, get_inbound_sources_for_url
from app.services.audit_rules import evaluate_site_audit_rules, extract_schema_types
from app.services.ai_solution_service import AISolutionService
from app.services.ai_usage_service import AIUsageService
from app.models.project import Project

def test_extract_schema_types_single_and_array_and_graph():
    # 1. Simple object
    sd1 = {"@type": "Organization", "name": "SEO Corp"}
    assert extract_schema_types(sd1) == ["Organization"]

    # 2. @type array
    sd2 = {"@type": ["Organization", "LocalBusiness"]}
    assert extract_schema_types(sd2) == ["Organization", "LocalBusiness"]

    # 3. @graph collection
    sd3 = {
        "@graph": [
            {"@type": "https://schema.org/WebSite", "name": "Site"},
            {"@type": "Article", "headline": "SEO Guide"}
        ]
    }
    assert extract_schema_types(sd3) == ["WebSite", "Article"]

    # 4. Multiple blocks in list
    sd4 = [sd1, sd3]
    types = extract_schema_types(sd4)
    assert "Organization" in types
    assert "WebSite" in types
    assert "Article" in types

def test_image_inventory_and_social_tags_extraction():
    crawler = SEOCrawler(start_url="https://example.com", max_pages=10)
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page for SEO Engine</title>
        <meta name="description" content="A valid test page with image and social metadata.">
        <meta property="og:title" content="Open Graph Title">
        <meta property="og:description" content="Open Graph Description">
        <meta name="twitter:card" content="summary_large_image">
    </head>
    <body>
        <h1>Main Heading</h1>
        <img src="/assets/logo.png" alt="Company Logo" width="200" height="50" loading="lazy">
        <img src="https://example.com/banner.jpg">
        <a href="/about">About Us</a>
    </body>
    </html>
    """
    
    extracted = crawler.extract_page_data_from_html("https://example.com", html_content)
    
    # Verify open graph & twitter cards
    assert extracted["og_title"] == "Open Graph Title"
    assert extracted["og_description"] == "Open Graph Description"
    assert extracted["twitter_card"] == "summary_large_image"
    
    # Verify image inventory
    images = extracted.get("image_inventory", [])
    assert len(images) == 2
    logo_img = next((i for i in images if "logo.png" in i["image_url"]), None)
    assert logo_img is not None
    assert logo_img["alt_text"] == "Company Logo"
    assert logo_img["alt_missing"] is False
    assert str(logo_img["width"]) == "200"
    assert str(logo_img["height"]) == "50"

    missing_alt_img = next((i for i in images if "banner.jpg" in i["image_url"]), None)
    assert missing_alt_img is not None
    assert missing_alt_img["alt_missing"] is True

def test_site_graph_reverse_mapping_and_orphan_detection():
    # Site with 3 pages: Root -> PageA -> PageB, and PageC (Orphan)
    pages = [
        {"url": "https://example.com/", "status_code": 200, "crawl_depth": 0},
        {"url": "https://example.com/page-a", "status_code": 200, "crawl_depth": 1},
        {"url": "https://example.com/page-b", "status_code": 200, "crawl_depth": 2},
        {"url": "https://example.com/page-orphan", "status_code": 200, "crawl_depth": 1}
    ]
    
    links = [
        {"source_url": "https://example.com/", "destination_url": "https://example.com/page-a", "is_internal": True},
        {"source_url": "https://example.com/page-a", "destination_url": "https://example.com/page-b", "is_internal": True}
    ]
    
    graph = build_internal_link_graph(pages, links)
    
    assert graph["total_nodes"] == 4
    assert graph["total_edges"] == 2
    
    # Reverse lookups
    inbound_a = get_inbound_sources_for_url("https://example.com/page-a", links)
    inbound_sources_urls = [s["source_url"] for s in inbound_a]
    assert "https://example.com/" in inbound_sources_urls
    
    inbound_b = get_inbound_sources_for_url("https://example.com/page-b", links)
    inbound_b_urls = [s["source_url"] for s in inbound_b]
    assert "https://example.com/page-a" in inbound_b_urls
    
    # Orphan check: page-orphan has 0 inbound links
    orphan_urls = [o["url"] for o in graph["orphan_pages"]]
    assert "https://example.com/page-orphan" in orphan_urls

def test_deterministic_audit_rules_expanded():
    pages = [
        {
            "url": "https://example.com/",
            "status_code": 200,
            "title": "A Very Long Page Title That Definitely Exceeds Sixty Characters In Total Length For Snippet Truncation Testing",
            "meta_description": "Valid meta description under 160 characters long for testing purposes.",
            "h1": ["Main H1 Heading", "Secondary H1 Heading"],
            "word_count": 250,
            "crawl_depth": 0,
            "inbound_internal_links_count": 5
        },
        {
            "url": "https://example.com/deep-page",
            "status_code": 200,
            "title": "Short Title",
            "meta_description": "",
            "h1": [],
            "word_count": 80,
            "crawl_depth": 4,
            "inbound_internal_links_count": 0
        }
    ]
    
    audit_results = evaluate_site_audit_rules(pages)
    
    issues = audit_results["issues"]
    rule_ids = [i["rule_id"] for i in issues]
    
    # Expected triggered rules
    assert "META_003" in rule_ids # Title too long
    assert "META_002" in rule_ids # Missing meta description
    assert "HEAD_001" in rule_ids # Missing H1
    assert "HEAD_002" in rule_ids # Multiple H1
    assert "CONT_001" in rule_ids # Thin content (<150 words)
    assert "LINK_001" in rule_ids # Orphan page
    assert "LINK_002" in rule_ids # Deep page (>3 depth)
    assert audit_results["health_score"] is not None

def test_ai_solution_generation_and_quota_enforcement():
    project = Project(id="proj-123", name="Acme Solar", domain="acmesolar.com", url="https://acmesolar.com")
    
    page = {
        "url": "https://acmesolar.com/services",
        "title": "Solar Installation Services | Acme Solar",
        "meta_description": "",
        "h1": "Solar Installation Services",
        "word_count": 400
    }
    
    # Test deterministic fallback solution generation for missing meta description
    solution = AISolutionService.get_or_generate_solution(
        project=project,
        rule_id="META_002",
        problem_title="Pages Missing Meta Descriptions",
        category="Metadata",
        severity="warning",
        description="Missing meta description tag.",
        recommendation="Add a 150-160 character meta description.",
        affected_url="https://acmesolar.com/services",
        pages=[page]
    )
    
    assert solution is not None
    assert solution["affected_url"] == "https://acmesolar.com/services"
    assert solution["recommended_replacement"] != ""
    assert 140 <= solution["character_count"] <= 165
    assert '<meta name="description"' in solution["implementation"]
    assert solution["why_this_version_is_better"] != ""

def test_ai_usage_service_accounting_isolation():
    mock_db = MagicMock()
    # Mock query count return 0
    mock_db.query().filter().count.return_value = 10
    
    can_use = AIUsageService.can_consume_ai_page("user-1", mock_db, limit=500)
    assert can_use is True
    
    # When limit reached
    mock_db.query().filter().count.return_value = 500
    can_use_exhausted = AIUsageService.can_consume_ai_page("user-1", mock_db, limit=500)
    assert can_use_exhausted is False
