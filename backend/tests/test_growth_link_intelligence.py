import pytest
import os
import json
import tempfile
from bs4 import BeautifulSoup

from app.models.link_record import LinkRecord
from app.crawler.crawler import canonicalize_url, extract_link_semantic_location_and_context
from app.crawler.broken_link_checker import BrokenLinkChecker, normalize_link_url
from app.services.link_graph_engine import (
    build_internal_link_graph,
    get_incoming_links_for_page,
    get_outgoing_links_for_page,
    get_link_detail
)
from app.services.opportunity_engine import (
    generate_stable_opp_id,
    compute_priority_score,
    generate_central_opportunities,
    sync_project_opportunities
)


def test_url_canonicalization():
    # 1. Scheme and host lowercase
    assert canonicalize_url("HTTPS://EXAMPLE.COM/about") == "https://example.com/about"
    
    # 2. Port removal for standard HTTP/HTTPS
    assert canonicalize_url("http://example.com:80/page") == "http://example.com/page"
    assert canonicalize_url("https://example.com:443/page") == "https://example.com/page"
    assert canonicalize_url("http://example.com:8080/page") == "http://example.com:8080/page"

    # 3. Fragment removal
    assert canonicalize_url("https://example.com/page#heading-2") == "https://example.com/page"

    # 4. Consecutive slash collapse and trailing slash normalization
    assert canonicalize_url("https://example.com/services//seo/") == "https://example.com/services/seo"
    assert canonicalize_url("https://example.com/") == "https://example.com/"

    # 5. Relative resolution
    assert canonicalize_url("/blog/post-1", base_url="https://example.com/category/") == "https://example.com/blog/post-1"

    # 6. Tracking parameter stripping and query sorting
    raw = "https://example.com/item?utm_source=google&b=2&a=1&fbclid=123"
    assert canonicalize_url(raw) == "https://example.com/item?a=1&b=2"


def test_link_semantic_location_and_context_extraction():
    html = """
    <!DOCTYPE html>
    <html>
    <body>
        <header>
            <nav id="main-nav">
                <a href="/about" class="nav-item">About Us</a>
            </nav>
        </header>
        <main>
            <h1>Main Title</h1>
            <h2>Section Solutions</h2>
            <p>Here is paragraph one discussing business needs.</p>
            <p>Businesses looking for reliable <a href="/solar-installation">solar installation</a> can trust our expert team.</p>
        </main>
        <aside class="sidebar">
            <h3>Related Links</h3>
            <p><a href="/blog">Our Blog</a></p>
        </aside>
        <footer>
            <a href="/privacy">Privacy Policy</a>
        </footer>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    anchors = soup.find_all("a")

    # 1. Nav link
    nav_a = [a for a in anchors if a.get("href") == "/about"][0]
    loc_nav = extract_link_semantic_location_and_context(nav_a, soup)
    assert loc_nav["source_section"] == "navigation"

    # 2. Main content link with heading, paragraph, sentence, and context
    solar_a = [a for a in anchors if a.get("href") == "/solar-installation"][0]
    loc_solar = extract_link_semantic_location_and_context(solar_a, soup)
    assert loc_solar["source_section"] == "main"
    assert loc_solar["nearest_heading"] == "Section Solutions"
    assert loc_solar["heading_level"] == 2
    assert "Businesses looking for reliable" in loc_solar["context_before"]
    assert "can trust our expert team." in loc_solar["context_after"]
    assert "solar installation" in loc_solar["context_text"]
    assert loc_solar["paragraph_index"] == 2
    assert loc_solar["sentence_index"] == 1

    # 3. Sidebar link
    blog_a = [a for a in anchors if a.get("href") == "/blog"][0]
    loc_blog = extract_link_semantic_location_and_context(blog_a, soup)
    assert loc_blog["source_section"] == "sidebar"
    assert loc_blog["nearest_heading"] == "Related Links"

    # 4. Footer link
    priv_a = [a for a in anchors if a.get("href") == "/privacy"][0]
    loc_priv = extract_link_semantic_location_and_context(priv_a, soup)
    assert loc_priv["source_section"] == "footer"


def test_link_graph_engine_and_orphan_detection():
    pages = [
        {"url": "https://example.com/", "crawl_depth": 0, "status_code": 200, "title": "Home"},
        {"url": "https://example.com/about", "crawl_depth": 1, "status_code": 200, "title": "About"},
        {"url": "https://example.com/services", "crawl_depth": 1, "status_code": 200, "title": "Services"},
        {"url": "https://example.com/orphan-page", "crawl_depth": 2, "status_code": 200, "title": "Orphan"}
    ]
    internal_links = [
        {"source": "https://example.com/", "target": "https://example.com/about", "anchor_text": "About"},
        {"source": "https://example.com/", "target": "https://example.com/services", "anchor_text": "Services"},
        {"source": "https://example.com/about", "target": "https://example.com/services", "anchor_text": "Our Services"}
    ]

    graph = build_internal_link_graph(pages, internal_links, seed_url="https://example.com/")

    # Orphan verification: /orphan-page has 0 inbound links and is not seed
    assert graph["orphan_pages_count"] == 1
    assert graph["orphan_pages"][0]["url"] == "https://example.com/orphan-page"

    # Inbound counts
    assert graph["inbound_counts"]["https://example.com/services"] == 2
    assert graph["inbound_counts"]["https://example.com/about"] == 1
    assert graph["inbound_counts"].get("https://example.com/orphan-page", 0) == 0

    # Incoming links lookup
    incoming_to_services = get_incoming_links_for_page("https://example.com/services", internal_links=internal_links, pages=pages)
    assert len(incoming_to_services) == 2
    sources = [i["source_url"] for i in incoming_to_services]
    assert "https://example.com/" in sources
    assert "https://example.com/about" in sources

    # Outgoing links lookup
    outgoing_from_home = get_outgoing_links_for_page("https://example.com/", internal_links=internal_links, pages=pages)
    assert len(outgoing_from_home) == 2


def test_link_record_detail_and_rich_evidence():
    records = [
        {
            "id": "link_rec_001",
            "source_url": "https://example.com/blog/article",
            "target_url": "https://example.com/pricing",
            "normalized_source_url": "https://example.com/blog/article",
            "normalized_target_url": "https://example.com/pricing",
            "anchor_text": "Check our pricing",
            "link_scope": "internal",
            "is_internal": True,
            "source_section": "main",
            "nearest_heading": "Pricing Details",
            "paragraph_index": 3,
            "sentence_index": 2,
            "context_before": "If you are interested,",
            "context_text": "Check our pricing",
            "context_after": "to see flexible options.",
            "html_snippet": '<a href="/pricing">Check our pricing</a>'
        }
    ]

    detail = get_link_detail("link_rec_001", records)
    assert detail is not None
    assert detail["source_section"] == "main"
    assert detail["nearest_heading"] == "Pricing Details"
    assert detail["paragraph_index"] == 3


def test_opportunity_stable_id_and_lifecycle():
    # 1. Stable deterministic ID check
    id1 = generate_stable_opp_id("proj_123", "technical", "rule_404_errors")
    id2 = generate_stable_opp_id("proj_123", "technical", "rule_404_errors")
    assert id1 == id2
    assert id1.startswith("opp_tech_")

    # 2. Priority calculation
    p_crit = compute_priority_score("critical", affected_count=10)
    assert p_crit["level"] == "CRITICAL"
    assert p_crit["score"] >= 80

    p_low = compute_priority_score("info", affected_count=1)
    assert p_low["level"] == "LOW"


def test_deterministic_opportunities_evidence_only():
    audit_results = {
        "issues": [
            {
                "rule_id": "meta_title_missing",
                "title": "Pages Missing Title Tags",
                "severity": "critical",
                "affected_count": 2,
                "affected_urls": ["https://example.com/page1", "https://example.com/page2"],
                "evidence": "2 pages missing <title>",
                "recommendation": "Add title tags"
            }
        ]
    }
    keywords = [
        {"keyword": "seo services", "position": 14, "target_url": "https://example.com/services"}
    ]
    pages = [
        {"url": "https://example.com/page1", "status_code": 200, "meta_description": ""},
        {"url": "https://example.com/page2", "status_code": 200, "meta_description": ""}
    ]

    opps = generate_central_opportunities(
        audit_results=audit_results,
        keywords=keywords,
        pages=pages,
        project_id="test_proj"
    )

    categories = [o["category"] for o in opps]
    assert "Technical" in categories
    assert "Content" in categories
    assert "Keywords" in categories
    # Assert Backlinks and Competitors are NOT fabricated
    assert "Backlinks" not in categories
    assert "Competitors" not in categories
