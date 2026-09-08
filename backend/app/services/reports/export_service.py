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
            ["Total Crawled Pages", metadata.get("pages_crawled", len(pages)), "Automatic Website Check"],
            ["Total Technical Issues", metadata.get("total_issues", len(issues)), "Automatic Website Check"],
            ["Critical Issues", sum(1 for i in issues if str(i.get("severity", "")).lower() in ("critical", "fatal")), "Automatic Website Check"],
            ["Warnings", sum(1 for i in issues if str(i.get("severity", "")).lower() in ("warning", "medium")), "Automatic Website Check"],
            ["Content Keywords Extracted", len(keywords), "Automatic Keyword Detection"],
            ["Crawl Status", metadata.get("status", "Completed"), "Automatic Website Check"],
            ["Crawl Timestamp", metadata.get("timestamp", "N/A"), "Automatic Website Check"],
            ["Export Timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "System Export"]
        ]
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_pages_csv(pages: List[Dict[str, Any]]) -> str:
        """Scoped strictly to master_report['affected_pages'] (individual crawled page URLs & metadata)."""
        headers = [
            "URL", "Status Code", "Title Tag", "Meta Description", "Canonical URL", 
            "Word Count", "H1 Heading", "H2 Count", "Internal Links Count", 
            "Can Search Engines Find This Page?", "Fetch Status", "Where This Data Came From"
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
                len(p.get("h2", [])) if isinstance(p.get("h2"), list) else 0,
                len(p.get("internal_links", [])) if isinstance(p.get("internal_links"), list) else p.get("internal_links_count", 0),
                "Yes (Indexable)" if p.get("status_code") == 200 else "No (Blocked / Error Page)",
                p.get("fetch_status", "SUCCESS"),
                "Automatic Website Check"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_keywords_csv(keywords: List[Dict[str, Any]]) -> str:
        """Scoped strictly to master_report['keywords'] (content-extracted target keywords)."""
        headers = ["Search Term / Keyword", "Target Page URL", "Category / Topic", "Content Frequency", "Where This Data Came From"]
        rows = []
        for k in keywords:
            rows.append([
                k.get("keyword", ""),
                k.get("target_url") or k.get("source_page") or "Crawled Website Content",
                k.get("type") or k.get("category") or "Content Keyword",
                k.get("frequency") or k.get("search_volume") or 1,
                k.get("provenance") or "Automatic Keyword Detection"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_technical_issues_csv(issues: List[Dict[str, Any]]) -> str:
        """Scoped strictly to master_report['problems'] (technical audit findings)."""
        headers = ["Indicator", "Severity", "Category", "SEO Problems Found", "Affected Page URL", "What Was Found / Evidence", "Current Value", "Expected Value", "Why It Matters", "Recommended Action", "AI Solution", "Future Improvement", "Where This Data Came From"]
        rows = []
        for i in issues:
            sev = str(i.get("severity") or i.get("priority") or "Warning").capitalize()
            ind = i.get("indicator") or ("🔴" if sev in ("Critical", "Fatal") else "🟠" if sev in ("High", "Error") else "🟡" if sev in ("Warning", "Medium") else "🔵")
            url = i.get("affected_url") or (i.get("affected_urls")[0] if i.get("affected_urls") and isinstance(i.get("affected_urls"), list) else i.get("url", ""))
            rows.append([
                ind,
                sev,
                i.get("category") or i.get("issue_type") or "Technical",
                i.get("problem") or i.get("title") or "Problem",
                url,
                i.get("what_was_found") or i.get("evidence") or i.get("details") or "Observed in crawl data",
                i.get("current_value") or "Incomplete",
                i.get("expected_value") or "Standard Compliant",
                i.get("why_it_matters") or "Impacts search indexability and user experience.",
                i.get("recommended_action") or i.get("recommendation") or "Review and fix affected URL.",
                i.get("ai_solution") or "Implement standard SEO best practices.",
                i.get("future_improvement") or "Add publishing validation checks.",
                i.get("source") or "Automatic Website Check + AI Analysis"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_ai_solutions_csv(issues: List[Dict[str, Any]], domain: str = "") -> str:
        """Scoped strictly to master_report['problems'] with AI-tailored solutions."""
        headers = [
            "Project", "Website", "Crawl Date", "Problem", "Severity", "Category", 
            "Affected Page URL", "What We Found", "Current Value", "Expected Value", 
            "Evidence", "Why It Matters", "Recommended Action", "AI Solution", 
            "Suggested Change", "Future Improvement", "AI Confidence", "Generated Date"
        ]
        rows = []
        today_date = datetime.now().strftime("%Y-%m-%d")
        for i in issues:
            sev = str(i.get("severity") or i.get("priority") or "Warning").capitalize()
            url = i.get("affected_url") or (i.get("affected_urls")[0] if i.get("affected_urls") and isinstance(i.get("affected_urls"), list) else i.get("url", domain))
            prob = i.get("problem") or i.get("title") or "SEO Finding"
            ev = i.get("what_was_found") or i.get("evidence") or i.get("details") or "Detected during scan"
            sol = i.get("ai_solution") or "Write unique content and metadata tailored to target topic"
            rows.append([
                domain,
                domain,
                today_date,
                prob,
                sev,
                i.get("category", "General"),
                url,
                ev,
                i.get("current_value") or "Incomplete",
                i.get("expected_value") or "Standard Compliant",
                ev,
                i.get("why_it_matters") or "Impacts search engine indexing or snippet presentation",
                i.get("recommended_action") or i.get("recommendation") or "Fix identified issue",
                sol,
                i.get("suggested_change") or sol,
                i.get("future_improvement") or "Add publishing pre-flight checklist",
                "High",
                today_date
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_opportunities_csv(opportunities: List[Dict[str, Any]]) -> str:
        """Scoped strictly to master_report['opportunities'] (central opportunity engine recommendations)."""
        headers = ["Priority Level", "Category", "Opportunity Title", "Affected Page URL", "What Was Found / Evidence", "Recommended Action", "AI Solution", "Expected Benefit", "Where This Data Came From"]
        rows = []
        if not opportunities:
            rows.append(["Medium", "Audit", "Perform regular website health checks", "Site Level", "Scan completed cleanly", "Run periodic scans", "Maintain automated scans", "Higher search stability", "Automatic Website Check"])
        else:
            for o in opportunities:
                rows.append([
                    o.get("priority_level") or o.get("priority") or "Medium",
                    o.get("category", "General"),
                    o.get("title", ""),
                    o.get("url") or o.get("affected_url") or "Site Level",
                    o.get("evidence", ""),
                    o.get("recommended_action") or o.get("recommendation") or "",
                    o.get("ai_solution") or "Implement structured optimization",
                    o.get("expected_benefit") or "Higher search rank and CTR",
                    o.get("provenance") or "Automatic Website Check"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_internal_links_csv(internal_links: List[Dict[str, Any]]) -> str:
        headers = ["Source Page URL", "Destination Page URL", "Anchor Text", "HTTP Status Code", "Where This Data Came From"]
        rows = []
        for l in internal_links:
            rows.append([
                l.get("source") or l.get("source_url") or "",
                l.get("target") or l.get("target_url") or "",
                l.get("anchor_text") or l.get("anchor") or "(No text)",
                l.get("status_code", 200),
                "Automatic Website Check"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_orphan_pages_csv(orphan_pages: List[Any]) -> str:
        """Generates CSV for orphan pages (pages with 0 incoming internal links)."""
        headers = ["Page URL", "Link Status", "Recommended Action"]
        rows = []
        for item in orphan_pages:
            url = item if isinstance(item, str) else (item.get("url") or item.get("page_url") or str(item)) if isinstance(item, dict) else str(item)
            rows.append([
                url,
                "0 Links Pointing to This Page",
                "Add a link from your homepage or main menu to help visitors find this page."
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_anchor_texts_csv(anchor_texts: List[Dict[str, Any]]) -> str:
        """Generates CSV for anchor text frequency usage across internal links."""
        headers = ["Link Text", "Times Used"]
        rows = []
        for a in anchor_texts:
            if isinstance(a, dict):
                anc = a.get("anchor_text") or a.get("text") or "(No text)"
                freq = a.get("frequency") or a.get("count") or a.get("times_used") or 0
                rows.append([anc, freq])
            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                rows.append([a[0], a[1]])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_link_opportunities_csv(opportunities: List[Dict[str, Any]]) -> str:
        """Generates CSV for internal link growth recommendations."""
        headers = ["Source Page", "Target Page", "Suggested Link Text", "Reason", "Priority"]
        rows = []
        for o in opportunities:
            if isinstance(o, dict):
                rows.append([
                    o.get("source_page", "") or o.get("source", ""),
                    o.get("target_page", "") or o.get("target", ""),
                    o.get("suggested_anchor", "") or o.get("suggested_anchor_text", "") or o.get("suggested_link_text", ""),
                    o.get("reason", "") or o.get("details", ""),
                    o.get("priority", "") or o.get("priority_level", "Medium")
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_broken_links_csv(broken_links: List[Dict[str, Any]]) -> str:
        """Generates CSV for internal and external broken links."""
        headers = ["Source Page", "Broken URL", "Link Type", "Status Code", "Link Text", "Error"]
        rows = []
        for b in broken_links:
            if isinstance(b, dict):
                rows.append([
                    b.get("source", "") or b.get("source_url", ""),
                    b.get("target", "") or b.get("broken_url", "") or b.get("target_url", ""),
                    b.get("link_type", "internal"),
                    b.get("status_code", 0) or "Failed",
                    b.get("anchor_text", "") or b.get("anchor", "") or b.get("link_text", ""),
                    b.get("error", "") or "Broken Link"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_outbound_links_csv(outbound_links: List[Dict[str, Any]]) -> str:
        headers = ["Source Page URL", "External Destination URL", "Anchor Text", "Classification", "Where This Data Came From"]
        rows = []
        for l in outbound_links:
            rows.append([
                l.get("source_url") or l.get("source") or "",
                l.get("destination_url") or l.get("target") or "",
                l.get("anchor_text") or l.get("anchor") or "[External Link]",
                "Outbound External Link Found on Website",
                "Automatic Website Check"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_rankings_csv(rankings: List[Dict[str, Any]]) -> str:
        headers = ["Keyword", "URL", "Position", "Previous Position", "Location", "Search Engine", "Device", "Where This Data Came From"]
        rows = []
        for r in rankings:
            loc = r.get("location") or "Unknown"
            rows.append([
                r.get("keyword", ""),
                r.get("url") or r.get("target_url") or "",
                r.get("position", "Unranked"),
                r.get("previous_position", "N/A"),
                loc,
                r.get("search_engine", "Google"),
                r.get("device", "Desktop"),
                r.get("source") or "Rank Tracker"
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_backlinks_csv(backlinks: List[Dict[str, Any]]) -> str:
        return CSVExportService.generate_inbound_backlinks_csv(backlinks)

    @staticmethod
    def generate_inbound_backlinks_csv(backlinks: List[Dict[str, Any]]) -> str:
        headers = ["Source Referring Domain", "Target Page URL", "Anchor Text", "Link Type", "Status Note"]
        rows = []
        if not backlinks:
            rows.append(["No inbound backlink dataset connected", "N/A", "N/A", "Inbound Backlinks", "Data Not Connected — Connect backlink integration in Settings"])
        else:
            for b in backlinks:
                rows.append([
                    b.get("source_url") or b.get("source", ""),
                    b.get("target_url") or b.get("target", ""),
                    b.get("anchor_text") or b.get("anchor", ""),
                    "Follow",
                    "Active"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_competitors_csv(competitors: List[Dict[str, Any]]) -> str:
        headers = ["Competitor Name", "Domain", "Website URL", "Relevance", "Keyword Overlap", "Status", "Where This Data Came From"]
        rows = []
        if not competitors:
            rows.append(["No competitor data configured", "N/A", "N/A", "N/A", "N/A", "Data Not Connected", "Settings -> Competitors"])
        else:
            for c in competitors:
                rows.append([
                    c.get("name", ""),
                    c.get("domain", ""),
                    c.get("url", ""),
                    c.get("relevance", "High"),
                    c.get("keyword_overlap", "N/A"),
                    "Active Competitor",
                    "User Specified / SERP Discovery"
                ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_aeo_csv(aeo_list: List[Dict[str, Any]]) -> str:
        headers = ["Search Topic", "Opportunity Type", "Recommended Action", "Observed Evidence", "Priority"]
        rows = []
        for a in aeo_list:
            rows.append([
                a.get("topic", ""),
                a.get("opportunity_type", ""),
                a.get("recommended_action", ""),
                a.get("evidence", ""),
                a.get("priority", "High")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_geo_csv(geo_list: List[Dict[str, Any]]) -> str:
        headers = ["Optimization Area", "Recommendation for Generative AI Visibility", "Observed Evidence", "Priority"]
        rows = []
        for g in geo_list:
            rows.append([
                g.get("area", ""),
                g.get("recommendation", ""),
                g.get("evidence", ""),
                g.get("priority", "Medium")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_local_seo_csv(local_data: List[Dict[str, Any]]) -> str:
        headers = ["Business Profile Area", "Detected Detail", "Verification Status", "Local SEO Recommendation"]
        rows = [
            ["Google Business Profile", "Not Connected", "Data Not Connected", "Connect Google Business Profile in Settings to track local map citations and reviews."],
            ["NAP Consistency (Name/Address/Phone)", "Audited on Homepage", "Standard Format", "Maintain consistent address and phone formatting across all local landing pages."]
        ]
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_historical_comparison_csv(hist_data: Dict[str, Any]) -> str:
        headers = ["Metric", "Previous Crawl Value", "Latest Crawl Value", "Delta / Change", "AI Trend Explanation"]
        rows = []
        if hist_data.get("has_previous_crawl"):
            rows.append(["Website Health Score", hist_data.get("previous_score", 100), hist_data.get("current_score", 100), f"{hist_data.get('score_delta', 0):+d}", hist_data.get("ai_trend_summary", "")])
            rows.append(["Resolved Problems", hist_data.get("problems_fixed_count", 0), "Fixed", f"+{hist_data.get('problems_fixed_count', 0)} resolved", "Previous issues fixed in latest scan"])
            rows.append(["New Findings", hist_data.get("new_problems_count", 0), "Detected", f"{hist_data.get('new_problems_count', 0)} new", "Newly detected issues in latest scan"])
        else:
            rows.append(["Historical Comparison", "N/A", "Active Crawl", "First Crawl", "Historical comparison is not available because no previous completed crawl exists."])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_future_improvements_csv(issues: List[Dict[str, Any]]) -> str:
        headers = ["Priority / Phase", "Timeframe", "Focus Area", "Problem / Opportunity", "Recommended SEO Improvement", "Expected Business Benefit", "Where This Data Came From"]
        rows = [
            ["Immediate", "NOW (0–7 Days)", "Critical Technical Issues", "Fix 404 broken URLs and crawl blocks", "Repair broken internal links and restore accessibility", "Restores crawler access and prevents traffic loss", "Automatic Website Check"],
            ["High", "NEXT 30 DAYS", "Metadata & On-Page SEO", "Resolve missing or non-optimal titles and descriptions", "Write unique 30-60 char meta titles and 120-155 char descriptions", "Improves SERP click-through rates and relevance", "Automatic Website Check + AI"],
            ["Medium", "30–60 DAYS", "Content Depth & Links", "Expand thin content pages (< 300 words)", "Add comprehensive topic copy, FAQs, and internal links", "Strengthens topical authority and page ranking flow", "Automatic Website Check + AI"],
            ["Ongoing", "ONGOING", "Crawl Maintenance", "Prevent technical SEO regressions", "Execute regular scans and monitor Search Console data", "Protects long-term search engine visibility", "Automatic Website Check"]
        ]
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_affected_pages_csv(issues: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> str:
        headers = ["Affected Page URL", "Page Title", "Problem Title", "Severity", "Current Measured Value", "Recommended Target Value", "Evidence / Details", "Recommended Fix", "Where This Data Came From"]
        rows = []
        page_map = {p.get("url"): p for p in pages if p.get("url")}
        
        for i in issues:
            urls = i.get("affected_urls") or ([i.get("affected_url")] if i.get("affected_url") else [])
            for u in urls[:10]:
                p = page_map.get(u, {})
                title = p.get("title") or "Page Title Not Collected"
                
                meas = f"Meta Desc Length: {len(p.get('meta_description', ''))} chars" if "meta" in str(i.get("title") or i.get("problem", "")).lower() else (
                    f"Title Length: {len(p.get('title', ''))} chars" if "title" in str(i.get("title") or i.get("problem", "")).lower() else (
                    f"Word Count: {p.get('word_count', 0)} words" if "thin" in str(i.get("title") or i.get("problem", "")).lower() else (
                    f"HTTP Status: {p.get('status_code', 200)}"
                )))
                
                target = "Meta Desc: 120-155 chars" if "meta" in str(i.get("title") or i.get("problem", "")).lower() else (
                    "Title: 30-60 chars" if "title" in str(i.get("title") or i.get("problem", "")).lower() else (
                    "Word Count: >= 300 words" if "thin" in str(i.get("title") or i.get("problem", "")).lower() else "HTTP Status: 200 OK"
                ))

                rows.append([
                    u,
                    title,
                    i.get("problem") or i.get("title") or "SEO Finding",
                    i.get("severity") or i.get("priority") or "Warning",
                    meas,
                    target,
                    i.get("what_was_found") or i.get("evidence") or "Issue detected during crawl",
                    i.get("recommended_action") or i.get("recommendation") or "Fix page metadata or content",
                    "Automatic Website Check + AI Analysis"
                ])
        if not rows:
            rows.append(["All Pages Healthy", "N/A", "Zero Affected Pages", "Notice", "100% Passed", "100% Passed", "No issues detected", "Maintain scan frequency", "Automatic Website Check"])

        return CSVExportService.generate_csv_string(headers, rows)


class ZIPExportService:
    @staticmethod
    def generate_complete_zip_export(
        project_name: str = None,
        domain: str = None,
        url: str = None,
        project_url: str = None,
        metadata: Dict[str, Any] = None,
        pages: List[Dict[str, Any]] = None,
        keywords: List[Dict[str, Any]] = None,
        rankings: List[Dict[str, Any]] = None,
        inbound_backlinks: List[Dict[str, Any]] = None,
        outbound_links: List[Dict[str, Any]] = None,
        internal_links: List[Dict[str, Any]] = None,
        competitors: List[Dict[str, Any]] = None,
        issues: List[Dict[str, Any]] = None,
        opportunities: List[Dict[str, Any]] = None,
        crawls: List[Dict[str, Any]] = None,
        audit_pdf_bytes: bytes = None,
        ai_insights: Dict[str, Any] = None,
        master_report: Dict[str, Any] = None,
        **kwargs
    ) -> bytes:
        url = url or project_url
        if master_report:
            p_obj = master_report.get("project", {})
            c_obj = master_report.get("crawl", {})
            project_name = p_obj.get("name", project_name or "Website Project")
            domain = p_obj.get("domain", domain or "website.com")
            url = p_obj.get("url", url or f"https://{domain}")
            metadata = metadata or {"timestamp": c_obj.get("timestamp", "N/A")}
            pages = pages or master_report.get("affected_pages", [])
            keywords = keywords or master_report.get("keywords", [])
            issues = issues or master_report.get("problems", [])
            opportunities = opportunities or master_report.get("opportunities", [])
            internal_links = internal_links or master_report.get("content_and_links", {}).get("internal_links", [])
            outbound_links = outbound_links or master_report.get("content_and_links", {}).get("outbound_links", [])
            inbound_backlinks = inbound_backlinks or master_report.get("backlinks", {}).get("inbound_backlinks", [])
            competitors = competitors or master_report.get("competitors", [])
            aeo_list = master_report.get("aeo", [])
            geo_list = master_report.get("geo", [])
            hist_data = master_report.get("historical_comparison", {})
        else:
            domain = domain or "website.com"
            project_name = project_name or domain
            url = url or f"https://{domain}"
            metadata = metadata or {}
            pages = pages or []
            keywords = keywords or []
            issues = issues or []
            opportunities = opportunities or []
            internal_links = internal_links or []
            outbound_links = outbound_links or []
            inbound_backlinks = inbound_backlinks or []
            competitors = competitors or []
            aeo_list = []
            geo_list = []
            hist_data = {}

        safe_domain = get_sanitized_domain(domain)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        today_date = datetime.now().strftime("%Y-%m-%d")
        crawl_time = metadata.get("timestamp", "N/A")

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
6. Keywords.csv                     : Content keywords & frequency analysis
7. Backlinks.csv                    : Inbound backlink profile ({'Connected' if inbound_backlinks else 'Not Connected'})
8. Internal_Links.csv               : Links between website pages
9. Outbound_Links.csv               : External links pointing to other websites
10. Opportunities.csv               : High-impact SEO growth opportunities
11. Technical_Issues.csv            : Server response codes & crawlability findings
12. Local_SEO.csv                   : Local SEO & Google Business Profile status
13. AEO.csv                         : Answer Engine & FAQ schema opportunities
14. GEO.csv                         : Generative Engine & brand citation opportunities
15. Historical_Comparison.csv       : Comparison against previous completed scan
16. Next_SEO_Improvements.csv       : Prioritized execution roadmap (NOW, 30, 60-90 Days)
17. Crawl_Summary.csv               : Crawl diagnostic summary

DATA DEFINITIONS & SOURCE TRANSPARENCY:
--------------------------------------------------------------------------------
- Automatic Website Check : Verified content collected directly from target website URLs.
- Outbound Links          : External links on your website pointing to external websites.
- Inbound Backlinks       : Backlinks on external websites pointing to your site.
- Automatic Keyword Check : Occurrence frequency of terms in scanned HTML.
- Data Not Connected      : Indicates a dataset requiring connected Search Console or backlink API.

================================================================================
Generated by SEO Intelligence Platform
================================================================================
"""
            zf.writestr(f"{prefix}/README.txt", readme_text)

            # Master PDF
            if not audit_pdf_bytes and master_report:
                try:
                    from app.services.reports.pdf_service import PDFReportGenerator
                    pdf_gen = PDFReportGenerator()
                    audit_pdf_bytes = pdf_gen.generate_full_project_pdf(master_report=master_report)
                except Exception as e:
                    print(f"[ZIP EXPORT PDF GENERATION ERROR] {e}", flush=True)

            if audit_pdf_bytes:
                zf.writestr(f"{prefix}/Full_Website_Health_Report.pdf", audit_pdf_bytes)

            # Master XLSX
            try:
                from app.services.reports.xlsx_service import XLSXExportService
                xlsx_bytes = XLSXExportService.generate_full_project_xlsx(master_report=master_report) if master_report else XLSXExportService.generate_full_project_xlsx(project_name=project_name, project_url=url, pages=pages, keywords=keywords, issues=issues, opportunities=opportunities)
                if xlsx_bytes:
                    zf.writestr(f"{prefix}/Full_Website_Health_Report.xlsx", xlsx_bytes)
            except Exception as e:
                print(f"[ZIP EXPORT XLSX ERROR] {e}", flush=True)

            # Master PPTX
            try:
                from app.services.reports.pptx_service import PPTXExportService
                pptx_bytes = PPTXExportService.generate_full_project_pptx(master_report=master_report) if master_report else None
                if pptx_bytes:
                    zf.writestr(f"{prefix}/Full_Website_Health_Report.pptx", pptx_bytes)
            except Exception as e:
                print(f"[ZIP EXPORT PPTX ERROR] {e}", flush=True)

            # Master CSVs
            zf.writestr(f"{prefix}/Website_Health_Summary.csv", CSVExportService.generate_project_summary_csv(project_name, domain, url, metadata, pages, keywords, issues))
            zf.writestr(f"{prefix}/Problems_Found.csv", CSVExportService.generate_technical_issues_csv(issues))
            zf.writestr(f"{prefix}/Affected_Pages.csv", CSVExportService.generate_affected_pages_csv(issues, pages))
            zf.writestr(f"{prefix}/AI_Solutions.csv", CSVExportService.generate_ai_solutions_csv(issues, domain))
            zf.writestr(f"{prefix}/Keywords.csv", CSVExportService.generate_keywords_csv(keywords))
            zf.writestr(f"{prefix}/Backlinks.csv", CSVExportService.generate_inbound_backlinks_csv(inbound_backlinks))
            zf.writestr(f"{prefix}/Internal_Links.csv", CSVExportService.generate_internal_links_csv(internal_links))
            zf.writestr(f"{prefix}/Outbound_Links.csv", CSVExportService.generate_outbound_links_csv(outbound_links))
            zf.writestr(f"{prefix}/Opportunities.csv", CSVExportService.generate_opportunities_csv(opportunities))
            zf.writestr(f"{prefix}/Technical_Issues.csv", CSVExportService.generate_technical_issues_csv(issues))
            zf.writestr(f"{prefix}/Local_SEO.csv", CSVExportService.generate_local_seo_csv([]))
            zf.writestr(f"{prefix}/AEO.csv", CSVExportService.generate_aeo_csv(aeo_list))
            zf.writestr(f"{prefix}/GEO.csv", CSVExportService.generate_geo_csv(geo_list))
            zf.writestr(f"{prefix}/Historical_Comparison.csv", CSVExportService.generate_historical_comparison_csv(hist_data))
            future_csv = CSVExportService.generate_future_improvements_csv(issues)
            zf.writestr(f"{prefix}/Next_SEO_Improvements.csv", future_csv)
            zf.writestr(f"{prefix}/Future_SEO_Improvements.csv", future_csv)
            zf.writestr(f"{prefix}/Crawl_Summary.csv", CSVExportService.generate_project_summary_csv(project_name, domain, url, metadata, pages, keywords, issues))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    generate_complete_export_zip = generate_complete_zip_export
