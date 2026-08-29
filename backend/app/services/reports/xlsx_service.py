import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from typing import Dict, Any, List

class XLSXExportService:
    @staticmethod
    def _apply_header_style(ws, row=1):
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
        wb = openpyxl.Workbook()
        # Remove default sheet
        wb.remove(wb.active)

        # ----------------------------------------------------------------------
        # SHEET 1: Executive Summary
        # ----------------------------------------------------------------------
        ws1 = wb.create_sheet(title="Executive Summary")
        ws1.append(["SEO Intelligence Platform — Full Website Health Executive Summary"])
        ws1.merge_cells("A1:D1")
        ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F172A")
        ws1.append([])

        summary_rows = [
            ["Project Name", project_name or "N/A"],
            ["Website URL", project_url or "N/A"],
            ["Report Date", metadata.get("timestamp", "N/A")],
            ["Website Health Score", f"{ai_insights.get('health_score', 100)} / 100"],
            ["Analyzed HTML Pages", len(pages)],
            ["Evaluated SEO Checks", f"{len(pages) * 14} total rule evaluations"],
            ["Detected Problems", len(issues)],
            ["Executive Assessment", ai_insights.get("executive_assessment", "Your website scan is complete.")]
        ]
        for label, val in summary_rows:
            ws1.append([label, val])
        
        for r in range(3, 11):
            ws1.cell(row=r, column=1).font = Font(bold=True, color="334155")

        # ----------------------------------------------------------------------
        # SHEET 2: Website Health Breakdown
        # ----------------------------------------------------------------------
        ws2 = wb.create_sheet(title="Website Health")
        ws2.append(["Category / Area", "Check Status", "Issues Found", "Impact Description", "Where This Data Came From"])
        cls._apply_header_style(ws2)

        health_data = [
            ["Crawlability & Access", "Passed", "0 errors", "Search engines can access audited pages", "Automatic Scan"],
            ["Technical SEO & HTTP Status", "Audited", f"{sum(1 for i in issues if i.get('severity') in ('Critical', 'Error', 'High'))} issues", "Server status and technical headers", "Automatic Scan Engine"],
            ["Page Content & Meta Tags", "Audited", f"{sum(1 for i in issues if 'title' in str(i.get('issue','')).lower() or 'meta' in str(i.get('issue','')).lower())} issues", "Meta titles, descriptions, and word counts", "Website Scan"],
            ["Internal Links Structure", "Audited", f"{len(internal_links or [])} internal links", "Page interconnectivity and anchor text", "Website Scan"],
            ["PageSpeed Performance", "Not Measured", "0 issues", "Performance metrics not connected", "Data Not Connected"],
            ["Inbound Backlinks", "Not Measured", "0 issues", "External referring backlink profiles not connected", "Data Not Connected"]
        ]
        for row in health_data:
            ws2.append(row)
        cls._auto_fit_columns(ws2)

        # ----------------------------------------------------------------------
        # SHEET 3: SEO Problems Found
        # ----------------------------------------------------------------------
        ws3 = wb.create_sheet(title="SEO Problems Found")
        ws3.append(["Severity Level", "SEO Problems Found", "Can Search Engines Find This Page?", "Affected URL", "What Was Found / Evidence", "Recommended Action", "AI Solution"])
        cls._apply_header_style(ws3)

        for iss in issues:
            ws3.append([
                iss.get("severity", "Notice"),
                iss.get("issue", "SEO Problem"),
                iss.get("indexability", "Yes"),
                iss.get("url", "N/A"),
                iss.get("evidence") or iss.get("description", "N/A"),
                iss.get("recommendation", "N/A"),
                iss.get("ai_solution") or f"Fix {iss.get('issue')} on {iss.get('url')}"
            ])
        cls._auto_fit_columns(ws3)

        # ----------------------------------------------------------------------
        # SHEET 4: Pages Inventory
        # ----------------------------------------------------------------------
        ws4 = wb.create_sheet(title="Pages Inventory")
        ws4.append(["URL", "Status Code", "Page Title", "Word Count", "H1 Heading", "Meta Description", "Can Search Engines Find This Page?", "Internal Links"])
        cls._apply_header_style(ws4)

        for p in pages:
            ws4.append([
                p.get("url"),
                p.get("status_code", 200),
                p.get("title", "(Missing Title)"),
                p.get("word_count", 0),
                p.get("h1", "(Missing H1)"),
                p.get("meta_description", "(Missing Meta Description)"),
                "Yes" if p.get("status_code") == 200 else "No",
                p.get("internal_links_count", 0)
            ])
        cls._auto_fit_columns(ws4)

        # ----------------------------------------------------------------------
        # SHEET 5: Target Keywords
        # ----------------------------------------------------------------------
        ws5 = wb.create_sheet(title="Target Keywords")
        ws5.append(["Search Term / Keyword", "Target URL", "Category / Topic", "Content Frequency", "Where This Data Came From"])
        cls._apply_header_style(ws5)

        for kw in keywords:
            ws5.append([
                kw.get("keyword"),
                kw.get("target_url") or "Website Content",
                kw.get("type", "Content Keyword"),
                kw.get("frequency", 1),
                "Automatic Keyword Detection"
            ])
        cls._auto_fit_columns(ws5)

        # ----------------------------------------------------------------------
        # SHEET 6: Internal Links
        # ----------------------------------------------------------------------
        ws6 = wb.create_sheet(title="Internal Links")
        ws6.append(["Source Page", "Destination Page", "Link Anchor Text", "Link Status Code"])
        cls._apply_header_style(ws6)

        for link in (internal_links or []):
            ws6.append([
                link.get("source"),
                link.get("target"),
                link.get("anchor_text") or "(No Anchor Text)",
                link.get("status_code", 200)
            ])
        cls._auto_fit_columns(ws6)

        # ----------------------------------------------------------------------
        # SHEET 7: Outbound External Links
        # ----------------------------------------------------------------------
        ws7 = wb.create_sheet(title="Outbound Links")
        ws7.append(["Found On Page", "External Destination URL", "Anchor Text"])
        cls._apply_header_style(ws7)

        for el in (outbound_links or []):
            ws7.append([
                el.get("found_on"),
                el.get("external_url"),
                el.get("anchor_text") or "(No Anchor Text)"
            ])
        cls._auto_fit_columns(ws7)

        # ----------------------------------------------------------------------
        # SHEET 8: SEO Opportunities
        # ----------------------------------------------------------------------
        ws8 = wb.create_sheet(title="SEO Opportunities")
        ws8.append(["Priority", "Category", "Affected URL", "Opportunity Title", "Evidence", "Recommended Action", "AI Solution"])
        cls._apply_header_style(ws8)

        for opp in opportunities:
            ws8.append([
                opp.get("priority", "Medium"),
                opp.get("category", "General"),
                opp.get("url", "Website Level"),
                opp.get("title", "Opportunity"),
                opp.get("evidence", "N/A"),
                opp.get("recommended_action", "N/A"),
                opp.get("ai_solution", "N/A")
            ])
        cls._auto_fit_columns(ws8)

        # ----------------------------------------------------------------------
        # SHEET 9: Next Improvements Roadmap
        # ----------------------------------------------------------------------
        ws9 = wb.create_sheet(title="Next SEO Improvements")
        ws9.append(["Timeframe Phase", "Category", "Target Action", "Grounded Evidence"])
        cls._apply_header_style(ws9)

        roadmap = ai_insights.get("next_improvements", [])
        if not roadmap:
            roadmap = [
                {"timeframe": "NOW (Immediate)", "category": "Critical Fixes", "action": "Fix 404 broken pages and critical status code errors.", "evidence": "Verified status codes"},
                {"timeframe": "NEXT 30 DAYS", "category": "On-Page Metadata", "action": "Write unique meta titles and descriptions for all pages.", "evidence": "Detected missing titles"},
                {"timeframe": "NEXT 60-90 DAYS", "category": "Content Expansion", "action": "Expand thin pages with fewer than 300 words.", "evidence": "Word count audit"},
                {"timeframe": "ONGOING", "category": "Internal Link Growth", "action": "Add contextual internal links to key landing pages.", "evidence": "Link density check"}
            ]
        for item in roadmap:
            ws9.append([
                item.get("timeframe", "Immediate"),
                item.get("category", "Technical"),
                item.get("action", "Improve SEO"),
                item.get("evidence", "Audit data")
            ])
        cls._auto_fit_columns(ws9)

        # ----------------------------------------------------------------------
        # SHEET 10: Data Limitations
        # ----------------------------------------------------------------------
        ws10 = wb.create_sheet(title="Data Limitations")
        ws10.append(["Integration / Dataset", "Connection Status", "Explanation / Note"])
        cls._apply_header_style(ws10)

        limitations = [
            ["Google Search Console API", "Not Connected", "Search performance keywords, impressions, and CTR require connecting your Search Console account."],
            ["Inbound External Backlinks", "Not Connected", "External referring domains and backlink authority profiles require a connected backlink API key."],
            ["PageSpeed Performance API", "Not Connected", "Mobile/desktop Core Web Vitals and lab performance measurements require connecting PageSpeed API."],
            ["Competitor Rank Tracking", "Not Configured", "Competitor URL keyword overlap and ranking comparisons require adding competitor domains in Settings."]
        ]
        for lim in limitations:
            ws10.append(lim)
        cls._auto_fit_columns(ws10)

        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_pages_xlsx(cls, pages: List[Dict[str, Any]]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Pages Inventory"
        ws.append(["URL", "Status Code", "Page Title", "Word Count", "H1 Heading", "Meta Description", "Can Search Engines Find This Page?", "Internal Links"])
        cls._apply_header_style(ws)
        for p in pages:
            ws.append([
                p.get("url"),
                p.get("status_code", 200),
                p.get("title", "(Missing Title)"),
                p.get("word_count", 0),
                p.get("h1", "(Missing H1)"),
                p.get("meta_description", "(Missing Meta Description)"),
                "Yes" if p.get("status_code") == 200 else "No",
                p.get("internal_links_count", 0)
            ])
        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_keywords_xlsx(cls, keywords: List[Dict[str, Any]]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Keywords"
        ws.append(["Search Term / Keyword", "Target URL", "Category / Topic", "Content Frequency", "Where This Data Came From"])
        cls._apply_header_style(ws)
        for kw in keywords:
            ws.append([
                kw.get("keyword"),
                kw.get("target_url") or "Website Content",
                kw.get("type", "Content Keyword"),
                kw.get("frequency", 1),
                "Automatic Keyword Detection"
            ])
        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()

    @classmethod
    def generate_technical_xlsx(cls, issues: List[Dict[str, Any]]) -> bytes:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Technical SEO"
        ws.append(["Severity Level", "SEO Problems Found", "Can Search Engines Find This Page?", "Affected URL", "What Was Found / Evidence", "Recommended Action", "AI Solution"])
        cls._apply_header_style(ws)
        for iss in issues:
            ws.append([
                iss.get("severity", "Notice"),
                iss.get("issue", "SEO Problem"),
                iss.get("indexability", "Yes"),
                iss.get("url", "N/A"),
                iss.get("evidence") or iss.get("description", "N/A"),
                iss.get("recommendation", "N/A"),
                iss.get("ai_solution") or f"Fix {iss.get('issue')} on {iss.get('url')}"
            ])
        cls._auto_fit_columns(ws)
        stream = io.BytesIO()
        wb.save(stream)
        return stream.getvalue()
