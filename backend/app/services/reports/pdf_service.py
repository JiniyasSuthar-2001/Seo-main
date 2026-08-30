import io
import html
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
        project_name: str = None,
        project_url: str = None,
        metadata: Dict[str, Any] = None,
        pages: List[Dict[str, Any]] = None,
        keywords: List[Dict[str, Any]] = None,
        rankings: List[Dict[str, Any]] = None,
        backlinks: List[Dict[str, Any]] = None,
        internal_links: List[Dict[str, Any]] = None,
        competitors: List[Dict[str, Any]] = None,
        issues: List[Dict[str, Any]] = None,
        crawls: List[Dict[str, Any]] = None,
        opportunities: Optional[List[Dict[str, Any]]] = None,
        ai_insights: Optional[Dict[str, Any]] = None,
        outbound_links: Optional[List[Dict[str, Any]]] = None,
        master_report: Optional[Dict[str, Any]] = None
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        story = []

        if master_report:
            p_obj = master_report.get("project", {})
            c_obj = master_report.get("crawl", {})
            h_obj = master_report.get("health", {})
            project_name = p_obj.get("name", project_name or "Website")
            domain = p_obj.get("domain", project_url or "Website")
            crawl_ts = c_obj.get("timestamp", "N/A")
            pages = master_report.get("affected_pages", [])
            keywords = master_report.get("keywords", [])
            issues = master_report.get("problems", [])
            opportunities = master_report.get("opportunities", [])
            ai_data = master_report.get("ai_analysis", {})
            internal_links = master_report.get("content_and_links", {}).get("internal_links", [])
            outbound = master_report.get("content_and_links", {}).get("outbound_links", [])
            backlinks = master_report.get("backlinks", {}).get("inbound_backlinks", [])
            competitors = master_report.get("competitors", [])
            aeo_list = master_report.get("aeo", [])
            geo_list = master_report.get("geo", [])
            hist_obj = master_report.get("historical_comparison", {})
            road_list = master_report.get("next_improvements", [])
            limits_list = master_report.get("data_limitations", [])
            health = h_obj.get("health_score", 100)
        else:
            domain = (metadata.get("website") if metadata else None) or project_url or project_name or "Website"
            crawl_ts = metadata.get("timestamp", "N/A") if metadata else "N/A"
            pages = pages or []
            keywords = keywords or []
            issues = issues or []
            opportunities = opportunities or []
            ai_data = ai_insights or {}
            internal_links = internal_links or []
            outbound = outbound_links or []
            backlinks = backlinks or []
            competitors = competitors or []
            aeo_list = []
            geo_list = []
            hist_obj = {}
            road_list = []
            limits_list = []
            health = metadata.get("health_score", 100) if metadata else 100

        self._build_header_block(story, "Full Website Health Report", domain, project_name, crawl_ts, "Automatic Website Scan & SEO Analysis")

        # 1. EXECUTIVE SUMMARY & OVERALL ASSESSMENT
        story.append(Paragraph("1. Executive Summary", self.section_heading))
        scanned_count = len(pages)
        html_count = sum(1 for p in pages if p.get("status_code") == 200 and p.get("is_success", True) is not False)
        failed_count = sum(1 for p in pages if (p.get("status_code") or 0) >= 400 or p.get("fetch_status") in ("FAILED", "BLOCKED"))
        
        crit_count = sum(1 for i in issues if str(i.get("severity") or i.get("priority") or "").lower() in ("critical", "fatal"))
        warn_count = sum(1 for i in issues if str(i.get("severity") or i.get("priority") or "").lower() in ("warning", "medium"))

        dash_data = [
            [Paragraph("Key Metric", self.table_header), Paragraph("Value", self.table_header), Paragraph("Key Metric", self.table_header), Paragraph("Value", self.table_header)],
            [Paragraph("Website Health Score", self.table_cell), Paragraph(f"<b>{health} / 100</b>", self.table_cell), Paragraph("Pages Scanned", self.table_cell), Paragraph(str(scanned_count), self.table_cell)],
            [Paragraph("Successfully Analyzed", self.table_cell), Paragraph(f"<b>{html_count}</b> pages", self.table_cell), Paragraph("Failed / Blocked", self.table_cell), Paragraph(f"<b>{failed_count}</b> pages", self.table_cell)],
            [Paragraph("Total Problems Found", self.table_cell), Paragraph(f"<b>{len(issues)}</b> issues", self.table_cell), Paragraph("Critical Problems", self.table_cell), Paragraph(f"<b>{crit_count}</b> critical", self.table_cell)],
            [Paragraph("Warning Issues", self.table_cell), Paragraph(f"<b>{warn_count}</b> warnings", self.table_cell), Paragraph("Scan Status", self.table_cell), Paragraph("Completed", self.table_cell)]
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
        exec_raw = ai_data.get("executive_assessment") or (
            f"The website {domain} is in {'excellent' if health >= 85 else 'sound'} condition with an overall health score of {health}/100. "
            f"The audit evaluated {scanned_count} pages across core SEO rule categories."
        )
        exec_text = html.escape(str(exec_raw))
        story.append(Paragraph(f"<b>Overall Assessment:</b> {exec_text}", self.body_style))
        story.append(Spacer(1, 14))

        # 2. HEALTH SCORE EXPLANATION
        story.append(Paragraph("2. Website Health Score Breakdown", self.section_heading))
        story.append(Paragraph(f"Current Overall Score: <b>{health} / 100</b>", ParagraphStyle('ScoreSub', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#2563eb'))))
        story.append(Spacer(1, 6))

        cat_breakdown_rows = [
            [Paragraph("Category / Area", self.table_header), Paragraph("Status", self.table_header), Paragraph("Issues Found", self.table_header), Paragraph("Impact Description", self.table_header), Paragraph("Where This Data Came From", self.table_header)]
        ]
        cat_data = [
            {"category": "Crawlability & Access", "status": "Passed" if failed_count == 0 else "Needs Attention", "issues": f"{failed_count} errors", "impact": "Search engine bots can access audited pages", "source": "Automatic Website Check"},
            {"category": "Technical SEO & HTTP Status", "status": "Audited", "issues": f"{crit_count} issues", "impact": "Server response codes and canonical directives", "source": "Automatic Website Check"},
            {"category": "Page Content & Headings", "status": "Audited", "issues": f"{warn_count} issues", "impact": "Title tags, meta descriptions, and word counts", "source": "Automatic Website Check"},
            {"category": "Internal Links Structure", "status": "Audited", "issues": f"{len(internal_links)} links", "impact": "Page interconnectivity and anchor text", "source": "Automatic Website Check"},
            {"category": "PageSpeed Performance", "status": "Not Measured", "issues": "0", "impact": "Page load speed was not measured during this crawl", "source": "Data Not Connected"},
            {"category": "Inbound Backlinks", "status": "Not Measured" if not backlinks else "Connected", "issues": "0" if not backlinks else str(len(backlinks)), "impact": "External referring backlink profiles", "source": "Data Not Connected" if not backlinks else "Imported Backlink API"}
        ]

        for c in cat_data:
            st = c.get("status", "Audited")
            st_color = "#10b981" if "pass" in st.lower() or st == "Passed" else ("#ef4444" if "attention" in st.lower() else "#64748b")
            cat_breakdown_rows.append([
                Paragraph(c.get("category", "-"), self.table_cell),
                Paragraph(f"<font color='{st_color}'><b>{st}</b></font>", self.table_cell),
                Paragraph(str(c.get("issues", "0")), self.table_cell),
                Paragraph(c.get("impact", ""), self.table_cell),
                Paragraph(c.get("source", "Automatic Scan"), self.table_cell)
            ])
        t_cat = Table(cat_breakdown_rows, colWidths=[130, 80, 70, 150, 110])
        t_cat.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(t_cat)
        story.append(Spacer(1, 14))

        # 3. FULL LIST OF SEO CHECKS PERFORMED
        story.append(Paragraph("3. Full List of SEO Checks Performed", self.section_heading))
        checklist_text = (
            f"The crawler completed a <b>14-point deep audit inspection</b> across {scanned_count} pages ({scanned_count * 14} total rule checks):<br/>"
            "• <b>Crawl & Accessibility:</b> HTTP Status Codes, Server Availability, Robots Restrictions, Redirects, Canonical URLs<br/>"
            "• <b>Page SEO:</b> Title Tag Existence & Length, Meta Description Optimization, H1 Headings, Heading Hierarchy<br/>"
            "• <b>Content Quality:</b> Word Count & Content Depth (>= 300 words), Thin Copy Detection, Missing Metadata<br/>"
            "• <b>Links & Navigation:</b> Broken Internal Links, Broken External Links, Anchor Text Distribution<br/>"
            "• <b>Security & Technical:</b> HTTPS Protocol Consistency, Canonical Link Tags, Search Engine Indexability"
        )
        story.append(Paragraph(checklist_text, self.body_style))
        story.append(Spacer(1, 14))

        # 4. PROBLEMS WE FOUND & AI SOLUTIONS
        story.append(Paragraph("4. Problems We Found & Evidence", self.section_heading))
        if issues:
            for idx, iss in enumerate(issues[:15]):
                sev = str(iss.get("severity") or iss.get("priority") or "Warning").upper()
                ind = iss.get("indicator") or ("🔴" if sev in ("CRITICAL", "FATAL") else "🟠" if sev in ("HIGH", "ERROR") else "🟡" if sev in ("WARNING", "MEDIUM") else "🔵")
                color_hex = "#ef4444" if sev in ("CRITICAL", "FATAL") else ("#f59e0b" if sev in ("HIGH", "WARNING") else "#3b82f6")
                url = html.escape(str(iss.get("affected_url") or iss.get("url") or domain))
                
                prob_title = html.escape(str(iss.get("problem") or iss.get("title") or iss.get("issue") or "Detected Finding"))
                story.append(Paragraph(f"<b>4.{idx+1} {ind} {prob_title}</b> <font color='{color_hex}'>[{sev}]</font>", ParagraphStyle('ProbTitle', parent=self.body_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor('#0f172a'))))
                story.append(Paragraph(f"<b>Affected URL:</b> {url}", self.body_style))
                story.append(Paragraph(f"<b>What We Found:</b> {html.escape(str(iss.get('what_was_found') or iss.get('evidence') or iss.get('description') or 'Observed in crawl.'))}", self.body_style))
                story.append(Paragraph(f"<b>Why It Matters:</b> {html.escape(str(iss.get('why_it_matters') or 'Search engines may struggle to accurately index or rank affected pages, impacting organic visibility.'))}", self.body_style))
                story.append(Paragraph(f"<b>Recommended Action:</b> {html.escape(str(iss.get('recommended_action') or iss.get('recommendation') or 'Update affected page content.'))}", self.body_style))
                
                ai_sol = html.escape(str(iss.get("ai_solution") or f"Implement unique updates tailored specifically to the page topic."))
                story.append(Paragraph(f"<b>AI Solution:</b> {ai_sol} <i>(Source: Automatic Website Check + AI Analysis)</i>", ParagraphStyle('AISolText', parent=self.body_style, textColor=colors.HexColor('#2563eb'))))
                story.append(Spacer(1, 8))
            
            if len(issues) > 15:
                story.append(Paragraph(f"<i>Showing 15 of {len(issues)} problems. See accompanying Problems_Found.csv / XLSX for the complete dataset.</i>", ParagraphStyle('IssTrunc', parent=self.body_style, fontSize=8, textColor=colors.HexColor('#64748b'))))
        else:
            story.append(Paragraph("✓ Zero problems detected in the latest website scan.", self.body_style))
        story.append(Spacer(1, 14))

        # 5. PRIORITIZED SEO OPPORTUNITIES
        story.append(Paragraph("5. Prioritized SEO Opportunities", self.section_heading))
        if opportunities:
            for opp in opportunities[:6]:
                opp_title = html.escape(str(opp.get('title') or 'SEO Opportunity'))
                opp_url = html.escape(str(opp.get('url') or opp.get('affected_url') or domain))
                opp_act = html.escape(str(opp.get('recommended_action') or opp.get('action') or 'N/A'))
                opp_sol = html.escape(str(opp.get('ai_solution') or 'Implement targeted optimization.'))
                story.append(Paragraph(f"• <b>[{opp.get('priority', 'Medium')}] {opp_title}</b> — {opp_url}", self.body_style))
                story.append(Paragraph(f"   <i>Action:</i> {opp_act}", ParagraphStyle('OppAction', parent=self.body_style, leftIndent=12)))
                story.append(Paragraph(f"   <i>AI Solution:</i> {opp_sol}", ParagraphStyle('OppSol', parent=self.body_style, leftIndent=12, textColor=colors.HexColor('#2563eb'))))
                story.append(Spacer(1, 4))
        else:
            story.append(Paragraph("No central SEO opportunities identified.", self.body_style))
        story.append(Spacer(1, 14))

        # 6. NEAR-FUTURE IMPROVEMENT PLAN (NEXT SEO IMPROVEMENTS)
        story.append(Paragraph("6. Next SEO Improvements (Roadmap)", self.section_heading))
        story.append(Paragraph("Based on verified crawl findings, we recommend the following phased execution roadmap:", self.body_style))
        story.append(Spacer(1, 6))

        roadmap_data = [
            [Paragraph("Timeframe", self.table_header), Paragraph("Focus Area", self.table_header), Paragraph("Recommended Action", self.table_header), Paragraph("Expected Benefit", self.table_header)],
            [Paragraph("<b>NOW (0–7 Days)</b>", self.table_cell), Paragraph("Critical Technical Issues", self.table_cell), Paragraph("Fix broken 404 URLs, resolve crawl errors, and repair broken links.", self.table_cell), Paragraph("Restores full crawlability and indexing access.", self.table_cell)],
            [Paragraph("<b>NEXT 30 DAYS</b>", self.table_cell), Paragraph("Metadata & On-Page SEO", self.table_cell), Paragraph("Rewrite missing/short meta titles (30-60 chars) and meta descriptions.", self.table_cell), Paragraph("Improves SERP snippet display and organic CTR.", self.table_cell)],
            [Paragraph("<b>NEXT 60-90 DAYS</b>", self.table_cell), Paragraph("Content Depth & Links", self.table_cell), Paragraph("Expand thin content pages (< 300 words) and add contextual internal links.", self.table_cell), Paragraph("Boosts topical authority and page rank flow.", self.table_cell)],
            [Paragraph("<b>ONGOING</b>", self.table_cell), Paragraph("Monitoring & Maintenance", self.table_cell), Paragraph("Run automated weekly website scans, monitor rankings, and track backlinks.", self.table_cell), Paragraph("Prevents technical regressions and protects search traffic.", self.table_cell)]
        ]
        t_road = Table(roadmap_data, colWidths=[100, 110, 200, 130])
        t_road.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f1f5f9')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t_road)
        story.append(Spacer(1, 14))

        # 7. TARGET KEYWORDS & CONTENT FREQUENCIES
        story.append(Paragraph("7. Target Keywords & Content Frequencies", self.section_heading))
        if keywords:
            display_kw = keywords[:12]
            kw_rows = [[Paragraph("Keyword / Topic", self.table_header), Paragraph("Content Frequency", self.table_header), Paragraph("Target Page URL", self.table_header), Paragraph("Google Position", self.table_header)]]
            for k in display_kw:
                kw_rows.append([
                    Paragraph(k.get("keyword", "-"), self.table_cell),
                    Paragraph(f"{k.get('frequency', 1)} times", self.table_cell),
                    Paragraph(k.get("target_url") or domain, self.table_cell),
                    Paragraph("Data Not Connected (Search Console)", self.table_cell)
                ])
            t_kw = Table(kw_rows, colWidths=[150, 90, 160, 140])
            t_kw.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f8fafc')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(t_kw)
        else:
            story.append(Paragraph("No extracted content keywords available.", self.body_style))
        story.append(Spacer(1, 14))

        # 8. LINKS OVERVIEW
        story.append(Paragraph("8. Website Links Overview", self.section_heading))
        story.append(Paragraph(f"• <b>Internal Links (Between Your Pages):</b> {len(internal_links)} links discovered across site.", self.body_style))
        story.append(Paragraph(f"• <b>Outbound Links (To Other Websites):</b> {len(outbound)} external links found on your pages.", self.body_style))
        story.append(Paragraph(f"• <b>Inbound Links (From Other Websites):</b> {len(backlinks)} backlink records." if backlinks else "• <b>Inbound Links (From Other Websites):</b> No inbound backlink dataset connected.", self.body_style))
        story.append(Spacer(1, 14))

        # 9. HISTORICAL COMPARISON
        if hist_obj.get("has_previous_crawl"):
            story.append(Paragraph("9. Historical Crawl Comparison", self.section_heading))
            story.append(Paragraph(
                f"• Previous Score: <b>{hist_obj.get('previous_score')}/100</b> | Latest Score: <b>{hist_obj.get('current_score')}/100</b> ({hist_obj.get('score_delta'):+d} points)<br/>"
                f"• Problems Resolved: <b>{hist_obj.get('problems_fixed_count')} issues fixed</b> since previous scan.<br/>"
                f"• New Findings: <b>{hist_obj.get('new_problems_count')} new issues detected</b>.<br/>"
                f"• AI Trend Summary: {hist_obj.get('ai_trend_summary')}",
                self.body_style
            ))
            story.append(Spacer(1, 14))

        # 10. DATA LIMITATIONS & NOT CONNECTED SERVICES
        story.append(Paragraph("10. Data Limitations & Unconnected Services", self.section_heading))
        lim_text = (
            "• <b>Google Search Console / Ranking Data:</b> Data Not Connected. Connect Search Console in Integrations to track daily Google keyword positions.<br/>"
            "• <b>Inbound Backlinks:</b> No inbound backlink dataset connected. Connect backlink integration to evaluate external referring domain authority.<br/>"
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
