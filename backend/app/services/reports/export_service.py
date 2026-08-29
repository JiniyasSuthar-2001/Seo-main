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
        headers = ["Metadata Field", "Value", "Where This Data Came From"]
        rows = [
            ["Project Name", project_name, "User Metadata"],
            ["Website Domain", domain, "User Metadata"],
            ["Target URL", url, "User Metadata"],
            ["Total Crawled Pages", metadata.get("pages_crawled", len(pages)), "Website Scan"],
            ["Total Technical Issues", metadata.get("total_issues", len(issues)), "Website Scan"],
            ["Critical Issues", metadata.get("critical_issues", 0), "Website Scan"],
            ["Warnings", metadata.get("warning_issues", 0), "Website Scan"],
            ["Notices", metadata.get("notice_issues", 0), "Website Scan"],
            ["Content Keywords Extracted", len(keywords), "Website Scan / Content Detection"],
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
            "External Links Count", "Can Search Engines Find This Page?", "Robots Directives", "Fetch Status", "Where This Data Came From"
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
                "Yes (200 OK)" if p.get("status_code") == 200 else "No (Blocked / Error Page)",
                p.get("robots_meta", "Not collected"),
                p.get("fetch_status", "SUCCESS"),
                "Website Scan"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_keywords_csv(keywords: List[Dict[str, Any]]) -> str:
        headers = ["Search Term / Keyword", "Source Page", "Category / Topic", "Content Frequency", "Pages Found", "Google Ranking Position", "Where This Data Came From"]
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
                k.get("provenance") or "Automatic Keyword Detection"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_rankings_csv(rankings: List[Dict[str, Any]]) -> str:
        headers = ["Search Term / Keyword", "Target URL", "Google Position", "Previous Position", "Position Change", "Search Engine", "Device", "Location", "Ranking Date", "Ranking Data Source"]
        rows = []
        if not rankings:
            rows.append([
                "No ranking dataset configured", "N/A", "Not available", "N/A", "0", "Google", "Desktop", "Unknown", "N/A", "Not Connected"
            ])
        else:
            for r in rankings:
                rows.append([
                    r.get("keyword", ""),
                    r.get("url", ""),
                    r.get("position", "N/A"),
                    r.get("previous_position", "N/A"),
                    r.get("change", 0),
                    r.get("engine", "Google"),
                    r.get("device", "Desktop"),
                    r.get("location", "Global"),
                    r.get("checked_at", "N/A"),
                    "Search Console Data"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_inbound_backlinks_csv(backlinks: List[Dict[str, Any]]) -> str:
        headers = ["Source Website URL", "Source Domain", "Target Page URL", "Anchor Text", "Link Type", "Domain Authority", "First Seen Date", "Where This Data Came From"]
        rows = []
        if not backlinks:
            rows.append([
                "No backlink dataset connected", "N/A", "N/A", "N/A", "Follow", "N/A", "N/A", "Not Connected"
            ])
        else:
            for b in backlinks:
                rows.append([
                    b.get("source_url", ""),
                    b.get("source_domain", ""),
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
        headers = ["Source Page URL", "Destination Domain", "Destination URL", "Clickable Link Text", "Link Type", "HTTP Status", "Discovered Timestamp", "Where This Data Came From"]
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
                "Website Scan — Outbound External Links"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_internal_links_csv(internal_links: List[Dict[str, Any]]) -> str:
        headers = ["Source Page URL", "Destination Page URL", "Clickable Link Text", "Link Type", "Status Code", "Where This Data Came From"]
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
        headers = ["Competitor Name", "Domain", "Website URL", "Location", "Geographic Level", "Relevance Match %", "Overlapping Keywords", "SERP Appearances", "Primary Competitor", "Status", "Discovery Source", "Where This Data Came From"]
        rows = []
        if not competitors:
            rows.append([
                "No competitor data yet", "N/A", "N/A", "Local Market", "City", "0%", "0", "0", "False", "None", "User Specified", "Not Connected"
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
        headers = ["Severity / Priority", "Category", "SEO Problems Found", "Affected Page URL", "What Was Found / Evidence", "Recommended Action", "Where This Data Came From", "Generated By", "Scan Date"]
        rows = []
        for i in issues:
            rows.append([
                i.get("severity") or i.get("priority") or "Warning",
                i.get("issue_type") or i.get("category") or "Technical",
                i.get("title") or f"Fix {i.get('issue_type', 'SEO Issue')}",
                i.get("affected_url") or (i.get("affected_urls")[0] if i.get("affected_urls") and isinstance(i.get("affected_urls"), list) else ""),
                i.get("details") or i.get("evidence") or "Issue detected during scan",
                i.get("recommendation") or "Review and fix affected URL",
                "Website Scan",
                "Audit Rule Engine",
                "Latest Scan"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_opportunities_csv(opportunities: List[Dict[str, Any]]) -> str:
        headers = ["Priority Level", "Category", "Recommended Action Title", "Why It Matters", "Affected URLs", "What Was Found / Evidence", "Recommended Action", "Where This Data Came From", "Generated By", "Scan Date"]
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
                    o.get("provenance") or "Website Scan",
                    "Opportunity Engine",
                    "Latest Scan"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_ai_solutions_csv(issues: List[Dict[str, Any]], domain: str = "") -> str:
        headers = ["Website Domain", "Issue Title", "Severity", "Affected Page URL", "What Was Found / Evidence", "Why It Matters", "Recommended Action", "AI Solution", "Where This Data Came From", "Generated Date"]
        rows = []
        today_date = datetime.now().strftime("%Y-%m-%d")
        for i in issues:
            urls = i.get("affected_urls") or ([i.get("affected_url")] if i.get("affected_url") else ["All Pages"])
            url_str = ", ".join(urls[:3]) if isinstance(urls, list) else str(urls)
            rows.append([
                domain,
                i.get("title", "SEO Finding"),
                i.get("severity") or i.get("priority") or "Warning",
                url_str,
                i.get("description") or i.get("evidence") or "Detected during scan",
                "Impacts search engine indexing or snippet presentation",
                i.get("recommendation") or "Fix identified issue",
                i.get("ai_solution") or "Write unique content and metadata tailored to target topic",
                "AI Analysis",
                today_date
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_future_improvements_csv(issues: List[Dict[str, Any]]) -> str:
        headers = ["Priority", "Timeframe", "Focus Area", "Problem / Opportunity", "Recommended SEO Improvement", "Expected Business Benefit", "Where This Data Came From"]
        rows = [
            ["Immediate", "NOW", "Critical Crawl Errors", "Fix 404 broken URLs and crawl blocks", "Repair broken internal links and restore accessibility", "Restores crawler access and prevents traffic loss", "Website Scan"],
            ["High", "NEXT 30 DAYS", "Metadata & Titles", "Resolve missing or non-optimal titles and descriptions", "Write unique 150-160 character meta descriptions and target H1s", "Improves SERP click-through rates and relevance", "Automatic SEO Check"],
            ["Medium", "NEXT 60-90 DAYS", "Content Depth", "Expand thin content pages (< 150 words)", "Add comprehensive topic copy, FAQs, and internal links", "Strengthens topical authority and page ranking flow", "AI Analysis"],
            ["Low", "ONGOING", "Crawl Maintenance", "Prevent technical SEO regressions", "Execute bi-weekly scans and monitor Search Console data", "Protects long-term search engine visibility", "SEO Platform Engine"]
        ]
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_affected_pages_csv(issues: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> str:
        headers = ["Affected Page URL", "Page Title", "Issue Title", "Severity", "Current Measured Value", "Recommended Target Value", "Evidence / Details", "Recommended Fix"]
        rows = []
        page_map = {p.get("url"): p for p in pages if p.get("url")}
        
        for i in issues:
            urls = i.get("affected_urls") or ([i.get("affected_url")] if i.get("affected_url") else [])
            for u in urls[:10]:
                p = page_map.get(u, {})
                title = p.get("title") or "Page Title Not Collected"
                
                meas = f"Meta Desc Length: {len(p.get('meta_description', ''))} chars" if "meta" in i.get("title", "").lower() else (
                    f"Title Length: {len(p.get('title', ''))} chars" if "title" in i.get("title", "").lower() else (
                    f"Word Count: {p.get('word_count', 0)} words" if "thin" in i.get("title", "").lower() else (
                    f"HTTP Status: {p.get('status_code', 200)}"
                )))
                
                target = "Meta Desc: 150-160 chars" if "meta" in i.get("title", "").lower() else (
                    "Title: 50-60 chars" if "title" in i.get("title", "").lower() else (
                    "Word Count: > 300 words" if "thin" in i.get("title", "").lower() else "HTTP Status: 200 OK"
                ))

                rows.append([
                    u,
                    title,
                    i.get("title", "SEO Issue"),
                    i.get("severity") or i.get("priority") or "Warning",
                    meas,
                    target,
                    i.get("description") or i.get("evidence") or "Issue detected during crawl",
                    i.get("recommendation") or "Fix page metadata or content"
                ])
        if not rows:
            rows.append(["All Pages Healthy", "N/A", "Zero Affected Pages", "Notice", "100% Passed", "100% Passed", "No issues detected", "Maintain scan frequency"])

        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_ai_insights_csv(ai_insights: Dict[str, Any]) -> str:
        headers = ["Priority", "Category", "Finding Title", "Why It Matters / Impact", "Recommended Action", "Affected URLs", "Where This Data Came From", "Generated By"]
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
                    ", ".join(f.get("affected_urls", [])) if isinstance(f.get("affected_urls"), list) else "All Pages",
                    "AI Analysis",
                    "AI Analyst Engine"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_crawl_history_csv(crawls: List[Dict[str, Any]]) -> str:
        headers = ["Scan Session ID", "Target Domain", "Scan Date / Time", "Status", "Pages Discovered", "Pages Analyzed", "Issues Found", "Where This Data Came From"]
        rows = []
        for c in crawls:
            rows.append([
                c.get("session_id") or c.get("id") or "N/A",
                c.get("domain", ""),
                c.get("created_at") or c.get("timestamp") or "N/A",
                c.get("status", "Completed"),
                c.get("pages_discovered", 0),
                c.get("pages_crawled", 0),
                c.get("total_issues", 0),
                "Scan History Log"
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
            prefix = f"{safe_domain}_SEO_Master_Export_{today_date}"

            # README.TXT
            readme_text = f"""================================================================================
FULL WEBSITE HEALTH MASTER REPORT & DATA PACKAGE
================================================================================

Website Domain: {domain}
Project Name: {project_name}
Target URL: {url}
Report Export Date: {now_str}
Last Website Scan Snapshot: {crawl_time}
Total Pages Scanned: {len(pages)}
Total Problems Found: {len(issues)}

INCLUDED MASTER REPORT DATASETS:
--------------------------------------------------------------------------------
1. Full_Website_Health_Report.pdf   : Complete client-ready master PDF report
2. Website_Health_Summary.csv       : Key performance indicator summary
3. Problems_Found.csv               : Complete technical and on-page audit findings
4. Affected_Pages.csv               : Affected page URLs with evidence measurements
5. AI_Solutions.csv                 : Evidence-grounded AI recommendations
6. Future_SEO_Improvements.csv      : Prioritized execution roadmap (NOW, 30, 60-90 Days)
7. Keywords.csv                     : Content keywords & frequency analysis
8. Internal_Links.csv               : Links between website pages
9. Outbound_Links.csv               : External links pointing to other websites
10. Inbound_Backlinks.csv           : Backlinks from external domains ({'Connected' if inbound_backlinks else 'Not Connected'})
11. Search_Rankings.csv             : Google ranking positions ({'Connected' if rankings else 'Not Connected'})
12. Competitors.csv                 : Competitor analysis ({'Configured' if competitors else 'Not Configured'})

DATA DEFINITIONS & SOURCE TRANSPARENCY:
--------------------------------------------------------------------------------
- Website Scan           : Verified content collected directly from target website URLs.
- Outbound Links         : External links on your website pointing to external websites.
- Inbound Backlinks       : Backlinks on external websites pointing to your site.
- Automatic Keyword Check: Occurrence frequency of terms in scanned HTML.
- Not Connected          : Indicates a dataset requiring connected Search Console or backlink API.

================================================================================
Generated by SEO Intelligence Platform
================================================================================
"""
            zf.writestr(f"{prefix}/README.txt", readme_text)

            # Master PDF
            if audit_pdf_bytes:
                zf.writestr(f"{prefix}/{safe_domain}_Full_Website_Health_Report_{today_date}.pdf", audit_pdf_bytes)

            # Master CSVs
            zf.writestr(f"{prefix}/Website_Health_Summary.csv", CSVExportService.generate_project_summary_csv(project_name, domain, url, metadata, pages, keywords, issues))
            zf.writestr(f"{prefix}/Problems_Found.csv", CSVExportService.generate_technical_issues_csv(issues))
            zf.writestr(f"{prefix}/Affected_Pages.csv", CSVExportService.generate_affected_pages_csv(issues, pages))
            zf.writestr(f"{prefix}/AI_Solutions.csv", CSVExportService.generate_ai_solutions_csv(issues, domain))
            zf.writestr(f"{prefix}/Future_SEO_Improvements.csv", CSVExportService.generate_future_improvements_csv(issues))
            zf.writestr(f"{prefix}/Keywords.csv", CSVExportService.generate_keywords_csv(keywords))
            zf.writestr(f"{prefix}/Internal_Links.csv", CSVExportService.generate_internal_links_csv(internal_links))
            zf.writestr(f"{prefix}/Outbound_Links.csv", CSVExportService.generate_outbound_links_csv(outbound_links))

            if inbound_backlinks:
                zf.writestr(f"{prefix}/Inbound_Backlinks.csv", CSVExportService.generate_inbound_backlinks_csv(inbound_backlinks))
            if rankings:
                zf.writestr(f"{prefix}/Search_Rankings.csv", CSVExportService.generate_rankings_csv(rankings))
            if competitors:
                zf.writestr(f"{prefix}/Competitors.csv", CSVExportService.generate_competitors_csv(competitors))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
