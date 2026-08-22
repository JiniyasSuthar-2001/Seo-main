import io
import csv
import zipfile
from typing import Dict, Any, List

from app.config.utils import sanitize_csv_cell

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
        headers = ["Field", "Value"]
        rows = [
            ["Project Name", project_name],
            ["Domain", domain],
            ["URL", url],
            ["Total Crawled Pages", metadata.get("pages_crawled", len(pages))],
            ["Total Technical Issues", metadata.get("total_issues", len(issues))],
            ["Critical Issues", metadata.get("critical_issues", 0)],
            ["Warnings", metadata.get("warning_issues", 0)],
            ["Keywords Tracked", len(keywords)],
            ["Crawl Status", metadata.get("status", "Completed")],
            ["Last Crawl Timestamp", metadata.get("timestamp", "N/A")]
        ]
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_pages_csv(pages: List[Dict[str, Any]]) -> str:
        headers = ["URL", "Status Code", "Title Tag", "Meta Description", "Canonical", "Word Count", "H1", "Internal Links"]
        rows = []
        for p in pages:
            rows.append([
                p.get("url", ""),
                p.get("status_code", 200),
                p.get("title", ""),
                p.get("meta_description", ""),
                p.get("canonical", ""),
                p.get("word_count", 0),
                p.get("h1", ""),
                p.get("internal_links_count", 0)
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_keywords_csv(keywords: List[Dict[str, Any]]) -> str:
        headers = ["Keyword", "Target URL", "Search Volume", "Difficulty", "Intent", "Position", "Country", "Device"]
        rows = []
        for k in keywords:
            rows.append([
                k.get("keyword", ""),
                k.get("target_url", ""),
                k.get("search_volume", ""),
                k.get("difficulty", ""),
                k.get("intent", ""),
                k.get("position", ""),
                k.get("country", ""),
                k.get("device", "")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_rankings_csv(rankings: List[Dict[str, Any]]) -> str:
        headers = ["Keyword", "Target URL", "Position", "Previous Position", "Change", "Engine", "Device", "Location", "Date"]
        rows = []
        for r in rankings:
            rows.append([
                r.get("keyword", ""),
                r.get("url", ""),
                r.get("position", ""),
                r.get("previous_position", ""),
                r.get("change", 0),
                r.get("engine", "Google"),
                r.get("device", "Desktop"),
                r.get("location") or "Unknown",
                r.get("date", "")
            ])
        return CSVExportService.generate_csv_string(headers, rows)


    @staticmethod
    def generate_backlinks_csv(backlinks: List[Dict[str, Any]]) -> str:
        headers = ["Source URL", "Target URL", "Anchor Text", "Link Type", "Domain Authority", "First Seen", "Last Seen"]
        rows = []
        for b in backlinks:
            rows.append([
                b.get("source_url", ""),
                b.get("target_url", ""),
                b.get("anchor_text", ""),
                b.get("link_type", "Dofollow"),
                b.get("domain_authority", ""),
                b.get("first_seen", ""),
                b.get("last_seen", "")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_internal_links_csv(internal_links: List[Dict[str, Any]]) -> str:
        headers = ["Source URL", "Target URL", "Anchor Text", "Link Type", "Status Code"]
        rows = []
        for l in internal_links:
            rows.append([
                l.get("source", ""),
                l.get("target", ""),
                l.get("anchor_text", ""),
                l.get("link_type", "Internal"),
                l.get("status_code", 200)
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_competitors_csv(competitors: List[Dict[str, Any]]) -> str:
        headers = ["Competitor Name", "Domain", "Common Keywords", "Visibility Index", "Ranking Comparison"]
        rows = []
        for c in competitors:
            rows.append([
                c.get("name", ""),
                c.get("domain", ""),
                c.get("keywords_count", 0),
                c.get("visibility", ""),
                c.get("comparison", "")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_technical_issues_csv(issues: List[Dict[str, Any]]) -> str:
        headers = ["Severity", "Issue Type", "Affected URL", "Details", "Recommendation"]
        rows = []
        for i in issues:
            rows.append([
                i.get("severity", "Notice"),
                i.get("issue_type", ""),
                i.get("affected_url", ""),
                i.get("details", ""),
                i.get("recommendation", "")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_crawl_history_csv(crawls: List[Dict[str, Any]]) -> str:
        headers = ["Crawl Date", "Start URL", "Pages Crawled", "Issues Found", "Status"]
        rows = []
        for cr in crawls:
            rows.append([
                cr.get("timestamp") or cr.get("started_at") or "",
                cr.get("url") or "",
                cr.get("pages_crawled", 0),
                cr.get("issues_found", 0),
                cr.get("status", "Completed")
            ])
        return CSVExportService.generate_csv_string(headers, rows)

    @staticmethod
    def generate_project_zip_export(project_name: str, domain: str, url: str, metadata: Dict[str, Any], pages: List[Dict[str, Any]], keywords: List[Dict[str, Any]], rankings: List[Dict[str, Any]], backlinks: List[Dict[str, Any]], internal_links: List[Dict[str, Any]], competitors: List[Dict[str, Any]], issues: List[Dict[str, Any]], crawls: List[Dict[str, Any]]) -> bytes:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("project_summary.csv", CSVExportService.generate_project_summary_csv(project_name, domain, url, metadata, pages, keywords, issues))
            zf.writestr("pages.csv", CSVExportService.generate_pages_csv(pages))
            zf.writestr("keywords.csv", CSVExportService.generate_keywords_csv(keywords))
            zf.writestr("rankings.csv", CSVExportService.generate_rankings_csv(rankings))
            zf.writestr("backlinks.csv", CSVExportService.generate_backlinks_csv(backlinks))
            zf.writestr("internal_links.csv", CSVExportService.generate_internal_links_csv(internal_links))
            zf.writestr("competitors.csv", CSVExportService.generate_competitors_csv(competitors))
            zf.writestr("technical_issues.csv", CSVExportService.generate_technical_issues_csv(issues))
            zf.writestr("crawl_history.csv", CSVExportService.generate_crawl_history_csv(crawls))

        zip_buffer.seek(0)
        return zip_buffer.getvalue()
