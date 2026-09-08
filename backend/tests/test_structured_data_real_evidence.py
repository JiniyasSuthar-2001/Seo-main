import pytest
from app.services.audit_rules import extract_schema_types, evaluate_site_audit_rules

class TestStructuredDataRealEvidence:
    """
    Tests for real Schema.org JSON-LD extraction, aggregation, and Website Health audit evidence.
    Enforces zero fabrication and supports all common JSON-LD patterns.
    """

    def test_extract_schema_types_standard_dict(self):
        # Pattern A: Single standard JSON-LD object
        data = {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Acme Corp"
        }
        types = extract_schema_types(data)
        assert types == ["Organization"]

    def test_extract_schema_types_graph_structure(self):
        # Pattern C: @graph structure with multiple schema entities
        data = {
            "@context": "https://schema.org",
            "@graph": [
                {"@type": "Organization", "name": "Acme Corp"},
                {"@type": "WebSite", "url": "https://acme.com"},
                {"@type": "BreadcrumbList"}
            ]
        }
        types = extract_schema_types(data)
        assert "Organization" in types
        assert "WebSite" in types
        assert "BreadcrumbList" in types
        assert len(types) == 3

    def test_extract_schema_types_type_array(self):
        # Pattern D: @type as an array of strings
        data = {
            "@context": "https://schema.org",
            "@type": ["Organization", "LocalBusiness"],
            "name": "Acme Local Store"
        }
        types = extract_schema_types(data)
        assert types == ["Organization", "LocalBusiness"]

    def test_extract_schema_types_uri_normalization(self):
        # Pattern: Types with Schema.org URLs or prefixes
        data = [
            {"@type": "https://schema.org/Product"},
            {"@type": "http://schema.org/FAQPage"},
            {"@type": "schema:Service"}
        ]
        types = extract_schema_types(data)
        assert "Product" in types
        assert "FAQPage" in types
        assert "Service" in types

    def test_extract_schema_types_multiple_scripts_and_strings(self):
        # Pattern B: Multiple script blocks containing parsed objects or raw strings
        data = [
            '{"@context": "https://schema.org", "@type": "Article"}',
            {"@type": "Person", "name": "John Doe"},
            {"@graph": [{"@type": "WebPage"}]}
        ]
        types = extract_schema_types(data)
        assert types == ["Article", "Person", "WebPage"]

    def test_extract_schema_types_empty_and_invalid(self):
        assert extract_schema_types([]) == []
        assert extract_schema_types(None) == []
        assert extract_schema_types({}) == []
        assert extract_schema_types({"no_type": "value"}) == []

    def test_audit_rules_structured_data_summary_aggregation(self):
        """
        Tests category-level summary and page counts calculation across crawled pages.
        """
        mock_pages = [
            {
                "url": "https://example.com/",
                "status_code": 200,
                "is_success": True,
                "structured_data": [
                    {"@type": "Organization"},
                    {"@type": "WebSite"}
                ]
            },
            {
                "url": "https://example.com/about",
                "status_code": 200,
                "is_success": True,
                "structured_data": [
                    {"@type": "Organization"},
                    {"@type": "BreadcrumbList"}
                ]
            },
            {
                "url": "https://example.com/services",
                "status_code": 200,
                "is_success": True,
                "structured_data": [
                    {"@type": "Service"},
                    {"@type": "BreadcrumbList"}
                ]
            },
            {
                "url": "https://example.com/contact",
                "status_code": 200,
                "is_success": True,
                "structured_data": [] # Missing schema
            }
        ]

        result = evaluate_site_audit_rules(mock_pages)
        sd_summary = result.get("structured_data_summary")
        assert sd_summary is not None
        assert sd_summary["evaluated"] is True
        assert sd_summary["total_pages_checked"] == 4
        assert sd_summary["total_pages_with_schema"] == 3
        assert sd_summary["total_pages_missing_schema"] == 1

        # Check real page counts:
        # Organization: on / and /about -> 2 pages
        # BreadcrumbList: on /about and /services -> 2 pages
        # WebSite: on / -> 1 page
        # Service: on /services -> 1 page
        types_found = sd_summary["schema_types_found"]
        assert types_found["Organization"] == 2
        assert types_found["BreadcrumbList"] == 2
        assert types_found["WebSite"] == 1
        assert types_found["Service"] == 1
        assert "FAQPage" not in types_found # Never fabricate unpresent types

        # Check page level detail
        pages_detail = sd_summary["pages_detail"]
        assert len(pages_detail) == 4

        home_page = next(p for p in pages_detail if p["url"] == "https://example.com/")
        assert home_page["has_structured_data"] is True
        assert home_page["schema_count"] == 2
        assert home_page["detected_schema_types"] == ["Organization", "WebSite"]

        contact_page = next(p for p in pages_detail if p["url"] == "https://example.com/contact")
        assert contact_page["has_structured_data"] is False
        assert contact_page["schema_count"] == 0
        assert contact_page["detected_schema_types"] == []

        # Verify category breakdown & category table
        sd_category = result["category_breakdown"]["Structured Data"]
        assert sd_category["status"] == "Issues Found" # Because 1 page missed schema
        assert sd_category["notice"] == 1
        assert sd_category["total_pages_with_schema"] == 3
        assert sd_category["total_pages_missing_schema"] == 1

        # Check category table row
        sd_row = next(r for r in result["category_checks_table"] if r["category"] == "Structured Data")
        assert sd_row["structured_data_summary"] == sd_summary
        assert sd_row["schema_types_found"] == types_found

    def test_audit_rules_all_pages_have_schema(self):
        """
        Tests clean pass state when all pages have structured data.
        """
        mock_pages = [
            {
                "url": "https://example.com/",
                "status_code": 200,
                "is_success": True,
                "structured_data": [{"@type": "WebSite"}]
            },
            {
                "url": "https://example.com/blog",
                "status_code": 200,
                "is_success": True,
                "structured_data": [{"@type": "Article"}]
            }
        ]

        result = evaluate_site_audit_rules(mock_pages)
        sd_summary = result.get("structured_data_summary")
        assert sd_summary["total_pages_checked"] == 2
        assert sd_summary["total_pages_with_schema"] == 2
        assert sd_summary["total_pages_missing_schema"] == 0
        assert result["category_breakdown"]["Structured Data"]["status"] == "Passed"

    def test_audit_rules_zero_pages(self):
        """
        Tests un-evaluated empty state.
        """
        result = evaluate_site_audit_rules([])
        sd_summary = result.get("structured_data_summary")
        assert sd_summary["evaluated"] is False
        assert sd_summary["total_pages_checked"] == 0
        assert sd_summary["schema_types_found"] == {}
        assert result["category_breakdown"]["Structured Data"]["status"] == "Not Evaluated"
