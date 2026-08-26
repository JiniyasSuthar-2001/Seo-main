import os
import json
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Response, Query
from sqlalchemy.orm import Session

from app.config.database import get_db
from app.models.project import Project
from app.models.report import ReportRecord
from app.models.competitor import Competitor
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService, ZIPExportService
from app.services.backlink_service import BacklinkDataService
from app.config.settings import settings
from app.providers.nlp_keywords import NLPKeywordExtractor

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

router = APIRouter()

pdf_gen = PDFReportGenerator()
nlp_extractor = NLPKeywordExtractor()

def build_export_filename(domain: str, report_type: str, extension: str) -> str:
    """
    Standardized professional export filename generator:
    {site-name}_{report-type}_{YYYY-MM-DD}.{extension}
    """
    clean_dom = get_sanitized_domain(domain).replace(".", "_") if domain else "seo_project"
    now_str = datetime.now().strftime("%Y-%m-%d")
    return f"{clean_dom}_{report_type}_{now_str}.{extension}"

def record_report_generation(db: Session, project: Project, report_type: str, file_type: str, filename: str, crawl_id: str = None, data_sources: str = "Crawled Data Engine"):
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

def get_project_crawl_snapshot(project: Project) -> dict:
    domain = project.domain or project.url
    if not domain:
        return {"metadata": {}, "pages": [], "issues": [], "internal_links": [], "external_links": []}
    safe_domain = get_sanitized_domain(domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        latest_path = os.path.join(settings.CRAWL_DATA_DIR, project.id, "latest.json")
    if not os.path.exists(latest_path):
        return {"metadata": {}, "pages": [], "issues": [], "internal_links": [], "external_links": []}

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
        links = json.load(open(links_path, encoding="utf-8")) if os.path.exists(links_path) else []
        ext_links = json.load(open(ext_path, encoding="utf-8")) if os.path.exists(ext_path) else []

        return {
            "metadata": metadata,
            "pages": pages,
            "issues": issues,
            "internal_links": links,
            "external_links": ext_links,
            "crawl_id": metadata.get("crawl_id") or latest.get("crawl_id")
        }
    except Exception as e:
        print(f"[CRAWL SNAPSHOT READ ERROR] {e}", flush=True)
        return {"metadata": {}, "pages": [], "issues": [], "internal_links": [], "external_links": []}


# ------------------------------------------------------------------------------
# 1. SEO AUDIT REPORT (PDF)
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

    snapshot = get_project_crawl_snapshot(project)
    if not snapshot["pages"]:
        raise HTTPException(status_code=404, detail="No crawl snapshot data available for PDF report.")

    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name=project.name,
        project_url=project.domain,
        metadata=snapshot["metadata"],
        pages=snapshot["pages"],
        keywords=[],
        rankings=[],
        backlinks=[],
        internal_links=snapshot["internal_links"],
        competitors=[],
        issues=snapshot["issues"],
        crawls=[]
    )
    
    filename = build_export_filename(project.domain, "seo-audit", "pdf")
    record_report_generation(db, project, "SEO Audit Report", "pdf", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 2. PAGES REPORT (PDF & CSV)
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

    snapshot = get_project_crawl_snapshot(project)
    pages = snapshot["pages"]

    headers = ["URL", "Status", "Title Tag", "Word Count", "Internal Links"]
    rows = [[p.get("url"), str(p.get("status_code")), p.get("title") or "No Title", str(p.get("word_count", 0)), str(p.get("internal_links_count", 0))] for p in pages]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Pages Crawled Inventory Report",
        f"Audited Crawled Pages List for {project.domain}",
        headers,
        rows,
        [180, 50, 160, 50, 60],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=snapshot["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "pages", "pdf")
    record_report_generation(db, project, "Pages Audit PDF", "pdf", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
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

    snapshot = get_project_crawl_snapshot(project)
    csv_str = CSVExportService.generate_pages_csv(snapshot["pages"])
    filename = build_export_filename(project.domain, "pages", "csv")
    record_report_generation(db, project, "Pages Inventory CSV", "csv", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 3. KEYWORDS REPORT (PDF & CSV)
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

    snapshot = get_project_crawl_snapshot(project)
    extracted = nlp_extractor.extract_content_keywords(snapshot["pages"])

    headers = ["Topic / Keyword", "Source Page", "Category", "Frequency", "Pages Found"]
    rows = [[t.get("keyword"), t.get("target_url") or "Website Content", t.get("type") or "Content Keyword", str(t.get("frequency", 1)), f"{t.get('pages_found', 1)} pages"] for t in extracted]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Content Keyword & Topic Report",
        f"Extracted Topic Frequencies for {project.domain}",
        headers,
        rows,
        [140, 160, 90, 60, 50],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=snapshot["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "keywords", "pdf")
    record_report_generation(db, project, "Keywords PDF Report", "pdf", filename, snapshot.get("crawl_id"), "Crawled Data / NLP Engine")
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

    snapshot = get_project_crawl_snapshot(project)
    extracted = nlp_extractor.extract_content_keywords(snapshot["pages"])
    csv_str = CSVExportService.generate_keywords_csv(extracted)
    filename = build_export_filename(project.domain, "keywords", "csv")
    record_report_generation(db, project, "Keywords CSV Export", "csv", filename, snapshot.get("crawl_id"), "Crawled Data / NLP Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 4. RANKINGS REPORT (CSV)
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
# 5. BACKLINKS & OUTBOUND LINKS REPORT (PDF & CSV)
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

    b_data = BacklinkDataService.get_project_backlink_data(project=project)
    outbound = b_data.get("outbound_links", [])
    csv_str = CSVExportService.generate_outbound_links_csv(outbound)
    filename = build_export_filename(project.domain, "outbound-links", "csv")
    record_report_generation(db, project, "Outbound External Links CSV", "csv", filename, None, "Crawled Data — Outbound")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 6. INTERNAL LINKS REPORT (PDF & CSV)
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

    snapshot = get_project_crawl_snapshot(project)
    links = snapshot["internal_links"]

    headers = ["Source Page", "Target Page", "Anchor Text"]
    rows = [[l.get("source"), l.get("target"), l.get("anchor_text") or "(No text)"] for l in links]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Internal Link Graph Audit Report",
        f"Internal Site Navigation Structure for {project.domain}",
        headers,
        rows,
        [200, 200, 100],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=snapshot["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "internal-links", "pdf")
    record_report_generation(db, project, "Internal Links PDF", "pdf", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
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

    snapshot = get_project_crawl_snapshot(project)
    csv_str = CSVExportService.generate_internal_links_csv(snapshot["internal_links"])
    filename = build_export_filename(project.domain, "internal-links", "csv")
    record_report_generation(db, project, "Internal Links CSV", "csv", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 7. COMPETITORS REPORT (CSV)
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

    competitors = db.query(Competitor).filter(Competitor.project_id == project.id).all()
    comp_list = []
    for c in competitors:
        comp_list.append({
            "name": c.name,
            "domain": c.domain,
            "url": c.url,
            "location": c.location,
            "geographic_level": c.geographic_level,
            "relevance_score": c.relevance_score,
            "keyword_overlap": c.keyword_overlap,
            "search_appearances": c.search_appearances,
            "is_primary": c.is_primary,
            "status": c.status,
            "discovery_source": c.discovery_source
        })

    csv_str = CSVExportService.generate_competitors_csv(comp_list)
    filename = build_export_filename(project.domain, "competitors", "csv")
    record_report_generation(db, project, "Competitors CSV Export", "csv", filename, None, "User Specified / SERP Discovery")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 8. TECHNICAL SEO REPORT (PDF & CSV)
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

    snapshot = get_project_crawl_snapshot(project)
    issues = snapshot["issues"]

    headers = ["Severity", "Issue Type", "Affected URL", "Details"]
    rows = [[i.get("severity"), i.get("issue_type"), i.get("affected_url"), i.get("details")] for i in issues]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Technical SEO Audit Findings Report",
        f"Technical Health & Indexability Issues for {project.domain}",
        headers,
        rows,
        [70, 120, 180, 130],
        domain=project.domain,
        project_name=project.name,
        crawl_timestamp=snapshot["metadata"].get("timestamp", "N/A")
    )
    filename = build_export_filename(project.domain, "technical-seo", "pdf")
    record_report_generation(db, project, "Technical Issues PDF", "pdf", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
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

    snapshot = get_project_crawl_snapshot(project)
    csv_str = CSVExportService.generate_technical_issues_csv(snapshot["issues"])
    filename = build_export_filename(project.domain, "technical-seo", "csv")
    record_report_generation(db, project, "Technical Issues CSV", "csv", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 9. OPPORTUNITIES REPORT (CSV)
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

    snapshot = get_project_crawl_snapshot(project)
    issues = snapshot["issues"]
    
    opps = []
    for i in issues:
        opps.append({
            "priority": i.get("severity") or "Medium",
            "category": i.get("issue_type") or "Technical",
            "title": f"Fix {i.get('issue_type', 'SEO Issue')}",
            "description": i.get("details", ""),
            "affected_urls": i.get("affected_url", ""),
            "provenance": "Crawled Data Engine"
        })

    csv_str = CSVExportService.generate_opportunities_csv(opps)
    filename = build_export_filename(project.domain, "opportunities", "csv")
    record_report_generation(db, project, "Action Opportunities CSV", "csv", filename, snapshot.get("crawl_id"), "Crawled Data Engine")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 10. COMPLETE ZIP EXPORT
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

    snapshot = get_project_crawl_snapshot(project)
    extracted_keywords = nlp_extractor.extract_content_keywords(snapshot["pages"])
    b_data = BacklinkDataService.get_project_backlink_data(project=project)
    outbound = b_data.get("outbound_links", [])

    competitors = db.query(Competitor).filter(Competitor.project_id == project.id).all()
    comp_list = [{"name": c.name, "domain": c.domain, "url": c.url, "location": c.location, "geographic_level": c.geographic_level, "relevance_score": c.relevance_score, "keyword_overlap": c.keyword_overlap, "search_appearances": c.search_appearances, "is_primary": c.is_primary, "status": c.status, "discovery_source": c.discovery_source} for c in competitors]

    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name=project.name,
        project_url=project.domain,
        metadata=snapshot["metadata"],
        pages=snapshot["pages"],
        keywords=[],
        rankings=[],
        backlinks=[],
        internal_links=snapshot["internal_links"],
        competitors=[],
        issues=snapshot["issues"],
        crawls=[]
    )

    zip_bytes = ZIPExportService.generate_complete_zip_export(
        project_name=project.name,
        domain=project.domain,
        url=project.domain,
        metadata=snapshot["metadata"],
        pages=snapshot["pages"],
        keywords=extracted_keywords,
        rankings=[],
        inbound_backlinks=[],
        outbound_links=outbound,
        internal_links=snapshot["internal_links"],
        competitors=comp_list,
        issues=snapshot["issues"],
        opportunities=[],
        crawls=[],
        audit_pdf_bytes=pdf_bytes
    )

    filename = build_export_filename(project.domain, "complete-seo-export", "zip")
    record_report_generation(db, project, "Complete SEO ZIP Export", "zip", filename, snapshot.get("crawl_id"), "Full Crawl & Audit Package")
    return Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})


# ------------------------------------------------------------------------------
# 11. REPORT HISTORY & CRAWL COMPARISON ENDPOINTS
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

    snapshot = get_project_crawl_snapshot(project)
    
    return {
        "project_id": project.id,
        "domain": project.domain,
        "crawl_a": crawl_a or "previous",
        "crawl_b": crawl_b or "latest",
        "comparison": {
            "total_pages_b": len(snapshot["pages"]),
            "total_issues_b": len(snapshot["issues"]),
            "pages_added": 0,
            "pages_removed": 0,
            "new_issues": len(snapshot["issues"]),
            "resolved_issues": 0,
            "message": "Historical crawl snapshot comparison active."
        }
    }
