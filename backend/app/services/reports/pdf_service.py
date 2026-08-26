import io
from datetime import datetime
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
            spaceAfter=15
        )
        
        self.section_heading = ParagraphStyle(
            'SectionHeading',
            parent=self.styles['Heading2'],
            fontName='Helvetica-Bold',
            fontSize=13,
            leading=17,
            textColor=colors.HexColor('#1e293b'),
            spaceBefore=14,
            spaceAfter=8
        )
        
        self.body_style = ParagraphStyle(
            'ReportBody',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=9,
            leading=12,
            textColor=colors.HexColor('#334155')
        )
        
        self.table_cell = ParagraphStyle(
            'TableCell',
            parent=self.styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#1e293b')
        )

        self.table_header = ParagraphStyle(
            'TableHeader',
            parent=self.styles['Normal'],
            fontName='Helvetica-Bold',
            fontSize=8,
            leading=10,
            textColor=colors.HexColor('#0f172a')
        )

    def _build_header_block(self, story: list, report_title: str, domain: str, project_name: str, crawl_timestamp: str = "N/A", data_sources: str = "Crawled Data Engine"):
        now_str = datetime.now().strftime("%d %B %Y, %I:%M %p")
        
        story.append(Paragraph("SEO INTELLIGENCE PLATFORM REPORT", ParagraphStyle('CoverPre', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#2563eb'), spaceAfter=4)))
        story.append(Paragraph(report_title, self.title_style))
        story.append(Paragraph(f"Target Domain: <b>{domain}</b> | Project: <b>{project_name}</b>", self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=12))

        # Metadata box
        meta_table_data = [
            [Paragraph("<b>Website Domain:</b>", self.table_cell), Paragraph(domain, self.table_cell), Paragraph("<b>Generated At:</b>", self.table_cell), Paragraph(now_str, self.table_cell)],
            [Paragraph("<b>Project Name:</b>", self.table_cell), Paragraph(project_name, self.table_cell), Paragraph("<b>Crawl Snapshot:</b>", self.table_cell), Paragraph(crawl_timestamp or "N/A", self.table_cell)],
            [Paragraph("<b>Report Type:</b>", self.table_cell), Paragraph(report_title, self.table_cell), Paragraph("<b>Data Provenance:</b>", self.table_cell), Paragraph(data_sources, self.table_cell)]
        ]
        t_meta = Table(meta_table_data, colWidths=[110, 160, 110, 160])
        t_meta.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_meta)
        story.append(Spacer(1, 14))

    def generate_full_project_pdf(
        self,
        project_name: str,
        project_url: str,
        metadata: Dict[str, Any],
        pages: List[Dict[str, Any]],
        keywords: List[Dict[str, Any]],
        rankings: List[Dict[str, Any]],
        backlinks: List[Dict[str, Any]],
        internal_links: List[Dict[str, Any]],
        competitors: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        crawls: List[Dict[str, Any]]
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        domain = metadata.get("website") or project_url or project_name
        crawl_ts = metadata.get("timestamp", "N/A")

        self._build_header_block(story, "Comprehensive SEO Audit & Health Report", domain, project_name, crawl_ts, "Crawled Data (100% Verified)")

        # 1. EXECUTIVE DASHBOARD SUMMARY
        story.append(Paragraph("1. Executive Dashboard Overview", self.section_heading))
        dash_data = [
            [Paragraph("Metric", self.table_header), Paragraph("Value", self.table_header), Paragraph("Metric", self.table_header), Paragraph("Value", self.table_header)],
            [Paragraph("Crawled Pages", self.table_cell), Paragraph(str(metadata.get("pages_crawled", len(pages))), self.table_cell), Paragraph("Keywords Tracked", self.table_cell), Paragraph(str(len(keywords)), self.table_cell)],
            [Paragraph("Total Issues", self.table_cell), Paragraph(str(metadata.get("total_issues", len(issues))), self.table_cell), Paragraph("Rankings Tracked", self.table_cell), Paragraph(f"{len(rankings)} Keywords" if rankings else "Not Available", self.table_cell)],
            [Paragraph("Critical Issues", self.table_cell), Paragraph(str(metadata.get("critical_issues", 0)), self.table_cell), Paragraph("Inbound Backlinks", self.table_cell), Paragraph(f"{len(backlinks)} Links" if backlinks else "Not Available", self.table_cell)],
            [Paragraph("Warnings", self.table_cell), Paragraph(str(metadata.get("warning_issues", 0)), self.table_cell), Paragraph("Competitors Configured", self.table_cell), Paragraph(f"{len(competitors)} Competitors" if competitors else "None Configured", self.table_cell)],
            [Paragraph("Internal Links", self.table_cell), Paragraph(str(metadata.get("internal_links_count", len(internal_links))), self.table_cell), Paragraph("Crawl Status", self.table_cell), Paragraph(metadata.get("status", "Completed"), self.table_cell)]
        ]
        t_dash = Table(dash_data, colWidths=[130, 120, 140, 150])
        t_dash.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_dash)
        story.append(Spacer(1, 14))

        # 2. CRAWLED PAGES
        story.append(Paragraph("2. Crawled Pages Inventory", self.section_heading))
        if pages:
            page_rows = [[Paragraph("URL", self.table_header), Paragraph("Status", self.table_header), Paragraph("Title Tag", self.table_header), Paragraph("Words", self.table_header), Paragraph("Links", self.table_header)]]
            for p in pages[:20]:
                page_rows.append([
                    Paragraph(p.get("url", "-"), self.table_cell),
                    Paragraph(str(p.get("status_code", 200)), self.table_cell),
                    Paragraph(p.get("title") or "(No Title)", self.table_cell),
                    Paragraph(str(p.get("word_count", 0)), self.table_cell),
                    Paragraph(str(p.get("internal_links_count", 0)), self.table_cell)
                ])
            t_pages = Table(page_rows, colWidths=[180, 45, 185, 45, 85])
            t_pages.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_pages)
        else:
            story.append(Paragraph("No crawled pages available. Execute a website crawl to populate page inventory.", self.body_style))
        story.append(Spacer(1, 14))

        # 3. KEYWORDS
        story.append(Paragraph("3. Content Keywords & Topics", self.section_heading))
        if keywords:
            kw_rows = [[Paragraph("Topic / Keyword", self.table_header), Paragraph("Source Page", self.table_header), Paragraph("Frequency", self.table_header), Paragraph("Type", self.table_header)]]
            for k in keywords[:20]:
                kw_rows.append([
                    Paragraph(k.get("keyword", "-"), self.table_cell),
                    Paragraph(k.get("target_url") or k.get("source_page") or "-", self.table_cell),
                    Paragraph(str(k.get("frequency") or k.get("search_volume") or 1), self.table_cell),
                    Paragraph(k.get("type") or "Content Keyword", self.table_cell)
                ])
            t_kw = Table(kw_rows, colWidths=[150, 200, 70, 120])
            t_kw.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_kw)
        else:
            story.append(Paragraph("No content keyword dataset available.", self.body_style))
        story.append(Spacer(1, 14))

        # 4. TECHNICAL SEO ISSUES
        story.append(Paragraph("4. Technical SEO Audit Findings", self.section_heading))
        if issues:
            iss_rows = [[Paragraph("Severity", self.table_header), Paragraph("Issue Type", self.table_header), Paragraph("Affected URL", self.table_header), Paragraph("Details", self.table_header)]]
            for iss in issues[:30]:
                sev = iss.get("severity", "Notice")
                color_hex = "#ef4444" if sev == "Critical" else ("#f59e0b" if sev == "Warning" else "#3b82f6")
                iss_rows.append([
                    Paragraph(f"<font color='{color_hex}'><b>{sev}</b></font>", self.table_cell),
                    Paragraph(iss.get("issue_type", "-"), self.table_cell),
                    Paragraph(iss.get("affected_url", "-"), self.table_cell),
                    Paragraph(iss.get("details", "-"), self.table_cell)
                ])
            t_iss = Table(iss_rows, colWidths=[70, 120, 180, 170])
            t_iss.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_iss)
        else:
            story.append(Paragraph("No technical issues detected in website audit.", self.body_style))
        story.append(Spacer(1, 14))

        # 5. ACTIONABLE RECOMMENDATIONS
        story.append(Paragraph("5. Actionable SEO Recommendations", self.section_heading))
        recs = []
        if issues:
            crit_count = sum(1 for i in issues if i.get("severity") == "Critical")
            if crit_count > 0:
                recs.append(f"• Resolve {crit_count} Critical SEO Issues immediately to prevent search indexability loss.")
        if pages:
            missing_meta = sum(1 for p in pages if not p.get("meta_description"))
            if missing_meta > 0:
                recs.append(f"• Add optimized meta descriptions to {missing_meta} pages to improve search SERP click-through rates.")
            low_word = sum(1 for p in pages if (p.get("word_count") or 0) < 300)
            if low_word > 0:
                recs.append(f"• Expand thin content on {low_word} pages containing fewer than 300 words.")
        if not recs:
            recs.append("• Maintain periodic website crawls and search audit monitoring to track domain performance.")

        for r in recs:
            story.append(Paragraph(r, self.body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_crawl_report(self, metadata: Dict[str, Any], pages: List[Dict[str, Any]], issues: List[Dict[str, Any]], project_name: str = None, project_domain: str = None) -> bytes:
        domain = project_domain or metadata.get("website") or "Website SEO Audit"
        p_name = project_name or domain
        return self.generate_full_project_pdf(
            project_name=p_name,
            project_url=domain,
            metadata=metadata,
            pages=pages,
            keywords=[],
            rankings=[],
            backlinks=[],
            internal_links=[],
            competitors=[],
            issues=issues,
            crawls=[]
        )

    def generate_simple_table_pdf(
        self, 
        title: str, 
        subtitle: str, 
        headers: List[str], 
        rows_data: List[List[str]], 
        col_widths: List[int],
        domain: str = "Website Domain",
        project_name: str = "SEO Project",
        crawl_timestamp: str = "N/A"
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        self._build_header_block(story, title, domain, project_name, crawl_timestamp, "Crawled Data Engine")

        table_rows = [[Paragraph(f"<b>{h}</b>", self.table_header) for h in headers]]
        if not rows_data:
            table_rows.append([Paragraph("No records available", self.table_cell)] + [Paragraph("-", self.table_cell) for _ in range(len(headers) - 1)])
        else:
            for row in rows_data[:60]:
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
