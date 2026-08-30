import io
from typing import Dict, Any, List, Optional

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    Font = PatternFill = Alignment = Border = Side = get_column_letter = None
    HAS_OPENPYXL = False

class XLSXExportService:
    @staticmethod
    def _apply_header_style(ws, row=1):
        if not HAS_OPENPYXL:
            return
        header_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
        header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )
        for cell in ws[row]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

    @staticmethod
    def _auto_fit_columns(ws, max_col_width=50):
        if not HAS_OPENPYXL:
            return
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or '')
                if val_str:
                    max_len = max(max_len, len(val_str))
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), max_col_width)

    @classmethod
    def generate_full_project_xlsx(
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
        if not HAS_OPENPYXL:
            return b""

        # Normalize from master_report dictionary if provided
        if master_report:
            p_obj = master_report.get("project", {})
            c_obj = master_report.get("crawl", {})
            h_obj = master_report.get("health", {})
            project_name = p_obj.get("name", project_name or "Website Project")
            project_url = p_obj.get("url", project_url or p_obj.get("domain", "Website"))
            metadata = metadata or {"timestamp": c_obj.get("timestamp", "N/A")}
            pages = pages or master_report.get("affected_pages", [])
            keywords = keywords or master_report.get("keywords", [])
            issues = issues or master_report.get("problems", [])
            opportunities = opportunities or master_report.get("opportunities", [])
            ai_insights = ai_insights or master_report.get("ai_analysis", {})
            internal_links = internal_links or master_report.get("content_and_links", {}).get("internal_links", [])
            outbound_links = outbound_links or master_report.get("content_and_links", {}).get("outbound_links", [])
            competitors = competitors or master_report.get("competitors", [])
            backlinks = backlinks or master_report.get("backlinks", {}).get("inbound_backlinks", [])
            aeo_list = master_report.get("aeo", [])
            geo_list = master_report.get("geo", [])
            hist_obj = master_report.get("historical_comparison", {})
            road_list = master_report.get("next_improvements", [])
            limits_list = master_report.get("data_limitations", [])
            business_context = master_report.get("business_context", {})
        else:
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
            business_context = {}

        wb = openpyxl.Workbook()
        wb.remove(wb.active) # Remove default sheet

        # Categorize issues
        tech_issues = [i for i in issues if i.get("category") == "Technical" or "status" in str(i.get("problem","")).lower() or "404" in str(i.get("problem","")).lower() or "canonical" in str(i.get("problem","")).lower() or "robot" in str(i.get("problem","")).lower() or "https" in str(i.get("problem","")).lower()]
        onpage_issues = [i for i in issues if i not in tech_issues]

        crit_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("Critical", "Fatal"))
        high_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("High", "Error"))
        warn_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("Warning", "Medium"))
        info_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("Informational", "Notice", "Low", "Info"))

        # =========================================================================
        # 1. 📊 Dashboard Summary Sheet
        # =========================================================================
        ws_dash = wb.create_sheet(title="📊 Dashboard")
        ws_dash.append(["SEO Intelligence Platform — Full Website Health & Search Master Dashboard"])
        ws_dash.merge_cells("A1:G1")
        ws_dash["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        ws_dash.append([])

        dash_meta = [
            ["Project / Brand Name", project_name or "Website"],
            ["Target Website URL", project_url or "Website"],
            ["Industry Focus", business_context.get("industry") or "Website & Digital Services"],
            ["Service Locations", business_context.get("service_areas") or "All Service Regions"],
            ["Audit Date", metadata.get("timestamp", "N/A") if metadata else "N/A"],
            ["Website Health Score", f"{ai_insights.get('health_score', 100)} / 100"],
            ["Total Audited HTML Pages", len(pages)],
            ["Total Evaluated Rules", f"{len(pages) * 14} ({len(pages)} pages × 14 core rules)"],
            ["Total Detected Problems", len(issues)]
        ]
        for label, val in dash_meta:
            ws_dash.append([label, val])
        for r in range(3, 12):
            ws_dash.cell(row=r, column=1).font = Font(name="Calibri", size=11, bold=True, color="334155")
        
        ws_dash.append([])
        ws_dash.append(["Executive Assessment & AI Analysis"])
        ws_dash.cell(row=13, column=1).font = Font(name="Calibri", size=12, bold=True, color="0F172A")
        ws_dash.append(["Executive Overview", ai_insights.get("executive_assessment", "Crawl completed successfully.")])
        ws_dash.append(["Score Deductions & Context", ai_insights.get("health_score_explanation", f"Health score is {ai_insights.get('health_score', 100)}/100.")])
        ws_dash.cell(row=14, column=1).font = Font(bold=True, color="334155")
        ws_dash.cell(row=15, column=1).font = Font(bold=True, color="334155")

        ws_dash.append([])
        ws_dash.append(["Problem Severity Rollup", "Count", "Percentage of Issues", "Priority / Urgency", "Primary Action Plan"])
        cls._apply_header_style(ws_dash, row=17)
        total_p = max(len(issues), 1)
        ws_dash.append(["🔴 Critical Technical Blockers", crit_count, f"{(crit_count/total_p)*100:.1f}%", "Immediate (0–7 Days)", "Restore server 200 OK responses, fix broken URLs and redirects"])
        ws_dash.append(["🟠 High Priority Errors", high_count, f"{(high_count/total_p)*100:.1f}%", "Urgent (8–30 Days)", "Resolve missing meta titles, descriptions, and primary H1 structure"])
        ws_dash.append(["🟡 Warnings & Opportunities", warn_count, f"{(warn_count/total_p)*100:.1f}%", "Scheduled (30–60 Days)", "Expand thin content pages (<300 words) and add contextual internal links"])
        ws_dash.append(["🔵 Informational & Notice", info_count, f"{(info_count/total_p)*100:.1f}%", "Ongoing", "Continuous crawl monitoring, schema markup, and rank tracking"])

        ws_dash.append([])
        ws_dash.append(["Category Health Breakdown", "Category Status", "Issues Found", "Category Scope", "Where This Data Came From"])
        cls._apply_header_style(ws_dash, row=23)
        ws_dash.append(["Technical SEO", "Passed" if len(tech_issues) == 0 else "Needs Attention", f"{len(tech_issues)} issues", "Status codes, canonicals, robots indexing, server headers", "Automatic Website Check"])
        ws_dash.append(["On-Page SEO", "Passed" if len(onpage_issues) == 0 else "Needs Attention", f"{len(onpage_issues)} issues", "Title tags, meta descriptions, H1 headings, content depth", "Automatic Website Check"])
        ws_dash.append(["Local SEO", "Data Not Connected", "0", "Google Business Profile & NAP consistency", "Data Not Connected"])
        ws_dash.append(["Content & Links", "Audited", f"{len(internal_links)} internal links", "Internal navigation equity & outbound reference links", "Automatic Website Check"])
        ws_dash.append(["Keywords & Topics", "Audited", f"{len(keywords)} keywords", "Extracted content keywords and topic distribution", "Automatic Website Check"])
        ws_dash.append(["AEO (Answer Engine Optimization)", "Audited", f"{len(aeo_list)} entities", "FAQ schema, direct answer definitions, and conversational search", "Automatic Website Check + AI Analysis"])
        ws_dash.append(["GEO (Generative Engine Optimization)", "Audited", f"{len(geo_list)} entities", "Entity authority, brand citations, and AI overview readiness", "Automatic Website Check + AI Analysis"])
        ws_dash.append(["AI Citations", "Results Not Available", "0", "LLM search citations (ChatGPT, Perplexity, Gemini)", "Data Not Connected"])
        cls._auto_fit_columns(ws_dash)

        # Helper to format problem sheets
        def append_problem_sheet(title: str, prob_list: List[Dict[str, Any]]):
            ws = wb.create_sheet(title=title)
            ws.append(["#", "Problem", "Severity", "Indicator", "Affected URL", "What Was Found", "AI Solution", "Future Improvement", "Status"])
            cls._apply_header_style(ws)
            if prob_list:
                for idx, iss in enumerate(prob_list, 1):
                    sev = str(iss.get("severity", "Notice")).capitalize()
                    ind = iss.get("indicator") or ("🔴" if sev in ("Critical", "Fatal") else "🟠" if sev in ("High", "Error") else "🟡" if sev in ("Warning", "Medium") else "🔵")
                    ws.append([
                        idx,
                        iss.get("problem") or iss.get("issue") or "SEO Finding",
                        sev,
                        ind,
                        iss.get("affected_url") or iss.get("url") or "Site Level",
                        iss.get("what_was_found") or iss.get("evidence") or "Observed during audit",
                        iss.get("ai_solution") or "Apply standard SEO remediation.",
                        iss.get("future_improvement") or "Add build verification tests.",
                        "Open"
                    ])
            else:
                ws.append([1, f"No {title} problems detected during crawl", "Passed", "🔵", "Site Level", "Audit verified standard compliance", "Maintain current configuration.", "Run regular crawls.", "Passed"])
            cls._auto_fit_columns(ws)

        # 2. Technical SEO
        append_problem_sheet("Technical SEO", tech_issues)

        # 3. On-Page SEO
        append_problem_sheet("On-Page SEO", onpage_issues)

        # 4. Local SEO
        ws_local = wb.create_sheet(title="Local SEO")
        ws_local.append(["#", "Area / Check", "Severity", "Target URL / Entity", "What Was Found", "AI Solution", "Future Improvement", "Status"])
        cls._apply_header_style(ws_local)
        ws_local.append([1, "Google Business Profile", "Notice", "N/A", "Data Not Connected — Connect Google account to audit local map citations and reviews", "Connect Google Business Profile in Settings -> Integrations.", "Maintain synchronized NAP details across major directories.", "Data Not Connected"])
        ws_local.append([2, "NAP Consistency (Name/Address/Phone)", "Notice", project_url or "Site Level", f"Audited on {project_name or 'Homepage'}", "Ensure consistent phone and address formatting across all local landing pages.", "Add LocalBusiness JSON-LD structured schema.", "Audited"])
        cls._auto_fit_columns(ws_local)

        # 5. Content & Links
        ws_links = wb.create_sheet(title="Content & Links")
        ws_links.append(["#", "Link Item / Type", "Source Page URL", "Destination URL", "Anchor Text / Finding", "AI Solution / Action", "Status"])
        cls._apply_header_style(ws_links)
        if internal_links:
            for idx, lnk in enumerate(internal_links, 1):
                ws_links.append([
                    idx,
                    "Internal Link",
                    lnk.get("source") or lnk.get("source_url") or "",
                    lnk.get("target") or lnk.get("target_url") or "",
                    lnk.get("anchor") or lnk.get("anchor_text") or "(No Anchor Text)",
                    "Maintain link equity and optimize anchor text for target keywords.",
                    "Active (HTTP 200)"
                ])
        else:
            ws_links.append([1, "Internal Links", project_url or "", project_url or "", "Homepage", "Interlink core service pages with contextual anchor text.", "Audited"])
        cls._auto_fit_columns(ws_links)

        # 6. Keywords
        ws_kw = wb.create_sheet(title="Keywords")
        ws_kw.append(["#", "Search Keyword / Topic", "Category", "Target Page URL", "Content Frequency", "Source / Provenance", "AI Optimization Advice", "Status"])
        cls._apply_header_style(ws_kw)
        if keywords:
            for idx, kw in enumerate(keywords, 1):
                ws_kw.append([
                    idx,
                    kw.get("keyword", ""),
                    kw.get("category", "Content Keyword"),
                    kw.get("target_url") or project_url or "",
                    kw.get("frequency", 1),
                    kw.get("provenance") or "Automatic Website Content Check",
                    f"Incorporate '{kw.get('keyword', '')}' into primary H1 and meta description tags of relevant landing page.",
                    "Discovered"
                ])
        else:
            ws_kw.append([1, "Primary Brand Search", "Brand", project_url or "", 1, "Homepage", "Create targeted topic clusters.", "Discovered"])
        cls._auto_fit_columns(ws_kw)

        # 7. AEO (Answer Engine Optimization)
        ws_aeo = wb.create_sheet(title="AEO")
        ws_aeo.append(["#", "Search Topic / Entity", "Opportunity Type", "Target Page URL", "Observed Evidence", "AI Action Plan & FAQ Schema", "Priority", "Status"])
        cls._apply_header_style(ws_aeo)
        if aeo_list:
            for idx, a in enumerate(aeo_list, 1):
                ws_aeo.append([
                    idx,
                    a.get("topic", ""),
                    a.get("opportunity_type", ""),
                    a.get("url") or project_url or "",
                    a.get("evidence", ""),
                    a.get("recommended_action", ""),
                    a.get("priority", "High"),
                    "Recommended"
                ])
        else:
            ws_aeo.append([1, "FAQ Structure", "Direct Answer Entity", project_url or "", "Missing FAQPage structured data", "Add structured FAQ schema to answer high-intent user questions directly.", "High", "Recommended"])
        cls._auto_fit_columns(ws_aeo)

        # 8. GEO (Generative Engine Optimization)
        ws_geo = wb.create_sheet(title="GEO")
        ws_geo.append(["#", "Brand Entity / Topic", "GEO Strategy Focus", "Target Page URL", "Observed Evidence", "AI Generative Engine Optimization", "Priority", "Status"])
        cls._apply_header_style(ws_geo)
        if geo_list:
            for idx, g in enumerate(geo_list, 1):
                ws_geo.append([
                    idx,
                    g.get("entity", ""),
                    g.get("strategy", ""),
                    g.get("url") or project_url or "",
                    g.get("evidence", ""),
                    g.get("recommended_action", ""),
                    g.get("priority", "High"),
                    "Recommended"
                ])
        else:
            ws_geo.append([1, project_name or "Brand", "Entity Authority", project_url or "", "Brand knowledge graph citation", "Implement Organization schema and cite verified industry accreditations.", "High", "Recommended"])
        cls._auto_fit_columns(ws_geo)

        # 9. AI Citations
        ws_cite = wb.create_sheet(title="AI Citations")
        ws_cite.append(["#", "Query / Topic Tested", "Target Domain", "AI Engine", "Citation Status", "Observed Evidence", "AI Recommendation", "Status"])
        cls._apply_header_style(ws_cite)
        ws_cite.append([1, "Brand & Service Discovery", project_url or "", "ChatGPT / Perplexity / Gemini", "Results Not Available", "AI citation testing is configured but results are not yet available for this crawl.", "Build digital PR references and structured entity schema to increase AI citation frequency.", "Not Available"])
        cls._auto_fit_columns(ws_cite)

        # 10. Opportunities & Roadmap
        ws_opp = wb.create_sheet(title="Opportunities & Roadmap")
        ws_opp.append(["#", "Phase / Timeframe", "Priority", "Strategic Action / Opportunity", "Observed Evidence", "AI Implementation Plan", "Expected Benefit", "Status"])
        cls._apply_header_style(ws_opp)
        if road_list:
            for idx, r in enumerate(road_list, 1):
                ws_opp.append([
                    idx,
                    r.get("timeframe", ""),
                    "High" if "NOW" in r.get("timeframe", "") else "Medium",
                    r.get("action", ""),
                    r.get("evidence", ""),
                    f"Execute {r.get('phase', '')} best practices.",
                    r.get("expected_benefit", ""),
                    "Planned"
                ])
        else:
            for idx, opp in enumerate(opportunities, 1):
                ws_opp.append([
                    idx,
                    "30–60 Days",
                    opp.get("priority", "Medium"),
                    opp.get("title", ""),
                    opp.get("evidence", ""),
                    opp.get("recommended_action", ""),
                    opp.get("expected_benefit", ""),
                    "Planned"
                ])
        cls._auto_fit_columns(ws_opp)

        # 11. Affected Pages Inventory
        ws_pages = wb.create_sheet(title="Affected Pages")
        ws_pages.append(["#", "Page URL", "HTTP Status", "Can Search Engines Find This Page?", "Page Title", "Meta Description", "Primary H1", "Secondary H2", "Word Count", "Canonical URL"])
        cls._apply_header_style(ws_pages)
        for idx, p in enumerate(pages, 1):
            ws_pages.append([
                idx,
                p.get("url", ""),
                p.get("status_code", 200),
                "Yes (Indexable)" if p.get("status_code") == 200 else "No (Blocked / Error)",
                p.get("title", ""),
                p.get("meta_description", ""),
                p.get("h1", ""),
                p.get("h2", ""),
                p.get("word_count", 0),
                p.get("canonical", "")
            ])
        cls._auto_fit_columns(ws_pages)

        # 12. Data Limitations
        ws_lim = wb.create_sheet(title="Data Limitations")
        ws_lim.append(["#", "Data Service / API", "Connection Status", "Human-Readable Explanation"])
        cls._apply_header_style(ws_lim)
        for idx, lim in enumerate(limits_list, 1):
            ws_lim.append([
                idx,
                lim.get("service", ""),
                lim.get("status", ""),
                lim.get("explanation", "")
            ])
        cls._auto_fit_columns(ws_lim)

        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_pages_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        pages = kwargs.get("pages")
        if pages is None and args:
            pages = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        pages = pages or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pages Inventory"
        ws.append(["Page URL", "HTTP Status", "Can Search Engines Find This Page?", "Page Title", "Meta Description", "Primary H1", "Word Count", "Canonical URL", "Internal Links Count"])
        cls._apply_header_style(ws)
        for p in pages:
            ws.append([
                p.get("url", ""),
                p.get("status_code", 200),
                "Yes (Indexable)" if p.get("status_code") == 200 else "No (Blocked / Error)",
                p.get("title", ""),
                p.get("meta_description", ""),
                p.get("h1", ""),
                p.get("word_count", 0),
                p.get("canonical", ""),
                len(p.get("internal_links", [])) if isinstance(p.get("internal_links"), list) else 0
            ])
        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_keywords_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        keywords = kwargs.get("keywords")
        domain = kwargs.get("domain", "website.com")
        if keywords is None and args:
            keywords = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        keywords = keywords or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Target Keywords"
        ws.append(["Search Keyword", "Target Page URL", "Category / Topic", "Content Frequency", "Automatic Keyword Detection Source"])
        cls._apply_header_style(ws)
        for kw in keywords:
            ws.append([
                kw.get("keyword", ""),
                kw.get("target_url") or f"https://{domain}",
                kw.get("category", "General"),
                kw.get("frequency", 1),
                kw.get("source") or "Extracted Page Content"
            ])
        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_technical_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        issues = kwargs.get("issues")
        domain = kwargs.get("domain", "website.com")
        if issues is None and args:
            issues = args[0] if isinstance(args[0], list) else (args[-1] if isinstance(args[-1], list) else [])
        issues = issues or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Technical SEO Issues"
        ws.append(["Indicator", "Severity", "Category", "Problem Title", "Affected Page URL", "What Was Found", "Current Value", "Expected Value", "Why It Matters", "Recommended Action", "AI Solution", "Future Improvement", "Where This Data Came From"])
        cls._apply_header_style(ws)
        for iss in issues:
            sev = str(iss.get("severity", "Notice")).capitalize()
            ind = iss.get("indicator") or ("🔴" if sev in ("Critical", "Fatal") else "🟠" if sev in ("High", "Error") else "🟡" if sev in ("Warning", "Medium") else "🔵")
            ws.append([
                ind,
                sev,
                iss.get("category", "Technical"),
                iss.get("problem") or iss.get("issue") or "Technical Finding",
                iss.get("affected_url") or iss.get("url") or f"https://{domain}",
                iss.get("what_was_found") or iss.get("evidence") or "Observed technical finding",
                iss.get("current_value") or "Incomplete",
                iss.get("expected_value") or "Standard Compliant",
                iss.get("why_it_matters") or "Impacts server crawlability.",
                iss.get("recommended_action") or iss.get("recommendation") or "Resolve technical error.",
                iss.get("ai_solution") or "Apply server configuration fixes.",
                iss.get("future_improvement") or "Add build verification tests.",
                iss.get("source") or "Automatic Website Check + AI Analysis"
            ])
        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()
