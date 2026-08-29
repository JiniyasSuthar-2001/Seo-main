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
            [Paragraph("<b>Report Type:</b>", self.table_cell), Paragraph(report_title, self.table_cell), Paragraph("<b>Data Sources:</b>", self.table_cell), Paragraph(data_sources, self.table_cell)]
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

        self._build_header_block(story, "Full Website Health Report", domain, project_name, crawl_ts, "Automatic Website Scan & SEO Analysis")

        # 1. EXECUTIVE SUMMARY & OVERALL ASSESSMENT
        story.append(Paragraph("1. Executive Summary", self.section_heading))
        health = metadata.get("health_score", 100)
        scanned_count = len(pages)
        html_count = sum(1 for p in pages if p.get("status_code") == 200 and p.get("is_success", True) is not False)
        failed_count = sum(1 for p in pages if (p.get("status_code") or 0) >= 400 or p.get("fetch_status") in ("FAILED", "BLOCKED"))
        
        crit_count = sum(1 for i in issues if (i.get("severity") or i.get("priority") or "").lower() == "critical")
        warn_count = sum(1 for i in issues if (i.get("severity") or i.get("priority") or "").lower() == "warning")

        dash_data = [
            [Paragraph("Key Metric", self.table_header), Paragraph("Value", self.table_header), Paragraph("Key Metric", self.table_header), Paragraph("Value", self.table_header)],
            [Paragraph("Website Health Score", self.table_cell), Paragraph(f"<b>{health} / 100</b>", self.table_cell), Paragraph("Pages Scanned", self.table_cell), Paragraph(str(scanned_count), self.table_cell)],
            [Paragraph("Successfully Analyzed", self.table_cell), Paragraph(f"<b>{html_count}</b> pages", self.table_cell), Paragraph("Failed / Blocked", self.table_cell), Paragraph(f"<b>{failed_count}</b> pages", self.table_cell)],
            [Paragraph("Total Problems Found", self.table_cell), Paragraph(f"<b>{len(issues)}</b> issues", self.table_cell), Paragraph("Critical Problems", self.table_cell), Paragraph(f"<b>{crit_count}</b> critical", self.table_cell)],
            [Paragraph("Warning Issues", self.table_cell), Paragraph(f"<b>{warn_count}</b> warnings", self.table_cell), Paragraph("Scan Status", self.table_cell), Paragraph(metadata.get("status", "Completed"), self.table_cell)]
        ]
        t_dash = Table(dash_data, colWidths=[130, 120, 140, 150])
        t_dash.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_dash)
        story.append(Spacer(1, 10))

        # Plain-English Executive Assessment
        health_label = "in excellent condition" if health >= 85 else ("generally healthy with moderate items to address" if health >= 70 else "experiencing significant technical items needing immediate attention")
        story.append(Paragraph(
            f"<b>Overall Assessment:</b> The website <b>{domain}</b> is currently {health_label} with an overall health score of <b>{health}/100</b>. "
            f"Our audit evaluated {html_count} pages across core SEO rule categories. "
            f"{'The primary areas requiring attention are ' + ', '.join([i.get('title') for i in issues[:3]]) + '.' if issues else 'No critical issues were detected during the scan.'}",
            self.body_style
        ))
        story.append(Spacer(1, 14))

        # 2. HEALTH SCORE EXPLANATION
        story.append(Paragraph("2. Website Health Score Breakdown", self.section_heading))
        story.append(Paragraph(f"Current Overall Score: <b>{health} / 100</b>", ParagraphStyle('ScoreSub', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#2563eb'))))
        story.append(Spacer(1, 6))

        cat_breakdown_rows = [
            [Paragraph("Category", self.table_header), Paragraph("Checks Count", self.table_header), Paragraph("Passed", self.table_header), Paragraph("Issues Found", self.table_header), Paragraph("Status", self.table_header)]
        ]
        cat_data = metadata.get("category_checks_table") or []
        if not cat_data:
            cat_data = [
                {"category": "Crawlability & Access", "checks_performed": html_count, "passed": max(0, html_count - failed_count), "issues_count": failed_count, "status": "Evaluated"},
                {"category": "Technical SEO & Metadata", "checks_performed": html_count, "passed": html_count, "issues_count": len(issues), "status": "Evaluated"},
                {"category": "Page Content & Headings", "checks_performed": html_count, "passed": html_count, "issues_count": 0, "status": "Evaluated"},
                {"category": "PageSpeed Performance", "checks_performed": 0, "passed": 0, "issues_count": 0, "status": "Not Measured"},
                {"category": "Inbound Backlinks", "checks_performed": 0, "passed": 0, "issues_count": 0, "status": "Not Measured"}
            ]

        for c in cat_data[:12]:
            st = c.get("status", "Evaluated")
            st_color = "#10b981" if "pass" in st.lower() or st == "Passed" else ("#ef4444" if "issue" in st.lower() or c.get("issues_count", 0) > 0 else "#64748b")
            cat_breakdown_rows.append([
                Paragraph(c.get("category", "-"), self.table_cell),
                Paragraph(str(c.get("checks_performed", html_count)), self.table_cell),
                Paragraph(str(c.get("passed", 0)), self.table_cell),
                Paragraph(str(c.get("issues_count", 0)), self.table_cell),
                Paragraph(f"<font color='{st_color}'><b>{st}</b></font>", self.table_cell)
            ])
        t_cat = Table(cat_breakdown_rows, colWidths=[150, 90, 80, 90, 130])
        t_cat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cat)
        story.append(Spacer(1, 14))

        # 3. WHAT WE CHECKED
        story.append(Paragraph("3. What We Checked", self.section_heading))
        evaluated_rules = metadata.get("evaluated_rules_count", 14)
        total_checks_count = html_count * evaluated_rules
        story.append(Paragraph(
            f"Our website scan performed <b>{total_checks_count:,} total rule evaluations</b> ({html_count} analyzed pages × {evaluated_rules} evaluated rules). Below is the category breakdown:",
            self.body_style
        ))
        story.append(Spacer(1, 6))

        checklist_text = (
            "• <b>Crawl & Accessibility:</b> HTTP Status Codes, Server Availability, Robots Restrictions, Redirects, Canonical URLs<br/>"
            "• <b>Page SEO:</b> Title Tag Existence & Length, Meta Description Optimization, H1 Headings, Heading Hierarchy<br/>"
            "• <b>Content Quality:</b> Word Count & Content Depth, Thin Copy Detection, Missing Metadata<br/>"
            "• <b>Links & Navigation:</b> Broken Internal Links, Broken External Links, Anchor Text, Link Lineage<br/>"
            "• <b>Security & Technical:</b> SSL Encryption, Viewport Meta Tags, Language Hreflangs, Schema.org Markup"
        )
        story.append(Paragraph(checklist_text, self.body_style))
        story.append(Spacer(1, 14))

        # 4. PROBLEMS WE FOUND & AI SOLUTIONS
        story.append(Paragraph("4. Problems We Found & Evidence", self.section_heading))
        if issues:
            for idx, iss in enumerate(issues[:15]):
                sev = (iss.get("severity") or iss.get("priority") or "Warning").upper()
                color_hex = "#ef4444" if sev == "CRITICAL" else ("#f59e0b" if sev == "WARNING" else "#3b82f6")
                urls_list = iss.get("affected_urls") or ([iss.get("affected_url")] if iss.get("affected_url") else [])
                
                story.append(Paragraph(f"<b>4.{idx+1} {iss.get('title', 'Detected Issue')}</b> <font color='{color_hex}'>[{sev}]</font>", ParagraphStyle('ProbTitle', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0f172a'))))
                story.append(Paragraph(f"<b>Affected Pages ({len(urls_list)}):</b> {', '.join(urls_list[:3])}{' (and more...)' if len(urls_list) > 3 else ''}", self.body_style))
                story.append(Paragraph(f"<b>What We Found:</b> {iss.get('description') or iss.get('details') or 'Issue detected during scan.'}", self.body_style))
                story.append(Paragraph(f"<b>Why It Matters:</b> Search engines may struggle to accurately index or rank affected pages, impacting organic visibility.", self.body_style))
                story.append(Paragraph(f"<b>Recommended Action:</b> {iss.get('recommendation', 'Review and update affected page content.')}", self.body_style))
                
                ai_sol = iss.get("ai_solution") or f"Implement unique <{iss.get('category', 'SEO')}> updates tailored specifically to the page topic and user search intent."
                story.append(Paragraph(f"<b>AI Solution:</b> {ai_sol} <i>(Source: Automatic AI Solution Engine)</i>", ParagraphStyle('AISolText', parent=self.body_style, textColor=colors.HexColor('#2563eb'))))
                story.append(Spacer(1, 8))
            
            if len(issues) > 15:
                story.append(Paragraph(f"<i>Showing 15 of {len(issues)} technical problems. Download the accompanying Problems_Found.csv for the complete dataset.</i>", ParagraphStyle('IssTrunc', parent=self.body_style, fontSize=8, textColor=colors.HexColor('#64748b'))))
        else:
            story.append(Paragraph("✓ Zero problems detected in the latest website scan.", self.body_style))
        story.append(Spacer(1, 14))

        # 5. NEAR-FUTURE IMPROVEMENT PLAN (NEXT SEO IMPROVEMENTS)
        story.append(Paragraph("5. Next SEO Improvements (Roadmap)", self.section_heading))
        story.append(Paragraph("Based on audit findings and website content, we recommend the following prioritized execution roadmap:", self.body_style))
        story.append(Spacer(1, 6))

        roadmap_data = [
            [Paragraph("Timeframe", self.table_header), Paragraph("Focus Area", self.table_header), Paragraph("Recommended Action", self.table_header), Paragraph("Expected Benefit", self.table_header)],
            [Paragraph("<b>NOW (Immediate)</b>", self.table_cell), Paragraph("Critical Audit Issues", self.table_cell), Paragraph("Fix broken URLs, resolve crawl blocks, and add missing title tags.", self.table_cell), Paragraph("Restores indexability and search crawler access.", self.table_cell)],
            [Paragraph("<b>NEXT 30 DAYS</b>", self.table_cell), Paragraph("Metadata & On-Page SEO", self.table_cell), Paragraph("Write unique meta descriptions (150-160 chars) and optimize H1 headings.", self.table_cell), Paragraph("Improves SERP CTR and topic relevance signals.", self.table_cell)],
            [Paragraph("<b>NEXT 60-90 DAYS</b>", self.table_cell), Paragraph("Content Depth & Links", self.table_cell), Paragraph("Expand thin content pages (< 150 words) and strengthen internal linking.", self.table_cell), Paragraph("Boosts topical authority and page rank flow.", self.table_cell)],
            [Paragraph("<b>ONGOING</b>", self.table_cell), Paragraph("Monitoring & Maintenance", self.table_cell), Paragraph("Run bi-weekly website scans, monitor rankings, and review Search Console.", self.table_cell), Paragraph("Prevents technical regressions and protects search traffic.", self.table_cell)]
        ]
        t_road = Table(roadmap_data, colWidths=[110, 110, 190, 130])
        t_road.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_road)
        story.append(Spacer(1, 14))

        # 6. TARGET KEYWORDS & CONTENT FREQUENCIES
        story.append(Paragraph("6. Target Keywords & Content Frequencies", self.section_heading))
        if keywords:
            display_kw = keywords[:15]
            kw_rows = [[Paragraph("Keyword", self.table_header), Paragraph("Content Frequency", self.table_header), Paragraph("Pages Found", self.table_header), Paragraph("Google Position", self.table_header)]]
            for k in display_kw:
                pos_val = f"#{k.get('position')}" if k.get("position") else "Not connected (Search Console Data)"
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

        # 7. LINKS OVERVIEW
        story.append(Paragraph("7. Website Links Overview", self.section_heading))
        story.append(Paragraph(f"• <b>Internal Links (Between Your Pages):</b> {len(internal_links)} links discovered.", self.body_style))
        story.append(Paragraph(f"• <b>Outbound Links (To Other Websites):</b> {len(outbound)} external links found on your site.", self.body_style))
        story.append(Paragraph(f"• <b>Inbound Links (From Other Websites):</b> {len(backlinks)} backlink records." if backlinks else "• <b>Inbound Links (From Other Websites):</b> No inbound backlink dataset connected.", self.body_style))
        story.append(Spacer(1, 14))

        # 8. DATA LIMITATIONS & NOT CONNECTED SERVICES
        story.append(Paragraph("8. Data Limitations & Unconnected Services", self.section_heading))
        lim_text = (
            "• <b>Google Search Console / Ranking Data:</b> Not connected. Connect Search Console in Integrations to track daily Google keyword positions.<br/>"
            "• <b>Inbound Backlinks:</b> No backlink dataset connected. Connect backlink integration or import backlink CSV to evaluate domain authority.<br/>"
            "• <b>PageSpeed Performance:</b> Not measured during this crawl. Configure PageSpeed API key in Settings to measure Core Web Vitals."
        )
        story.append(Paragraph(lim_text, self.body_style))
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
