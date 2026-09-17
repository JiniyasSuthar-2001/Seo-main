import os
import json
import pytest
from app.config.utils import get_project_storage_dir
from app.services.audit_rules import evaluate_site_audit_rules, get_canonical_rule_registry
from app.services.schema_intelligence import SchemaIntelligenceService
from app.services.robots_sitemap_service import RobotsSitemapService
from app.services.canonical_audit_service import CanonicalAuditService


def test_project_isolation_same_domain(tmp_path):
    base_dir = str(tmp_path)
    domain = "https://example.com"
    proj_a_id = "proj_11111"
    proj_b_id = "proj_22222"

    dir_a = get_project_storage_dir(base_dir, domain, proj_a_id)
    dir_b = get_project_storage_dir(base_dir, domain, proj_b_id)

    # Folders must be separate
    assert dir_a != dir_b
    assert proj_a_id in dir_a or "proj_11111" in dir_a
    assert proj_b_id in dir_b or "proj_22222" in dir_b

    # Simulate crawl in Project A
    crawls_a = os.path.join(dir_a, "crawls", "crawl_001")
    os.makedirs(crawls_a, exist_ok=True)
    with open(os.path.join(dir_a, "latest.json"), "w") as f:
        json.dump({"crawl_id": "crawl_001", "project_id": proj_a_id, "path": crawls_a}, f)

    with open(os.path.join(crawls_a, "pages.json"), "w") as f:
        json.dump([{"url": "https://example.com", "status_code": 200, "title": "Home", "word_count": 500, "h1": "Main"}], f)

    # Project B's storage folder does NOT exist yet — checking storage must return primary dir and NOT inherit dir_a
    dir_b_check = get_project_storage_dir(base_dir, domain, proj_b_id)
    assert dir_b_check == dir_b
    assert not os.path.exists(dir_b_check)


def test_canonical_rule_registry():
    registry = get_canonical_rule_registry()
    assert len(registry) >= 14
    rule_ids = [r["rule_id"] for r in registry]
    assert "META_001" in rule_ids
    assert "SCHEMA_001" in rule_ids

    for rule in registry:
        assert "rule_id" in rule
        assert "category" in rule
        assert "rule_name" in rule
        assert "severity" in rule
        assert "evaluated" in rule


def test_health_score_calculation():
    # 1. Zero pages -> None
    eval_empty = evaluate_site_audit_rules([])
    assert eval_empty["health_score"] is None
    assert eval_empty["score_available"] is False

    # 2. Fully compliant 20 Pages
    sample_pages = [
        {
            "url": f"https://example.com/page{i}",
            "status_code": 200,
            "title": f"Technical SEO Test Page Component {i}",
            "meta_description": f"This is a comprehensive meta description detailing the page content for search engines for page {i}.",
            "word_count": 300,
            "h1": f"Heading {i}",
            "canonical": f"https://example.com/page{i}",
            "canonical_url": f"https://example.com/page{i}",
            "images": [{"src": "a.jpg", "alt": "Image"}],
            "links": [{"target_url": f"https://example.com/page{(i+1)%20}", "is_external": False}],
            "structured_data": [{"@type": "Article", "headline": f"Page {i}", "author": "Admin"}],
            "viewport": "width=device-width",
            "open_graph": {"og:title": f"Page {i}"},
            "hreflangs": [{"href": f"https://example.com/page{i}"}],
            "inbound_internal_links": 2
        }
        for i in range(20)
    ]

    eval_clean = evaluate_site_audit_rules(sample_pages)
    assert eval_clean["health_score"] == 100, f"Issues: {eval_clean['issues']}"
    assert eval_clean["total_evaluated_checks"] == 280  # 20 pages * 14 rules
    assert eval_clean["score_available"] is True


def test_schema_intelligence():
    raw_schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": "Test Company",
        "url": "https://example.com"
    }

    eval_res = SchemaIntelligenceService.evaluate_page_schema("https://example.com", raw_schema)
    assert eval_res["status"] in ("Verified/Supported", "Recognized Schema.org Type")
    assert "Organization" in eval_res["types_found"]

    raw_incomplete = {
        "@type": "Article"
    }
    eval_incomp = SchemaIntelligenceService.evaluate_page_schema("https://example.com/blog", raw_incomplete)
    assert eval_incomp["status"] == "Incomplete"
