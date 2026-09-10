import pytest
from app.providers.pagespeed_provider import GooglePageSpeedProvider
from app.providers.gsc_provider import GoogleSearchConsoleProvider
from app.providers.serp_provider import SERPRankTrackerProvider
from app.providers.backlink_provider import BacklinkIntelligenceProvider

def test_pagespeed_provider_response_parsing():
    provider = GooglePageSpeedProvider()
    mock_lighthouse = {
        "lighthouseResult": {
            "categories": {
                "performance": {"score": 0.88}
            },
            "audits": {
                "largest-contentful-paint": {"numericValue": 1850.0, "displayValue": "1.9 s", "score": 0.95},
                "cumulative-layout-shift": {"numericValue": 0.045, "displayValue": "0.045", "score": 0.99},
                "first-contentful-paint": {"numericValue": 1100.0, "displayValue": "1.1 s", "score": 0.98},
                "total-blocking-time": {"numericValue": 150.0, "displayValue": "150 ms", "score": 0.90},
                "server-response-time": {"numericValue": 250.0, "displayValue": "250 ms", "score": 0.99},
                "speed-index": {"numericValue": 1900.0, "displayValue": "1.9 s"},
                "interaction-to-next-paint": {"numericValue": 120.0}
            }
        }
    }

    parsed = provider._parse_pagespeed_response("https://example.com", "mobile", mock_lighthouse, "2026-09-10T12:00:00")
    assert parsed["status"] == "success"
    assert parsed["performance_score"] == 88
    assert parsed["core_web_vitals"]["lcp"]["rating"] == "GOOD"
    assert parsed["core_web_vitals"]["cls"]["rating"] == "GOOD"
    assert parsed["core_web_vitals"]["assessment"] == "PASSED"


def test_gsc_crawler_prioritization_matrix():
    pages = [
        {"url": "https://example.com/high-traffic-weak-title", "title": "Home", "word_count": 500},
        {"url": "https://example.com/low-traffic", "title": "Detailed Long Article Title", "word_count": 800}
    ]

    gsc_rows = [
        {"page": "https://example.com/high-traffic-weak-title", "query": "best seo tool", "clicks": 20, "impressions": 5000, "ctr": 0.4, "position": 4.2}
    ]

    issues = [
        {"rule_id": "META_006", "title": "Short Title", "severity": "warning", "affected_urls": ["https://example.com/high-traffic-weak-title"]}
    ]

    priorities = GoogleSearchConsoleProvider.calculate_page_priorities(pages, gsc_rows, issues)
    assert len(priorities) == 2
    # High-traffic page with weak CTR and issue must be ranked first
    assert priorities[0]["url"] == "https://example.com/high-traffic-weak-title"
    assert priorities[0]["priority_score"] > priorities[1]["priority_score"]
    assert priorities[0]["gsc_connected"] is True


def test_serp_provider_position_deltas():
    current = [
        {"keyword": "seo audit tool", "position": 3, "target_url": "https://example.com/tool"},
        {"keyword": "rank tracker", "position": 8, "target_url": "https://example.com/tracker"},
        {"keyword": "new keyword", "position": 12, "target_url": "https://example.com/new"}
    ]
    previous = [
        {"keyword": "seo audit tool", "position": 5}, # Improved (+2)
        {"keyword": "rank tracker", "position": 4},    # Declined (-4)
        {"keyword": "lost keyword", "position": 15}    # Lost
    ]

    deltas = SERPRankTrackerProvider.calculate_position_deltas(current, previous)
    assert deltas["improved_count"] == 1
    assert deltas["declined_count"] == 1
    assert deltas["new_count"] == 1
    assert deltas["lost_count"] == 1
    assert deltas["winners"][0]["keyword"] == "seo audit tool"
    assert deltas["winners"][0]["change"] == 2


def test_backlink_provider_referring_domains_aggregation():
    provider = BacklinkIntelligenceProvider()
    assert provider.get_backlinks("") == []
    assert provider.get_referring_domains("") == []
