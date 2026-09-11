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
        "purpose": "Import target keyword lists, search term frequencies, CPC, and difficulty metrics into your project workspace.",
        "where_to_get": "Export keyword lists from your rank-tracking software, keyword planner, or SEO analytics tool.",
        "supported_formats": ["CSV", "XLSX"],
        "max_file_size": "25 MB",
        "version": "Version 1.2 — August 2026",
        "required_columns": [
            {"name": "Keyword", "description": "Target search phrase", "example": "solar panels australia"}
        ],
        "optional_columns": [
            {"name": "URL", "description": "Target landing page URL on your domain", "example": "https://example.com/solar-panels"},
            {"name": "Search Volume", "description": "Monthly search volume number", "example": "2400"},
            {"name": "Position", "description": "External rank position (if available)", "example": "5"},
            {"name": "Difficulty", "description": "Keyword difficulty percentage (0-100)", "example": "45"},
            {"name": "CPC", "description": "Cost Per Click in USD/AUD", "example": "3.50"},
            {"name": "Country", "description": "2-letter country code", "example": "AU"},
            {"name": "Language", "description": "Target language", "example": "English"}
        ],
        "synthetic_headers": ["Keyword", "URL", "Search Volume", "Position", "Difficulty", "CPC", "Country", "Language"],
        "synthetic_rows": [
            ["solar panels australia", "https://example.com/solar-panels", "2400", "5", "45", "3.50", "AU", "English"],
            ["commercial electrician sydney", "https://example.com/commercial", "1200", "12", "58", "5.20", "AU", "English"],
            ["emergency electrical repair", "https://example.com/emergency", "880", "3", "32", "6.10", "AU", "English"]
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
        "version": "Version 1.2 — August 2026",
        "required_columns": [
            {"name": "Keyword", "description": "Ranked search phrase", "example": "electrician near me"},
            {"name": "URL", "description": "Ranking target URL on your domain", "example": "https://example.com/services"},
            {"name": "Position", "description": "Actual Google search rank position number", "example": "8"}
        ],
        "optional_columns": [
            {"name": "Search Volume", "description": "Monthly estimated volume", "example": "3600"},
            {"name": "Country", "description": "Target geographic country code", "example": "AU"},
            {"name": "Device", "description": "Desktop or Mobile", "example": "Desktop"},
            {"name": "Search Engine", "description": "Search provider name", "example": "Google"},
            {"name": "Date", "description": "Snapshot ranking date (YYYY-MM-DD)", "example": "2026-08-26"}
        ],
        "synthetic_headers": ["Keyword", "URL", "Position", "Search Volume", "Country", "Device", "Search Engine", "Date"],
        "synthetic_rows": [
            ["electrician near me", "https://example.com/services", "8", "3600", "AU", "Desktop", "Google", "2026-08-26"],
            ["solar battery installer", "https://example.com/solar-batteries", "4", "1400", "AU", "Mobile", "Google", "2026-08-26"],
            ["industrial wiring expert", "https://example.com/industrial", "14", "590", "AU", "Desktop", "Google", "2026-08-26"]
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
        "version": "Version 1.2 — August 2026",
        "required_columns": [
            {"name": "Source URL", "description": "External website URL containing the link", "example": "https://industry-news.com/top-electricians"},
            {"name": "Target URL", "description": "Your website URL being linked to", "example": "https://example.com/services"},
            {"name": "Anchor Text", "description": "Clickable text of the link", "example": "Licensed Sydney Electricians"}
        ],
        "optional_columns": [
            {"name": "Referring Domain", "description": "External root domain name", "example": "industry-news.com"},
            {"name": "Link Type", "description": "Text, Image, or Redirect", "example": "Text"},
            {"name": "Follow/Nofollow", "description": "Follow, Nofollow, UGC, or Sponsored attribute", "example": "Follow"},
            {"name": "First Seen", "description": "Discovered date timestamp", "example": "2026-01-15"},
            {"name": "Last Seen", "description": "Last verified date timestamp", "example": "2026-08-20"}
        ],
        "synthetic_headers": ["Source URL", "Target URL", "Anchor Text", "Referring Domain", "Link Type", "Follow/Nofollow", "First Seen", "Last Seen"],
        "synthetic_rows": [
            ["https://industry-news.com/top-electricians", "https://example.com/services", "Licensed Sydney Electricians", "industry-news.com", "Text", "Follow", "2026-01-15", "2026-08-20"],
            ["https://trade-directory.org/listings/solar", "https://example.com/solar-panels", "Visit Website", "trade-directory.org", "Text", "Nofollow", "2026-03-10", "2026-08-22"]
        ],
        "privacy_warning": "Do not upload passwords, API keys, OAuth tokens, authentication cookies, private keys, payment information, or unnecessary personal/customer data."
    },
    "competitors": {
        "id": "competitors",
        "title": "Competitor Dataset Upload Guide",
        "purpose": "Import verified competitor domain lists and keyword overlap records for market intelligence.",
        "where_to_get": "Export competitor domain tracking datasets or SERP analysis files.",
        "supported_formats": ["CSV", "XLSX"],
        "max_file_size": "25 MB",
        "version": "Version 1.2 — August 2026",
        "required_columns": [
            {"name": "Competitor Domain", "description": "Competitor root domain name", "example": "competitor-electric.com"}
        ],
        "optional_columns": [
            {"name": "Competitor Name", "description": "Company or business name", "example": "Competitor Electric Co"},
            {"name": "Competitor URL", "description": "Main website homepage URL", "example": "https://competitor-electric.com"},
            {"name": "Location", "description": "Geographic market location", "example": "Sydney, Australia"},
            {"name": "Overlapping Keywords", "description": "Count of shared search phrases", "example": "450"}
        ],
        "synthetic_headers": ["Competitor Domain", "Competitor Name", "Competitor URL", "Location", "Overlapping Keywords"],
        "synthetic_rows": [
            ["competitor-electric.com", "Competitor Electric Co", "https://competitor-electric.com", "Sydney, Australia", "450"],
            ["apex-solar-solutions.com.au", "Apex Solar Solutions", "https://apex-solar-solutions.com.au", "Melbourne, Australia", "320"]
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
