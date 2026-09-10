import pytest
from app.services.audit_rules import evaluate_site_audit_rules, extract_schema_types

def test_extract_schema_types_various_formats():
    # 1. Simple dict
    assert extract_schema_types({"@type": "Organization"}) == ["Organization"]
    # 2. URI prefix
    assert extract_schema_types({"@type": "https://schema.org/Product"}) == ["Product"]
    # 3. Array of types
    assert extract_schema_types({"@type": ["WebSite", "LocalBusiness"]}) == ["WebSite", "LocalBusiness"]
    # 4. @graph node
    graph_data = {"@graph": [{"@type": "Article"}, {"@type": "Person"}]}
    assert extract_schema_types(graph_data) == ["Article", "Person"]
    # 5. Empty / None
    assert extract_schema_types(None) == []


def test_metadata_expanded_rules():
    pages = [
        {
            "url": "https://example.com/page1",
            "status_code": 200,
            "is_success": True,
            "title": "Short",  # < 30 chars (META_006)
            "meta_description": "Shared description across multiple pages.",  # duplicate (META_007)
            "h1": "Heading 1",
            "word_count": 400
        },
        {
            "url": "https://example.com/page2",
            "status_code": 200,
            "is_success": True,
            "title": "Short",  # duplicate title with page1 (META_004)
            "meta_description": "Shared description across multiple pages.",  # duplicate (META_007)
            "h1": "Heading 2",
            "word_count": 350
        }
    ]

    res = evaluate_site_audit_rules(pages)
    rule_ids = [i["rule_id"] for i in res["issues"]]

    assert "META_006" in rule_ids  # Short title
    assert "META_004" in rule_ids  # Duplicate title
    assert "META_007" in rule_ids  # Duplicate meta description
    assert res["health_score"] <= 100


def test_heading_hierarchy_skip_rule():
    pages = [
        {
            "url": "https://example.com/hierarchy",
            "status_code": 200,
            "is_success": True,
            "title": "Page with Skipped Heading Hierarchy Structure",
            "meta_description": "This is a detailed meta description that meets the length requirements for SEO.",
            "h1": "Main Title",
            "h2": [],  # No H2
            "h3": ["Subheading level 3"],  # Has H3 -> HEAD_003
            "word_count": 500
        }
    ]

    res = evaluate_site_audit_rules(pages)
    rule_ids = [i["rule_id"] for i in res["issues"]]
    assert "HEAD_003" in rule_ids


def test_image_dimensions_and_social_tags():
    pages = [
        {
            "url": "https://example.com/images-test",
            "status_code": 200,
            "is_success": True,
            "title": "Valid Standard Page Title Optimization",
            "meta_description": "Comprehensive and well-structured meta description for testing purposes.",
            "h1": "Main Heading",
            "image_inventory": [
                {"image_url": "https://example.com/img1.png", "width": None, "height": 300, "alt_missing": False}
            ],
            "open_graph": {},  # Missing OG -> OG_001
            "word_count": 600
        }
    ]

    res = evaluate_site_audit_rules(pages)
    rule_ids = [i["rule_id"] for i in res["issues"]]
    assert "IMG_002" in rule_ids  # Missing image width
    assert "OG_001" in rule_ids   # Missing OG title


def test_canonical_conflict_and_insecure_links():
    pages = [
        {
            "url": "https://example.com/secure-page",
            "status_code": 200,
            "is_success": True,
            "title": "Secure Page with Canonical Conflict and Outbound Link",
            "meta_description": "A descriptive summary of the page content for search engines and social shares.",
            "canonical": "http://example.com/insecure-canonical",  # Insecure canonical -> CANON_002
            "links": [
                {"target_url": "http://external-site.com/resource", "is_external": True}  # Insecure external -> EXT_001
            ],
            "word_count": 400
        }
    ]

    res = evaluate_site_audit_rules(pages)
    rule_ids = [i["rule_id"] for i in res["issues"]]
    assert "CANON_002" in rule_ids
    assert "EXT_001" in rule_ids


def test_health_score_calculation_deterministic():
    # 0 pages returns health_score=None or score_available=False
    empty_res = evaluate_site_audit_rules([])
    assert empty_res["score_available"] is False

    # Perfect page scores 100
    perfect_pages = [
        {
            "url": "https://example.com/perfect",
            "status_code": 200,
            "is_success": True,
            "title": "A Fully Compliant and Well-Structured Web Page Title",
            "meta_description": "This is an optimal meta description between 70 and 160 characters designed for maximum CTR and clarity.",
            "canonical": "https://example.com/perfect",
            "h1": "Primary Page Title",
            "h2": ["Section Subheading"],
            "h3": ["Deep Subheading"],
            "word_count": 600,
            "viewport": "width=device-width, initial-scale=1.0",
            "structured_data": {"@type": "Article"},
            "open_graph": {"og:title": "A Fully Compliant and Well-Structured Web Page Title"},
            "images_missing_alt": 0,
            "image_inventory": [{"image_url": "https://example.com/logo.png", "width": 200, "height": 50, "alt_missing": False}],
            "inbound_internal_links_count": 5,
            "crawl_depth": 1
        }
    ]
    perfect_res = evaluate_site_audit_rules(perfect_pages)
    assert perfect_res["health_score"] == 100
    assert perfect_res["summary"]["critical_errors"] == 0
