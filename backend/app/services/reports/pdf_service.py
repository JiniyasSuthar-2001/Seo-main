import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Any, List

class PDFReportGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        
        # Custom Brand Styles
        self.title_style = ParagraphStyle(
            'ReportTitle',
            parent=self.styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=22,
            leading=26,
            textColor=colors.HexColor('#0f172a'),
            spaceAfter=6
        )
        
        self.subtitle_style = ParagraphStyle(
            'ReportSubtitle',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=11,
            leading=14,
            textColor=colors.HexColor('#64748b'),
            spaceAfter=20
        )
        
        self.section_heading = ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=14,
            leading=18,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=16,
            spaceAfter=10
        )
        
        self.body_style = ParagraphStyle(
            'ReportBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            leading=13,
            textColor=colors.HexColor('#334155')
        )
        
        self.table_cell = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=11,
            textColor=colors.HexColor('#1e293b')
        )

    def generate_crawl_report(self, metadata: Dict[str, Any], pages: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        # 1. Header Banner
        domain_name = metadata.get("website", "Website SEO Report")
        story.append(Paragraph(f"SEO Audit Report: {domain_name}", self.title_style))
        story.append(Paragraph(f"Snapshot Timestamp: {metadata.get('timestamp', 'N/A')} | Pages Crawled: {metadata.get('pages_crawled', 0)} | Total Issues: {metadata.get('total_issues', 0)}", self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

        # 2. Executive KPI Summary
        summary_data = [
            [Paragraph("<b>Metric</b>", self.table_cell), Paragraph("<b>Value</b>", self.table_cell)],
            [Paragraph("Crawled Pages", self.table_cell), Paragraph(str(metadata.get("pages_crawled", 0)), self.table_cell)],
            [Paragraph("Critical Issues", self.table_cell), Paragraph(str(metadata.get("critical_issues", 0)), self.table_cell)],
            [Paragraph("Warning Issues", self.table_cell), Paragraph(str(metadata.get("warning_issues", 0)), self.table_cell)],
            [Paragraph("Notice Issues", self.table_cell), Paragraph(str(metadata.get("notice_issues", 0)), self.table_cell)],
            [Paragraph("Internal Links Discovered", self.table_cell), Paragraph(str(metadata.get("internal_links_count", 0)), self.table_cell)]
        ]
        
        t_summary = Table(summary_data, colWidths=[200, 300])
        t_summary.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(t_summary)
        story.append(Spacer(1, 20))

        # 3. Technical SEO Issues Table
        story.append(Paragraph("Technical SEO Audit Findings", self.section_heading))
        if issues:
            issue_rows = [[Paragraph("<b>Severity</b>", self.table_cell), Paragraph("<b>Issue Type</b>", self.table_cell), Paragraph("<b>Affected URL</b>", self.table_cell)]]
            for iss in issues[:30]:
                sev = iss.get("severity", "Notice")
                color_hex = "#ef4444" if sev == "Critical" else ("#f59e0b" if sev == "Warning" else "#3b82f6")
                issue_rows.append([
                    Paragraph(f"<font color='{color_hex}'><b>{sev}</b></font>", self.table_cell),
                    Paragraph(iss.get("issue_type", "-"), self.table_cell),
                    Paragraph(iss.get("affected_url", "-"), self.table_cell)
                ])
            t_issues = Table(issue_rows, colWidths=[80, 150, 270])
            t_issues.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(t_issues)
        else:
            story.append(Paragraph("No technical issues detected in this crawl snapshot.", self.body_style))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_simple_table_pdf(self, title: str, subtitle: str, headers: List[str], rows_data: List[List[str]], col_widths: List[int]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph(title, self.title_style))
        story.append(Paragraph(subtitle, self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

        table_rows = [[Paragraph(f"<b>{h}</b>", self.table_cell) for h in headers]]
        for row in rows_data[:50]:
            table_rows.append([Paragraph(str(cell or "-"), self.table_cell) for cell in row])

        t = Table(table_rows, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
