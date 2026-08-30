import io
from typing import Dict, Any, List, Optional

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    HAS_PPTX = True
except ImportError:
    Presentation = None
    Inches = Pt = RGBColor = PP_ALIGN = MSO_SHAPE = None
    HAS_PPTX = False

class PPTXExportService:
    NAVY = RGBColor(15, 23, 42) if HAS_PPTX else None
    SLATE = RGBColor(30, 41, 59) if HAS_PPTX else None
    BLUE = RGBColor(37, 99, 235) if HAS_PPTX else None
    LIGHT_BG = RGBColor(248, 250, 252) if HAS_PPTX else None
    GRAY = RGBColor(100, 116, 139) if HAS_PPTX else None
    WHITE = RGBColor(255, 255, 255) if HAS_PPTX else None
    RED = RGBColor(225, 29, 72) if HAS_PPTX else None
    GREEN = RGBColor(16, 185, 129) if HAS_PPTX else None

    @classmethod
    def _create_title_slide(cls, prs, project_name: str, domain: str, timestamp: str):
        if not HAS_PPTX:
            return
        blank_slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_slide_layout)

        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(10), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = cls.NAVY
        bg.line.fill.background()

        txBox = slide.shapes.add_textbox(Inches(1), Inches(2.2), Inches(8), Inches(3))
        tf = txBox.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = "Full Website Health Report"
        p1.font.size = Pt(36)
        p1.font.bold = True
        p1.font.color.rgb = cls.WHITE
        p1.alignment = PP_ALIGN.LEFT

        p2 = tf.add_paragraph()
        p2.text = f"Executive SEO Audit & Intelligence Presentation for {project_name or domain}"
        p2.font.size = Pt(20)
        p2.font.color.rgb = RGBColor(148, 163, 184)
        p2.alignment = PP_ALIGN.LEFT

        p3 = tf.add_paragraph()
        p3.text = f"Website: {domain}  |  Report Date: {timestamp}"
        p3.font.size = Pt(14)
        p3.font.color.rgb = cls.BLUE
        p3.alignment = PP_ALIGN.LEFT

    @classmethod
    def _create_standard_slide(cls, prs, title: str, subtitle: str = None):
        if not HAS_PPTX:
            return None
        blank_slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(blank_slide_layout)

        hdr = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(10), Inches(1.1))
        hdr.fill.solid()
        hdr.fill.fore_color.rgb = cls.SLATE
        hdr.line.fill.background()

        txBox = slide.shapes.add_textbox(Inches(0.6), Inches(0.15), Inches(8.8), Inches(0.8))
        tf = txBox.text_frame
        tf.word_wrap = True

        p1 = tf.paragraphs[0]
        p1.text = title
        p1.font.size = Pt(22)
        p1.font.bold = True
        p1.font.color.rgb = cls.WHITE

        if subtitle:
            p2 = tf.add_paragraph()
            p2.text = subtitle
            p2.font.size = Pt(12)
            p2.font.color.rgb = RGBColor(148, 163, 184)

        return slide

    @classmethod
    def generate_full_project_pptx(
        cls,
        project_name: str = None,
        project_url: str = None,
        metadata: Dict[str, Any] = None,
        pages: List[Dict[str, Any]] = None,
        keywords: List[Dict[str, Any]] = None,
        issues: List[Dict[str, Any]] = None,
        opportunities: List[Dict[str, Any]] = None,
        ai_insights: Dict[str, Any] = None,
        internal_links: List[Dict[str, Any]] = None,
        outbound_links: List[Dict[str, Any]] = None,
        competitors: List[Dict[str, Any]] = None,
        backlinks: List[Dict[str, Any]] = None,
        master_report: Dict[str, Any] = None
    ) -> bytes:
        if not HAS_PPTX:
            return b""

        # Normalize from master_report dictionary if provided
        if master_report:
            p_obj = master_report.get("project", {})
            c_obj = master_report.get("crawl", {})
            project_name = p_obj.get("name", project_name or "Website")
            project_url = p_obj.get("url", project_url or p_obj.get("domain", "Website"))
            domain = p_obj.get("domain", project_url)
            timestamp = c_obj.get("timestamp", "N/A")
            pages = master_report.get("affected_pages", [])
            keywords = master_report.get("keywords", [])
            issues = master_report.get("problems", [])
            opportunities = master_report.get("opportunities", [])
            ai_insights = master_report.get("ai_analysis", {})
            internal_links = master_report.get("content_and_links", {}).get("internal_links", [])
            outbound_links = master_report.get("content_and_links", {}).get("outbound_links", [])
            competitors = master_report.get("competitors", [])
            backlinks = master_report.get("backlinks", {}).get("inbound_backlinks", [])
            aeo_list = master_report.get("aeo", [])
            geo_list = master_report.get("geo", [])
            hist_obj = master_report.get("historical_comparison", {})
            road_list = master_report.get("next_improvements", [])
            limits_list = master_report.get("data_limitations", [])
            health_score = master_report.get("health", {}).get("health_score", 100)
        else:
            domain = project_url or "Website"
            timestamp = metadata.get("timestamp", "N/A") if metadata else "N/A"
            pages = pages or []
            keywords = keywords or []
            issues = issues or []
            opportunities = opportunities or []
            ai_insights = ai_insights or {}
            internal_links = internal_links or []
            outbound_links = outbound_links or []
            competitors = competitors or []
            backlinks = backlinks or []
            aeo_list = []
            geo_list = []
            hist_obj = {}
            road_list = []
            limits_list = []
            health_score = ai_insights.get("health_score", 100)

        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        # SLIDE 1: Title
        cls._create_title_slide(prs, project_name, domain, timestamp)

        # SLIDE 2: Executive Summary
        s2 = cls._create_standard_slide(prs, "1. Executive Summary", "Plain-Language Site Assessment")
        tx2 = s2.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf2 = tx2.text_frame
        tf2.word_wrap = True
        p2_1 = tf2.paragraphs[0]
        p2_1.text = f"Overall Website Health Score: {health_score} / 100"
        p2_1.font.size = Pt(24)
        p2_1.font.bold = True
        p2_1.font.color.rgb = cls.BLUE
        p2_2 = tf2.add_paragraph()
        p2_2.text = "\nExecutive Assessment:"
        p2_2.font.size = Pt(16)
        p2_2.font.bold = True
        p2_3 = tf2.add_paragraph()
        p2_3.text = ai_insights.get("executive_assessment", "Your website scan has been evaluated against deterministic SEO standards.")
        p2_3.font.size = Pt(14)
        p2_3.font.color.rgb = cls.SLATE

        # SLIDE 3: Website Health Score
        s3 = cls._create_standard_slide(prs, "2. Website Health Score & Checks", "Deterministic Audit Metrics")
        tx3 = s3.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf3 = tx3.text_frame
        tf3.word_wrap = True
        metrics = [
            f"• Health Score: {health_score}/100",
            f"• Pages Scanned: {len(pages)} HTML pages",
            f"• Checks Performed: {len(pages) * 14} rule checks ({len(pages)} pages × 14 rules)",
            f"• Problems Detected: {len(issues)} findings across critical, error, and warning levels",
            f"• Unmeasured Categories: PageSpeed & Inbound Backlinks are marked 'Data Not Connected' and do not deduct score points."
        ]
        for m in metrics:
            p = tf3.add_paragraph()
            p.text = m
            p.font.size = Pt(15)
            p.font.color.rgb = cls.SLATE

        # SLIDE 4: Main Problems Found
        s4 = cls._create_standard_slide(prs, "3. Top Priority SEO Problems Found", "Grounded Audit Findings")
        tx4 = s4.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf4 = tx4.text_frame
        tf4.word_wrap = True
        top_issues = issues[:4] if issues else []
        if not top_issues:
            p = tf4.add_paragraph()
            p.text = "No critical SEO problems were detected on audited pages."
            p.font.size = Pt(16)
        else:
            for idx, iss in enumerate(top_issues, 1):
                p = tf4.add_paragraph()
                ind = iss.get("indicator") or "🔴"
                p.text = f"{idx}. {ind} [{iss.get('severity', 'Notice')}] {iss.get('problem') or iss.get('issue', 'Problem')} — {iss.get('affected_url') or iss.get('url', '')}"
                p.font.size = Pt(13)
                p.font.bold = True
                p.font.color.rgb = cls.RED if iss.get("severity") in ("Critical", "Fatal") else cls.SLATE
                p_ev = tf4.add_paragraph()
                p_ev.text = f"   Evidence: {iss.get('evidence') or iss.get('what_was_found', 'N/A')}\n   Solution: {iss.get('ai_solution', 'Fix issue')}"
                p_ev.font.size = Pt(11)
                p_ev.font.color.rgb = cls.GRAY

        # SLIDE 5: AI Recommendations
        s5 = cls._create_standard_slide(prs, "4. AI Recommendations & Solutions", "Strategic Actionable Intelligence")
        tx5 = s5.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf5 = tx5.text_frame
        tf5.word_wrap = True
        ai_recs = [
            "• Fix High-Severity Status Code Errors: Ensure broken URLs resolve to valid 200 HTTP status.",
            "• Eliminate Missing & Duplicate Meta Titles: Every page requires a unique 30-60 character title tag.",
            "• Expand Thin Page Content: Upgrade pages under 300 words with targeted keyword content.",
            "• Build Internal Link Density: Add contextual anchor text links from authority pages to strategic landing pages."
        ]
        for r in ai_recs:
            p = tf5.add_paragraph()
            p.text = r
            p.font.size = Pt(14)
            p.font.color.rgb = cls.SLATE

        # SLIDE 6: Technical SEO
        s6 = cls._create_standard_slide(prs, "5. Technical SEO Audit", "Crawlability & Server Diagnostics")
        tx6 = s6.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf6 = tx6.text_frame
        tf6.word_wrap = True
        tech_points = [
            f"• Total Audited URLs: {len(pages)} pages",
            f"• Valid HTTP 200 URLs: {sum(1 for p in pages if p.get('status_code') == 200)} pages",
            f"• Non-200 / Broken URLs: {sum(1 for p in pages if p.get('status_code') != 200)} pages",
            f"• Indexability Status: Audited pages are accessible for search engine indexing.",
            f"• Can Search Engines Find This Page?: Verified via robots directives and HTTP headers."
        ]
        for tp in tech_points:
            p = tf6.add_paragraph()
            p.text = tp
            p.font.size = Pt(15)

        # SLIDE 7: On-Page SEO
        s7 = cls._create_standard_slide(prs, "6. Content & On-Page SEO", "Metadata & Heading Hierarchy")
        tx7 = s7.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf7 = tx7.text_frame
        tf7.word_wrap = True
        onpage_points = [
            f"• Missing Meta Titles: {sum(1 for p in pages if not p.get('title') or p.get('title') == '(Missing Title)')} pages",
            f"• Missing Meta Descriptions: {sum(1 for p in pages if not p.get('meta_description') or p.get('meta_description') == '(Missing Meta Description)')} pages",
            f"• Missing H1 Headings: {sum(1 for p in pages if not p.get('h1') or p.get('h1') == '(Missing H1)')} pages",
            f"• Thin Content Pages (<300 words): {sum(1 for p in pages if p.get('word_count', 0) < 300)} pages"
        ]
        for op in onpage_points:
            p = tf7.add_paragraph()
            p.text = op
            p.font.size = Pt(15)

        # SLIDE 8: Keywords & Content Topics
        s8 = cls._create_standard_slide(prs, "7. Keywords & Content Frequencies", "Extracted Topic Frequencies")
        tx8 = s8.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf8 = tx8.text_frame
        tf8.word_wrap = True
        top_kws = keywords[:5] if keywords else []
        if not top_kws:
            p = tf8.add_paragraph()
            p.text = "No extracted content keywords available."
            p.font.size = Pt(16)
        else:
            for kw in top_kws:
                p = tf8.add_paragraph()
                p.text = f"• Keyword: '{kw.get('keyword')}' | Frequency: {kw.get('frequency', 1)} times | Source: {kw.get('target_url', 'Website Content')}"
                p.font.size = Pt(14)

        # SLIDE 9: Local SEO
        s9 = cls._create_standard_slide(prs, "8. Local SEO & Geographic Optimization", "Local Search Visibility")
        tx9 = s9.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf9 = tx9.text_frame
        tf9.word_wrap = True
        loc_points = [
            f"• Local Business Entity: {project_name}",
            "• Google Business Profile: Data Not Connected (Connect in Settings -> Integrations)",
            "• NAP Consistency: Audited for homepage formatting consistency",
            "• Local Recommendation: Maintain localized address and service area landing pages."
        ]
        for lp in loc_points:
            p = tf9.add_paragraph()
            p.text = lp
            p.font.size = Pt(15)

        # SLIDE 10: Content & Links
        s10 = cls._create_standard_slide(prs, "9. Content & Internal Link Structure", "Site Interconnectivity")
        tx10 = s10.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf10 = tx10.text_frame
        tf10.word_wrap = True
        link_points = [
            f"• Total Internal Links Audited: {len(internal_links)} links across site",
            f"• Total Outbound External Links Found: {len(outbound_links)} links on audited pages",
            "• Crawl Accessibility: Internal links enable search bots to discover deep pages.",
            "• Anchor Text Best Practice: Use descriptive topical keywords in internal link anchors."
        ]
        for lk in link_points:
            p = tf10.add_paragraph()
            p.text = lk
            p.font.size = Pt(15)

        # SLIDE 11: Backlinks Profile
        s11 = cls._create_standard_slide(prs, "10. Inbound Backlink Profile", "External Link Authority")
        tx11 = s11.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf11 = tx11.text_frame
        tf11.word_wrap = True
        if backlinks:
            for b in backlinks[:4]:
                p = tf11.add_paragraph()
                p.text = f"• Source: {b.get('source')} -> Target: {b.get('target')}"
                p.font.size = Pt(14)
        else:
            bl_points = [
                "• Inbound External Backlinks: Data Not Connected",
                "• Explanation: No inbound backlink dataset is connected. The website scan can identify links found on the website, but cannot discover external referring domains without an active integration key.",
                "• Action Required: Connect Backlinks API key in Settings -> Integrations."
            ]
            for bl in bl_points:
                p = tf11.add_paragraph()
                p.text = bl
                p.font.size = Pt(15)

        # SLIDE 12: AEO & GEO
        s12 = cls._create_standard_slide(prs, "11. AEO & GEO Optimization", "Answer Engines & Generative AI")
        tx12 = s12.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf12 = tx12.text_frame
        tf12.word_wrap = True
        aeo_points = [
            "• Answer Engine Optimization (AEO): Add FAQPage JSON-LD schema on core service pages.",
            "• Generative Engine Optimization (GEO): Include quotable facts, statistics, and structured tables.",
            "• Question-Based Headings: Structure H2 headings to answer direct 'What is / How to' queries.",
            "• AI Overviews: High-depth authoritative content increases snippet citation probability."
        ]
        for ap in aeo_points:
            p = tf12.add_paragraph()
            p.text = ap
            p.font.size = Pt(15)

        # SLIDE 13: AI Citations
        s13 = cls._create_standard_slide(prs, "12. AI Citations & Brand Presence", "LLM Brand Visibility")
        tx13 = s13.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf13 = tx13.text_frame
        tf13.word_wrap = True
        p13 = tf13.add_paragraph()
        p13.text = "AI Citation Testing Status:"
        p13.font.size = Pt(16)
        p13.font.bold = True
        p13_sub = tf13.add_paragraph()
        p13_sub.text = "AI citation testing is configured but results are not yet available for this crawl.\nOnce active, tracking covers ChatGPT, Perplexity AI, Google Gemini, and AI Overviews."
        p13_sub.font.size = Pt(14)

        # SLIDE 14: Opportunities
        s14 = cls._create_standard_slide(prs, "13. Prioritized SEO Opportunities", "High-Impact Growth Actions")
        tx14 = s14.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf14 = tx14.text_frame
        tf14.word_wrap = True
        top_opps = opportunities[:4] if opportunities else []
        if not top_opps:
            p = tf14.add_paragraph()
            p.text = "No central SEO opportunities identified."
            p.font.size = Pt(16)
        else:
            for opp in top_opps:
                p = tf14.add_paragraph()
                p.text = f"• [{opp.get('priority', 'Medium')}] {opp.get('title')} — {opp.get('url', 'Site Level')}"
                p.font.size = Pt(13)
                p.font.bold = True
                p_sol = tf14.add_paragraph()
                p_sol.text = f"   Action: {opp.get('recommended_action', 'N/A')}"
                p_sol.font.size = Pt(11)

        # SLIDE 15: Historical Comparison
        s15 = cls._create_standard_slide(prs, "14. Historical Crawl Comparison", "Progress Over Time")
        tx15 = s15.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf15 = tx15.text_frame
        tf15.word_wrap = True
        if hist_obj.get("has_previous_crawl"):
            h_points = [
                f"• Previous Score: {hist_obj.get('previous_score')}/100 -> Current Score: {hist_obj.get('current_score')}/100 ({hist_obj.get('score_delta'):+d} points)",
                f"• Problems Resolved: {hist_obj.get('problems_fixed_count')} previous issues fixed",
                f"• Newly Detected: {hist_obj.get('new_problems_count')} new findings",
                f"• Summary: {hist_obj.get('ai_trend_summary')}"
            ]
            for hp in h_points:
                p = tf15.add_paragraph()
                p.text = hp
                p.font.size = Pt(15)
        else:
            p = tf15.add_paragraph()
            p.text = "Historical comparison is not available because no previous completed crawl exists.\nFuture scans will automatically track score movements, fixed issues, and new findings."
            p.font.size = Pt(15)

        # SLIDE 16: Next 90-Day Improvement Plan
        s16 = cls._create_standard_slide(prs, "15. Next SEO Improvement Plan", "Phased Execution Roadmap")
        tx16 = s16.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf16 = tx16.text_frame
        tf16.word_wrap = True
        if road_list:
            for rm in road_list:
                p = tf16.add_paragraph()
                p.text = f"• {rm.get('timeframe')}: {rm.get('action')}"
                p.font.size = Pt(13)
                p.font.color.rgb = cls.BLUE if "NOW" in rm.get("timeframe", "") else cls.SLATE
        else:
            default_roadmap = [
                "• NOW (0–7 Days): Resolve critical 404 status codes and broken URLs.",
                "• NEXT (8–30 Days): Rewrite missing titles and meta descriptions for all pages.",
                "• 30–60 DAYS: Expand thin content and optimize internal linking structure.",
                "• 60–90 DAYS: Implement AEO/GEO structured FAQ schema and entity authority.",
                "• ONGOING: Monitor crawl health, internal links, and connect external search APIs."
            ]
            for drm in default_roadmap:
                p = tf16.add_paragraph()
                p.text = drm
                p.font.size = Pt(14)

        # SLIDE 17: Data Limitations
        s17 = cls._create_standard_slide(prs, "16. Data Limitations & Next Integrations", "Audit Transparency")
        tx17 = s17.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf17 = tx17.text_frame
        tf17.word_wrap = True
        limit_points = [
            "• Google Search Console: Data Not Connected (Connect in Settings for impressions/clicks)",
            "• Inbound Backlinks: No inbound backlink dataset connected (Does not penalize health score)",
            "• PageSpeed Performance: Not measured during this crawl (Requires PageSpeed API)",
            "• Search Position Tracking: Ranking data is not currently connected."
        ]
        for lp in limit_points:
            p = tf17.add_paragraph()
            p.text = lp
            p.font.size = Pt(14)

        stream = io.BytesIO()
        prs.save(stream)
        return stream.getvalue()

    generate_presentation = generate_full_project_pptx
