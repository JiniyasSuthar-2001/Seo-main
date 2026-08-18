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

        # COVER / TITLE HEADER
        story.append(Paragraph(f"SEO PROJECT AUDIT REPORT", ParagraphStyle('CoverPre', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#2563eb'), spaceAfter=4)))
        story.append(Paragraph(project_name, self.title_style))
        story.append(Paragraph(f"Target Website: {project_url} | Generated: {datetime.utcnow().strftime('%B %d, %Y')}", self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=14))

        # 1. EXECUTIVE DASHBOARD SUMMARY
        story.append(Paragraph("1. Executive Dashboard Overview", self.section_heading))
        dash_data = [
            [Paragraph("Metric", self.table_header), Paragraph("Value", self.table_header), Paragraph("Metric", self.table_header), Paragraph("Value", self.table_header)],
            [Paragraph("Crawled Pages", self.table_cell), Paragraph(str(metadata.get("pages_crawled", len(pages))), self.table_cell), Paragraph("Keywords Tracked", self.table_cell), Paragraph(str(len(keywords)), self.table_cell)],
            [Paragraph("Total Issues", self.table_cell), Paragraph(str(metadata.get("total_issues", len(issues))), self.table_cell), Paragraph("Rankings Tracked", self.table_cell), Paragraph(f"{len(rankings)} Keywords", self.table_cell)],
            [Paragraph("Critical Issues", self.table_cell), Paragraph(str(metadata.get("critical_issues", 0)), self.table_cell), Paragraph("Backlinks Mapped", self.table_cell), Paragraph(f"{len(backlinks)} Links", self.table_cell)],
            [Paragraph("Warnings", self.table_cell), Paragraph(str(metadata.get("warning_issues", 0)), self.table_cell), Paragraph("Competitors Configured", self.table_cell), Paragraph(f"{len(competitors)} Competitors", self.table_cell)],
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
        story.append(Paragraph("3. Keyword Intelligence & Topics", self.section_heading))
        if keywords:
            kw_rows = [[Paragraph("Keyword", self.table_header), Paragraph("Target URL", self.table_header), Paragraph("Volume", self.table_header), Paragraph("Difficulty", self.table_header), Paragraph("Intent", self.table_header)]]
            for k in keywords[:20]:
                kw_rows.append([
                    Paragraph(k.get("keyword", "-"), self.table_cell),
                    Paragraph(k.get("target_url", "-"), self.table_cell),
                    Paragraph(str(k.get("search_volume") or "-"), self.table_cell),
                    Paragraph(str(k.get("difficulty") or "-"), self.table_cell),
                    Paragraph(k.get("intent") or "Informational", self.table_cell)
                ])
            t_kw = Table(kw_rows, colWidths=[130, 180, 70, 70, 90])
            t_kw.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_kw)
        else:
            story.append(Paragraph("No keyword dataset available.", self.body_style))
        story.append(Spacer(1, 14))

        # 4. RANKINGS
        story.append(Paragraph("4. Search Engine Rankings", self.section_heading))
        if rankings:
            rk_rows = [[Paragraph("Keyword", self.table_header), Paragraph("Position", self.table_header), Paragraph("Engine", self.table_header), Paragraph("Device", self.table_header), Paragraph("Target URL", self.table_header)]]
            for r in rankings[:20]:
                rk_rows.append([
                    Paragraph(r.get("keyword", "-"), self.table_cell),
                    Paragraph(str(r.get("position") or "-"), self.table_cell),
                    Paragraph(r.get("engine", "Google"), self.table_cell),
                    Paragraph(r.get("device", "Desktop"), self.table_cell),
                    Paragraph(r.get("url", "-"), self.table_cell)
                ])
            t_rk = Table(rk_rows, colWidths=[130, 50, 70, 60, 230])
            t_rk.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_rk)
        else:
            story.append(Paragraph("No ranking dataset available.", self.body_style))
        story.append(Spacer(1, 14))

        # 5. BACKLINKS
        story.append(Paragraph("5. Backlink Profile", self.section_heading))
        if backlinks:
            bl_rows = [[Paragraph("Source URL", self.table_header), Paragraph("Target URL", self.table_header), Paragraph("Anchor Text", self.table_header), Paragraph("Type", self.table_header)]]
            for b in backlinks[:20]:
                bl_rows.append([
                    Paragraph(b.get("source_url", "-"), self.table_cell),
                    Paragraph(b.get("target_url", "-"), self.table_cell),
                    Paragraph(b.get("anchor_text") or "(No Text)", self.table_cell),
                    Paragraph(b.get("link_type", "Dofollow"), self.table_cell)
                ])
            t_bl = Table(bl_rows, colWidths=[180, 180, 110, 70])
            t_bl.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_bl)
        else:
            story.append(Paragraph("No backlink dataset available.", self.body_style))
        story.append(Spacer(1, 14))

        # 6. INTERNAL LINKS
        story.append(Paragraph("6. Internal Link Graph", self.section_heading))
        if internal_links:
            il_rows = [[Paragraph("Source Page", self.table_header), Paragraph("Target Page", self.table_header), Paragraph("Anchor Text", self.table_header)]]
            for l in internal_links[:20]:
                il_rows.append([
                    Paragraph(l.get("source", "-"), self.table_cell),
                    Paragraph(l.get("target", "-"), self.table_cell),
                    Paragraph(l.get("anchor_text") or "(No Anchor)", self.table_cell)
                ])
            t_il = Table(il_rows, colWidths=[200, 200, 140])
            t_il.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_il)
        else:
            story.append(Paragraph("No internal link data available.", self.body_style))
        story.append(Spacer(1, 14))

        # 7. COMPETITORS
        story.append(Paragraph("7. Competitor Intelligence", self.section_heading))
        if competitors:
            comp_rows = [[Paragraph("Competitor", self.table_header), Paragraph("Domain", self.table_header), Paragraph("Common Keywords", self.table_header), Paragraph("Visibility Index", self.table_header)]]
            for c in competitors[:10]:
                comp_rows.append([
                    Paragraph(c.get("name", "-"), self.table_cell),
                    Paragraph(c.get("domain", "-"), self.table_cell),
                    Paragraph(str(c.get("keywords_count", "-")), self.table_cell),
                    Paragraph(str(c.get("visibility", "N/A")), self.table_cell)
                ])
            t_comp = Table(comp_rows, colWidths=[150, 170, 110, 110])
            t_comp.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_comp)
        else:
            story.append(Paragraph("No competitors configured.", self.body_style))
        story.append(Spacer(1, 14))

        # 8. TECHNICAL SEO ISSUES
        story.append(Paragraph("8. Technical SEO Audit Findings", self.section_heading))
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

        # 9. CRAWL HISTORY
        story.append(Paragraph("9. Historical Crawl Snapshots", self.section_heading))
        if crawls:
            cr_rows = [[Paragraph("Crawl Date", self.table_header), Paragraph("Start URL", self.table_header), Paragraph("Pages", self.table_header), Paragraph("Issues", self.table_header), Paragraph("Status", self.table_header)]]
            for cr in crawls[:10]:
                cr_rows.append([
                    Paragraph(str(cr.get("timestamp") or cr.get("started_at") or "N/A"), self.table_cell),
                    Paragraph(cr.get("url") or project_url, self.table_cell),
                    Paragraph(str(cr.get("pages_crawled", 0)), self.table_cell),
                    Paragraph(str(cr.get("issues_found", 0)), self.table_cell),
                    Paragraph(cr.get("status", "Completed"), self.table_cell)
                ])
            t_cr = Table(cr_rows, colWidths=[120, 200, 60, 60, 100])
            t_cr.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_cr)
        else:
            story.append(Paragraph("No historical crawl snapshots available.", self.body_style))
        story.append(Spacer(1, 14))

        # 10. SEO RECOMMENDATIONS
        story.append(Paragraph("10. Actionable SEO Recommendations", self.section_heading))
        recs = []
        if issues:
            crit_count = sum(1 for i in issues if i.get("severity") == "Critical")
            if crit_count > 0:
                recs.append(f"• Resolve {crit_count} Critical SEO Issues immediately to prevent indexing/crawl budget loss.")
        if pages:
            missing_meta = sum(1 for p in pages if not p.get("meta_description"))
            if missing_meta > 0:
                recs.append(f"• Add optimized meta descriptions to {missing_meta} pages to improve search SERP click-through rates.")
            low_word = sum(1 for p in pages if (p.get("word_count") or 0) < 300)
            if low_word > 0:
                recs.append(f"• Expand thin content on {low_word} pages containing fewer than 300 words.")
        if not recs:
            recs.append("• Maintain periodic website crawls and keyword ranking monitoring to track domain performance.")

        for r in recs:
            story.append(Paragraph(r, self.body_style))
            story.append(Spacer(1, 4))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def generate_crawl_report(self, metadata: Dict[str, Any], pages: List[Dict[str, Any]], issues: List[Dict[str, Any]]) -> bytes:
        return self.generate_full_project_pdf(
            project_name=metadata.get("website", "Website SEO Audit"),
            project_url=metadata.get("website", "https://uisdigital.com/"),
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

    def generate_simple_table_pdf(self, title: str, subtitle: str, headers: List[str], rows_data: List[List[str]], col_widths: List[int]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        story.append(Paragraph(title, self.title_style))
        story.append(Paragraph(subtitle, self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e2e8f0'), spaceAfter=15))

        table_rows = [[Paragraph(f"<b>{h}</b>", self.table_header) for h in headers]]
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
