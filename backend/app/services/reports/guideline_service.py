import io
import csv
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
        info = BACKEND_GUIDELINES.get(guideline_id, BACKEND_GUIDELINES["keywords"])
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('GTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#0f172a'))
        sub_style = ParagraphStyle('GSub', parent=styles['Normal'], fontName='Helvetica', fontSize=10, leading=13, textColor=colors.HexColor('#64748b'))
        h2_style = ParagraphStyle('GH2', parent=styles['Heading2'], fontName='Helvetica-Bold', fontSize=12, leading=15, textColor=colors.HexColor('#1e293b'), spaceBefore=12, spaceAfter=6)
        body_style = ParagraphStyle('GBody', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=12, textColor=colors.HexColor('#334155'))
        table_cell = ParagraphStyle('GCell', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, textColor=colors.HexColor('#1e293b'))
        table_header = ParagraphStyle('GHead', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10, textColor=colors.HexColor('#0f172a'))

        story.append(Paragraph("SEO INTELLIGENCE PLATFORM", ParagraphStyle('Pre', parent=body_style, fontName='Helvetica-Bold', fontSize=9, textColor=colors.HexColor('#2563eb'), spaceAfter=2)))
        story.append(Paragraph(info["title"], title_style))
        story.append(Paragraph(f"{info['version']} | Target Formats: {', '.join(info['supported_formats'])} | Max Size: {info['max_file_size']}", sub_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=12))

        # 1. Purpose
        story.append(Paragraph("1. Purpose & Source Data", h2_style))
        story.append(Paragraph(f"<b>Purpose:</b> {info['purpose']}", body_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"<b>Where to get data:</b> {info['where_to_get']}", body_style))
        story.append(Spacer(1, 10))

        # 2. Required & Optional Columns
        story.append(Paragraph("2. Required & Optional Column Matrix", h2_style))
        col_rows = [[Paragraph("Column Name", table_header), Paragraph("Required?", table_header), Paragraph("Description", table_header), Paragraph("Example Value", table_header)]]
        
        for c in info["required_columns"]:
            col_rows.append([
                Paragraph(f"<b>{c['name']}</b>", table_cell),
                Paragraph("<font color='#ef4444'><b>Required</b></font>", table_cell),
                Paragraph(c["description"], table_cell),
                Paragraph(f"<code>{c['example']}</code>", table_cell)
            ])
        for c in info["optional_columns"]:
            col_rows.append([
                Paragraph(c["name"], table_cell),
                Paragraph("<font color='#64748b'>Optional</font>", table_cell),
                Paragraph(c["description"], table_cell),
                Paragraph(f"<code>{c['example']}</code>", table_cell)
            ])

        t_cols = Table(col_rows, colWidths=[120, 70, 200, 150])
        t_cols.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cols)
        story.append(Spacer(1, 10))

        # 3. Synthetic Example Rows Table
        story.append(Paragraph("3. Synthetic Example Data Rows", h2_style))
        syn_rows = [[Paragraph(f"<b>{h}</b>", table_header) for h in info["synthetic_headers"][:5]]]
        for r in info["synthetic_rows"]:
            syn_rows.append([Paragraph(str(cell), table_cell) for cell in r[:5]])

        t_syn = Table(syn_rows, colWidths=[110, 140, 70, 60, 160])
        t_syn.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_syn)
        story.append(Spacer(1, 12))

        # 4. Data Privacy Warning Box
        story.append(Paragraph("4. Data Security & Data Privacy Notice", h2_style))
        warn_data = [
            [Paragraph("<font color='#ef4444'><b>SECURITY WARNING — DO NOT UPLOAD SECRETS OR CREDENTIALS</b></font>", table_header)],
            [Paragraph(f"{info['privacy_warning']} Use the platform's secure OAuth 'Connect Account' flow for live integrations instead of putting credentials in CSV files.", body_style)]
        ]
        t_warn = Table(warn_data, colWidths=[540])
        t_warn.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#fca5a5')),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(t_warn)

        doc.build(story)
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
