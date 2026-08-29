import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Any, List, Optional

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

    def _build_header_block(self, story: list, report_title: str, domain: str, project_name: str, crawl_timestamp: str = "N/A", data_sources: str = "Website Scan"):
        now_str = datetime.now().strftime("%d %B %Y, %I:%M %p")
        
        story.append(Paragraph("SEO INTELLIGENCE PLATFORM REPORT", ParagraphStyle('CoverPre', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#2563eb'), spaceAfter=4)))
        story.append(Paragraph(report_title, self.title_style))
        story.append(Paragraph(f"Target Website: <b>{domain}</b> | Project: <b>{project_name}</b>", self.subtitle_style))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#2563eb'), spaceAfter=12))

        # Metadata box
        meta_table_data = [
            [Paragraph("<b>Website Domain:</b>", self.table_cell), Paragraph(domain, self.table_cell), Paragraph("<b>Generated Date:</b>", self.table_cell), Paragraph(now_str, self.table_cell)],
            [Paragraph("<b>Project Name:</b>", self.table_cell), Paragraph(project_name, self.table_cell), Paragraph("<b>Scan Timestamp:</b>", self.table_cell), Paragraph(crawl_timestamp or "N/A", self.table_cell)],
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
        crawls: List[Dict[str, Any]],
        opportunities: Optional[List[Dict[str, Any]]] = None,
        ai_insights: Optional[Dict[str, Any]] = None,
        outbound_links: Optional[List[Dict[str, Any]]] = None
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        domain = metadata.get("website") or project_url or project_name
        crawl_ts = metadata.get("timestamp", "N/A")
        opps_list = opportunities or []
        ai_data = ai_insights or {}
        outbound = outbound_links or []

        self._build_header_block(story, "Website Health & SEO Audit Report", domain, project_name, crawl_ts, "Website Scan & Audit Engine")

        # 1. EXECUTIVE OVERVIEW
        story.append(Paragraph("1. Executive Overview", self.section_heading))
        health = metadata.get("health_score", 100)
        dash_data = [
            [Paragraph("Key Metric", self.table_header), Paragraph("Value", self.table_header), Paragraph("Key Metric", self.table_header), Paragraph("Value", self.table_header)],
            [Paragraph("Website Health Score", self.table_cell), Paragraph(f"<b>{health} / 100</b>", self.table_cell), Paragraph("Keywords Extracted", self.table_cell), Paragraph(f"{len(keywords)} Terms", self.table_cell)],
            [Paragraph("Pages Scanned", self.table_cell), Paragraph(str(metadata.get("pages_crawled", len(pages))), self.table_cell), Paragraph("Search Rankings", self.table_cell), Paragraph(f"{len(rankings)} Tracked" if rankings else "Not Available", self.table_cell)],
            [Paragraph("Problems Found", self.table_cell), Paragraph(str(metadata.get("total_issues", len(issues))), self.table_cell), Paragraph("Inbound Backlinks", self.table_cell), Paragraph(f"{len(backlinks)} Links" if backlinks else "Not Available", self.table_cell)],
            [Paragraph("Critical Problems", self.table_cell), Paragraph(str(metadata.get("critical_issues", 0)), self.table_cell), Paragraph("Outbound Links Found", self.table_cell), Paragraph(f"{len(outbound)} Links", self.table_cell)],
            [Paragraph("Internal Links", self.table_cell), Paragraph(str(metadata.get("internal_links_count", len(internal_links))), self.table_cell), Paragraph("Scan Status", self.table_cell), Paragraph(metadata.get("status", "Completed"), self.table_cell)]
        ]
        t_dash = Table(dash_data, colWidths=[130, 120, 140, 150])
        t_dash.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_dash)
        story.append(Spacer(1, 14))

        # 2. CRAWLED PAGES INVENTORY
        story.append(Paragraph("2. Pages Found on Your Site", self.section_heading))
        if pages:
            display_pages = pages[:20]
            page_rows = [[Paragraph("Page Address / URL", self.table_header), Paragraph("Status", self.table_header), Paragraph("Page Title", self.table_header), Paragraph("Word Count", self.table_header), Paragraph("Page Links", self.table_header)]]
            for p in display_pages:
                page_rows.append([
                    Paragraph(p.get("url", "-"), self.table_cell),
                    Paragraph(str(p.get("status_code", 200)), self.table_cell),
                    Paragraph(p.get("title") or "(Missing Page Title)", self.table_cell),
                    Paragraph(str(p.get("word_count", 0)), self.table_cell),
                    Paragraph(str(p.get("internal_links_count", 0)), self.table_cell)
                ])
            t_pages = Table(page_rows, colWidths=[180, 45, 185, 55, 75])
            t_pages.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_pages)
            if len(pages) > 20:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<i>Showing 20 of {len(pages)} pages. Download the complete Pages CSV for all pages.</i>", ParagraphStyle('PagesTrunc', parent=self.body_style, fontSize=8, textColor=colors.HexColor('#64748b'))))
        else:
            story.append(Paragraph("No scanned pages available. Run a website scan to map page inventory.", self.body_style))
        story.append(Spacer(1, 14))

        # 3. PROBLEMS WE FOUND & EVIDENCE
        story.append(Paragraph("3. Problems We Found (Audit Findings & Evidence)", self.section_heading))
        if issues:
            display_issues = issues[:25]
            iss_rows = [[Paragraph("Priority", self.table_header), Paragraph("Category", self.table_header), Paragraph("Problem Finding", self.table_header), Paragraph("Affected Page URL", self.table_header)]]
            for iss in display_issues:
                sev = iss.get("severity") or iss.get("priority") or "Warning"
                color_hex = "#ef4444" if sev.lower() == "critical" else ("#f59e0b" if sev.lower() == "warning" else "#3b82f6")
                iss_rows.append([
                    Paragraph(f"<font color='{color_hex}'><b>{sev.upper()}</b></font>", self.table_cell),
                    Paragraph(iss.get("issue_type") or iss.get("category") or "Technical", self.table_cell),
                    Paragraph(iss.get("title") or iss.get("details") or "Issue detected", self.table_cell),
                    Paragraph(iss.get("affected_url") or "-", self.table_cell)
                ])
            t_iss = Table(iss_rows, colWidths=[70, 110, 200, 160])
            t_iss.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_iss)
            if len(issues) > 25:
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<i>Showing 25 of {len(issues)} technical problems. Download the complete Technical Issues CSV for all evidence.</i>", ParagraphStyle('IssTrunc', parent=self.body_style, fontSize=8, textColor=colors.HexColor('#64748b'))))
        else:
            story.append(Paragraph("✓ Zero problems detected in latest website scan.", self.body_style))
        story.append(Spacer(1, 14))

        # 4. RECOMMENDED ACTIONS
        story.append(Paragraph("4. Recommended Actions (Opportunity Engine)", self.section_heading))
        if opps_list:
            display_opps = opps_list[:15]
            o_rows = [[Paragraph("Priority", self.table_header), Paragraph("Action Title", self.table_header), Paragraph("Recommended Fix", self.table_header)]]
            for o in display_opps:
                o_rows.append([
                    Paragraph(str(o.get("priority_level") or o.get("priority") or "Medium").upper(), self.table_cell),
                    Paragraph(o.get("title", "-"), self.table_cell),
                    Paragraph(o.get("recommendation", "-"), self.table_cell)
                ])
            t_opps = Table(o_rows, colWidths=[80, 200, 260])
            t_opps.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_opps)
        else:
            story.append(Paragraph("No recommended actions generated. Website health is verified.", self.body_style))
        story.append(Spacer(1, 14))

        # 5. KEYWORDS & TOPICS
        story.append(Paragraph("5. Target Keywords & Content Frequencies", self.section_heading))
        if keywords:
            display_kw = keywords[:20]
            kw_rows = [[Paragraph("Keyword", self.table_header), Paragraph("Content Frequency", self.table_header), Paragraph("Pages Found", self.table_header), Paragraph("Google Position", self.table_header)]]
            for k in display_kw:
                pos_val = f"#{k.get('position')}" if k.get("position") else "Not available (Connect Search Data)"
                kw_rows.append([
                    Paragraph(k.get("keyword", "-"), self.table_cell),
                    Paragraph(f"{k.get('frequency') or k.get('search_volume') or 1} times", self.table_cell),
                    Paragraph(f"{k.get('pages_found', 1)} pages", self.table_cell),
                    Paragraph(pos_val, self.table_cell)
                ])
            t_kw = Table(kw_rows, colWidths=[160, 100, 90, 190])
            t_kw.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_kw)
        else:
            story.append(Paragraph("No content keyword dataset available.", self.body_style))
        story.append(Spacer(1, 14))

        # 6. SEARCH RANKINGS
        story.append(Paragraph("6. Search Rankings", self.section_heading))
        if rankings:
            display_rk = rankings[:20]
            rk_rows = [[Paragraph("Keyword", self.table_header), Paragraph("Target URL", self.table_header), Paragraph("Google Position", self.table_header), Paragraph("Change", self.table_header)]]
            for r in display_rk:
                rk_rows.append([
                    Paragraph(r.get("keyword", "-"), self.table_cell),
                    Paragraph(r.get("url", "-"), self.table_cell),
                    Paragraph(str(r.get("position", "Not available")), self.table_cell),
                    Paragraph(str(r.get("change", 0)), self.table_cell)
                ])
            t_rk = Table(rk_rows, colWidths=[160, 220, 100, 60])
            t_rk.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_rk)
        else:
            story.append(Paragraph("Ranking data is not available for this project.", self.body_style))
        story.append(Spacer(1, 14))

        # 7. LINKS (Internal, Outbound, Inbound)
        story.append(Paragraph("7. Website Links Overview", self.section_heading))
        story.append(Paragraph(f"• <b>Internal Links (Between Your Pages):</b> {len(internal_links)} links discovered.", self.body_style))
        story.append(Paragraph(f"• <b>Outbound Links (To Other Websites):</b> {len(outbound)} external links found on your site.", self.body_style))
        story.append(Paragraph(f"• <b>Inbound Links (From Other Websites):</b> {len(backlinks)} backlink records." if backlinks else "• <b>Inbound Links (From Other Websites):</b> Not available for this project.", self.body_style))
        story.append(Spacer(1, 14))

        # 8. COMPETITORS
        story.append(Paragraph("8. Competitor Comparison", self.section_heading))
        if competitors:
            comp_rows = [[Paragraph("Competitor", self.table_header), Paragraph("Domain", self.table_header), Paragraph("Relevance Match", self.table_header)]]
            for c in competitors[:10]:
                comp_rows.append([
                    Paragraph(c.get("name", "-"), self.table_cell),
                    Paragraph(c.get("domain", "-"), self.table_cell),
                    Paragraph(f"{c.get('relevance_score', 0)}%", self.table_cell)
                ])
            t_comp = Table(comp_rows, colWidths=[200, 220, 120])
            t_comp.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_comp)
        else:
            story.append(Paragraph("Competitor data is not available for this project.", self.body_style))
        story.append(Spacer(1, 14))

        # 9. AI INSIGHTS
        story.append(Paragraph("9. AI Insights & Recommendations", self.section_heading))
        ai_summary = ai_data.get("summary") or ai_data.get("message")
        ai_findings = ai_data.get("findings") or ai_data.get("insights") or []

        if ai_findings and isinstance(ai_findings, list) and len(ai_findings) > 0:
            story.append(Paragraph(f"<b>AI Executive Analysis:</b> {ai_summary}", self.body_style))
            story.append(Spacer(1, 6))
            for f in ai_findings[:10]:
                f_title = f.get("finding") or f.get("title") or "AI Finding"
                f_rec = f.get("recommendation") or f.get("description") or ""
                f_sev = f.get("severity") or f.get("priority") or "Medium"
                story.append(Paragraph(f"• <b>[{f_sev.upper()}] {f_title}:</b> {f_rec} <i>(Source: AI Analysis)</i>", self.body_style))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("AI analysis has not been generated for this project.", self.body_style))
        story.append(Spacer(1, 14))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

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

        self._build_header_block(story, title, domain, project_name, crawl_timestamp, "Website Scan")

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

        if len(rows_data) > 60:
            story.append(Spacer(1, 4))
            story.append(Paragraph(f"<i>Showing 60 of {len(rows_data)} records. Download the complete CSV for full dataset.</i>", ParagraphStyle('SimpleTrunc', parent=self.body_style, fontSize=8, textColor=colors.HexColor('#64748b'))))

        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
