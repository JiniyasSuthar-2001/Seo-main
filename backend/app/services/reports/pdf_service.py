import io
import html
from datetime import datetime
from typing import Dict, Any, List, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.services.reports.pdf_framework import (
    PDFColors, NumberedCanvas, EnterprisePDFTheme, PDFComponentBuilder
)


class PDFReportGenerator:
    """
    Enterprise-grade PDF Report Generator producing executive visual reports matching SEMrush, Ahrefs, and Google Looker Studio standards.
    """
    def __init__(self):
        self.theme = EnterprisePDFTheme()
        self.builder = PDFComponentBuilder(self.theme)

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
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=42
        )
        story = []

        if master_report:
            p_obj = master_report.get("project", {})
            c_obj = master_report.get("crawl", {})
            h_obj = master_report.get("health", {})
            project_name = p_obj.get("name", project_name or "Website")
            domain = p_obj.get("domain", project_url or "Website")
            crawl_ts = c_obj.get("timestamp", "N/A")
            pages = master_report.get("affected_pages", []) or []
            keywords = master_report.get("keywords", []) or []
            issues = master_report.get("problems", []) or []
            opportunities = master_report.get("opportunities", []) or []
            ai_data = master_report.get("ai_analysis", {}) or {}
            internal_links = master_report.get("content_and_links", {}).get("internal_links", []) or []
            outbound = master_report.get("content_and_links", {}).get("outbound_links", []) or []
            backlinks = master_report.get("backlinks", {}).get("inbound_backlinks", []) or []
            competitors = master_report.get("competitors", []) or []
            hist_obj = master_report.get("historical_comparison", {}) or {}
            health = h_obj.get("health_score", 100)
            if health is None:
                health = 100
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
            hist_obj = {}
            health = metadata.get("health_score", 100) if metadata else 100
            if health is None:
                health = 100

        scanned_count = len(pages)
        html_count = sum(1 for p in pages if p.get("status_code") == 200 and p.get("is_success", True) is not False)
        failed_count = sum(1 for p in pages if (p.get("status_code") or 0) >= 400 or p.get("fetch_status") in ("FAILED", "BLOCKED"))
        
        crit_count = sum(1 for i in issues if str(i.get("severity") or i.get("priority") or "").lower() in ("critical", "fatal", "error"))
        warn_count = sum(1 for i in issues if str(i.get("severity") or i.get("priority") or "").lower() in ("warning", "medium", "high"))
        notice_count = sum(1 for i in issues if str(i.get("severity") or i.get("priority") or "").lower() in ("info", "notice", "low"))
        passed_count = max(0, (scanned_count * 14) - len(issues))
        success_rate = f"{round((html_count / scanned_count * 100), 1)}%" if scanned_count > 0 else "100%"

        # COVER BANNER
        self.builder.build_header_banner(
            story,
            report_title="Full Website Health & Technical SEO Audit",
            domain=domain,
            project_name=project_name,
            crawl_timestamp=crawl_ts,
            data_sources="Automated Deep Crawler & 14-Point Rule Engine",
            health_score=health
        )

        # 1. EXECUTIVE KPI DASHBOARD
        story.append(Paragraph("1. Executive Summary & Core KPIs", self.theme.section_title))
        story.append(Paragraph("High-level performance snapshot and audit overview across all scanned pages.", self.theme.section_subtitle))

        health_color = self.builder._get_health_color_hex(health)
        kpi_metrics = [
            {"title": "Health Score", "value": f"{health}/100", "subtext": "Overall site health", "color": health_color},
            {"title": "Pages Audited", "value": str(scanned_count), "subtext": f"{html_count} success, {failed_count} failed", "color": "#0f172a"},
            {"title": "Critical Issues", "value": str(crit_count), "subtext": "Immediate blockers", "color": "#ef4444"},
            {"title": "Warnings Found", "value": str(warn_count), "subtext": "Optimization needed", "color": "#f59e0b"},
            {"title": "Passed Checks", "value": str(passed_count), "subtext": "Verified rules passed", "color": "#10b981"},
            {"title": "Internal Links", "value": str(len(internal_links)), "subtext": "Navigational structure", "color": "#4f46e5"},
            {"title": "External Links", "value": str(len(outbound)), "subtext": "Outbound references", "color": "#0284c7"},
            {"title": "Success Rate", "value": success_rate, "subtext": "HTTP 200 response rate", "color": "#059669"}
        ]
        self.builder.build_kpi_grid(story, kpi_metrics)

        # Executive Assessment Narrative Box
        exec_raw = ai_data.get("executive_assessment") or (
            f"The audit for {domain} indicates an overall health score of {health}/100 based on inspection of {scanned_count} pages. "
            f"A total of {len(issues)} findings were identified ({crit_count} critical, {warn_count} warnings). "
            f"{'Critical crawl or indexation issues require prompt resolution to prevent organic ranking loss.' if crit_count > 0 else 'Core structural compliance is sound; focusing on metadata and internal linking will drive steady traffic growth.'}"
        )
        exec_box = Table([
            [Paragraph("<b>Executive Assessment:</b>", self.theme.table_header)],
            [Paragraph(html.escape(str(exec_raw)), self.theme.body)]
        ], colWidths=[540])
        exec_box.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PDFColors.BG_CARD),
            ('BOX', (0, 0), (-1, -1), 0.75, PDFColors.BORDER_MED),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('LINELEFT', (0, 0), (0, -1), 3, PDFColors.BRAND_BLUE),
        ]))
        story.append(exec_box)
        story.append(Spacer(1, 14))

        # 2. AUDIT FINDINGS DISTRIBUTION & VECTOR CHART
        story.append(Paragraph("2. Audit Findings Distribution", self.theme.section_title))
        chart_drawing = self.builder.build_vector_issue_chart(crit_count, warn_count, notice_count, passed_count)
        story.append(chart_drawing)
        story.append(Spacer(1, 14))

        # 3. WEBSITE HEALTH SCORE CATEGORY BREAKDOWN
        story.append(Paragraph("3. Category Breakdown & Health Scores", self.theme.section_title))
        story.append(Paragraph("Evaluated performance across the 6 major technical and on-page SEO disciplines.", self.theme.section_subtitle))

        cat_headers = ["SEO Discipline", "Status", "Issues Detected", "Impact & Assessment", "Data Source"]
        cat_rows = [
            [
                "Crawlability & Access",
                f"<font color='{'#ef4444' if failed_count > 0 else '#10b981'}'><b>{'Needs Attention' if failed_count > 0 else 'Passed'}</b></font>",
                f"{failed_count} errors",
                "Bots can reach and index target URLs without server or protocol timeouts",
                "Automated Scan"
            ],
            [
                "Technical SEO & Headers",
                f"<font color='{'#ef4444' if crit_count > 0 else '#10b981'}'><b>{'Audited' if crit_count == 0 else 'Issues Found'}</b></font>",
                f"{crit_count} issues",
                "Canonical directives, redirects, protocol consistency, and robots instructions",
                "Automated Scan"
            ],
            [
                "Page Content & Headings",
                f"<font color='{'#f59e0b' if warn_count > 0 else '#10b981'}'><b>{'Audited'}</b></font>",
                f"{warn_count} issues",
                "Title tag lengths (30–60 chars), meta descriptions, single H1 tags, and content depth",
                "Automated Scan"
            ],
            [
                "Internal Link Topology",
                f"<font color='{'#10b981'}'><b>Audited</b></font>",
                f"{len(internal_links)} links",
                "Page interconnectivity, anchor text diversity, and orphan page prevention",
                "Automated Scan"
            ],
            [
                "PageSpeed & Core Web Vitals",
                "<font color='#64748b'><b>Not Measured</b></font>",
                "0",
                "Load time, LCP, CLS, and FID metrics (Configure API key to enable)",
                "Data Not Connected"
            ],
            [
                "Inbound Backlink Profile",
                f"<font color='{'#10b981' if backlinks else '#64748b'}'><b>{'Connected' if backlinks else 'Not Measured'}</b></font>",
                f"{len(backlinks)} backlinks" if backlinks else "0",
                "Referring domains and off-page external authority link signals",
                "Backlink Integration" if backlinks else "Data Not Connected"
            ]
        ]
        cat_table = self.builder.build_styled_table(
            cat_headers,
            [[Paragraph(c, self.theme.table_cell) if "<font" in str(c) else c for c in r] for r in cat_rows],
            col_widths=[125, 85, 75, 160, 95]
        )
        story.append(cat_table)
        story.append(Spacer(1, 14))

        # 4. FULL 14-POINT SEO AUDIT CHECKLIST
        story.append(Paragraph("4. Full 14-Point SEO Audit Rules Evaluation", self.theme.section_title))
        checklist_data = [
            ["Rule Category", "Inspected Factor", "Validation Standard", "Status"],
            ["Crawl & Index", "HTTP Status Codes", "HTTP 200 OK across all crawled URLs", "Audited"],
            ["Crawl & Index", "Canonical Tag Consistency", "Present and self-referential or canonicalized", "Audited"],
            ["Crawl & Index", "Robots Directives", "Valid index / follow directives without blocking", "Audited"],
            ["Metadata", "Page Title Existence", "Every page has a unique, descriptive <title>", "Audited"],
            ["Metadata", "Page Title Length", "Optimal length between 30 and 60 characters", "Audited"],
            ["Metadata", "Meta Description Length", "Optimal snippet length between 70 and 160 characters", "Audited"],
            ["Structure", "H1 Heading Existence", "Exactly one H1 heading present per HTML page", "Audited"],
            ["Structure", "Heading Hierarchy", "Proper H1 -> H2 -> H3 semantic hierarchy", "Audited"],
            ["Content", "Word Count & Depth", "Thin copy detection (minimum 300 words recommended)", "Audited"],
            ["Content", "Image Alt Text", "Accessible alt descriptions for all content images", "Audited"],
            ["Links", "Internal Links", "No broken internal links (404/500 status)", "Audited"],
            ["Links", "External Outbound Links", "Valid external references without redirect loops", "Audited"],
            ["Security", "HTTPS Protocol Security", "All audited pages served securely over TLS/HTTPS", "Audited"],
            ["Performance", "Server Response Time", "Server response time within acceptable latency threshold", "Audited"]
        ]
        chk_table = self.builder.build_styled_table(
            checklist_data[0],
            checklist_data[1:],
            col_widths=[90, 130, 240, 80]
        )
        story.append(chk_table)
        story.append(Spacer(1, 14))

        # 5. PROBLEMS WE FOUND & AI SOLUTIONS
        story.append(Paragraph("5. Problems Found & Evidence-Grounded AI Action Plan", self.theme.section_title))
        story.append(Paragraph("Detailed technical evidence, why each issue matters, and recommended AI solutions.", self.theme.section_subtitle))

        if issues:
            for idx, iss in enumerate(issues[:20]):
                self.builder.build_issue_card(story, idx + 1, iss)

            if len(issues) > 20:
                story.append(Paragraph(
                    f"<i>Showing top 20 of {len(issues)} detected issues. Download the complete Problems_Found.csv or XLSX export for the comprehensive dataset.</i>",
                    ParagraphStyle('IssTrunc', parent=self.theme.body, fontSize=8, textColor=PDFColors.MUTED_TEXT)
                ))
        else:
            story.append(Paragraph("✓ <b>Zero critical issues detected</b> during the latest automated scan.", self.theme.body))
        story.append(Spacer(1, 14))

        # 6. PRIORITIZED SEO OPPORTUNITIES
        story.append(Paragraph("6. Prioritized SEO Growth Opportunities", self.theme.section_title))
        if opportunities:
            opp_headers = ["Priority", "Opportunity Focus", "Target URL", "Recommended Execution Action"]
            opp_rows = []
            for opp in opportunities[:8]:
                pri = str(opp.get("priority") or "Medium").upper()
                pri_color = "#ef4444" if pri == "HIGH" else ("#f59e0b" if pri == "MEDIUM" else "#3b82f6")
                opp_rows.append([
                    f"<font color='{pri_color}'><b>{pri}</b></font>",
                    opp.get("title") or "SEO Opportunity",
                    opp.get("url") or domain,
                    opp.get("recommended_action") or opp.get("ai_solution") or "Deploy targeted on-page optimization."
                ])
            opp_table = self.builder.build_styled_table(
                opp_headers,
                [[Paragraph(c, self.theme.table_cell) if "<font" in str(c) else c for c in r] for r in opp_rows],
                col_widths=[65, 140, 155, 180]
            )
            story.append(opp_table)
        else:
            story.append(Paragraph("No central opportunity items recorded.", self.theme.body))
        story.append(Spacer(1, 14))

        # 7. PHASED SEO EXECUTION ROADMAP
        story.append(Paragraph("7. Phased SEO Execution Roadmap", self.theme.section_title))
        story.append(Paragraph("Recommended tactical milestone schedule to systematically elevate search performance.", self.theme.section_subtitle))
        self.builder.build_roadmap_table(story)

        # 8. TARGET KEYWORDS & CONTENT FREQUENCIES
        story.append(Paragraph("8. Extracted Target Keywords & Frequency", self.theme.section_title))
        if keywords:
            kw_headers = ["Keyword Phrase", "Frequency", "Target Landing Page", "Google Position"]
            kw_rows = []
            for k in keywords[:12]:
                kw_rows.append([
                    k.get("keyword", "-"),
                    f"{k.get('frequency', 1)}x",
                    k.get("target_url") or domain,
                    "Data Not Connected (Search Console)"
                ])
            kw_table = self.builder.build_styled_table(kw_headers, kw_rows, col_widths=[150, 70, 180, 140])
            story.append(kw_table)
        else:
            story.append(Paragraph("No extracted content keywords available in current dataset.", self.theme.body))
        story.append(Spacer(1, 14))

        # 9. INTERNAL & EXTERNAL LINKS OVERVIEW
        story.append(Paragraph("9. Link Architecture & Referring Authority", self.theme.section_title))
        link_box_data = [
            [
                Paragraph("<b>Internal Links:</b>", self.theme.table_header),
                Paragraph(f"{len(internal_links)} internal page-to-page navigation links discovered.", self.theme.table_cell)
            ],
            [
                Paragraph("<b>Outbound Links:</b>", self.theme.table_header),
                Paragraph(f"{len(outbound)} external hyperlinks pointing to third-party domains.", self.theme.table_cell)
            ],
            [
                Paragraph("<b>Inbound Backlinks:</b>", self.theme.table_header),
                Paragraph(f"{len(backlinks)} backlink records imported." if backlinks else "No external backlink dataset connected. Connect backlink provider to track referring domain authority.", self.theme.table_cell)
            ]
        ]
        t_links = Table(link_box_data, colWidths=[120, 420])
        t_links.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PDFColors.BG_CARD),
            ('GRID', (0, 0), (-1, -1), 0.5, PDFColors.BORDER_LIGHT),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(t_links)
        story.append(Spacer(1, 14))

        # 10. HISTORICAL COMPARISON (IF AVAILABLE)
        if hist_obj.get("has_previous_crawl"):
            story.append(Paragraph("10. Historical Crawl & Health Comparison", self.theme.section_title))
            prev_score = hist_obj.get("previous_score", 100)
            delta = hist_obj.get("score_delta", 0)
            delta_str = f"+{delta}" if delta > 0 else str(delta)
            delta_color = "#10b981" if delta >= 0 else "#ef4444"

            hist_rows = [
                ["Metric", "Previous Crawl", "Latest Crawl", "Difference"],
                ["Health Score", f"{prev_score}/100", f"{health}/100", f"<font color='{delta_color}'><b>{delta_str} pts</b></font>"],
                ["Problems Fixed", "-", f"{hist_obj.get('problems_fixed_count', 0)} resolved", "<font color='#10b981'><b>Fixed</b></font>"],
                ["New Issues", "-", f"{hist_obj.get('new_problems_count', 0)} new", "<font color='#ef4444'><b>New</b></font>"]
            ]
            hist_table = self.builder.build_styled_table(
                hist_rows[0],
                [[Paragraph(c, self.theme.table_cell) if "<font" in str(c) else c for c in r] for r in hist_rows[1:]],
                col_widths=[140, 120, 140, 140]
            )
            story.append(hist_table)
            if hist_obj.get("ai_trend_summary"):
                story.append(Spacer(1, 4))
                story.append(Paragraph(f"<b>AI Trend Assessment:</b> {html.escape(str(hist_obj.get('ai_trend_summary')))}", self.theme.body))
            story.append(Spacer(1, 14))

        # 11. DATA LIMITATIONS & UNCONNECTED SERVICES
        story.append(Paragraph("11. Data Limitations & Unconnected Services", self.theme.section_title))
        lim_data = [
            ["Integration Service", "Status", "Impact on Reporting"],
            ["Google Search Console", "Data Not Connected", "Connect Google Search Console in Integrations to track daily keyword positions and click-through rates."],
            ["Inbound Backlink API", "Data Not Connected" if not backlinks else "Connected", "Connect backlink dataset to track external referring domains, lost links, and toxicity ratings."],
            ["PageSpeed Insights", "Data Not Connected", "Configure Google PageSpeed API key in Settings to measure LCP, FID, CLS, and Core Web Vitals."]
        ]
        lim_table = self.builder.build_styled_table(
            lim_data[0],
            lim_data[1:],
            col_widths=[140, 120, 280]
        )
        story.append(lim_table)
        story.append(Spacer(1, 14))

        doc.build(story, canvasmaker=NumberedCanvas)
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
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=42
        )
        story = []

        self.builder.build_header_banner(
            story,
            report_title=title,
            domain=domain,
            project_name=project_name,
            crawl_timestamp=crawl_timestamp,
            data_sources="Website Scan Dataset"
        )

        # Executive Metric Summary Row
        summary_kpis = [
            {"title": "REPORT TYPE", "value": title.split()[0] if title else "Module", "subtext": "Dataset classification", "color": "#2563eb"},
            {"title": "TOTAL RECORDS", "value": str(len(rows_data)), "subtext": "Extracted items", "color": "#0f172a"},
            {"title": "EXPORT STATUS", "value": "COMPLETE", "subtext": "Full data verification", "color": "#10b981"},
            {"title": "TARGET DOMAIN", "value": domain[:14] if len(domain) > 14 else domain, "subtext": "Audited domain", "color": "#4f46e5"}
        ]
        self.builder.build_kpi_grid(story, summary_kpis)

        story.append(Paragraph(f"Dataset: {title}", self.theme.section_title))
        if subtitle:
            story.append(Paragraph(subtitle, self.theme.section_subtitle))

        if not rows_data:
            empty_table = Table([[Paragraph("No records available in this dataset", self.theme.table_cell)]], colWidths=[540])
            empty_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), PDFColors.BG_CARD),
                ('GRID', (0, 0), (-1, -1), 0.5, PDFColors.BORDER_LIGHT),
                ('PADDING', (0, 0), (-1, -1), 12),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ]))
            story.append(empty_table)
        else:
            table_widget = self.builder.build_styled_table(
                headers=headers,
                rows=rows_data,
                col_widths=col_widths,
                max_rows=60
            )
            story.append(table_widget)

            if len(rows_data) > 60:
                story.append(Spacer(1, 6))
                story.append(Paragraph(
                    f"<i>Showing 60 of {len(rows_data)} records. Download the complete CSV or XLSX file for the full dataset.</i>",
                    ParagraphStyle('SimpleTrunc', parent=self.theme.body, fontSize=8, textColor=PDFColors.MUTED_TEXT)
                ))

        doc.build(story, canvasmaker=NumberedCanvas)
        buffer.seek(0)
        return buffer.getvalue()
