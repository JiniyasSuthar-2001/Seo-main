import io
import csv
import html
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Any

BACKEND_GUIDELINES = {
    "keywords": {
        "id": "keywords",
        "title": "Keyword Dataset Upload Guide",
        "purpose": "Import target keyword lists, search term frequencies, CPC, difficulty, and intent metrics into your project workspace.",
        "where_to_get": "Export keyword lists from Google Search Console, rank-tracking tools, or SEO keyword planners.",
        "supported_formats": ["CSV", "XLSX"],
        "max_file_size": "25 MB",
        "version": "Version 1.3 — September 2026",
        "required_columns": [
            {"name": "Keyword", "description": "Target search phrase (Required)", "example": "seo audit checklist"}
        ],
        "optional_columns": [
            {"name": "Target URL", "description": "Target landing page URL on your domain (e.g. https://example.com/page)", "example": "https://example.com/blog/seo-audit"},
            {"name": "Search Volume", "description": "Estimated monthly search queries (integer >= 0)", "example": "3600"},
            {"name": "Difficulty", "description": "Keyword difficulty score between 0 and 100", "example": "42"},
            {"name": "CPC", "description": "Cost Per Click in currency units (decimal number)", "example": "4.20"},
            {"name": "Intent", "description": "Search intent: Informational, Commercial, Transactional, Navigational", "example": "Informational"},
            {"name": "Position", "description": "Google SERP position rank if available (integer 1-100)", "example": "8"},
            {"name": "Country", "description": "2-letter ISO country code (e.g. US, AU, GB)", "example": "US"}
        ],
        "synthetic_headers": ["Keyword", "Target URL", "Search Volume", "Difficulty", "CPC", "Intent", "Position", "Country"],
        "synthetic_rows": [
            ["seo audit checklist", "https://example.com/blog/seo-audit", "3600", "42", "4.20", "Informational", "8", "US"],
            ["enterprise technical seo", "https://example.com/services/technical-seo", "1200", "65", "8.50", "Commercial", "3", "US"],
            ["local seo agency sydney", "https://example.com/locations/sydney", "880", "51", "6.75", "Transactional", "5", "AU"],
            ["page speed optimization service", "https://example.com/services/page-speed", "1450", "38", "5.10", "Commercial", "12", "US"],
            ["xml sitemap generator tool", "https://example.com/tools/sitemap", "5400", "29", "2.80", "Navigational", "2", "GB"]
        ],
        "privacy_warning": "Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data."
    },
    "rankings": {
        "id": "rankings",
        "title": "Search Ranking Dataset Upload Guide",
        "purpose": "Import genuine historical search engine ranking positions exported from a rank tracking provider or Google Search Console.",
        "where_to_get": "Export position history from your rank tracking platform, Search Console performance export, or SERP provider.",
        "supported_formats": ["CSV", "XLSX"],
        "max_file_size": "25 MB",
        "version": "Version 1.3 — September 2026",
        "required_columns": [
            {"name": "Keyword", "description": "Ranked search phrase (Required)", "example": "seo audit services"},
            {"name": "URL", "description": "Ranking target URL on your domain (Required)", "example": "https://example.com/services/audit"},
            {"name": "Position", "description": "Actual Google search rank position number (1-100, Required)", "example": "4"}
        ],
        "optional_columns": [
            {"name": "Search Volume", "description": "Monthly estimated search volume (integer >= 0)", "example": "4500"},
            {"name": "Country", "description": "Target geographic country code (e.g. US, AU, GB)", "example": "US"},
            {"name": "Device", "description": "Target device type: Desktop or Mobile", "example": "Desktop"},
            {"name": "Search Engine", "description": "Search provider name (e.g. Google, Bing)", "example": "Google"},
            {"name": "Date", "description": "Snapshot ranking date in ISO format (YYYY-MM-DD)", "example": "2026-09-01"}
        ],
        "synthetic_headers": ["Keyword", "URL", "Position", "Search Volume", "Country", "Device", "Search Engine", "Date"],
        "synthetic_rows": [
            ["seo audit services", "https://example.com/services/audit", "4", "4500", "US", "Desktop", "Google", "2026-09-01"],
            ["best backlink checker", "https://example.com/tools/backlinks", "7", "8200", "US", "Desktop", "Google", "2026-09-01"],
            ["local seo consultant", "https://example.com/consulting", "3", "1900", "AU", "Mobile", "Google", "2026-09-01"],
            ["ecommerce schema markup", "https://example.com/guides/schema", "11", "950", "GB", "Desktop", "Google", "2026-09-01"],
            ["broken link checker free", "https://example.com/tools/broken-links", "6", "6100", "US", "Mobile", "Google", "2026-09-01"]
        ],
        "privacy_warning": "Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data."
    },
    "backlinks": {
        "id": "backlinks",
        "title": "Inbound Backlink Dataset Upload Guide",
        "purpose": "Import external inbound backlinks linking from external websites TO your target domain.",
        "where_to_get": "Export backlink reports from your SEO analytics tool or Google Search Console links report.",
        "supported_formats": ["CSV", "XLSX"],
        "max_file_size": "25 MB",
        "version": "Version 1.3 — September 2026",
        "required_columns": [
            {"name": "Source URL", "description": "External website URL containing the inbound link (Required)", "example": "https://tech-journal.com/top-seo-tools-2026"},
            {"name": "Target URL", "description": "Your website destination URL being linked to (Required)", "example": "https://example.com/services/audit"},
            {"name": "Anchor Text", "description": "Clickable anchor text of the link (Required)", "example": "Comprehensive SEO Audit Suite"}
        ],
        "optional_columns": [
            {"name": "Referring Domain", "description": "External root domain name (e.g. tech-journal.com)", "example": "tech-journal.com"},
            {"name": "Follow/Nofollow", "description": "Link rel attribute: Follow, Nofollow, UGC, or Sponsored", "example": "Follow"},
            {"name": "Status", "description": "Backlink status: Active or Lost", "example": "Active"},
            {"name": "First Seen", "description": "Initial discovery date timestamp (YYYY-MM-DD)", "example": "2026-02-10"},
            {"name": "Last Seen", "description": "Last verified crawl date timestamp (YYYY-MM-DD)", "example": "2026-08-15"}
        ],
        "synthetic_headers": ["Source URL", "Target URL", "Anchor Text", "Referring Domain", "Follow/Nofollow", "Status", "First Seen", "Last Seen"],
        "synthetic_rows": [
            ["https://tech-journal.com/top-seo-tools-2026", "https://example.com/services/audit", "Comprehensive SEO Audit Suite", "tech-journal.com", "Follow", "Active", "2026-02-10", "2026-08-15"],
            ["https://marketing-insider.org/resources", "https://example.com/blog/seo-audit", "SEO Guide", "marketing-insider.org", "Nofollow", "Active", "2026-03-22", "2026-08-20"],
            ["https://industry-directory.net/agencies", "https://example.com/", "Visit Website", "industry-directory.net", "Follow", "Active", "2026-01-05", "2026-08-18"],
            ["https://dev-community.io/discussions/crawlers", "https://example.com/tools/sitemap", "fast sitemap tool", "dev-community.io", "UGC", "Active", "2026-05-14", "2026-08-25"],
            ["https://business-weekly.com/news/digital-trends", "https://example.com/services/technical-seo", "Technical SEO Specialist", "business-weekly.com", "Sponsored", "Active", "2026-06-01", "2026-08-22"]
        ],
        "privacy_warning": "Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data."
    },
    "competitors": {
        "id": "competitors",
        "title": "Competitor Dataset Upload Guide",
        "purpose": "Import verified competitor domain lists and keyword overlap records for market intelligence.",
        "where_to_get": "Export competitor domain tracking datasets or SERP competitive analysis files.",
        "supported_formats": ["CSV", "XLSX"],
        "max_file_size": "25 MB",
        "version": "Version 1.3 — September 2026",
        "required_columns": [
            {"name": "Competitor Domain", "description": "Competitor root domain name (e.g. bright-seo-solutions.com, Required)", "example": "bright-seo-solutions.com"}
        ],
        "optional_columns": [
            {"name": "Competitor Name", "description": "Company or business brand name", "example": "Bright SEO Solutions"},
            {"name": "Location", "description": "Primary geographic market location", "example": "New York, USA"},
            {"name": "Overlapping Keywords", "description": "Count of shared search ranking phrases (integer >= 0)", "example": "840"},
            {"name": "Relevance Score", "description": "Market relevance percentage score between 0.0 and 100.0", "example": "88.5"}
        ],
        "synthetic_headers": ["Competitor Domain", "Competitor Name", "Location", "Overlapping Keywords", "Relevance Score"],
        "synthetic_rows": [
            ["bright-seo-solutions.com", "Bright SEO Solutions", "New York, USA", "840", "88.5"],
            ["apex-digital-search.co.uk", "Apex Digital Search", "London, UK", "620", "79.2"],
            ["pacific-rankings.com.au", "Pacific Rankings", "Sydney, Australia", "490", "74.0"],
            ["vanguard-organic.com", "Vanguard Organic Growth", "Chicago, USA", "310", "65.8"],
            ["summit-search-partners.com", "Summit Search Partners", "San Francisco, USA", "950", "92.4"]
        ],
        "privacy_warning": "Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data."
    }
}

class GuidelineReportService:
    @staticmethod
    def generate_guideline_pdf(guideline_id: str) -> bytes:
        from app.services.reports.pdf_framework import (
            PDFColors, NumberedCanvas, EnterprisePDFTheme, PDFComponentBuilder
        )
        info = BACKEND_GUIDELINES.get(guideline_id, BACKEND_GUIDELINES["keywords"])
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=42
        )
        theme = EnterprisePDFTheme()
        builder = PDFComponentBuilder(theme)
        story = []

        builder.build_header_banner(
            story,
            report_title=info["title"],
            domain="Integration Workspace",
            project_name=f"Dataset Spec ({info['version']})",
            crawl_timestamp=datetime.utcnow().strftime("%B %d, %Y"),
            data_sources=f"Formats: {', '.join(info['supported_formats'])} | Max: {info['max_file_size']}"
        )

        # 1. Purpose
        story.append(Paragraph("1. Purpose & Source Data", theme.section_title))
        story.append(Paragraph(f"<b>Purpose:</b> {html.escape(info['purpose'])}", theme.body))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Where to get data:</b> {html.escape(info['where_to_get'])}", theme.body))
        story.append(Spacer(1, 12))

        # 2. Required & Optional Columns
        story.append(Paragraph("2. Required & Optional Column Matrix", theme.section_title))
        col_rows = []
        for c in info["required_columns"]:
            col_rows.append([
                Paragraph(f"<b>{c['name']}</b>", theme.table_cell_bold),
                Paragraph("<font color='#ef4444'><b>Required</b></font>", theme.table_cell),
                Paragraph(html.escape(c["description"]), theme.table_cell),
                Paragraph(f"<code>{html.escape(c['example'])}</code>", theme.table_cell)
            ])
        for c in info["optional_columns"]:
            col_rows.append([
                Paragraph(c["name"], theme.table_cell),
                Paragraph("<font color='#64748b'>Optional</font>", theme.table_cell),
                Paragraph(html.escape(c["description"]), theme.table_cell),
                Paragraph(f"<code>{html.escape(c['example'])}</code>", theme.table_cell)
            ])

        t_cols = builder.build_styled_table(
            ["Column Name", "Required?", "Description", "Example Value"],
            col_rows,
            col_widths=[120, 70, 200, 150]
        )
        story.append(t_cols)
        story.append(Spacer(1, 12))

        # 3. Synthetic Example Rows Table
        story.append(Paragraph("3. Synthetic Example Data Rows", theme.section_title))
        syn_rows = []
        for r in info["synthetic_rows"]:
            syn_rows.append([Paragraph(html.escape(str(cell)), theme.table_cell) for cell in r[:5]])

        t_syn = builder.build_styled_table(
            info["synthetic_headers"][:5],
            syn_rows,
            col_widths=[110, 140, 70, 60, 160]
        )
        story.append(t_syn)
        story.append(Spacer(1, 14))

        # 4. Data Privacy Warning Box
        story.append(Paragraph("4. Data Security & Data Privacy Notice", theme.section_title))
        warn_data = [
            [Paragraph("<font color='#ef4444'><b>SECURITY NOTICE — DO NOT UPLOAD SECRETS OR SENSITIVE CREDENTIALS</b></font>", theme.table_header)],
            [Paragraph(f"{info['privacy_warning']} Use the platform's secure OAuth 'Connect Account' flow for live integrations instead of embedding credentials in CSV files.", theme.body)]
        ]
        t_warn = Table(warn_data, colWidths=[540])
        t_warn.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PDFColors.CRITICAL_RED_BG),
            ('BOX', (0, 0), (-1, -1), 1, PDFColors.CRITICAL_RED),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_warn)

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()

    @staticmethod
    def generate_sample_template_csv(guideline_id: str) -> str:
        info = BACKEND_GUIDELINES.get(guideline_id, BACKEND_GUIDELINES["keywords"])
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(info["synthetic_headers"])
        for row in info["synthetic_rows"]:
            writer.writerow(row)
        return output.getvalue()
