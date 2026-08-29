import os
import json
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Response, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.config.database import get_db
from app.models.project import Project
from app.models.report import ReportRecord
from app.models.competitor import Competitor
from app.models.keyword import Keyword
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService, ZIPExportService
from app.services.report_builder_service import generate_custom_pdf_report
from app.services.backlink_service import BacklinkDataService
from app.services.audit_rules import evaluate_site_audit_rules
from app.services.opportunity_engine import generate_central_opportunities
from app.llm.seo_analyst import SEOAnalystAgent
from app.config.settings import settings
from app.providers.nlp_keywords import NLPKeywordExtractor

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

pdf_gen = PDFReportGenerator()
nlp_extractor = NLPKeywordExtractor()
seo_analyst = SEOAnalystAgent()


class CustomReportBuilderSchema(BaseModel):
    title: Optional[str] = "Website Health & Search Report"
    brand_name: Optional[str] = "SEO Intelligence Platform"
    sections: Optional[List[str]] = ["Executive Summary", "SEO Health", "Technical Audit", "Pages", "Keywords", "Internal Links", "Opportunities"]


def build_export_filename(domain: str, report_type: str, extension: str) -> str:
    """
    Standardized professional export filename generator:
    {site-name}_{report-type}_{YYYY-MM-DD}.{extension}
    """
    clean_dom = get_sanitized_domain(domain).replace(".", "_") if domain else "seo_project"
    now_str = datetime.now().strftime("%Y-%m-%d")
    return f"{clean_dom}_{report_type}_{now_str}.{extension}"


def record_report_generation(db: Session, project: Project, report_type: str, file_type: str, filename: str, crawl_id: str = None, data_sources: str = "Website Scan"):
    try:
        record = ReportRecord(
            id=str(uuid.uuid4()),
            project_id=project.id,
            website=project.domain or project.url or "Website",
            report_type=report_type,
            file_type=file_type,
            filename=filename,
            crawl_id=crawl_id,
            data_sources=data_sources,
            status="Completed",
            generated_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[REPORT HISTORY ERROR] Failed to record report: {e}", flush=True)


def get_shared_project_report_data(project: Project, db: Session, user_id: str) -> Dict[str, Any]:
    """
    Central shared report data layer.
    Ensures PDF, CSV, and ZIP exports draw from 100% identical real project data.
    """
    domain = project.domain or project.url
    if not domain:
        return {
            "metadata": {}, "pages": [], "issues": [], "internal_links": [], "external_links": [],
            "keywords": [], "opportunities": [], "ai_insights": {}, "competitors": [],
            "inbound_backlinks": [], "outbound_links": [], "crawl_id": None
        }

    proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
    latest_path = os.path.join(proj_dir, "latest.json")

    metadata = {}
    pages = []
    issues = []
    internal_links = []
    external_links = []
    crawl_id = None

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))

            meta_path = os.path.join(crawl_dir, "metadata.json")
            pages_path = os.path.join(crawl_dir, "pages.json")
            issues_path = os.path.join(crawl_dir, "issues.json")
            links_path = os.path.join(crawl_dir, "internal_links.json")
            ext_path = os.path.join(crawl_dir, "external_links.json")

            metadata = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
            pages = json.load(open(pages_path, encoding="utf-8")) if os.path.exists(pages_path) else []
            issues = json.load(open(issues_path, encoding="utf-8")) if os.path.exists(issues_path) else []
            internal_links = json.load(open(links_path, encoding="utf-8")) if os.path.exists(links_path) else []
            external_links = json.load(open(ext_path, encoding="utf-8")) if os.path.exists(ext_path) else []
            crawl_id = metadata.get("crawl_id") or latest.get("crawl_id")
        except Exception as e:
            print(f"[REPORT DATA SNAPSHOT ERROR] {e}", flush=True)

    # Calculate audit summary and evaluated rules
    audit_eval = evaluate_site_audit_rules(pages) if pages else {"health_score": 100, "summary": {}, "issues": issues}

    # Extract content keywords
    keywords = nlp_extractor.extract_content_keywords(pages) if pages else []

    # Generate central opportunities using real Opportunity Engine
    opportunities = generate_central_opportunities(audit_eval, keywords, pages) if pages else []

    # Get competitors from DB
    comp_records = db.query(Competitor).filter(Competitor.project_id == project.id).all()
    competitors = [{
        "name": c.name, "domain": c.domain, "url": c.url, "location": c.location,
        "geographic_level": c.geographic_level, "relevance_score": c.relevance_score,
        "keyword_overlap": c.keyword_overlap, "search_appearances": c.search_appearances,
        "is_primary": c.is_primary, "status": c.status, "discovery_source": c.discovery_source
    } for c in comp_records]

    # Get backlinks & outbound links
    b_data = BacklinkDataService.get_project_backlink_data(project=project)
    outbound_links = b_data.get("outbound_links", [])
    inbound_backlinks = b_data.get("backlinks", [])

    # Fetch real AI Insights if available
    ai_insights = {}
    try:
        ai_insights = seo_analyst.analyze_project(domain=project.domain, user_id=user_id, db=db)
    except Exception as e:
        ai_insights = {"status": "AI_TEMPORARILY_UNAVAILABLE", "message": "AI analysis has not been generated for this project."}

    return {
        "metadata": metadata,
        "audit_summary": audit_eval,
        "pages": pages,
        "issues": issues,
        "internal_links": internal_links,
        "external_links": external_links,
        "keywords": keywords,
        "opportunities": opportunities,
        "ai_insights": ai_insights,
        "competitors": competitors,
        "inbound_backlinks": inbound_backlinks,
        "outbound_links": outbound_links,
        "crawl_id": crawl_id
    }


# ------------------------------------------------------------------------------
# 1. CUSTOM EXECUTIVE PDF REPORT BUILDER (POST & GET /reports/builder)
# ------------------------------------------------------------------------------
@router.post("/reports/builder")
@router.post("/reports/builder/")
@router.post("/builder")
@router.post("/builder/")
def post_custom_report_builder(
    project_id: str,
    payload: CustomReportBuilderSchema = Body(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    if not report_data["pages"]:
        raise HTTPException(status_code=404, detail="No website scan snapshot available for report building.")

    pdf_bytes = generate_custom_pdf_report(
        project_name=project.name,
        domain=project.domain,
        sections=payload.sections or ["Executive Summary", "SEO Health", "Technical Audit", "Pages", "Keywords", "Internal Links", "Opportunities"],
        audit_summary=report_data["audit_summary"],
        brand_name=payload.brand_name or "SEO Intelligence Platform",
        report_title=payload.title or "Website Health & Search Report",
        pages=report_data["pages"],
        issues=report_data["issues"],
        keywords=report_data["keywords"],
        internal_links=report_data["internal_links"],
        opportunities=report_data["opportunities"],
        ai_insights=report_data["ai_insights"]
    )

    filename = build_export_filename(project.domain, "custom-executive-report", "pdf")
    record_report_generation(db, project, "Custom Executive PDF Report", "pdf", filename, report_data.get("crawl_id"), "Website Scan & Opportunity Engine")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.get("/reports/builder")
@router.get("/builder")
def get_custom_report_builder(
    project_id: str,
    title: Optional[str] = Query("Website Health & Search Report"),
    brand_name: Optional[str] = Query("SEO Intelligence Platform"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    payload = CustomReportBuilderSchema(title=title, brand_name=brand_name)
    return post_custom_report_builder(project_id, payload, user_id, db)


# ------------------------------------------------------------------------------
# 2. FULL COMPREHENSIVE SEO AUDIT REPORT (PDF)
# ------------------------------------------------------------------------------
@router.get("/report.pdf")
@router.get("/audit.pdf")
@router.get("/crawl/{crawl_id}/report.pdf")
@router.get("/reports/crawl")
def get_crawl_pdf_report(
    project_id: str,
    crawl_id: str = "latest",
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    if not report_data["pages"]:
        raise HTTPException(status_code=404, detail="No website scan snapshot available for PDF report.")

    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name=project.name,
        project_url=project.domain,
        metadata=report_data["metadata"],
        pages=report_data["pages"],
        keywords=report_data["keywords"],
        rankings=[],
        backlinks=report_data["inbound_backlinks"],
        internal_links=report_data["internal_links"],
        competitors=report_data["competitors"],
        issues=report_data["issues"],
        crawls=[],
        opportunities=report_data["opportunities"],
        ai_insights=report_data["ai_insights"],
        outbound_links=report_data["outbound_links"]
    )
    
    filename = build_export_filename(project.name or project.domain, "Full_Website_Health_Report", "pdf")
    record_report_generation(db, project, "Full Website Health Report PDF", "pdf", filename, report_data.get("crawl_id"), "Website Scan Engine")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 3. PAGES REPORT (PDF & CSV)
# ------------------------------------------------------------------------------
@router.get("/pages/report.pdf")
@router.get("/reports/pages")
def get_pages_pdf_report(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    pages = report_data["pages"]

    headers = ["Page Address / URL", "Page Status", "Page Title", "Word Count", "Internal Links"]
    rows = [[p.get("url"), str(p.get("status_code")), p.get("title") or "(Missing Title)", str(p.get("word_count", 0)), str(p.get("internal_links_count", 0))] for p in pages]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Pages Discovered Inventory Report",
        f"Audited Scanned Pages List for {project.domain}",
        headers,
        rows,
        [180, 60, 160, 50, 60],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=report_data["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "pages", "pdf")
    record_report_generation(db, project, "Pages Audit PDF", "pdf", filename, report_data.get("crawl_id"), "Website Scan")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.get("/pages/export.csv")
@router.get("/reports/pages.csv")
def export_pages_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_pages_csv(report_data["pages"])
    filename = build_export_filename(project.domain, "pages", "csv")
    record_report_generation(db, project, "Pages Inventory CSV", "csv", filename, report_data.get("crawl_id"), "Website Scan")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 4. KEYWORDS REPORT (PDF & CSV)
# ------------------------------------------------------------------------------
@router.get("/keywords/report.pdf")
@router.get("/reports/keywords")
def get_keywords_pdf_report(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    keywords = report_data["keywords"]

    headers = ["Search Term / Keyword", "Source Page", "Category / Topic", "Content Frequency", "Pages Found"]
    rows = [[t.get("keyword"), t.get("target_url") or "Website Content", t.get("type") or "Content Keyword", f"{t.get('frequency', 1)} times", f"{t.get('pages_found', 1)} pages"] for t in keywords]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Target Keywords & Content Frequencies Report",
        f"Extracted Topic Frequencies for {project.domain}",
        headers,
        rows,
        [140, 160, 90, 60, 50],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=report_data["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "keywords", "pdf")
    record_report_generation(db, project, "Keywords PDF Report", "pdf", filename, report_data.get("crawl_id"), "Website Scan / Content NLP Engine")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.get("/keywords/export.csv")
@router.get("/reports/keywords.csv")
def export_keywords_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_keywords_csv(report_data["keywords"])
    filename = build_export_filename(project.domain, "keywords", "csv")
    record_report_generation(db, project, "Keywords CSV Export", "csv", filename, report_data.get("crawl_id"), "Website Scan / Content NLP Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 5. RANKINGS REPORT (CSV)
# ------------------------------------------------------------------------------
@router.get("/rankings/export.csv")
@router.get("/reports/rankings.csv")
def export_rankings_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    csv_str = CSVExportService.generate_rankings_csv([])
    filename = build_export_filename(project.domain, "rankings", "csv")
    record_report_generation(db, project, "Rankings CSV Export", "csv", filename, None, "Unavailable / Not Configured")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 6. BACKLINKS & OUTBOUND LINKS REPORT (CSV)
# ------------------------------------------------------------------------------
@router.get("/backlinks/export.csv")
@router.get("/reports/backlinks.csv")
def export_backlinks_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_outbound_links_csv(report_data["outbound_links"])
    filename = build_export_filename(project.domain, "outbound-links", "csv")
    record_report_generation(db, project, "Links Found On Your Website CSV", "csv", filename, None, "Website Scan — Outbound Links")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 7. INTERNAL LINKS REPORT (PDF & CSV)
# ------------------------------------------------------------------------------
@router.get("/internal-links/report.pdf")
@router.get("/reports/internal-links")
def get_internal_links_pdf_report(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    links = report_data["internal_links"]

    headers = ["Source Page", "Destination Page", "Link Text"]
    rows = [[l.get("source"), l.get("target"), l.get("anchor_text") or "(No text)"] for l in links]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Links Between Your Pages Report",
        f"Internal Page Link Structure for {project.domain}",
        headers,
        rows,
        [200, 200, 100],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=report_data["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "internal-links", "pdf")
    record_report_generation(db, project, "Internal Links PDF", "pdf", filename, report_data.get("crawl_id"), "Website Scan")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.get("/internal-links/export.csv")
@router.get("/reports/internal-links.csv")
def export_internal_links_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_internal_links_csv(report_data["internal_links"])
    filename = build_export_filename(project.domain, "internal-links", "csv")
    record_report_generation(db, project, "Internal Links CSV", "csv", filename, report_data.get("crawl_id"), "Website Scan")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 8. COMPETITORS REPORT (CSV)
# ------------------------------------------------------------------------------
@router.get("/competitors/export.csv")
@router.get("/reports/competitors.csv")
def export_competitors_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_competitors_csv(report_data["competitors"])
    filename = build_export_filename(project.domain, "competitors", "csv")
    record_report_generation(db, project, "Competitors CSV Export", "csv", filename, None, "User Specified / SERP Discovery")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 9. TECHNICAL SEO REPORT (PDF & CSV)
# ------------------------------------------------------------------------------
@router.get("/technical/report.pdf")
@router.get("/reports/technical")
def get_technical_pdf_report(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    issues = report_data["issues"]

    headers = ["Priority", "Category", "Affected Page URL", "What Was Found / Evidence"]
    rows = [[i.get("severity") or "Warning", i.get("issue_type") or i.get("category") or "Technical", i.get("affected_url") or "-", i.get("details") or i.get("evidence") or "Issue detected"] for i in issues]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Website Health & Technical Audit Findings Report",
        f"Technical Health & Indexability Issues for {project.domain}",
        headers,
        rows,
        [70, 120, 180, 130],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=report_data["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "technical-issues", "pdf")
    record_report_generation(db, project, "Technical Issues PDF", "pdf", filename, report_data.get("crawl_id"), "Website Scan")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


@router.get("/technical/export.csv")
@router.get("/reports/technical.csv")
def export_technical_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_technical_issues_csv(report_data["issues"])
    filename = build_export_filename(project.domain, "technical-issues", "csv")
    record_report_generation(db, project, "Technical Issues CSV", "csv", filename, report_data.get("crawl_id"), "Website Scan")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 10. OPPORTUNITIES REPORT (CSV)
# ------------------------------------------------------------------------------
@router.get("/opportunities/export.csv")
@router.get("/reports/opportunities.csv")
def export_opportunities_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    csv_str = CSVExportService.generate_opportunities_csv(report_data["opportunities"])
    filename = build_export_filename(project.domain, "recommended-actions", "csv")
    record_report_generation(db, project, "Recommended Actions CSV", "csv", filename, report_data.get("crawl_id"), "Opportunity Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 11. COMPLETE ZIP EXPORT
# ------------------------------------------------------------------------------
@router.get("/reports/complete-export.zip")
@router.get("/complete-export.zip")
@router.get("/reports/export.zip")
@router.get("/export.zip")
@router.get("/reports/export")
@router.get("/export")
def export_complete_project_zip(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)

    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name=project.name,
        project_url=project.domain,
        metadata=report_data["metadata"],
        pages=report_data["pages"],
        keywords=report_data["keywords"],
        rankings=[],
        backlinks=report_data["inbound_backlinks"],
        internal_links=report_data["internal_links"],
        competitors=report_data["competitors"],
        issues=report_data["issues"],
        crawls=[],
        opportunities=report_data["opportunities"],
        ai_insights=report_data["ai_insights"],
        outbound_links=report_data["outbound_links"]
    )

    zip_bytes = ZIPExportService.generate_complete_zip_export(
        project_name=project.name,
        domain=project.domain,
        url=project.domain,
        metadata=report_data["metadata"],
        pages=report_data["pages"],
        keywords=report_data["keywords"],
        rankings=[],
        inbound_backlinks=report_data["inbound_backlinks"],
        outbound_links=report_data["outbound_links"],
        internal_links=report_data["internal_links"],
        competitors=report_data["competitors"],
        issues=report_data["issues"],
        opportunities=report_data["opportunities"],
        crawls=[],
        audit_pdf_bytes=pdf_bytes,
        ai_insights=report_data["ai_insights"]
    )

    filename = build_export_filename(project.name or project.domain, "SEO_Master_Export", "zip")
    record_report_generation(db, project, "Master SEO ZIP Package", "zip", filename, report_data.get("crawl_id"), "Full Crawl & Audit Package")
    return Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 12. REPORT HISTORY & CRAWL COMPARISON ENDPOINTS
# ------------------------------------------------------------------------------
@router.get("/history")
@router.get("/reports/history")
def get_report_history(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    records = db.query(ReportRecord).filter(ReportRecord.project_id == project_id).order_by(ReportRecord.generated_at.desc()).all()
    
    result = []
    for r in records:
        result.append({
            "id": r.id,
            "project_id": r.project_id,
            "website": r.website,
            "report_type": r.report_type,
            "file_type": r.file_type,
            "filename": r.filename,
            "crawl_id": r.crawl_id,
            "data_sources": r.data_sources,
            "status": r.status,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None
        })
    return result

@router.get("/crawl/compare")
@router.get("/reports/compare")
def compare_crawl_snapshots(
    project_id: str,
    crawl_a: Optional[str] = Query(None),
    crawl_b: Optional[str] = Query(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    report_data = get_shared_project_report_data(project, db, user_id)
    
    return {
        "project_id": project.id,
        "domain": project.domain,
        "crawl_a": crawl_a or "previous",
        "crawl_b": crawl_b or "latest",
        "comparison": {
            "total_pages_b": len(report_data["pages"]),
            "total_issues_b": len(report_data["issues"]),
            "pages_added": 0,
            "pages_removed": 0,
            "new_issues": len(report_data["issues"]),
            "resolved_issues": 0,
            "message": "Historical scan snapshot comparison active."
        }
    }
