import io
import csv
import zipfile
from datetime import datetime
from typing import Dict, Any, List, Optional

from app.config.utils import sanitize_csv_cell, get_sanitized_domain

class CSVExportService:
    @staticmethod
    def generate_csv_string(headers: List[str], rows: List[List[Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([sanitize_csv_cell(h) for h in headers])
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
            ["Total Crawled Pages", metadata.get("pages_crawled", len(pages)), "Website Scan"],
            ["Total Technical Issues", metadata.get("total_issues", len(issues)), "Website Scan"],
            ["Critical Issues", metadata.get("critical_issues", 0), "Website Scan"],
            ["Warnings", metadata.get("warning_issues", 0), "Website Scan"],
            ["Notices", metadata.get("notice_issues", 0), "Website Scan"],
            ["Content Keywords Extracted", len(keywords), "Website Scan / Content NLP Engine"],
            ["Crawl Status", metadata.get("status", "Completed"), "Website Scan"],
            ["Crawl Timestamp", metadata.get("timestamp", "N/A"), "Website Scan"],
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
                "Can Search Engines Find This Page?" if p.get("status_code") == 200 else "Blocked / Error Page",
                p.get("robots_meta", "Not collected"),
                p.get("fetch_status", "SUCCESS"),
                "Website Scan"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_keywords_csv(keywords: List[Dict[str, Any]]) -> str:
        headers = ["Search Term / Keyword", "Source Page", "Category / Topic", "Content Frequency", "Pages Found", "Google Ranking Position", "Data Source"]
        rows = []
        for k in keywords:
            rank_val = f"#{k.get('position')}" if k.get("position") else "Not available (Connect Search Data)"
            rows.append([
                k.get("keyword", ""),
                k.get("target_url") or k.get("source_page") or "Crawled Website Content",
                k.get("type") or k.get("category") or "Content Keyword",
                k.get("frequency") or k.get("search_volume") or 1,
                k.get("pages_found", 1),
                rank_val,
                k.get("provenance") or "Website Scan / Content NLP Engine"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_rankings_csv(rankings: List[Dict[str, Any]]) -> str:
        headers = ["Search Term / Keyword", "Target URL", "Google Position", "Previous Position", "Position Change", "Search Engine", "Device", "Location", "Ranking Date", "Data Source"]
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
                    r.get("provenance", "Google Search Data")
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_inbound_backlinks_csv(backlinks: List[Dict[str, Any]]) -> str:
        headers = ["Referring Website Domain", "Referring URL", "Target Page URL", "Clickable Link Text", "Link Type", "Domain Authority", "First Seen", "Data Source"]
        rows = []
        if not backlinks:
            rows.append([
                "No links from other websites dataset connected", "N/A", "N/A", "N/A", "N/A", "N/A", "N/A", "Unavailable"
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
        headers = ["Source Page URL", "Destination Domain", "Destination URL", "Clickable Link Text", "Link Type", "HTTP Status", "Discovered Timestamp", "Data Source"]
        rows = []
        for l in outbound_links:
            rows.append([
                l.get("source_url") or l.get("source") or "",
                l.get("destination_domain") or "",
                l.get("destination_url") or l.get("target") or "",
                l.get("anchor_text") or "[External Link]",
                l.get("link_type") or l.get("rel") or "Follow",
                l.get("status_code", "200"),
                l.get("first_discovered", "Website Scan"),
                "Website Scan — Outbound Links"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_internal_links_csv(internal_links: List[Dict[str, Any]]) -> str:
        headers = ["Source Page URL", "Destination Page URL", "Clickable Link Text", "Link Type", "Status Code", "Data Source"]
        rows = []
        for l in internal_links:
            rows.append([
                l.get("source", ""),
                l.get("target", ""),
                l.get("anchor_text", "(No text)"),
                l.get("link_type", "Internal"),
                l.get("status_code", 200),
                "Website Scan"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_competitors_csv(competitors: List[Dict[str, Any]]) -> str:
        headers = ["Competitor Name", "Domain", "Website URL", "Location", "Geographic Level", "Relevance Match %", "Overlapping Keywords", "SERP Appearances", "Primary Competitor", "Status", "Discovery Source", "Data Source"]
        rows = []
        if not competitors:
            rows.append([
                "No competitor data yet", "N/A", "N/A", "Local Market", "City", "0%", "0", "0", "False", "None", "User Specified", "Unavailable"
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
        headers = ["Severity / Priority", "Category", "Problem Finding", "Affected Page URL", "What Was Found / Evidence", "Recommended Action", "Data Source", "Generated By", "Scan Date"]
        rows = []
        for i in issues:
            rows.append([
                i.get("severity", "Warning"),
                i.get("issue_type") or i.get("category") or "Technical",
                i.get("title") or f"Fix {i.get('issue_type', 'SEO Issue')}",
                i.get("affected_url", ""),
                i.get("details") or i.get("evidence") or "Issue detected during scan",
                i.get("recommendation") or "Review and fix affected URL",
                "Website Scan",
                "Audit Rule Engine",
                "Latest Scan"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_opportunities_csv(opportunities: List[Dict[str, Any]]) -> str:
        headers = ["Priority Level", "Category", "Recommended Action Title", "Why It Matters", "Affected URLs", "What Was Found / Evidence", "Recommended Action", "Data Source", "Generated By", "Scan Date"]
        rows = []
        if not opportunities:
            rows.append(["Medium", "Audit", "Perform regular website health checks", "Keep website content and links updated.", "All Pages", "Scan completed cleanly", "Run periodic scans", "Website Scan", "Opportunity Engine", "Latest Scan"])
        else:
            for o in opportunities:
                rows.append([
                    o.get("priority_level") or o.get("priority") or "Medium",
                    o.get("category", "General"),
                    o.get("title", ""),
                    o.get("impact") or o.get("description", ""),
                    ", ".join(o.get("affected_urls", [])) if isinstance(o.get("affected_urls"), list) else str(o.get("affected_urls", "")),
                    o.get("evidence", ""),
                    o.get("recommendation", ""),
                    "Website Scan",
                    "Opportunity Engine",
                    "Latest Scan"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_ai_insights_csv(ai_insights: Dict[str, Any]) -> str:
        headers = ["Priority", "Category", "Finding Title", "Why It Matters / Impact", "Recommended Action", "Affected URLs", "Data Source", "Generated By"]
        rows = []
        findings = ai_insights.get("findings") or ai_insights.get("insights") or []
        if not findings:
            rows.append(["Info", "AI", "AI Analysis Not Generated", "AI analysis has not been generated for this project.", "Run AI analysis when AI provider is connected.", "N/A", "Unavailable", "AI Analyst"])
        else:
            for f in findings:
                rows.append([
                    f.get("severity") or f.get("priority") or "Medium",
                    f.get("category") or "AI Insights",
                    f.get("finding") or f.get("title") or "AI Finding",
                    f.get("impact") or f.get("description") or "",
                    f.get("recommendation") or "",
                    ", ".join(f.get("affected_urls", [])) if isinstance(f.get("affected_urls"), list) else "",
                    "AI Analysis",
                    "AI Assistant Agent"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_crawl_history_csv(crawls: List[Dict[str, Any]]) -> str:
        headers = ["Scan Date & Time", "Target Website URL", "Pages Scanned", "Problems Found", "Scan Status", "Data Source"]
        rows = []
        for cr in crawls:
            rows.append([
                cr.get("timestamp") or cr.get("started_at") or "N/A",
                cr.get("url") or "",
                cr.get("pages_crawled", 0),
                cr.get("issues_found", 0),
                cr.get("status", "Completed"),
                "Website Scan Logs"
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
        audit_pdf_bytes: bytes = None,
        ai_insights: Dict[str, Any] = None
    ) -> bytes:
        safe_domain = get_sanitized_domain(domain)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_date = datetime.now().strftime("%Y-%m-%d")
        crawl_time = metadata.get("timestamp", "N/A")
        ai_data = ai_insights or {}

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            prefix = f"{safe_domain}_SEO_{today_date}"

            # README.txt
            readme_text = f"""================================================================================
COMPLETE SEO PLATFORM DATA EXPORT
================================================================================

Website Domain: {domain}
Project Name: {project_name}
Target URL: {url}
Export Timestamp: {now_str}
Last Scan Snapshot: {crawl_time}
Total Pages Scanned: {len(pages)}
Total Problems Found: {len(issues)}

INCLUDED DATASETS & DATA PROVENANCE:
--------------------------------------------------------------------------------
1. 01-seo-audit/          : Website Health Report PDF & Executive Summary (Website Scan)
2. 02-pages/              : Pages Discovered Inventory (Website Scan)
3. 03-keywords/           : Target Keywords & Content Frequencies (Website Scan / Content NLP Engine)
4. 04-rankings/           : Search Rankings ({'Active Google Search Data' if rankings else 'Unavailable / Not Configured'})
5. 05-backlinks/          : Links From Other Websites ({'Active Backlink Dataset' if inbound_backlinks else 'Unavailable / Not Configured'})
6. 06-outbound-links/     : Discovered Links To Other Websites (Website Scan — Outbound Links)
7. 07-internal-links/     : Links Between Your Pages (Website Scan)
8. 08-competitors/        : Market Competitors ({'Configured' if competitors else 'None Configured'})
9. 09-technical-seo/      : Technical Health Checks & Evidence (Website Scan)
10. 10-opportunities/     : Prioritized Recommended Actions (Opportunity Engine)
11. 11-ai-insights/       : AI Insights & Strategic Analysis ({'Active AI Insights' if ai_data.get('findings') else 'AI analysis not generated'})
12. 12-crawl-history/     : Website Scan Audit Logs (Scan History)

DATA DICTIONARY & COMPLIANCE RULES:
--------------------------------------------------------------------------------
- Website Scan           : Verified content collected directly from target website URLs.
- Links To Other Websites: External links on your website pointing TO external domains.
- Links From Other Sites : Backlinks on external domains pointing TO your website.
- Content Frequency      : Occurrence count of terms in scanned HTML. Does NOT equal search rankings.
- Unavailable            : Indicates a dataset requiring a connected data source or imported CSV.

================================================================================
Generated by SEO Intelligence Platform
================================================================================
"""
            zf.writestr(f"{prefix}/README.txt", readme_text)

            # 01-seo-audit/
            if audit_pdf_bytes:
                zf.writestr(f"{prefix}/01-seo-audit/{safe_domain}_SEO-Report_{today_date}.pdf", audit_pdf_bytes)
            zf.writestr(f"{prefix}/01-seo-audit/{safe_domain}_Audit-Summary_{today_date}.csv", CSVExportService.generate_project_summary_csv(project_name, domain, url, metadata, pages, keywords, issues))

            # 02-pages/
            zf.writestr(f"{prefix}/02-pages/{safe_domain}_Pages-Inventory_{today_date}.csv", CSVExportService.generate_pages_csv(pages))

            # 03-keywords/
            zf.writestr(f"{prefix}/03-keywords/{safe_domain}_Keyword-Topics_{today_date}.csv", CSVExportService.generate_keywords_csv(keywords))

            # 04-rankings/ (if data exists)
            if rankings:
                zf.writestr(f"{prefix}/04-rankings/{safe_domain}_Search-Rankings_{today_date}.csv", CSVExportService.generate_rankings_csv(rankings))

            # 05-backlinks/ (if data exists)
            if inbound_backlinks:
                zf.writestr(f"{prefix}/05-backlinks/{safe_domain}_Links-From-Other-Websites_{today_date}.csv", CSVExportService.generate_inbound_backlinks_csv(inbound_backlinks))

            # 06-outbound-links/
            zf.writestr(f"{prefix}/06-outbound-links/{safe_domain}_Links-To-Other-Websites_{today_date}.csv", CSVExportService.generate_outbound_links_csv(outbound_links))

            # 07-internal-links/
            zf.writestr(f"{prefix}/07-internal-links/{safe_domain}_Page-Links_{today_date}.csv", CSVExportService.generate_internal_links_csv(internal_links))

            # 08-competitors/ (if data exists)
            if competitors:
                zf.writestr(f"{prefix}/08-competitors/{safe_domain}_Competitors_{today_date}.csv", CSVExportService.generate_competitors_csv(competitors))

            # 09-technical-seo/
            zf.writestr(f"{prefix}/09-technical-seo/{safe_domain}_Technical-Issues_{today_date}.csv", CSVExportService.generate_technical_issues_csv(issues))

            # 10-opportunities/
            zf.writestr(f"{prefix}/10-opportunities/{safe_domain}_Recommended-Actions_{today_date}.csv", CSVExportService.generate_opportunities_csv(opportunities))

            # 11-ai-insights/ (if data exists)
            if ai_data and (ai_data.get("findings") or ai_data.get("insights")):
                zf.writestr(f"{prefix}/11-ai-insights/{safe_domain}_AI-Insights_{today_date}.csv", CSVExportService.generate_ai_insights_csv(ai_data))

            # 12-crawl-history/
            if crawls:
                zf.writestr(f"{prefix}/12-crawl-history/{safe_domain}_Scan-History_{today_date}.csv", CSVExportService.generate_crawl_history_csv(crawls))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
