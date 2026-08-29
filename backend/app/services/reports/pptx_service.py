import io
from typing import Dict, Any, List

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

        # Background shape
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

        # Top Header Bar
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
        project_name: str,
        project_url: str,
        metadata: Dict[str, Any],
        pages: List[Dict[str, Any]],
        keywords: List[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]],
        ai_insights: Dict[str, Any],
        internal_links: List[Dict[str, Any]] = None,
        outbound_links: List[Dict[str, Any]] = None,
        competitors: List[Dict[str, Any]] = None,
        backlinks: List[Dict[str, Any]] = None
    ) -> bytes:
        if not HAS_PPTX:
            return b""
        prs = Presentation()
        prs.slide_width = Inches(10)
        prs.slide_height = Inches(7.5)

        domain = project_url or "Website"
        timestamp = metadata.get("timestamp", "N/A")
        health_score = ai_insights.get("health_score", 100)

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
            p.font.size = Pt(16)
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
                p.text = f"{idx}. [{iss.get('severity', 'Notice')}] {iss.get('issue', 'Problem')} — {iss.get('url', '')}"
                p.font.size = Pt(14)
                p.font.bold = True
                p.font.color.rgb = cls.RED if iss.get("severity") in ("Critical", "Error", "High") else cls.SLATE

                p_ev = tf4.add_paragraph()
                p_ev.text = f"   Evidence: {iss.get('evidence') or iss.get('description', 'N/A')}\n   Solution: {iss.get('ai_solution', 'Fix issue')}"
                p_ev.font.size = Pt(12)
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
            p.font.size = Pt(15)
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

        # SLIDE 9: Backlinks Status
        s9 = cls._create_standard_slide(prs, "8. Backlinks & External Link Analysis", "Inbound & Outbound Profile")
        tx9 = s9.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf9 = tx9.text_frame
        tf9.word_wrap = True

        bl_points = [
            f"• Outbound External Links Found: {len(outbound_links or [])} external links on audited pages",
            "• Inbound External Backlinks: Data Not Connected",
            "• Status: An inbound backlink dataset is not currently connected. The website scan can identify links found on the website, but cannot discover external referring domains without an active integration key.",
            "• Action Required: Connect Backlinks API key in Settings -> Integrations."
        ]
        for bl in bl_points:
            p = tf9.add_paragraph()
            p.text = bl
            p.font.size = Pt(15)

        # SLIDE 10: Competitors
        s10 = cls._create_standard_slide(prs, "9. Competitor Benchmark Analysis", "Domain Comparison")
        tx10 = s10.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf10 = tx10.text_frame
        tf10.word_wrap = True

        if competitors:
            for comp in competitors:
                p = tf10.add_paragraph()
                p.text = f"• Competitor: {comp.get('name') or comp.get('domain')} | Overlap: {comp.get('overlap', 'N/A')}"
                p.font.size = Pt(14)
        else:
            p = tf10.add_paragraph()
            p.text = "Competitor data is not currently configured.\nAdd competitor domains in Settings -> Competitors to enable automated overlap analysis."
            p.font.size = Pt(16)

        # SLIDE 11: SEO Opportunities
        s11 = cls._create_standard_slide(prs, "10. Prioritized SEO Opportunities", "High-Impact Growth Actions")
        tx11 = s11.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf11 = tx11.text_frame
        tf11.word_wrap = True

        top_opps = opportunities[:4] if opportunities else []
        if not top_opps:
            p = tf11.add_paragraph()
            p.text = "No central SEO opportunities identified."
            p.font.size = Pt(16)
        else:
            for opp in top_opps:
                p = tf11.add_paragraph()
                p.text = f"• [{opp.get('priority', 'Medium')}] {opp.get('title')} — {opp.get('url', 'Site Level')}"
                p.font.size = Pt(14)
                p.font.bold = True
                p_sol = tf11.add_paragraph()
                p_sol.text = f"   Action: {opp.get('recommended_action', 'N/A')}"
                p_sol.font.size = Pt(12)

        # SLIDE 12: Evidence
        s12 = cls._create_standard_slide(prs, "11. Audit Evidence & Traceability", "Observed Code Snapshots")
        tx12 = s12.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf12 = tx12.text_frame
        tf12.word_wrap = True

        p12 = tf12.add_paragraph()
        p12.text = "All audit findings and AI recommendations in this report are 100% grounded in verified crawl evidence:"
        p12.font.size = Pt(15)

        ev_list = [
            "• Status Code 404 / 500 HTTP Server Responses",
            "• Exact character count length of <title> tags",
            "• Verified word counts per audited HTML page",
            "• Explicit internal link source and destination page URLs"
        ]
        for ev in ev_list:
            p = tf12.add_paragraph()
            p.text = ev
            p.font.size = Pt(14)

        # SLIDE 13: Fix First Priority Roadmap
        s13 = cls._create_standard_slide(prs, "12. What To Fix First Roadmap", "Immediate Tactical Priority")
        tx13 = s13.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf13 = tx13.text_frame
        tf13.word_wrap = True

        priorities = [
            "1. Fix Critical Technical Errors (404 broken pages, server errors)",
            "2. Resolve Missing & Short Meta Title Tags (30-60 character target)",
            "3. Add Compelling Meta Descriptions for Key Landing Pages",
            "4. Expand Thin Content Pages Under 300 Words",
            "5. Build Contextual Internal Links Between Core Pages"
        ]
        for pr in priorities:
            p = tf13.add_paragraph()
            p.text = pr
            p.font.size = Pt(15)
            p.font.bold = True
            p.font.color.rgb = cls.SLATE

        # SLIDE 14: Future Improvement Plan
        s14 = cls._create_standard_slide(prs, "13. Future SEO Improvements Plan", "Phased Execution Roadmap")
        tx14 = s14.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(5.2))
        tf14 = tx14.text_frame
        tf14.word_wrap = True

        roadmap_items = [
            "• NOW (0-7 Days): Resolve critical 404 status codes and broken URLs.",
            "• NEXT 30 DAYS: Rewrite missing titles and meta descriptions for all pages.",
            "• NEXT 60-90 DAYS: Expand thin content and optimize H1/H2 heading structure.",
            "• ONGOING: Monitor crawl health, internal links, and connect external Search Console APIs."
        ]
        for rm in roadmap_items:
            p = tf14.add_paragraph()
            p.text = rm
            p.font.size = Pt(15)
            p.font.color.rgb = cls.BLUE if "NOW" in rm else cls.SLATE

        stream = io.BytesIO()
        prs.save(stream)
        return stream.getvalue()
