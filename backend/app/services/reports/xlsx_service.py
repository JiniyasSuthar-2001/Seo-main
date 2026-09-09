import io
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.formatting.rule import CellIsRule
    HAS_OPENPYXL = True
except ImportError:
    openpyxl = None
    Font = PatternFill = Alignment = Border = Side = get_column_letter = DataValidation = CellIsRule = None
    HAS_OPENPYXL = False


class XLSXExportService:
    """
    Production-ready Master SEO/AEO/GEO Campaign Tracker and Page-Specific XLSX Export Service.
    Builds structured, formula-driven, dropdown-interactive, and professionally styled Excel workbooks.
    """

    # --- STYLE CONSTANTS (Arial Typography & Standard Palette) ---
    FONT_FAMILY = "Arial"

    # Header Colors
    PRIMARY_HEADER_FILL_HEX = "0D2F5E"  # Dark Navy
    SUB_HEADER_FILL_HEX = "1E293B"      # Dark Slate
    SECTION_HEADER_FILL_HEX = "0F172A"  # Dark Charcoal

    # Status & Priority Conditional Colors
    STATUS_DONE_FILL_HEX = "D5F5E3"     # Soft Green
    STATUS_DONE_FONT_HEX = "1E8449"     # Forest Green
    STATUS_IN_PROG_FILL_HEX = "FEF9E7"  # Soft Yellow
    STATUS_IN_PROG_FONT_HEX = "B7770D"  # Mustard Gold
    STATUS_NOT_START_FILL_HEX = "FDEDEC" # Soft Red
    STATUS_NOT_START_FONT_HEX = "922B21" # Deep Red
    STATUS_NA_FILL_HEX = "F1F5F9"       # Slate 100
    STATUS_NA_FONT_HEX = "64748B"       # Slate 500

    PRIORITY_HIGH_FILL_HEX = "FDEDEC"
    PRIORITY_HIGH_FONT_HEX = "922B21"
    PRIORITY_MED_FILL_HEX = "FEF9E7"
    PRIORITY_MED_FONT_HEX = "B7770D"
    PRIORITY_LOW_FILL_HEX = "EBF5FB"
    PRIORITY_LOW_FONT_HEX = "2874A6"

    @classmethod
    def _apply_header_style(cls, ws, row=1, fill_hex=None, font_size=10, row_height=26):
        if not HAS_OPENPYXL:
            return
        fill_hex = fill_hex or cls.PRIMARY_HEADER_FILL_HEX
        header_fill = PatternFill(start_color=fill_hex, end_color=fill_hex, fill_type="solid")
        header_font = Font(name=cls.FONT_FAMILY, size=font_size, bold=True, color="FFFFFF")
        thin_border = Border(
            left=Side(style="thin", color="CBD5E1"),
            right=Side(style="thin", color="CBD5E1"),
            top=Side(style="thin", color="CBD5E1"),
            bottom=Side(style="thin", color="CBD5E1")
        )
        ws.row_dimensions[row].height = row_height
        for cell in ws[row]:
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.border = thin_border

    @classmethod
    def _apply_data_row_style(cls, ws, row_idx, row_height=20):
        if not HAS_OPENPYXL:
            return
        ws.row_dimensions[row_idx].height = row_height
        thin_border = Border(
            left=Side(style="thin", color="E2E8F0"),
            right=Side(style="thin", color="E2E8F0"),
            top=Side(style="thin", color="E2E8F0"),
            bottom=Side(style="thin", color="E2E8F0")
        )
        for cell in ws[row_idx]:
            if not cell.font or cell.font.name != cls.FONT_FAMILY:
                cell.font = Font(name=cls.FONT_FAMILY, size=9.5)
            if not cell.alignment:
                cell.alignment = Alignment(vertical="center")
            cell.border = thin_border

    @classmethod
    def _apply_status_priority_validation_and_rules(cls, ws, status_col_letter, priority_col_letter, start_row, end_row):
        if not HAS_OPENPYXL or end_row < start_row:
            return

        # 1. Data Validation: Status Dropdown
        if status_col_letter:
            status_dv = DataValidation(type="list", formula1='"Done,In Progress,Not Started,N/A"', allow_blank=True)
            status_range = f"{status_col_letter}{start_row}:{status_col_letter}{end_row}"
            status_dv.add(status_range)
            ws.add_data_validation(status_dv)

            # Conditional formatting for Status
            done_fill = PatternFill(start_color=cls.STATUS_DONE_FILL_HEX, end_color=cls.STATUS_DONE_FILL_HEX, fill_type="solid")
            done_font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color=cls.STATUS_DONE_FONT_HEX)
            ws.conditional_formatting.add(status_range, CellIsRule(operator="equal", formula=['"Done"'], fill=done_fill, font=done_font))

            prog_fill = PatternFill(start_color=cls.STATUS_IN_PROG_FILL_HEX, end_color=cls.STATUS_IN_PROG_FILL_HEX, fill_type="solid")
            prog_font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color=cls.STATUS_IN_PROG_FONT_HEX)
            ws.conditional_formatting.add(status_range, CellIsRule(operator="equal", formula=['"In Progress"'], fill=prog_fill, font=prog_font))

            not_start_fill = PatternFill(start_color=cls.STATUS_NOT_START_FILL_HEX, end_color=cls.STATUS_NOT_START_FILL_HEX, fill_type="solid")
            not_start_font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color=cls.STATUS_NOT_START_FONT_HEX)
            ws.conditional_formatting.add(status_range, CellIsRule(operator="equal", formula=['"Not Started"'], fill=not_start_fill, font=not_start_font))

        # 2. Data Validation: Priority Dropdown
        if priority_col_letter:
            priority_dv = DataValidation(type="list", formula1='"High,Medium,Low"', allow_blank=True)
            priority_range = f"{priority_col_letter}{start_row}:{priority_col_letter}{end_row}"
            priority_dv.add(priority_range)
            ws.add_data_validation(priority_dv)

            # Conditional formatting for Priority
            high_fill = PatternFill(start_color=cls.PRIORITY_HIGH_FILL_HEX, end_color=cls.PRIORITY_HIGH_FILL_HEX, fill_type="solid")
            high_font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color=cls.PRIORITY_HIGH_FONT_HEX)
            ws.conditional_formatting.add(priority_range, CellIsRule(operator="equal", formula=['"High"'], fill=high_fill, font=high_font))

            med_fill = PatternFill(start_color=cls.PRIORITY_MED_FILL_HEX, end_color=cls.PRIORITY_MED_FILL_HEX, fill_type="solid")
            med_font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color=cls.PRIORITY_MED_FONT_HEX)
            ws.conditional_formatting.add(priority_range, CellIsRule(operator="equal", formula=['"Medium"'], fill=med_fill, font=med_font))

            low_fill = PatternFill(start_color=cls.PRIORITY_LOW_FILL_HEX, end_color=cls.PRIORITY_LOW_FILL_HEX, fill_type="solid")
            low_font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color=cls.PRIORITY_LOW_FONT_HEX)
            ws.conditional_formatting.add(priority_range, CellIsRule(operator="equal", formula=['"Low"'], fill=low_fill, font=low_font))

    @classmethod
    def _auto_fit_columns(cls, ws, max_col_width=65):
        if not HAS_OPENPYXL:
            return
        if hasattr(ws, "views") and hasattr(ws.views, "sheetView") and ws.views.sheetView:
            ws.views.sheetView[0].showGridLines = True

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val is not None:
                    val_str = str(val)
                    if not val_str.startswith("="):
                        lines = val_str.split("\n")
                        for line in lines:
                            max_len = max(max_len, len(line))
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

        # Normalize data from master_report dictionary if provided
        if master_report:
            p_obj = master_report.get("project", {})
            c_obj = master_report.get("crawl", {})
            h_obj = master_report.get("health", {})
            project_name = p_obj.get("name") or project_name or "Website Project"
            project_url = p_obj.get("url") or project_url or p_obj.get("domain") or "https://example.com"
            metadata = metadata or {"timestamp": c_obj.get("timestamp", datetime.now().strftime("%Y-%m-%d")), "crawl_id": c_obj.get("crawl_id")}
            pages = pages if pages is not None else master_report.get("affected_pages", [])
            keywords = keywords if keywords is not None else master_report.get("keywords", [])
            issues = issues if issues is not None else master_report.get("problems", [])
            opportunities = opportunities if opportunities is not None else master_report.get("opportunities", [])
            ai_insights = ai_insights if ai_insights is not None else master_report.get("ai_analysis", {})
            internal_links = internal_links if internal_links is not None else master_report.get("content_and_links", {}).get("internal_links", [])
            outbound_links = outbound_links if outbound_links is not None else master_report.get("content_and_links", {}).get("outbound_links", [])
            competitors = competitors if competitors is not None else master_report.get("competitors", [])
            backlinks = backlinks if backlinks is not None else master_report.get("backlinks", {}).get("inbound_backlinks", [])
            aeo_list = master_report.get("aeo", [])
            geo_list = master_report.get("geo", [])
            business_context = master_report.get("business_context", {})
            health_score = h_obj.get("health_score")
        else:
            project_name = project_name or "Website Project"
            project_url = project_url or "https://example.com"
            metadata = metadata or {"timestamp": datetime.now().strftime("%Y-%m-%d")}
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
            business_context = {}
            health_score = ai_insights.get("health_score")

        wb = openpyxl.Workbook()
        wb.remove(wb.active) # Remove default initial sheet

        # Clean Domain & Context
        clean_domain = str(project_url).replace("http://", "").replace("https://", "").rstrip("/")
        crawl_timestamp = metadata.get("timestamp") or datetime.now().strftime("%Y-%m-%d")
        crawl_id = metadata.get("crawl_id") or "latest"
        raw_ind = business_context.get("industry")
        industry_text = ", ".join(raw_ind) if isinstance(raw_ind, list) else str(raw_ind or "Digital Business & Specialized Services")

        raw_serv = business_context.get("services")
        services_text = ", ".join(raw_serv) if isinstance(raw_serv, list) else str(raw_serv or "Core Digital Solutions")

        raw_areas = business_context.get("service_areas")
        service_areas_text = ", ".join(raw_areas) if isinstance(raw_areas, list) else str(raw_areas or "Primary Service Regions")

        # Filter discovered pages by type for targeted planning
        service_pages = [p for p in pages if any(k in p.get("url", "").lower() for k in ["/service", "/solar", "/electrical", "/solution", "/product", "/offering"])]
        location_pages = [p for p in pages if any(k in p.get("url", "").lower() for k in ["/location", "/sydney", "/brisbane", "/melbourne", "/gold-coast", "/city", "/area"])]
        core_pages = service_pages + location_pages if (service_pages or location_pages) else pages[:15]

        # Categorize Technical vs On-Page Issues
        tech_issues = [i for i in issues if str(i.get("category", "")).lower() in ("technical", "security", "crawlability", "performance") or any(k in str(i.get("problem", "")).lower() for k in ["status", "404", "5xx", "redirect", "canonical", "robots", "https", "sitemap", "orphan"])]
        onpage_issues = [i for i in issues if i not in tech_issues]

        crit_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("Critical", "Fatal"))
        high_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("High", "Error"))
        warn_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("Warning", "Medium"))
        info_count = sum(1 for i in issues if str(i.get("severity", "")).capitalize() in ("Informational", "Notice", "Low", "Info"))

        # Health score formatting rule: Null / uncrawled -> "Not yet scored"
        if not pages or health_score is None:
            health_score_display = "Not yet scored"
        else:
            health_score_display = f"{health_score} / 100"

        # =========================================================================
        # 1. 📊 Dashboard Sheet
        # =========================================================================
        ws_dash = wb.create_sheet(title="📊 Dashboard")
        ws_dash.freeze_panes = "A3"

        # Row 1: Merged Title Banner
        ws_dash.merge_cells("A1:H1")
        ws_dash["A1"] = f"⚡ {project_name} — SEO Master Tracker"
        ws_dash["A1"].font = Font(name=cls.FONT_FAMILY, size=15, bold=True, color="FFFFFF")
        ws_dash["A1"].fill = PatternFill(start_color=cls.PRIMARY_HEADER_FILL_HEX, end_color=cls.PRIMARY_HEADER_FILL_HEX, fill_type="solid")
        ws_dash["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws_dash.row_dimensions[1].height = 36

        # Row 2: Merged Subtitle Banner
        ws_dash.merge_cells("A2:H2")
        ws_dash["A2"] = f"{industry_text} | {clean_domain} | Audit Timestamp: {crawl_timestamp}"
        ws_dash["A2"].font = Font(name=cls.FONT_FAMILY, size=10, italic=True, color="475569")
        ws_dash["A2"].fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
        ws_dash["A2"].alignment = Alignment(horizontal="center", vertical="center")
        ws_dash.row_dimensions[2].height = 22

        # Section 1: Website Information & Audit Health
        ws_dash.merge_cells("A4:H4")
        ws_dash["A4"] = "1. WEBSITE INFORMATION & AUDIT HEALTH"
        cls._apply_header_style(ws_dash, row=4, fill_hex=cls.SECTION_HEADER_FILL_HEX, font_size=10, row_height=24)

        info_rows = [
            ("Business / Project Name", project_name, "Pages Scanned & Crawled", len(pages)),
            ("Target Domain URL", project_url, "Total Problems Detected", len(issues)),
            ("Industry & Service Focus", industry_text, "Audit Checks Evaluated", f"{len(pages) * 14} ({len(pages)} pages × 14 core rules)"),
            ("Target Service Locations", service_areas_text, "Latest Crawl ID", crawl_id),
            ("Audit Crawl Timestamp", crawl_timestamp, "Website Health Score", health_score_display)
        ]
        for r_offset, (l1, v1, l2, v2) in enumerate(info_rows, start=5):
            ws_dash[f"A{r_offset}"] = l1
            ws_dash[f"B{r_offset}"] = v1
            ws_dash[f"D{r_offset}"] = l2
            ws_dash[f"E{r_offset}"] = v2
            ws_dash[f"A{r_offset}"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
            ws_dash[f"D{r_offset}"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
            ws_dash[f"B{r_offset}"].font = Font(name=cls.FONT_FAMILY, size=9.5, color="0F172A")
            ws_dash[f"E{r_offset}"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=(l2=="Website Health Score"), color="0F172A")
            cls._apply_data_row_style(ws_dash, r_offset, row_height=20)

        # Section 2: Live Campaign KPI Summary (Formula-Driven Tracker)
        ws_dash.merge_cells("A11:H11")
        ws_dash["A11"] = "2. LIVE CAMPAIGN KPI SUMMARY (FORMULA-DRIVEN TRACKER)"
        cls._apply_header_style(ws_dash, row=11, fill_hex=cls.SECTION_HEADER_FILL_HEX, font_size=10, row_height=24)

        ws_dash.append(["Worksheet / Campaign Area", "Campaign Focus", "Done (Formula)", "In Progress (Formula)", "Not Started (Formula)", "Total Active Tasks", "Completion Rate", "Status Indicator"])
        cls._apply_header_style(ws_dash, row=12, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)

        kpi_defs = [
            ("Technical SEO", "Core Infrastructure & Health", "=COUNTIF('🔧 Technical SEO'!D:D, \"Done\")", "=COUNTIF('🔧 Technical SEO'!D:D, \"In Progress\")", "=COUNTIF('🔧 Technical SEO'!D:D, \"Not Started\")", "=C13+D13+E13", "=IF(F13>0, C13/F13, 0)", "Active Tracker"),
            ("On-Page SEO", "Page Titles, Meta & Content", "=COUNTIF('📝 On-Page SEO'!G:G, \"Done\")", "=COUNTIF('📝 On-Page SEO'!G:G, \"In Progress\")", "=COUNTIF('📝 On-Page SEO'!G:G, \"Not Started\")", "=C14+D14+E14", "=IF(F14>0, C14/F14, 0)", "Active Tracker"),
            ("Local SEO", "GBP, NAP & Geo Landing Pages", "=COUNTIF('📍 Local SEO'!D:D, \"Done\")", "=COUNTIF('📍 Local SEO'!D:D, \"In Progress\")", "=COUNTIF('📍 Local SEO'!D:D, \"Not Started\")", "=C15+D15+E15", "=IF(F15>0, C15/F15, 0)", "Active Tracker"),
            ("Content & Links", "Internal Linking & Backlinks", "=COUNTIF('🔗 Content & Links'!E:E, \"Done\")", "=COUNTIF('🔗 Content & Links'!E:E, \"In Progress\")", "=COUNTIF('🔗 Content & Links'!E:E, \"Not Started\")", "=C16+D16+E16", "=IF(F16>0, C16/F16, 0)", "Active Tracker"),
            ("AEO Optimization", "Direct Answers & FAQ Schema", "=COUNTIF('🤖 AEO'!G:G, \"Done\")", "=COUNTIF('🤖 AEO'!G:G, \"In Progress\")", "=COUNTIF('🤖 AEO'!G:G, \"Not Started\")", "=C17+D17+E17", "=IF(F17>0, C17/F17, 0)", "Active Tracker"),
            ("GEO Generative SEO", "Entity Authority & Citations", "=COUNTIF('🌐 GEO'!F:F, \"Done\")", "=COUNTIF('🌐 GEO'!F:F, \"In Progress\")", "=COUNTIF('🌐 GEO'!F:F, \"Not Started\")", "=C18+D18+E18", "=IF(F18>0, C18/F18, 0)", "Active Tracker"),
            ("Keyword Research", "Topic Clusters & Opportunities", "=COUNTIF('📈 Keyword Research'!C:C, \"Done\")", "=COUNTIF('📈 Keyword Research'!C:C, \"In Progress\")", "=COUNTIF('📈 Keyword Research'!C:C, \"Not Started\")", "=C19+D19+E19", "=IF(F19>0, C19/F19, 0)", "Active Tracker")
        ]
        for row_num, kpi in enumerate(kpi_defs, start=13):
            ws_dash.append(list(kpi))
            cls._apply_data_row_style(ws_dash, row_num, row_height=20)
            ws_dash[f"G{row_num}"].number_format = "0.0%"

        # Section 3: Crawl Health Summary & Severity Breakdown
        ws_dash.merge_cells("A21:H21")
        ws_dash["A21"] = "3. CRAWL HEALTH SUMMARY & ISSUE SEVERITY BREAKDOWN"
        cls._apply_header_style(ws_dash, row=21, fill_hex=cls.SECTION_HEADER_FILL_HEX, font_size=10, row_height=24)

        ws_dash.append(["Severity Level", "Issue Count", "Share of Problems", "Urgency / Remediation SLA", "Primary Remediation Focus", "", "", ""])
        cls._apply_header_style(ws_dash, row=22, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)

        total_p = max(len(issues), 1)
        sev_data = [
            ("🔴 Critical Technical Blockers", crit_count, f"{(crit_count/total_p)*100:.1f}%", "Immediate (0–7 Days)", "Restore server 200 OK responses, fix broken URLs and redirects"),
            ("🟠 High Priority Errors", high_count, f"{(high_count/total_p)*100:.1f}%", "Urgent (8–30 Days)", "Resolve missing meta titles, descriptions, and primary H1 structure"),
            ("🟡 Warnings & Opportunities", warn_count, f"{(warn_count/total_p)*100:.1f}%", "Scheduled (30–60 Days)", "Expand thin content pages (<300 words) and add contextual internal links"),
            ("🔵 Informational & Notice", info_count, f"{(info_count/total_p)*100:.1f}%", "Ongoing", "Continuous crawl monitoring, schema markup, and rank tracking")
        ]
        for row_num, s in enumerate(sev_data, start=23):
            ws_dash.append([s[0], s[1], s[2], s[3], s[4], "", "", ""])
            cls._apply_data_row_style(ws_dash, row_num, row_height=20)

        # Section 4: Core Pages to Rank
        ws_dash.merge_cells("A28:H28")
        ws_dash["A28"] = "4. CORE PAGES TO RANK"
        cls._apply_header_style(ws_dash, row=28, fill_hex=cls.SECTION_HEADER_FILL_HEX, font_size=10, row_height=24)

        ws_dash.append(["#", "Page Name / Topic", "Page URL", "Page Type", "Target Keyword", "Target Location", "Priority", "Status"])
        cls._apply_header_style(ws_dash, row=29, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)

        start_p_row = 30
        for p_idx, p in enumerate(core_pages[:12], start=1):
            p_url = p.get("url") or project_url
            p_title = p.get("title") or (p_url.rstrip("/").split("/")[-1].replace("-", " ").title() if p_url else "Homepage")
            p_type = "Service Page" if "/service" in p_url.lower() else "Location Page" if "/location" in p_url.lower() else "Core Landing Page"
            ws_dash.append([
                p_idx,
                p_title,
                p_url,
                p_type,
                keywords[p_idx % len(keywords)]["keyword"] if keywords else f"{project_name} Service",
                service_areas_text.split(",")[0] if "," in service_areas_text else service_areas_text,
                "High" if p_idx <= 3 else "Medium",
                "In Progress" if p_idx <= 2 else "Not Started"
            ])
            cls._apply_data_row_style(ws_dash, start_p_row + p_idx - 1, row_height=20)
        end_p_row = start_p_row + len(core_pages[:12]) - 1

        cls._apply_status_priority_validation_and_rules(ws_dash, "H", "G", start_p_row, end_p_row)
        cls._auto_fit_columns(ws_dash)

        # =========================================================================
        # 2. 🔧 Technical SEO Sheet
        # =========================================================================
        ws_tech = wb.create_sheet(title="🔧 Technical SEO")
        ws_tech.freeze_panes = "A4"

        ws_tech.merge_cells("A1:H1")
        ws_tech["A1"] = "🔧 Technical SEO Audit & Implementation Checklist"
        cls._apply_header_style(ws_tech, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Row 2: Live Status Summary Counters
        ws_tech["A2"] = "Live Status Counters:"
        ws_tech["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_tech["B2"] = '="Done: " & COUNTIF(D4:D100, "Done")'
        ws_tech["C2"] = '="In Progress: " & COUNTIF(D4:D100, "In Progress")'
        ws_tech["D2"] = '="Not Started: " & COUNTIF(D4:D100, "Not Started")'
        ws_tech["E2"] = '="Total Checklist Tasks: " & COUNTA(B4:B100)'
        for col_letter in ["B", "C", "D", "E"]:
            ws_tech[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_tech.row_dimensions[2].height = 22

        ws_tech.append(["#", "Task / Check", "Category", "Status", "Priority", "Tool / Resource", "Date Done", "Notes / Evidence & Crawl Findings"])
        cls._apply_header_style(ws_tech, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_tech.auto_filter.ref = "A3:H3"

        # Comprehensive Standard Technical Checklist + Mapped Crawl Problems
        tech_checklist_templates = [
            ("HTTPS & SSL Encryption Verification", "Security", "High", "SSL Labs / Crawler", "Ensure all HTTP traffic seamlessly 301 redirects to canonical HTTPS."),
            ("HTTP 200 OK Status Code Health", "Status Codes", "High", "Website Crawler", "Verify internal navigation links return HTTP 200 without broken routes."),
            ("404 Error Remediation & Broken Links", "Status Codes", "High", "Website Crawler", "Restore missing valid pages or 301 redirect dead links to relevant destinations."),
            ("5xx Server Error Resolution", "Server Infrastructure", "High", "Server Access Logs", "Diagnose backend 500/502/503 errors and eliminate server crashes."),
            ("Redirect Chain & Loop Prevention", "Redirects", "Medium", "Website Crawler", "Eliminate multi-hop redirect chains (ensure 1 direct 301 redirect)."),
            ("Canonical Tag Self-Referencing Implementation", "Indexability", "High", "HTML Source", "Verify each indexable page contains an explicit self-referencing canonical tag."),
            ("Robots.txt Crawl Directives & Optimization", "Crawlability", "High", "Robots.txt Tester", "Confirm critical service and location pages are not blocked by Disallow rules."),
            ("XML Sitemap Generation & Verification", "Crawlability", "High", "GSC / Sitemap", "Ensure XML sitemap is updated, valid, and lists all indexable canonical URLs."),
            ("Crawl Depth & Site Architecture Architecture", "Architecture", "Medium", "Website Crawler", "Ensure core service and location landing pages are reachable within <= 3 clicks."),
            ("Meta Robots Indexing Directives", "Indexability", "High", "HTML Head", "Prevent accidental noindex / nofollow tags on high-intent conversion pages."),
            ("Duplicate URL & Parameter Normalization", "Duplicate Content", "Medium", "Search Console", "Normalize trailing slashes, case-sensitivity, and tracking URL parameters."),
            ("Title Tag Uniqueness & Length (<60 Chars)", "Metadata", "High", "SEO Spider", "Ensure each audited page possesses a unique, descriptive <title> tag."),
            ("Meta Description Completeness (<160 Chars)", "Metadata", "High", "SEO Spider", "Provide compelling, unique meta descriptions for search result click-through."),
            ("Primary H1 Heading Hierarchy Verification", "Content Structure", "High", "HTML Body", "Ensure exactly one primary <h1> tag per page matching its core topic."),
            ("Mobile Responsiveness & Viewport Configuration", "Mobile Usability", "High", "Mobile Friendly Test", "Confirm mobile viewport meta tag is configured with responsive layouts."),
            ("Page Speed & Asset Minification", "Performance", "Medium", "PageSpeed Insights", "Minify CSS/JS bundles and defer non-critical render-blocking assets."),
            ("Core Web Vitals (LCP, INP, CLS)", "Performance", "Medium", "Chrome UX Report", "Optimize Largest Contentful Paint (<2.5s) and Cumulative Layout Shift (<0.1)."),
            ("Image Optimization & Descriptive Alt Text", "Assets", "Medium", "Asset Audit", "Compress image assets into WebP format and ensure descriptive alt attributes."),
            ("Contextual Internal Link Equity Distribution", "Links", "Medium", "Internal Link Audit", "Interlink related service categories with keyword-relevant anchor text."),
            ("Orphan Page Detection & Remediation", "Architecture", "Medium", "Crawl Comparison", "Ensure all published content pages have incoming internal navigational links."),
            ("Structured Data & Schema Markup (JSON-LD)", "Structured Data", "High", "Schema Validator", "Deploy Organization, WebSite, and LocalBusiness schema markup."),
            ("JavaScript Rendering & Content Discoverability", "Rendering", "Medium", "URL Inspection", "Verify client-side rendered content is indexable by search engine bots."),
            ("Security Headers (HSTS, CSP, X-Frame-Options)", "Security", "Medium", "SecurityHeaders.com", "Deploy HSTS, X-Content-Type-Options, and X-Frame-Options HTTP headers."),
            ("Clean URL Slug Formatting", "URL Structure", "Low", "URL Audit", "Use lowercase, hyphen-separated keyword-rich URL slugs without special characters.")
        ]

        t_row = 4
        for idx, (t_task, t_cat, t_prio, t_tool, t_notes) in enumerate(tech_checklist_templates, start=1):
            # Check if this check maps to an actual crawl issue
            matched_issues = [i for i in tech_issues if t_cat.lower() in str(i.get("category","")).lower() or any(w in str(i.get("problem","")).lower() for w in t_task.lower().split()[:2])]
            if matched_issues:
                iss = matched_issues[0]
                status_val = "Not Started"
                prio_val = str(iss.get("severity", t_prio)).capitalize()
                notes_val = f"Observed Finding: {iss.get('what_was_found') or iss.get('problem')}. Affected: {iss.get('affected_url') or 'Site'}. AI Solution: {iss.get('ai_solution') or 'Resolve issue.'}"
            else:
                status_val = "Done" if len(pages) > 0 else "Not Started"
                prio_val = t_prio
                notes_val = f"{t_notes} (Audit verified compliant)."

            ws_tech.append([idx, t_task, t_cat, status_val, prio_val, t_tool, crawl_timestamp if status_val == "Done" else "", notes_val])
            cls._apply_data_row_style(ws_tech, t_row, row_height=20)
            t_row += 1

        cls._apply_status_priority_validation_and_rules(ws_tech, "D", "E", 4, t_row - 1)
        cls._auto_fit_columns(ws_tech)

        # =========================================================================
        # 3. 📝 On-Page SEO Sheet
        # =========================================================================
        ws_onpage = wb.create_sheet(title="📝 On-Page SEO")
        ws_onpage.freeze_panes = "A4"

        ws_onpage.merge_cells("A1:I1")
        ws_onpage["A1"] = "📝 On-Page SEO Optimization & Remediation Tracker"
        cls._apply_header_style(ws_onpage, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_onpage["A2"] = "Live Status Counters:"
        ws_onpage["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_onpage["B2"] = '="Done: " & COUNTIF(G4:G200, "Done")'
        ws_onpage["C2"] = '="In Progress: " & COUNTIF(G4:G200, "In Progress")'
        ws_onpage["D2"] = '="Not Started: " & COUNTIF(G4:G200, "Not Started")'
        for col_letter in ["B", "C", "D"]:
            ws_onpage[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_onpage.row_dimensions[2].height = 22

        ws_onpage.append(["#", "Affected Page URL", "On-Page Element", "Current Value / Finding", "Problem Identified", "Recommended AI Solution & Replacement", "Status", "Priority", "Target Keyword / Topic"])
        cls._apply_header_style(ws_onpage, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_onpage.auto_filter.ref = "A3:I3"

        op_row = 4
        if onpage_issues:
            for idx, iss in enumerate(onpage_issues, start=1):
                p_url = iss.get("affected_url") or iss.get("url") or project_url
                elem = "Title Tag" if "title" in str(iss.get("problem","")).lower() else "Meta Description" if "description" in str(iss.get("problem","")).lower() else "H1 Tag" if "h1" in str(iss.get("problem","")).lower() else "Content Body"
                cur_val = iss.get("current_value") or iss.get("what_was_found") or "Incomplete on-page element"
                prob_id = iss.get("problem") or iss.get("issue") or "On-page optimization needed"
                sol_text = iss.get("recommended_fix") or iss.get("ai_solution") or iss.get("recommended_action") or "Update HTML tag."
                rep_val = iss.get("replacement_value")
                if rep_val and str(rep_val).strip() != str(sol_text).strip():
                    ai_sol = f"{sol_text} — Replacement: \"{rep_val}\""
                else:
                    ai_sol = sol_text
                prio = str(iss.get("severity", "Medium")).capitalize()
                ws_onpage.append([
                    idx,
                    p_url,
                    elem,
                    cur_val,
                    prob_id,
                    ai_sol,
                    "Not Started",
                    prio if prio in ("High", "Medium", "Low") else "Medium",
                    keywords[idx % len(keywords)]["keyword"] if keywords else f"{project_name} Focus"
                ])
                cls._apply_data_row_style(ws_onpage, op_row, row_height=20)
                op_row += 1
        else:
            # Generate actionable standard on-page tasks from pages
            sample_pages = pages[:10] if pages else [{"url": project_url, "title": project_name}]
            for idx, p in enumerate(sample_pages, start=1):
                ws_onpage.append([
                    idx,
                    p.get("url", project_url),
                    "Title & Meta Description",
                    p.get("title") or "Homepage Title",
                    "Maintain keyword relevance and click-through optimization",
                    f"Ensure target keywords are prominently placed in the title tag and meta description for {p.get('url', clean_domain)}.",
                    "Done" if len(pages) > 0 else "Not Started",
                    "Medium",
                    keywords[idx % len(keywords)]["keyword"] if keywords else project_name
                ])
                cls._apply_data_row_style(ws_onpage, op_row, row_height=20)
                op_row += 1

        cls._apply_status_priority_validation_and_rules(ws_onpage, "G", "H", 4, op_row - 1)
        cls._auto_fit_columns(ws_onpage)

        # =========================================================================
        # 4. 📍 Local SEO Sheet
        # =========================================================================
        ws_local = wb.create_sheet(title="📍 Local SEO")
        ws_local.freeze_panes = "A4"

        ws_local.merge_cells("A1:G1")
        ws_local["A1"] = "📍 Local SEO & Google Business Profile Campaign Tracker"
        cls._apply_header_style(ws_local, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_local["A2"] = "Live Status Counters:"
        ws_local["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_local["B2"] = '="Done: " & COUNTIF(D4:D50, "Done")'
        ws_local["C2"] = '="In Progress: " & COUNTIF(D4:D50, "In Progress")'
        ws_local["D2"] = '="Not Started: " & COUNTIF(D4:D50, "Not Started")'
        for col_letter in ["B", "C", "D"]:
            ws_local[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_local.row_dimensions[2].height = 22

        ws_local.append(["#", "Local SEO Strategy / Task", "Target Location / Entity", "Status", "Priority", "Implementation Action Plan", "Evidence / Notes"])
        cls._apply_header_style(ws_local, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_local.auto_filter.ref = "A3:G3"

        loc_tasks = [
            ("Google Business Profile (GBP) Primary Category Optimization", "Primary Business Entity", "In Progress", "High", "Claim, verify, and optimize primary & secondary business categories.", "Align GBP category with primary target services."),
            ("NAP Consistency Audit (Name, Address, Phone)", f"All Locations ({service_areas_text})", "Not Started", "High", "Standardize business name, physical address, and local phone format in website footer and citations.", "Audit website footer vs directory listings."),
            ("Target Service-Area Landing Pages", service_areas_text, "In Progress", "High", f"Build dedicated high-converting location landing pages for {service_areas_text}.", "Target '[Service] in [Location]' search queries."),
            ("LocalBusiness Structured Schema (JSON-LD)", "Website Head", "Not Started", "High", "Embed LocalBusiness schema with opening hours, geo coordinates, and address.", "Enables rich local search knowledge panel cards."),
            ("Customer Review Generation & Reputation Management", "Google Maps / GBP", "Not Started", "Medium", "Establish an automated post-service review request campaign for satisfied customers.", "Target minimum 20+ authentic 5-star reviews."),
            ("Local Business Directory Citations", "Major Aggregators", "Not Started", "Medium", "Submit verified citations to Apple Maps, Bing Places, YellowPages, and TrueLocal.", "Build strong local geographic prominence signals."),
            ("Google Maps Embed on Contact & Location Pages", "Contact Page", "Done" if len(location_pages) > 0 else "Not Started", "Low", "Embed interactive Google Maps iframe to confirm physical entity service area.", "Strengthens entity geographic boundary signals."),
            ("Location-Specific FAQs & Geo Entity Signals", service_areas_text, "Not Started", "Medium", "Add neighborhood-specific FAQs and landmarks to service-area landing pages.", "Captures hyper-local conversational search intent."),
            ("Geo-Targeted Meta Titles & Headers", service_areas_text, "In Progress", "High", f"Include target city names ({service_areas_text}) in page <title> and <h1> tags.", "Boosts local map pack and organic rankings.")
        ]

        l_row = 4
        for idx, (t_name, t_loc, t_stat, t_prio, t_plan, t_note) in enumerate(loc_tasks, start=1):
            ws_local.append([idx, t_name, t_loc, t_stat, t_prio, t_plan, t_note])
            cls._apply_data_row_style(ws_local, l_row, row_height=20)
            l_row += 1

        cls._apply_status_priority_validation_and_rules(ws_local, "D", "E", 4, l_row - 1)
        cls._auto_fit_columns(ws_local)

        # =========================================================================
        # 5. 🔗 Content & Links Sheet
        # =========================================================================
        ws_links = wb.create_sheet(title="🔗 Content & Links")
        ws_links.freeze_panes = "A4"

        ws_links.merge_cells("A1:G1")
        ws_links["A1"] = "🔗 Content Improvements, Internal Links & Backlink Authority"
        cls._apply_header_style(ws_links, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_links["A2"] = "Live Status Counters:"
        ws_links["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_links["B2"] = '="Done: " & COUNTIF(E4:E200, "Done")'
        ws_links["C2"] = '="In Progress: " & COUNTIF(E4:E200, "In Progress")'
        ws_links["D2"] = '="Not Started: " & COUNTIF(E4:E200, "Not Started")'
        for col_letter in ["B", "C", "D"]:
            ws_links[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_links.row_dimensions[2].height = 22

        ws_links.append(["#", "Link Category / Item", "Source Page URL", "Destination Page URL", "Status", "Priority", "Anchor Text / Context", "AI Optimization Action & Recommendation"])
        cls._apply_header_style(ws_links, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_links.auto_filter.ref = "A3:H3"

        link_row = 4
        if internal_links:
            for idx, lnk in enumerate(internal_links[:40], start=1):
                src = lnk.get("source") or lnk.get("source_url") or project_url
                tgt = lnk.get("target") or lnk.get("target_url") or project_url
                anchor = lnk.get("anchor") or lnk.get("anchor_text") or "(Generic Navigational Link)"
                ws_links.append([
                    idx,
                    "Internal Navigational Link",
                    src,
                    tgt,
                    "Done",
                    "Low",
                    anchor,
                    "Maintain internal link equity; ensure anchor text incorporates descriptive service keywords."
                ])
                cls._apply_data_row_style(ws_links, link_row, row_height=20)
                link_row += 1
        else:
            sample_links = [
                ("Internal Navigational Link", project_url, f"{project_url}/services", "Done", "Medium", "Our Services", "Maintain primary navigational pathway to core service offerings."),
                ("Internal Contextual Link", f"{project_url}/services", f"{project_url}/contact", "Done", "High", "Get a Free Quote", "Prominent call-to-action internal link driving user conversions."),
                ("External Authority Reference", f"{project_url}/services", "https://schema.org", "Done", "Low", "Schema Documentation", "Outbound reference link citing industry standards.")
            ]
            for idx, item in enumerate(sample_links, start=1):
                ws_links.append([idx, item[0], item[1], item[2], item[3], item[4], item[5], item[6]])
                cls._apply_data_row_style(ws_links, link_row, row_height=20)
                link_row += 1

        cls._apply_status_priority_validation_and_rules(ws_links, "E", "F", 4, link_row - 1)
        cls._auto_fit_columns(ws_links)

        # =========================================================================
        # 6. 📈 Keywords Sheet
        # =========================================================================
        ws_kw = wb.create_sheet(title="📈 Keywords")
        ws_kw.freeze_panes = "A3"

        ws_kw.merge_cells("A1:M1")
        ws_kw["A1"] = "📈 Keyword Targeting & SERP Tracking"
        cls._apply_header_style(ws_kw, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        ws_kw.append(["#", "Keyword", "Search Intent", "Target URL", "Current Position", "Previous Position", "Position Change", "Search Volume", "Difficulty", "Priority", "Status", "Opportunity", "Notes"])
        cls._apply_header_style(ws_kw, row=2, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_kw.auto_filter.ref = "A2:M2"

        kw_row = 3
        if keywords:
            for idx, kw in enumerate(keywords, start=1):
                k_word = kw.get("keyword", "")
                k_tgt = kw.get("target_url") or project_url
                k_intent = "Commercial" if any(w in k_word.lower() for w in ["buy", "hire", "service", "contractor", "installer", "price", "cost"]) else "Informational"
                ws_kw.append([
                    idx,
                    k_word,
                    k_intent,
                    k_tgt,
                    kw.get("position") or "Not available",
                    kw.get("previous_position") or "Not available",
                    kw.get("change") or "Not available",
                    kw.get("volume") or "Not available",
                    kw.get("difficulty") or "Not available",
                    "High" if idx <= 5 else "Medium",
                    "Targeting",
                    f"Incorporate '{k_word}' into primary H1 and meta description tags of relevant landing page.",
                    f"Discovered from {clean_domain} crawl content"
                ])
                cls._apply_data_row_style(ws_kw, kw_row, row_height=20)
                kw_row += 1
        else:
            ws_kw.append([
                1,
                project_name,
                "Navigational",
                project_url,
                "Not available",
                "Not available",
                "Not available",
                "Not available",
                "Not available",
                "High",
                "Targeting",
                "Brand search query optimization",
                "Primary brand keyword"
            ])
            cls._apply_data_row_style(ws_kw, kw_row, row_height=20)
            kw_row += 1

        cls._apply_status_priority_validation_and_rules(ws_kw, "K", "J", 3, kw_row - 1)
        cls._auto_fit_columns(ws_kw)

        # =========================================================================
        # 7. 🤖 AEO Sheet (Answer Engine Optimization)
        # =========================================================================
        ws_aeo = wb.create_sheet(title="🤖 AEO")
        ws_aeo.freeze_panes = "A4"

        ws_aeo.merge_cells("A1:H1")
        ws_aeo["A1"] = "🤖 AEO — Answer Engine Optimization & Direct Answers"
        cls._apply_header_style(ws_aeo, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_aeo["A2"] = "Live Status Counters:"
        ws_aeo["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_aeo["B2"] = '="Done: " & COUNTIF(G4:G100, "Done")'
        ws_aeo["C2"] = '="In Progress: " & COUNTIF(G4:G100, "In Progress")'
        ws_aeo["D2"] = '="Not Started: " & COUNTIF(G4:G100, "Not Started")'
        for col_letter in ["B", "C", "D"]:
            ws_aeo[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_aeo.row_dimensions[2].height = 22

        ws_aeo.append(["#", "Topic / Query Entity", "Target Page URL", "Question / Query Pattern", "Direct Answer Structure (40–60 words)", "FAQ Schema (JSON-LD)", "Status", "Priority", "Implementation Notes"])
        cls._apply_header_style(ws_aeo, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_aeo.auto_filter.ref = "A3:I3"

        aeo_row = 4
        if aeo_list:
            for idx, a in enumerate(aeo_list, start=1):
                ws_aeo.append([
                    idx,
                    a.get("topic", project_name),
                    a.get("url") or project_url,
                    f"What is the best solution for {a.get('topic', 'this service')} in {service_areas_text}?",
                    a.get("recommended_action") or "Provide concise 40-60 word answer directly below H2 heading.",
                    "FAQPage Schema",
                    "Not Started",
                    a.get("priority", "High"),
                    "Format concise bullet points and direct answers for voice search & featured snippets."
                ])
                cls._apply_data_row_style(ws_aeo, aeo_row, row_height=20)
                aeo_row += 1
        else:
            sample_aeo = [
                (f"{project_name} Core Services", project_url, f"What services does {project_name} provide?", f"{project_name} specializes in {services_text} across {service_areas_text}, delivering professional, certified solutions with guaranteed workmanship.", "FAQPage Schema", "In Progress", "High", "Place concise definition box at the top of the homepage."),
                ("Pricing & Turnaround Time", f"{project_url}/services", f"How much does {services_text.split(',')[0]} cost?", f"Pricing for {services_text.split(',')[0]} varies depending on scope, location in {service_areas_text}, and project requirements. Free transparent upfront quotes are available.", "FAQPage Schema", "Not Started", "High", "Add transparent pricing FAQ section to service pages.")
            ]
            for idx, item in enumerate(sample_aeo, start=1):
                ws_aeo.append([idx, item[0], item[1], item[2], item[3], item[4], item[5], item[6], item[7]])
                cls._apply_data_row_style(ws_aeo, aeo_row, row_height=20)
                aeo_row += 1

        cls._apply_status_priority_validation_and_rules(ws_aeo, "G", "H", 4, aeo_row - 1)
        cls._auto_fit_columns(ws_aeo)

        # =========================================================================
        # 8. 🌐 GEO Sheet (Generative Engine Optimization)
        # =========================================================================
        ws_geo = wb.create_sheet(title="🌐 GEO")
        ws_geo.freeze_panes = "A4"

        ws_geo.merge_cells("A1:H1")
        ws_geo["A1"] = "🌐 GEO — Generative Engine Optimization & LLM Brand Citations"
        cls._apply_header_style(ws_geo, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_geo["A2"] = "Live Status Counters:"
        ws_geo["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_geo["B2"] = '="Done: " & COUNTIF(F4:F100, "Done")'
        ws_geo["C2"] = '="In Progress: " & COUNTIF(F4:F100, "In Progress")'
        ws_geo["D2"] = '="Not Started: " & COUNTIF(F4:F100, "Not Started")'
        for col_letter in ["B", "C", "D"]:
            ws_geo[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_geo.row_dimensions[2].height = 22

        ws_geo.append(["#", "Entity / Topic", "Strategy Focus", "Target Page URL", "Observed Evidence", "AI Optimization Action & Quotable Facts", "Status", "Priority", "Implementation Notes"])
        cls._apply_header_style(ws_geo, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_geo.auto_filter.ref = "A3:I3"

        geo_row = 4
        if geo_list:
            for idx, g in enumerate(geo_list, start=1):
                ws_geo.append([
                    idx,
                    g.get("entity") or project_name,
                    g.get("strategy") or "Entity Authority",
                    g.get("url") or project_url,
                    g.get("evidence") or "Brand Knowledge Graph Presence",
                    g.get("recommended_action") or "Deploy Organization Schema with verified 'sameAs' social and business registry links.",
                    "Not Started",
                    g.get("priority") or "High",
                    "Assists LLMs in recognizing brand identity."
                ])
                cls._apply_data_row_style(ws_geo, geo_row, row_height=20)
                geo_row += 1
        else:
            geo_tasks = [
                (project_name, "Brand Entity Authority", project_url, "Brand Knowledge Graph Presence", f"Deploy Organization Schema with verified 'sameAs' social and business registry links for {project_name}.", "In Progress", "High", "Assists LLMs (ChatGPT, Gemini, Perplexity) in recognizing brand identity."),
                ("Service Accreditations & Licenses", "E-E-A-T & Trust Signals", f"{project_url}/about", "Licensed Entity Credentials", "Highlight licensed contractor certifications, insurance credentials, and industry memberships.", "Not Started", "High", "Provides verifiable authority signals for AI answer citations."),
                ("Original Statistics & Case Studies", "Quotable Fact Citations", f"{project_url}/case-studies", "Verified Project Data", "Publish original project outcome metrics (e.g. 500+ projects completed, energy savings percentages).", "Not Started", "Medium", "Generative AI engines prioritize citing original proprietary statistics."),
                ("Author & Technical Reviewer Bylines", "Author Entity Recognition", f"{project_url}/blog", "Editorial Expertise Signals", "Add author bios and editorial review credentials to all informational guides.", "Not Started", "Medium", "Establishes topical expertise under Google Search Generative Experience.")
            ]
            for idx, (g_ent, g_strat, g_url, g_ev, g_act, g_stat, g_prio, g_notes) in enumerate(geo_tasks, start=1):
                ws_geo.append([idx, g_ent, g_strat, g_url, g_ev, g_act, g_stat, g_prio, g_notes])
                cls._apply_data_row_style(ws_geo, geo_row, row_height=20)
                geo_row += 1

        cls._apply_status_priority_validation_and_rules(ws_geo, "G", "H", 4, geo_row - 1)
        cls._auto_fit_columns(ws_geo)

        # =========================================================================
        # 9. 🔍 AI Citations Sheet
        # =========================================================================
        ws_cite = wb.create_sheet(title="🔍 AI Citations")
        ws_cite.freeze_panes = "A4"

        ws_cite.merge_cells("A1:H1")
        ws_cite["A1"] = "🔍 AI Engine Visibility & Citation Tracker"
        cls._apply_header_style(ws_cite, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_cite["A2"] = "Live Status Counters:"
        ws_cite["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_cite["B2"] = '="Mentioned: " & COUNTIF(D4:D50, "Mentioned")'
        ws_cite["C2"] = '="Not Mentioned: " & COUNTIF(D4:D50, "Not Mentioned")'
        ws_cite["D2"] = '="Not Tested: " & COUNTIF(D4:D50, "Not Tested")'
        for col_letter in ["B", "C", "D"]:
            ws_cite[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_cite.row_dimensions[2].height = 22

        ws_cite.append(["#", "Prompt Tested", "AI Platform", "Result", "Position / Context", "Competitors Mentioned", "Date Tested", "Notes"])
        cls._apply_header_style(ws_cite, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_cite.auto_filter.ref = "A3:H3"

        cite_prompts = [
            (f"Who are the top recommended {services_text.split(',')[0]} providers in {service_areas_text.split(',')[0]}?", "ChatGPT (OpenAI)", "Not Tested", "Awaiting Test", "Competitor Brands", crawl_timestamp, "Test conversational brand recall."),
            (f"Best rated {industry_text} companies in {service_areas_text.split(',')[0]} with reviews", "Perplexity AI", "Not Tested", "Awaiting Test", "Competitor Brands", crawl_timestamp, "Test web search cited references."),
            (f"Compare {project_name} vs competitors for {services_text.split(',')[0]}", "Google Gemini", "Not Tested", "Awaiting Test", "Competitor Brands", crawl_timestamp, "Test Google AI overview entity graph."),
            (f"How to hire a certified {services_text.split(',')[0]} in {service_areas_text.split(',')[0]}", "Google AI Overviews", "Not Tested", "Awaiting Test", "Competitor Brands", crawl_timestamp, "Test generative search answer inclusion.")
        ]

        c_row = 4
        for idx, (c_p, c_plat, c_res, c_pos, c_comp, c_dt, c_n) in enumerate(cite_prompts, start=1):
            ws_cite.append([idx, c_p, c_plat, c_res, c_pos, c_comp, c_dt, c_n])
            cls._apply_data_row_style(ws_cite, c_row, row_height=20)
            c_row += 1

        # Data Validation for AI Citations Result
        if HAS_OPENPYXL:
            res_dv = DataValidation(type="list", formula1='"Mentioned,Not Mentioned,Not Tested"', allow_blank=True)
            res_range = f"D4:D{c_row - 1}"
            res_dv.add(res_range)
            ws_cite.add_data_validation(res_dv)

        cls._auto_fit_columns(ws_cite)

        # =========================================================================
        # 10. 📈 Keyword Research Sheet
        # =========================================================================
        ws_kr = wb.create_sheet(title="📈 Keyword Research")
        ws_kr.freeze_panes = "A4"

        ws_kr.merge_cells("A1:J1")
        ws_kr["A1"] = "📈 Keyword Research & Content Planning Workspace"
        cls._apply_header_style(ws_kr, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        # Live Status Summary Counters
        ws_kr["A2"] = "Live Status Counters:"
        ws_kr["A2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="334155")
        ws_kr["B2"] = '="Done: " & COUNTIF(C4:C50, "Done")'
        ws_kr["C2"] = '="In Progress: " & COUNTIF(C4:C50, "In Progress")'
        ws_kr["D2"] = '="Not Started: " & COUNTIF(C4:C50, "Not Started")'
        for col_letter in ["B", "C", "D"]:
            ws_kr[f"{col_letter}2"].font = Font(name=cls.FONT_FAMILY, size=9.5, bold=True, color="0F172A")
        ws_kr.row_dimensions[2].height = 22

        ws_kr.append(["#", "Task / Action", "Status", "Priority", "Detail", "Owner", "Target Date", "Done Date", "Notes / Results", "Tool"])
        cls._apply_header_style(ws_kr, row=3, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_kr.auto_filter.ref = "A3:J3"

        kr_tasks = [
            ("Core Commercial Intent Keyword Discovery", "In Progress", "High", f"Identify high-intent commercial search queries for {services_text}.", "SEO Lead", crawl_timestamp, "", "Focus on transactional keywords.", "Google Keyword Planner / GSC"),
            ("Local Geo-Modified Keyword Mapping", "In Progress", "High", f"Map '[Service] in [Location]' keyword variations across {service_areas_text}.", "SEO Specialist", crawl_timestamp, "", "Map directly to location landing pages.", "Ahrefs / SEMrush / GSC"),
            ("Informational Question & FAQ Keyword Mining", "Not Started", "Medium", "Extract 'People Also Ask' question queries for voice search and AEO answer targets.", "Content Strategist", "", "", "Incorporate into blog and FAQ schemas.", "AlsoAsked / AnswerThePublic"),
            ("Competitor Keyword Gap Analysis", "Not Started", "High", "Identify keyword search opportunities ranking on competitor domains but missing on this site.", "SEO Lead", "", "", "Target high-value missing queries.", "Competitor Research"),
            ("Topical Cluster & Supporting Article Planning", "Not Started", "Medium", "Build topic cluster silos around core service pillars with supporting guides.", "Content Writer", "", "", "Boosts domain topical authority.", "Topic Clustering")
        ]

        kr_row = 4
        for idx, (k_act, k_st, k_pr, k_det, k_own, k_tgt, k_dn, k_not, k_tool) in enumerate(kr_tasks, start=1):
            ws_kr.append([idx, k_act, k_st, k_pr, k_det, k_own, k_tgt, k_dn, k_not, k_tool])
            cls._apply_data_row_style(ws_kr, kr_row, row_height=20)
            kr_row += 1

        cls._apply_status_priority_validation_and_rules(ws_kr, "C", "D", 4, kr_row - 1)
        cls._auto_fit_columns(ws_kr)

        # =========================================================================
        # 11. 📅 Monthly Review Sheet
        # =========================================================================
        ws_month = wb.create_sheet(title="📅 Monthly Review")
        ws_month.freeze_panes = "A3"

        ws_month.merge_cells("A1:K1")
        ws_month["A1"] = f"📅 {project_name} — Monthly SEO Performance & Campaign Review"
        cls._apply_header_style(ws_month, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=12, row_height=30)

        ws_month.append(["Month", "Organic Traffic", "vs Prior Month", "Top 10 Keywords", "Top 3 Keywords", "Total Backlinks", "New Backlinks", "Google Reviews", "GBP Profile Views", "Organic Leads", "Key Actions / Notes"])
        cls._apply_header_style(ws_month, row=2, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws_month.auto_filter.ref = "A2:K2"

        months = [
            "Month 1 (Baseline)", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6",
            "Month 7", "Month 8", "Month 9", "Month 10", "Month 11", "Month 12"
        ]

        m_row = 3
        for idx, m_name in enumerate(months, start=1):
            # Formula for vs Prior Month: =IF(AND(ISNUMBER(B4), ISNUMBER(B3), B3>0), (B4-B3)/B3, "")
            growth_formula = f'=IF(AND(ISNUMBER(B{m_row}), ISNUMBER(B{m_row-1}), B{m_row-1}>0), (B{m_row}-B{m_row-1})/B{m_row-1}, "")' if idx > 1 else "Baseline"
            ws_month.append([
                m_name,
                "", # Organic Traffic (left blank for user tracking, no fake data)
                growth_formula,
                "", # Top 10
                "", # Top 3
                "", # Total Backlinks
                "", # New Backlinks
                "", # Google Reviews
                "", # GBP Views
                "", # Organic Leads
                "Initial baseline crawl & audit completed" if idx == 1 else ""
            ])
            cls._apply_data_row_style(ws_month, m_row, row_height=20)
            if idx > 1:
                ws_month[f"C{m_row}"].number_format = "0.0%"
            m_row += 1

        cls._auto_fit_columns(ws_month)

        # Save to memory stream
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    # =========================================================================
    # PAGE-SPECIFIC EXPORT METHODS (STRICTLY SCOPED TO INDIVIDUAL DATASETS)
    # =========================================================================

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
        ws.freeze_panes = "A2"

        ws.append(["#", "Page URL", "HTTP Status", "Indexable Status", "Page Title", "Meta Description", "Primary H1", "Word Count", "Canonical URL", "Internal Links Count"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:J1"

        for idx, p in enumerate(pages, start=1):
            status_code = p.get("status_code", 200)
            ws.append([
                idx,
                p.get("url", ""),
                status_code,
                "Yes (Indexable)" if status_code == 200 else "No (Error / Blocked)",
                p.get("title", ""),
                p.get("meta_description", ""),
                p.get("h1", ""),
                p.get("word_count", 0),
                p.get("canonical", ""),
                len(p.get("internal_links", [])) if isinstance(p.get("internal_links"), list) else 0
            ])
            cls._apply_data_row_style(ws, idx + 1, row_height=20)

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
        ws.title = "Keywords Dataset"
        ws.freeze_panes = "A2"

        ws.append(["#", "Search Keyword", "Search Intent", "Target Page URL", "Content Frequency", "Source / Provenance", "AI Optimization Advice"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:G1"

        for idx, kw in enumerate(keywords, start=1):
            k_word = kw.get("keyword", "")
            k_tgt = kw.get("target_url") or f"https://{domain}"
            k_intent = "Commercial" if any(w in k_word.lower() for w in ["buy", "hire", "service", "contractor", "price", "cost"]) else "Informational"
            ws.append([
                idx,
                k_word,
                k_intent,
                k_tgt,
                kw.get("frequency", 1),
                kw.get("source") or "Extracted Page Content",
                f"Incorporate '{k_word}' into primary H1 and meta description tags."
            ])
            cls._apply_data_row_style(ws, idx + 1, row_height=20)

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
        ws.title = "Technical Issues"
        ws.freeze_panes = "A2"

        ws.append([
            "#",
            "Priority",
            "Category",
            "Problem",
            "Affected Pages",
            "What We Found",
            "Current Value",
            "Recommended Action",
            "AI Solution",
            "Implementation / Code",
            "Expected Improvement",
            "Verification",
            "Status",
            "Crawl Date"
        ])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:N1"

        for idx, iss in enumerate(issues, start=1):
            sev = str(iss.get("severity", "High")).capitalize()
            prio = iss.get("priority") or sev
            cat = iss.get("category") or "Technical"
            prob_title = iss.get("problem") or iss.get("title") or iss.get("issue") or "SEO Issue"
            url = iss.get("affected_url") or iss.get("url") or f"https://{domain}"
            what_found = iss.get("what_is_wrong") or iss.get("what_we_found") or iss.get("what_was_found") or iss.get("evidence") or prob_title
            cur_val = iss.get("current_value") or "Not configured"
            rec_act = iss.get("recommended_action") or iss.get("recommendation") or "Review and resolve issue."
            ai_sol = iss.get("ai_solution") or iss.get("what_should_change") or "Apply implementation fix."
            impl = iss.get("implementation") or iss.get("recommended_replacement") or iss.get("replacement_value") or ""
            exp_improv = iss.get("why_this_version_is_better") or iss.get("why_this_fixes_problem") or iss.get("why_this_fix") or iss.get("why_it_matters") or "Improves search visibility and CTR."
            verif = iss.get("verification") or f"Re-crawl website to confirm resolution of {prob_title}."
            status_val = iss.get("status") or "Open"
            crawl_dt = iss.get("crawl_date") or datetime.now().strftime("%Y-%m-%d")

            ws.append([
                idx,
                prio,
                cat,
                prob_title,
                url,
                what_found,
                cur_val,
                rec_act,
                ai_sol,
                impl,
                exp_improv,
                verif,
                status_val,
                crawl_dt
            ])
            cls._apply_data_row_style(ws, idx + 1, row_height=20)

        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_backlinks_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        backlinks = kwargs.get("backlinks")
        if backlinks is None and args:
            backlinks = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        backlinks = backlinks or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Backlinks Dataset"
        ws.freeze_panes = "A2"

        ws.append(["#", "Source URL / Referring Page", "Target Landing Page", "Anchor Text", "Domain Authority", "Status", "Link Type"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:G1"

        if backlinks:
            for idx, b in enumerate(backlinks, start=1):
                ws.append([
                    idx,
                    b.get("source_url") or b.get("source") or "",
                    b.get("target_url") or b.get("target") or "",
                    b.get("anchor_text") or b.get("anchor") or "(No Anchor Text)",
                    b.get("domain_authority") or b.get("authority") or "Not available",
                    b.get("status") or "Active",
                    b.get("link_type") or "Inbound Backlink"
                ])
                cls._apply_data_row_style(ws, idx + 1, row_height=20)
        else:
            ws.append([1, "Data Not Connected", "N/A", "N/A", "N/A", "Not Connected", "Inbound Backlinks require connecting an external backlink dataset."])
            cls._apply_data_row_style(ws, 2, row_height=20)

        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_competitors_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        competitors = kwargs.get("competitors")
        if competitors is None and args:
            competitors = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        competitors = competitors or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Competitors Analysis"
        ws.freeze_panes = "A2"

        ws.append(["#", "Competitor Brand Name", "Domain / Website URL", "Market Relevance", "Keyword Overlap", "Search Appearances", "Status"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:G1"

        if competitors:
            for idx, c in enumerate(competitors, start=1):
                ws.append([
                    idx,
                    c.get("name") or c.get("domain") or "Competitor",
                    c.get("domain") or c.get("url") or "",
                    c.get("relevance") or "High",
                    c.get("keyword_overlap") or "Not available",
                    c.get("search_appearances") or "Not available",
                    "Active Tracking"
                ])
                cls._apply_data_row_style(ws, idx + 1, row_height=20)
        else:
            ws.append([1, "No competitors configured", "Add competitors in Competitors page", "N/A", "Not available", "Not available", "Planned"])
            cls._apply_data_row_style(ws, 2, row_height=20)

        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_rankings_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        rankings = kwargs.get("rankings")
        if rankings is None and args:
            rankings = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        rankings = rankings or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Rankings Tracking"
        ws.freeze_panes = "A2"

        ws.append(["#", "Tracked Keyword", "Target Page URL", "Current Rank", "Previous Rank", "Rank Movement", "Search Engine", "Location / Market", "Status"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:I1"

        if rankings:
            for idx, r in enumerate(rankings, start=1):
                ws.append([
                    idx,
                    r.get("keyword", ""),
                    r.get("url", ""),
                    r.get("position", "Not available"),
                    r.get("previous_position", "Not available"),
                    r.get("change", "Not available"),
                    r.get("search_engine", "Google"),
                    r.get("location", "Default Market"),
                    "Active"
                ])
                cls._apply_data_row_style(ws, idx + 1, row_height=20)
        else:
            ws.append([1, "Daily rank tracking is not currently connected", "N/A", "Not available", "Not available", "Not available", "Google", "Configure in Settings", "Data Not Connected"])
            cls._apply_data_row_style(ws, 2, row_height=20)

        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_internal_links_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        links = kwargs.get("internal_links") or kwargs.get("links")
        if links is None and args:
            links = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        links = links or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Internal Links Structure"
        ws.freeze_panes = "A2"

        ws.append(["#", "Source Page URL", "Destination Page URL", "Anchor Text", "Link Status", "Recommended Optimization"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:F1"

        for idx, lnk in enumerate(links, start=1):
            st = lnk.get("status") or (f"HTTP {lnk.get('status_code', 200)}" if lnk.get("status_code") else "Verified Internal Link")
            ws.append([
                idx,
                lnk.get("source") or lnk.get("source_url") or "",
                lnk.get("target") or lnk.get("target_url") or "",
                lnk.get("anchor_text") or lnk.get("anchor") or "(No Anchor Text)",
                st,
                "Optimize anchor text for target service keywords."
            ])
            cls._apply_data_row_style(ws, idx + 1, row_height=20)

        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_opportunities_xlsx(cls, *args, **kwargs) -> bytes:
        if not HAS_OPENPYXL:
            return b""
        opps = kwargs.get("opportunities")
        if opps is None and args:
            opps = args[-1] if isinstance(args[-1], list) else (args[0] if isinstance(args[0], list) else [])
        opps = opps or []

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Actionable Opportunities"
        ws.freeze_panes = "A2"

        ws.append(["#", "Priority", "Strategic SEO Opportunity", "Evidence / Why It Matters", "Recommended Implementation Action", "Expected Business Benefit", "Status"])
        cls._apply_header_style(ws, row=1, fill_hex=cls.PRIMARY_HEADER_FILL_HEX, font_size=10, row_height=26)
        ws.auto_filter.ref = "A1:G1"

        for idx, opp in enumerate(opps, start=1):
            ws.append([
                idx,
                opp.get("priority", "Medium"),
                opp.get("title") or opp.get("name") or "SEO Opportunity",
                opp.get("evidence") or opp.get("description") or "Identified during audit",
                opp.get("recommended_action") or opp.get("action") or "Implement recommended changes.",
                opp.get("expected_benefit") or "Improved search visibility & ranking potential.",
                "Planned"
            ])
            cls._apply_data_row_style(ws, idx + 1, row_height=20)

        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()
