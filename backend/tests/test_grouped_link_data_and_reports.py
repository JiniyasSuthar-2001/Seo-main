import pytest
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.crawler.broken_link_checker import check_single_link, check_links_status, BrokenLinkChecker, normalize_link_url
from app.services.crawl_data.crawl_dataset_service import CrawlDatasetService
from app.crawler.crawler import canonicalize_url
from app.services.link_graph_engine import build_internal_link_graph, normalize_graph_url


class TestGroupedLinkDataAndReports(unittest.IsolatedAsyncioTestCase):
    """
    Automated test suite verifying the grouped link data layer, Content-Type headers,
    real status verification without 'Active' fallbacks, DOM context preservation,
    and crawl snapshot integrity.
    """

    # -------------------------------------------------------------------------
    # A. Same external URL appears on 20 pages -> 1 grouped destination, 20 source pages
    # -------------------------------------------------------------------------
    def test_case_a_external_url_on_20_pages_groups_to_one_destination(self):
        artifacts = {
            "external_links": [
                {
                    "source_url": f"https://example.com/page-{i}",
                    "destination_url": "https://external.org/partner",
                    "anchor_text": f"Partner link {i}",
                    "rel": "nofollow",
                    "status": "200 OK",
                    "status_code": 200,
                    "content_type": "text/html"
                }
                for i in range(1, 21)
            ],
            "timestamp": "2026-09-09T10:00:00"
        }

        dataset = CrawlDatasetService.get_external_links_dataset(artifacts)
        self.assertEqual(len(dataset), 1, "Should group 20 occurrences of the same destination into 1 row")
        
        row = dataset[0]
        self.assertEqual(row["destination_url"], "https://external.org/partner")
        self.assertEqual(row["source_pages"], 20, "Source pages count must be 20")
        self.assertEqual(row["occurrences"], 20, "Total occurrences count must be 20")
        self.assertEqual(len(row["unique_source_urls"]), 20)
        self.assertEqual(len(row["occurrences_list"]), 20)
        self.assertEqual(row["status"], "200 OK")
        self.assertEqual(row["content_type"], "text/html")

    # -------------------------------------------------------------------------
    # B. Same destination appears multiple times on one page -> 1 source page, multiple occurrences
    # -------------------------------------------------------------------------
    def test_case_b_same_destination_multiple_times_on_page(self):
        artifacts = {
            "external_links": [
                {
                    "source_url": "https://example.com/about",
                    "destination_url": "https://partner.com/service",
                    "anchor_text": "Header partner",
                    "nearest_heading": "About Us",
                    "paragraph_index": 0
                },
                {
                    "source_url": "https://example.com/about",
                    "destination_url": "https://partner.com/service",
                    "anchor_text": "Body partner",
                    "nearest_heading": "Our Services",
                    "paragraph_index": 3
                },
                {
                    "source_url": "https://example.com/about",
                    "destination_url": "https://partner.com/service",
                    "anchor_text": "Footer partner",
                    "nearest_heading": "Contact Us",
                    "paragraph_index": 8
                },
                {
                    "source_url": "https://example.com/pricing",
                    "destination_url": "https://partner.com/service",
                    "anchor_text": "Pricing integration",
                    "nearest_heading": "Integrations",
                    "paragraph_index": 2
                }
            ]
        }

        dataset = CrawlDatasetService.get_external_links_dataset(artifacts)
        self.assertEqual(len(dataset), 1)
        row = dataset[0]
        self.assertEqual(row["source_pages"], 2, "2 unique source pages (about and pricing)")
        self.assertEqual(row["occurrences"], 4, "4 total occurrences")
        self.assertEqual(len(row["occurrences_list"]), 4)

    # -------------------------------------------------------------------------
    # C. External URL returns 200 -> 200 OK status
    # -------------------------------------------------------------------------
    async def test_case_c_external_url_returns_200(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://verified-site.com/about"
        mock_response.headers = {"content-type": "text/html; charset=UTF-8"}
        mock_response.history = []

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response

        res = await check_single_link(mock_client, "https://verified-site.com/about")
        self.assertEqual(res["status_code"], 200)
        self.assertEqual(res["status"], "200 OK")
        self.assertEqual(res["content_type"], "text/html")
        self.assertFalse(res["is_broken"])
        self.assertIsNone(res["error"])

    # -------------------------------------------------------------------------
    # D. External URL returns 404 -> 404 Not Found
    # -------------------------------------------------------------------------
    async def test_case_d_external_url_returns_404(self):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.reason_phrase = "Not Found"
        mock_response.url = "https://example.com/missing-resource"
        mock_response.headers = {"content-type": "text/html"}
        mock_response.history = []

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response

        res = await check_single_link(mock_client, "https://example.com/missing-resource")
        self.assertEqual(res["status_code"], 404)
        self.assertEqual(res["status"], "404 Not Found")
        self.assertTrue(res["is_broken"])
        self.assertEqual(res["error_type"], "not_found")

    # -------------------------------------------------------------------------
    # E. External URL redirects -> 3xx + final URL + redirect chain
    # -------------------------------------------------------------------------
    async def test_case_e_external_url_redirects(self):
        hop1 = MagicMock()
        hop1.status_code = 301
        hop1.url = "http://example.com/old"

        final_resp = MagicMock()
        final_resp.status_code = 200
        final_resp.url = "https://example.com/new"
        final_resp.headers = {"content-type": "text/html"}
        final_resp.history = [hop1]

        mock_client = AsyncMock()
        mock_client.head.return_value = final_resp

        res = await check_single_link(mock_client, "http://example.com/old")
        self.assertEqual(res["status"], "301 Redirect")
        self.assertEqual(res["final_url"], "https://example.com/new")
        self.assertEqual(len(res["redirect_chain"]), 2)
        self.assertEqual(res["redirect_chain"][0]["status_code"], 301)
        self.assertEqual(res["redirect_chain"][1]["status_code"], 200)

    # -------------------------------------------------------------------------
    # F. External URL has Content-Type: application/pdf -> captured
    # -------------------------------------------------------------------------
    async def test_case_f_external_url_content_type_pdf(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/manual.pdf"
        mock_response.headers = {"content-type": "application/pdf"}
        mock_response.history = []

        mock_client = AsyncMock()
        mock_client.head.return_value = mock_response

        res = await check_single_link(mock_client, "https://example.com/manual.pdf")
        self.assertEqual(res["content_type"], "application/pdf")
        self.assertEqual(res["status"], "200 OK")

    # -------------------------------------------------------------------------
    # G. External URL timeout -> Timeout
    # -------------------------------------------------------------------------
    async def test_case_g_external_url_timeout(self):
        mock_client = AsyncMock()
        mock_client.head.side_effect = httpx.TimeoutException("Read timed out")

        res = await check_single_link(mock_client, "https://slow-server.org/api")
        self.assertEqual(res["status"], "Timeout")
        self.assertEqual(res["status_code"], 0)
        self.assertTrue(res["is_broken"])
        self.assertEqual(res["error_type"], "timeout")

    # -------------------------------------------------------------------------
    # H. DNS failure -> DNS Error
    # -------------------------------------------------------------------------
    async def test_case_h_dns_failure(self):
        mock_client = AsyncMock()
        mock_client.head.side_effect = httpx.ConnectError("getaddrinfo failed: nodename nor servname provided")

        res = await check_single_link(mock_client, "https://non-existent-domain-xyz99.org")
        self.assertEqual(res["status"], "DNS Error")
        self.assertTrue(res["is_broken"])
        self.assertEqual(res["error_type"], "dns_error")

    # -------------------------------------------------------------------------
    # I. URL not checked -> Not Checked (NO FAKE ACTIVE FALLBACK)
    # -------------------------------------------------------------------------
    def test_case_i_url_not_checked_never_defaults_to_active(self):
        artifacts = {
            "external_links": [
                {
                    "source_url": "https://example.com/blog",
                    "destination_url": "https://unverified-third-party.com",
                    "anchor_text": "Unchecked Link",
                    "rel": "nofollow"
                }
            ]
        }

        dataset = CrawlDatasetService.get_external_links_dataset(artifacts)
        self.assertEqual(len(dataset), 1)
        row = dataset[0]
        self.assertEqual(row["status"], "Not Checked", "Unverified external link must NOT default to 'Active'")
        self.assertEqual(row["content_type"], "Not Checked")
        self.assertNotIn("Active", row["status"])

    # -------------------------------------------------------------------------
    # J. Internal link grouping -> unique source pages count separate from occurrences
    # -------------------------------------------------------------------------
    def test_case_j_internal_link_grouping_separate_counts(self):
        artifacts = {
            "internal_links": [
                {"source_url": "https://example.com/page-1", "destination_url": "https://example.com/features", "anchor_text": "Features #1"},
                {"source_url": "https://example.com/page-1", "destination_url": "https://example.com/features", "anchor_text": "Features #2"},
                {"source_url": "https://example.com/page-1", "destination_url": "https://example.com/features", "anchor_text": "Features #3"},
                {"source_url": "https://example.com/page-2", "destination_url": "https://example.com/features", "anchor_text": "Features #4"}
            ],
            "pages": [
                {"url": "https://example.com/features", "status_code": 200, "content_type": "text/html"}
            ]
        }

        dataset = CrawlDatasetService.get_internal_links_dataset(artifacts)
        self.assertEqual(len(dataset), 1)
        row = dataset[0]
        self.assertEqual(row["source_pages"], 2, "Page 1 and Page 2 link to features")
        self.assertEqual(row["occurrences"], 4, "Total 4 link occurrences")
        self.assertEqual(row["status"], "200 OK")

    # -------------------------------------------------------------------------
    # K. Link context -> nearest heading, paragraph, sentence, context, snippet preserved
    # -------------------------------------------------------------------------
    def test_case_k_link_context_preserved_in_occurrences(self):
        artifacts = {
            "external_links": [
                {
                    "source_url": "https://example.com/services",
                    "destination_url": "https://partner.com/tool",
                    "anchor_text": "Analytics Engine",
                    "rel": "nofollow sponsored",
                    "source_section": "main_content",
                    "nearest_heading": "Advanced Analytics Integration",
                    "heading_level": "h2",
                    "paragraph_index": 4,
                    "sentence_index": 2,
                    "link_index": 1,
                    "context_before": "For enterprise reporting, we integrate with",
                    "context_text": "Analytics Engine",
                    "context_after": "to provide real-time dashboards.",
                    "html_snippet": '<a href="https://partner.com/tool" rel="nofollow sponsored">Analytics Engine</a>'
                }
            ]
        }

        dataset = CrawlDatasetService.get_external_links_dataset(artifacts)
        self.assertEqual(len(dataset), 1)
        row = dataset[0]
        self.assertEqual(len(row["occurrences_list"]), 1)
        
        occ = row["occurrences_list"][0]
        self.assertEqual(occ["nearest_heading"], "Advanced Analytics Integration")
        self.assertEqual(occ["heading_level"], "h2")
        self.assertEqual(occ["paragraph_index"], 4)
        self.assertEqual(occ["sentence_index"], 2)
        self.assertEqual(occ["context_before"], "For enterprise reporting, we integrate with")
        self.assertEqual(occ["context_text"], "Analytics Engine")
        self.assertEqual(occ["context_after"], "to provide real-time dashboards.")
        self.assertIn('<a href="https://partner.com/tool"', occ["html_snippet"])

    # -------------------------------------------------------------------------
    # L. Crawl isolation -> Crawl A data never appears in Crawl B
    # -------------------------------------------------------------------------
    def test_case_l_crawl_snapshot_isolation(self):
        crawl_a = {
            "external_links": [
                {"source_url": "https://site-a.com", "destination_url": "https://ext-a.org", "anchor_text": "Link A"}
            ],
            "timestamp": "2026-09-01T00:00:00"
        }
        crawl_b = {
            "external_links": [
                {"source_url": "https://site-b.com", "destination_url": "https://ext-b.org", "anchor_text": "Link B"}
            ],
            "timestamp": "2026-09-02T00:00:00"
        }

        dataset_a = CrawlDatasetService.get_external_links_dataset(crawl_a)
        dataset_b = CrawlDatasetService.get_external_links_dataset(crawl_b)

        self.assertEqual(dataset_a[0]["destination_url"], "https://ext-a.org")
        self.assertEqual(dataset_b[0]["destination_url"], "https://ext-b.org")
        self.assertNotEqual(dataset_a[0]["destination_url"], dataset_b[0]["destination_url"])

    # -------------------------------------------------------------------------
    # M. Orphan normalization -> equivalent normalized URLs treated consistently
    # -------------------------------------------------------------------------
    def test_case_m_orphan_normalization_consistency(self):
        pages = [
            {"url": "https://example.com/", "crawl_depth": 0},
            {"url": "https://example.com/blog", "crawl_depth": 1}
        ]
        # Link references blog with trailing slash, crawled page has no trailing slash
        internal_links = [
            {"source_url": "https://example.com/", "target_url": "https://example.com/blog/"}
        ]

        graph = build_internal_link_graph(pages, internal_links, seed_url="https://example.com/")
        orphans = graph.get("orphan_pages", [])
        
        self.assertEqual(len(orphans), 0, "Page should not be marked orphan due to trailing slash mismatch")
        self.assertEqual(graph["page_metrics"][1]["incoming_internal_links"], 1)

    # -------------------------------------------------------------------------
    # N. Broken links grouping -> distinguishes internal vs external broken links
    # -------------------------------------------------------------------------
    def test_case_n_broken_links_grouping_distinguishes_scope(self):
        artifacts = {
            "broken_links": [
                {
                    "source": "https://example.com/page-1",
                    "target": "https://example.com/missing-internal",
                    "link_type": "internal",
                    "status_code": 404,
                    "anchor_text": "Broken Page"
                },
                {
                    "source": "https://example.com/page-2",
                    "target": "https://example.com/missing-internal",
                    "link_type": "internal",
                    "status_code": 404,
                    "anchor_text": "Dead Link"
                },
                {
                    "source": "https://example.com/page-3",
                    "target": "https://external-vendor.com/deleted-doc",
                    "link_type": "external",
                    "status_code": 410,
                    "anchor_text": "Vendor Doc"
                }
            ]
        }

        dataset = CrawlDatasetService.get_broken_links_dataset(artifacts)
        self.assertEqual(len(dataset), 2, "2 unique broken target destinations")

        internal_row = next(r for r in dataset if "missing-internal" in r["target_url"])
        external_row = next(r for r in dataset if "external-vendor" in r["target_url"])

        self.assertEqual(internal_row["link_scope"], "Internal Broken Link")
        self.assertEqual(internal_row["source_pages"], 2)
        self.assertEqual(internal_row["occurrences"], 2)

        self.assertEqual(external_row["link_scope"], "External Broken Link")
        self.assertEqual(external_row["source_pages"], 1)
        self.assertEqual(external_row["occurrences"], 1)

    # -------------------------------------------------------------------------
    # Comprehensive Section 26 Test Suite (TEST 1 to TEST 14)
    # -------------------------------------------------------------------------
    def test_section_26_all_cases(self):
        # TEST 1: One external destination appears on 20 different pages -> 1 row, No. Pages = 20
        art1 = {
            "external_links": [
                {"source_url": f"https://example.com/p{i}", "destination_url": "https://external.org/service", "status": "200 OK", "content_type": "text/html"}
                for i in range(20)
            ]
        }
        res1 = CrawlDatasetService.get_external_links_dataset(art1)
        self.assertEqual(len(res1), 1)
        self.assertEqual(res1[0]["source_pages"], 20)
        self.assertEqual(res1[0]["occurrences"], 20)

        # TEST 2: One destination appears 5 times on one page -> 1 row, No. Pages = 1, Total occurrences = 5
        art2 = {
            "external_links": [
                {"source_url": "https://example.com/page-x", "destination_url": "https://vendor.com/docs", "anchor_text": f"Doc {i}"}
                for i in range(5)
            ]
        }
        res2 = CrawlDatasetService.get_external_links_dataset(art2)
        self.assertEqual(len(res2), 1)
        self.assertEqual(res2[0]["source_pages"], 1)
        self.assertEqual(res2[0]["occurrences"], 5)

        # TEST 3: Destination appears 3 times on Page A and 2 times on Page B -> No. Pages = 2, Total occurrences = 5
        art3 = {
            "external_links": [
                {"source_url": "https://example.com/page-a", "destination_url": "https://target.com/item"}
                for _ in range(3)
            ] + [
                {"source_url": "https://example.com/page-b", "destination_url": "https://target.com/item"}
                for _ in range(2)
            ]
        }
        res3 = CrawlDatasetService.get_external_links_dataset(art3)
        self.assertEqual(len(res3), 1)
        self.assertEqual(res3[0]["source_pages"], 2)
        self.assertEqual(res3[0]["occurrences"], 5)

        # TEST 6: External destination has not been checked -> Status = Not Checked, NOT Active
        art6 = {
            "external_links": [
                {"source_url": "https://example.com/p1", "destination_url": "https://unverified.com"}
            ]
        }
        res6 = CrawlDatasetService.get_external_links_dataset(art6)
        self.assertEqual(res6[0]["status"], "Not Checked")
        self.assertNotIn("Active", res6[0]["status"])

        # TEST 7: Destination Content-Type = text/html -> Type = HTML
        art7 = {
            "external_links": [
                {"source_url": "https://example.com/p1", "destination_url": "https://html-doc.com", "content_type": "text/html; charset=utf-8"}
            ]
        }
        res7 = CrawlDatasetService.get_external_links_dataset(art7)
        self.assertEqual(res7[0]["type"], "HTML")

        # TEST 8: Destination Content-Type = application/pdf -> Type = PDF
        art8 = {
            "external_links": [
                {"source_url": "https://example.com/p1", "destination_url": "https://pdf-doc.com/brochure.pdf", "content_type": "application/pdf"}
            ]
        }
        res8 = CrawlDatasetService.get_external_links_dataset(art8)
        self.assertEqual(res8[0]["type"], "PDF")

        # TEST 9: Inspect evidence fields -> Source Page, Target Content Type, Anchor Text, DOM & Page Location, etc.
        art9 = {
            "external_links": [
                {
                    "source_url": "https://example.com/services",
                    "destination_url": "https://partner.com/tool",
                    "anchor_text": "Analytics Tool",
                    "content_type": "text/html",
                    "nearest_heading": "Integration Options",
                    "paragraph_index": 3,
                    "sentence_index": 1,
                    "context_before": "Check out our",
                    "context_text": "Analytics Tool",
                    "context_after": "for deeper insights.",
                    "html_snippet": '<a href="https://partner.com/tool">Analytics Tool</a>'
                }
            ]
        }
        res9 = CrawlDatasetService.get_external_links_dataset(art9)
        occ = res9[0]["occurrences_list"][0]
        self.assertEqual(occ["source_url"], "https://example.com/services")
        self.assertEqual(occ["anchor_text"], "Analytics Tool")
        self.assertEqual(occ["content_type"], "text/html")
        self.assertEqual(occ["nearest_heading"], "Integration Options")
        self.assertEqual(occ["paragraph_index"], 3)
        self.assertEqual(occ["sentence_index"], 1)
        self.assertEqual(occ["context_before"], "Check out our")
        self.assertEqual(occ["context_text"], "Analytics Tool")
        self.assertEqual(occ["context_after"], "for deeper insights.")
        self.assertEqual(occ["html_snippet"], '<a href="https://partner.com/tool">Analytics Tool</a>')

        # TEST 10: Broken destination appears on 15 source pages -> 1 row, No. Pages = 15
        art10 = {
            "broken_links": [
                {"source": f"https://example.com/page-{i}", "target": "https://uisdigital.com/old-page", "status_code": 404, "link_type": "internal"}
                for i in range(15)
            ]
        }
        res10 = CrawlDatasetService.get_broken_links_dataset(art10)
        self.assertEqual(len(res10), 1)
        self.assertEqual(res10[0]["source_pages"], 15)
        self.assertEqual(res10[0]["occurrences"], 15)

        # TEST 11: Broken destination has multiple occurrences -> Inspect shows all occurrences
        art11 = {
            "broken_links": [
                {"source": "https://example.com/p1", "target": "https://example.com/dead", "status_code": 404, "anchor_text": "Dead 1"},
                {"source": "https://example.com/p1", "target": "https://example.com/dead", "status_code": 404, "anchor_text": "Dead 2"},
                {"source": "https://example.com/p2", "target": "https://example.com/dead", "status_code": 404, "anchor_text": "Dead 3"}
            ]
        }
        res11 = CrawlDatasetService.get_broken_links_dataset(art11)
        self.assertEqual(len(res11), 1)
        self.assertEqual(res11[0]["source_pages"], 2)
        self.assertEqual(res11[0]["occurrences"], 3)
        self.assertEqual(len(res11[0]["occurrences_list"]), 3)

        # TEST 12: No broken links -> empty list
        art12 = {"broken_links": []}
        self.assertEqual(CrawlDatasetService.get_broken_links_dataset(art12), [])

        # TEST 13: No external links -> empty list
        art13 = {"external_links": []}
        self.assertEqual(CrawlDatasetService.get_external_links_dataset(art13), [])

        # TEST 14: Different rel values for same destination -> rel summary is "Mixed", exact rel in occurrences
        art14 = {
            "external_links": [
                {"source_url": "https://example.com/p1", "destination_url": "https://mixed-rel.org", "rel": "nofollow"},
                {"source_url": "https://example.com/p2", "destination_url": "https://mixed-rel.org", "rel": "sponsored"},
                {"source_url": "https://example.com/p3", "destination_url": "https://mixed-rel.org", "rel": ""}
            ]
        }
        res14 = CrawlDatasetService.get_external_links_dataset(art14)
        self.assertEqual(len(res14), 1)
        self.assertEqual(res14[0]["rel"], "Mixed")
        self.assertEqual(res14[0]["occurrences_list"][0]["rel"], "nofollow")
        self.assertEqual(res14[0]["occurrences_list"][1]["rel"], "sponsored")
        self.assertEqual(res14[0]["occurrences_list"][2]["rel"], "")


if __name__ == "__main__":
    unittest.main()
