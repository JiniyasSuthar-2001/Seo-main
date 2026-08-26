import io
import csv
import zipfile
from datetime import datetime
from typing import Dict, Any, List

from app.config.utils import sanitize_csv_cell, get_sanitized_domain

class CSVExportService:
    @staticmethod
    def generate_csv_string(headers: List[str], rows: List[List[Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow([sanitize_csv_cell(val) for val in row])
        return output.getvalue()

    @staticmethod
    def generate_project_summary_csv(project_name: str, domain: str, url: str, metadata: Dict[str, Any], pages: List[Dict[str, Any]], keywords: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> str:
        headers = ["Metadata Field", "Value", "Data Source Provenance"]
        rows = [
            ["Project Name", project_name, "User Metadata"],
            ["Website Domain", domain, "User Metadata"],
            ["Target URL", url, "User Metadata"],
            ["Total Crawled Pages", metadata.get("pages_crawled", len(pages)), "Crawled Data"],
            ["Total Technical Issues", metadata.get("total_issues", len(issues)), "Crawled Data"],
            ["Critical Issues", metadata.get("critical_issues", 0), "Crawled Data"],
            ["Warnings", metadata.get("warning_issues", 0), "Crawled Data"],
            ["Notices", metadata.get("notice_issues", 0), "Crawled Data"],
            ["Content Keywords Extracted", len(keywords), "Crawled Data / NLP Engine"],
            ["Crawl Status", metadata.get("status", "Completed"), "Crawled Data"],
            ["Crawl Timestamp", metadata.get("timestamp", "N/A"), "Crawled Data"],
            ["Export Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "System Export"]
        ]
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_pages_csv(pages: List[Dict[str, Any]]) -> str:
        headers = [
            "URL", "Status Code", "Title Tag", "Meta Description", "Canonical URL", 
            "Word Count", "H1 Heading", "H2 Count", "Internal Links Count", 
            "External Links Count", "Indexability", "Robots Directives", "Fetch Status", "Data Source"
        ]
        rows = []
        for p in pages:
            rows.append([
                p.get("url", ""),
                p.get("status_code", 200),
                p.get("title", "Not collected"),
                p.get("meta_description", "Not collected"),
                p.get("canonical", "Not collected"),
                p.get("word_count", 0),
                p.get("h1", "Not collected"),
                p.get("h2_count", len(p.get("h2", [])) if isinstance(p.get("h2"), list) else 0),
                p.get("internal_links_count", 0),
                p.get("external_links_count", 0),
                p.get("indexable", "Indexable" if p.get("status_code") == 200 else "Non-Indexable"),
                p.get("robots_meta", "Not collected"),
                p.get("fetch_status", "SUCCESS"),
                "Crawled Data"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_keywords_csv(keywords: List[Dict[str, Any]]) -> str:
        headers = ["Topic / Keyword", "Source Page", "Category / Type", "Frequency", "Pages Found", "Google Ranking Position", "Data Provenance"]
        rows = []
        for k in keywords:
            rank_val = k.get("position") if k.get("has_serp_ranking") else "Not available (Requires SERP Provider)"
            rows.append([
                k.get("keyword", ""),
                k.get("target_url") or k.get("source_page") or "Crawled Website Content",
                k.get("type") or k.get("category") or "Content Keyword",
                k.get("frequency") or k.get("search_volume") or 1,
                k.get("pages_found", 1),
                rank_val,
                k.get("provenance") or "Crawled Data / Content NLP Engine"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_rankings_csv(rankings: List[Dict[str, Any]]) -> str:
        headers = ["Keyword", "Target URL", "Google Position", "Previous Position", "Change", "Search Engine", "Device", "Location", "Ranking Date", "Data Provenance"]
        rows = []
        if not rankings:
            rows.append([
                "No ranking dataset configured", "N/A", "Not available", "N/A", "0", "Google", "Desktop", "Unknown", "N/A", "Unavailable"
            ])
        else:
            for r in rankings:
                rows.append([
                    r.get("keyword", ""),
                    r.get("url", ""),
                    r.get("position", "Not available"),
                    r.get("previous_position", "N/A"),
                    r.get("change", 0),
                    r.get("engine", "Google"),
                    r.get("device", "Desktop"),
                    r.get("location") or "Unknown",
                    r.get("date", ""),
                    r.get("provenance", "SERP Provider")
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_inbound_backlinks_csv(backlinks: List[Dict[str, Any]]) -> str:
        headers = ["Source Domain", "Source URL", "Target URL", "Anchor Text", "Link Type", "Domain Authority", "First Seen", "Data Provenance"]
        rows = []
        if not backlinks:
            rows.append([
                "No inbound backlink dataset connected", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "Unavailable"
            ])
        else:
            for b in backlinks:
                rows.append([
                    b.get("source_domain", ""),
                    b.get("source_url", ""),
                    b.get("target_url", ""),
                    b.get("anchor_text", ""),
                    b.get("link_type", "Follow"),
                    b.get("domain_authority", "N/A"),
                    b.get("first_seen", "N/A"),
                    b.get("provenance", "Imported Data")
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_outbound_links_csv(outbound_links: List[Dict[str, Any]]) -> str:
        headers = ["Source Page URL", "Destination Domain", "Destination URL", "Anchor Text", "Rel Attributes / Link Type", "HTTP Status", "Discovered Timestamp", "Data Provenance"]
        rows = []
        for l in outbound_links:
            rows.append([
                l.get("source_url") or l.get("source") or "",
                l.get("destination_domain") or "",
                l.get("destination_url") or l.get("target") or "",
                l.get("anchor_text") or "[External Link]",
                l.get("link_type") or l.get("rel") or "Follow",
                l.get("status_code", "Not checked"),
                l.get("first_discovered", "Not collected"),
                "Crawled Data — Outbound"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_internal_links_csv(internal_links: List[Dict[str, Any]]) -> str:
        headers = ["Source Page URL", "Target Page URL", "Anchor Text", "Link Type", "Status Code", "Data Provenance"]
        rows = []
        for l in internal_links:
            rows.append([
                l.get("source", ""),
                l.get("target", ""),
                l.get("anchor_text", "(No text)"),
                l.get("link_type", "Internal"),
                l.get("status_code", 200),
                "Crawled Data"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_competitors_csv(competitors: List[Dict[str, Any]]) -> str:
        headers = ["Competitor Name", "Domain", "Website URL", "Location", "Geographic Level", "Relevance Match %", "Overlapping Keywords", "SERP Appearances", "Primary Competitor", "Status", "Discovery Source", "Data Provenance"]
        rows = []
        if not competitors:
            rows.append([
                "No competitors configured", "N/A", "N/A", "Local Market", "City", "0%", "0", "0", "False", "None", "User Specified", "Unavailable"
            ])
        else:
            for c in competitors:
                rows.append([
                    c.get("name", ""),
                    c.get("domain", ""),
                    c.get("url", ""),
                    c.get("location", "Local Market"),
                    c.get("geographic_level", "City"),
                    f"{c.get('relevance_score', 0)}%",
                    c.get("keyword_overlap", 0),
                    c.get("search_appearances", 0),
                    str(c.get("is_primary", False)),
                    c.get("status", "Confirmed"),
                    c.get("discovery_source", "User Specified"),
                    "User Specified / SERP Discovery"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_technical_issues_csv(issues: List[Dict[str, Any]]) -> str:
        headers = ["Severity", "Issue Type", "Affected URL", "Details / Evidence", "Recommended Action", "Data Provenance"]
        rows = []
        for i in issues:
            rows.append([
                i.get("severity", "Notice"),
                i.get("issue_type", "General"),
                i.get("affected_url", ""),
                i.get("details", ""),
                i.get("recommendation") or "Review and fix affected URL structure",
                "Crawled Data Engine"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_opportunities_csv(opportunities: List[Dict[str, Any]]) -> str:
        headers = ["Priority", "Category", "Opportunity Title", "Description", "Affected URLs", "Data Provenance"]
        rows = []
        if not opportunities:
            rows.append(["Medium", "Audit", "Perform regular website audits", "Keep website software and content updated.", "All Pages", "Crawled Data Engine"])
        else:
            for o in opportunities:
                rows.append([
                    o.get("priority", "Medium"),
                    o.get("category", "General"),
                    o.get("title", ""),
                    o.get("description", ""),
                    ", ".join(o.get("affected_urls", [])) if isinstance(o.get("affected_urls"), list) else str(o.get("affected_urls", "")),
                    o.get("provenance", "Crawled Data Engine")
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_crawl_history_csv(crawls: List[Dict[str, Any]]) -> str:
        headers = ["Crawl Date & Time", "Target Start URL", "Pages Crawled", "Issues Discovered", "Crawl Status", "Data Provenance"]
        rows = []
        for cr in crawls:
            rows.append([
                cr.get("timestamp") or cr.get("started_at") or "N/A",
                cr.get("url") or "",
                cr.get("pages_crawled", 0),
                cr.get("issues_found", 0),
                cr.get("status", "Completed"),
                "Crawl Engine History Logs"
            ])
        return CSVExportService.generate_csv_string(headers, rows)


class ZIPExportService:
    @staticmethod
    def generate_complete_zip_export(
        project_name: str,
        domain: str,
        url: str,
        metadata: Dict[str, Any],
        pages: List[Dict[str, Any]],
        keywords: List[Dict[str, Any]],
        rankings: List[Dict[str, Any]],
        inbound_backlinks: List[Dict[str, Any]],
        outbound_links: List[Dict[str, Any]],
        internal_links: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]],
        crawls: List[Dict[str, Any]],
        audit_pdf_bytes: bytes = None
    ) -> bytes:
        safe_domain = get_sanitized_domain(domain)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        crawl_time = metadata.get("timestamp", "N/A")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            # 01-seo-audit/
            if audit_pdf_bytes:
                zf.writestr(f"01-seo-audit/{safe_domain}_audit-report.pdf", audit_pdf_bytes)
            zf.writestr(f"01-seo-audit/{safe_domain}_audit-summary.csv", CSVExportService.generate_project_summary_csv(project_name, domain, url, metadata, pages, keywords, issues))

            # 02-pages/
            zf.writestr(f"02-pages/{safe_domain}_pages-inventory.csv", CSVExportService.generate_pages_csv(pages))

            # 03-keywords/
            zf.writestr(f"03-keywords/{safe_domain}_keywords-topics.csv", CSVExportService.generate_keywords_csv(keywords))

            # 04-rankings/
            zf.writestr(f"04-rankings/{safe_domain}_serp-rankings.csv", CSVExportService.generate_rankings_csv(rankings))

            # 05-backlinks/
            zf.writestr(f"05-backlinks/{safe_domain}_inbound-backlinks.csv", CSVExportService.generate_inbound_backlinks_csv(inbound_backlinks))

            # 06-outbound-links/
            zf.writestr(f"06-outbound-links/{safe_domain}_outbound-links.csv", CSVExportService.generate_outbound_links_csv(outbound_links))

            # 07-internal-links/
            zf.writestr(f"07-internal-links/{safe_domain}_internal-links.csv", CSVExportService.generate_internal_links_csv(internal_links))

            # 08-competitors/
            zf.writestr(f"08-competitors/{safe_domain}_competitors.csv", CSVExportService.generate_competitors_csv(competitors))

            # 09-technical-seo/
            zf.writestr(f"09-technical-seo/{safe_domain}_technical-issues.csv", CSVExportService.generate_technical_issues_csv(issues))

            # 10-opportunities/
            zf.writestr(f"10-opportunities/{safe_domain}_seo-opportunities.csv", CSVExportService.generate_opportunities_csv(opportunities))

            # 11-crawl-history/
            zf.writestr(f"11-crawl-history/{safe_domain}_crawl-history.csv", CSVExportService.generate_crawl_history_csv(crawls))

            # README.txt
            readme_text = f"""================================================================================
COMPLETE SEO PLATFORM DATA EXPORT
================================================================================

Website Domain: {domain}
Project Name: {project_name}
Target URL: {url}
Export Timestamp: {now_str}
Last Crawl Snapshot: {crawl_time}
Total Pages Crawled: {len(pages)}
Total Technical Issues: {len(issues)}

INCLUDED DATASETS & DATA PROVENANCE:
--------------------------------------------------------------------------------
1. 01-seo-audit/          : Executive Audit Summary & PDF Report (Crawled Data)
2. 02-pages/              : Crawled Pages Inventory (Crawled Data)
3. 03-keywords/           : Keyword & Topic Content Frequencies (Crawled Data / NLP Engine)
4. 04-rankings/           : Search Engine Rankings ({'Active SERP Provider' if rankings else 'Unavailable / Not Configured'})
5. 05-backlinks/          : Inbound Backlink Dataset ({'Active Dataset' if inbound_backlinks else 'Unavailable / Not Configured'})
6. 06-outbound-links/     : Discovered Outbound External Links (Crawled Data — Outbound)
7. 07-internal-links/     : Internal Link Graph (Crawled Data)
8. 08-competitors/        : Market Competitors ({'Configured' if competitors else 'None Configured'})
9. 09-technical-seo/      : Technical SEO Audit Findings (Crawled Data)
10. 10-opportunities/     : Prioritized SEO Recommendations (Crawled Data Engine)
11. 11-crawl-history/     : Historical Website Crawl Audit Logs (Crawl Logs)

DATA DICTIONARY & COMPLIANCE RULES:
--------------------------------------------------------------------------------
- Crawled Data           : Verified content collected directly from target website URLs.
- Outbound External Links: Links on your website pointing TO external domains.
- Inbound Backlinks      : Links from external domains pointing TO your website.
- Keyword Frequency      : Occurrence count of terms in crawled HTML. Does NOT equal search rankings.
- Unavailable            : Indicates a dataset requiring an external provider or imported CSV.

================================================================================
Generated by SEO Intelligence Platform
================================================================================
"""
            zf.writestr("README.txt", readme_text)

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
