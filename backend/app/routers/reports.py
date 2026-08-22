import os
import json
import re
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.services.reports.pdf_service import PDFReportGenerator
from app.config.settings import settings
from app.providers.nlp_keywords import NLPKeywordExtractor

router = APIRouter()


pdf_gen = PDFReportGenerator()
nlp_extractor = NLPKeywordExtractor()

def get_export_timestamp() -> str:
    return datetime.now().strftime("%d-%m-%y-%I-%M-%p")

def sanitize_filename_part(name: str) -> str:
    if not name:
        return "SEO-Project"
    cleaned = re.sub(r'[^\w\s-]', '', name).strip()
    result = re.sub(r'[-\s]+', '-', cleaned)
    return result or "SEO-Project"

@router.get("/report.pdf")
@router.get("/crawl/{crawl_id}/report.pdf")
@router.get("/reports/crawl")
def get_crawl_pdf_report(project_id: str, crawl_id: str = "latest", db: Session = Depends(get_db)):
    if project_id == "all":
        from app.routers.projects import get_all_projects_pdf
        return get_all_projects_pdf(db)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    if not os.path.exists(latest_path):
        raise HTTPException(status_code=404, detail="No crawl snapshot available")

    with open(latest_path, "r") as f:
        latest = json.load(f)
    crawl_dir = normalize_stored_path(latest.get("path"))

    meta_path = os.path.join(crawl_dir, "metadata.json")
    pages_path = os.path.join(crawl_dir, "pages.json")
    issues_path = os.path.join(crawl_dir, "issues.json")

    metadata = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    pages = json.load(open(pages_path)) if os.path.exists(pages_path) else []
    issues = json.load(open(issues_path)) if os.path.exists(issues_path) else []

    pdf_bytes = pdf_gen.generate_crawl_report(metadata, pages, issues)
    proj_name = sanitize_filename_part(project.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Crawl-Report-{ts}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/export")
def export_project_data(project_id: str, db: Session = Depends(get_db)):
    if project_id == "all":
        from app.routers.projects import get_all_projects_zip_export
        return get_all_projects_zip_export(db)

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    
    export_payload = {
        "project": {
            "id": project.id,
            "name": project.name,
            "domain": project.domain,
            "created_at": str(project.created_at) if hasattr(project, 'created_at') else None
        },
        "snapshot": None
    }

    if os.path.exists(latest_path):
        try:
            latest = json.load(open(latest_path))
            crawl_dir = normalize_stored_path(latest.get("path"))
            meta_path = os.path.join(crawl_dir, "metadata.json")
            pages_path = os.path.join(crawl_dir, "pages.json")
            issues_path = os.path.join(crawl_dir, "issues.json")
            links_path = os.path.join(crawl_dir, "internal_links.json")

            export_payload["snapshot"] = {
                "metadata": json.load(open(meta_path)) if os.path.exists(meta_path) else {},
                "pages": json.load(open(pages_path)) if os.path.exists(pages_path) else [],
                "issues": json.load(open(issues_path)) if os.path.exists(issues_path) else [],
                "internal_links": json.load(open(links_path)) if os.path.exists(links_path) else []
            }
        except Exception as e:
            print(f"[EXPORT ERROR] {e}", flush=True)

    proj_name = sanitize_filename_part(project.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-Data-Export-{ts}.json"
    json_bytes = json.dumps(export_payload, indent=4).encode('utf-8')
    return Response(content=json_bytes, media_type="application/json", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/pages/report.pdf")
@router.get("/reports/pages")
def get_pages_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    pages = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        crawl_dir = normalize_stored_path(latest.get("path"))
        pages_file = os.path.join(crawl_dir, "pages.json")
        if os.path.exists(pages_file):
            pages = json.load(open(pages_file))

    headers = ["URL", "Status", "Title", "Word Count", "Internal Links"]
    rows = [[p.get("url"), str(p.get("status_code")), p.get("title") or "No Title", str(p.get("word_count", 0)), str(p.get("internal_links_count", 0))] for p in pages]
    
    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        f"Pages Audit Report: {project.name}",
        f"Target Domain: {project.domain} | Total Crawled Pages: {len(pages)}",
        headers,
        rows,
        [180, 50, 160, 50, 60]
    )
    proj_name = sanitize_filename_part(project.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Pages-{ts}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/technical/report.pdf")
@router.get("/reports/technical")
def get_technical_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    issues = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        crawl_dir = normalize_stored_path(latest.get("path"))
        issues_file = os.path.join(crawl_dir, "issues.json")
        if os.path.exists(issues_file):
            issues = json.load(open(issues_file))

    headers = ["Severity", "Issue Type", "Affected URL", "Details"]
    rows = [[i.get("severity"), i.get("issue_type"), i.get("affected_url"), i.get("details")] for i in issues]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        f"Technical SEO Audit Report: {project.name}",
        f"Target Domain: {project.domain} | Total Technical Issues: {len(issues)}",
        headers,
        rows,
        [70, 120, 180, 130]
    )
    proj_name = sanitize_filename_part(project.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Technical-Issues-{ts}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/keywords/report.pdf")
@router.get("/reports/keywords")
def get_keywords_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    pages = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        crawl_dir = normalize_stored_path(latest.get("path"))
        pages_file = os.path.join(crawl_dir, "pages.json")
        if os.path.exists(pages_file):
            pages = json.load(open(pages_file))

    extracted = nlp_extractor.extract_content_keywords(pages)
    headers = ["Topic / Keyword", "Source", "Type", "Frequency", "Pages Found"]
    rows = [[t.get("keyword"), t.get("source"), t.get("type"), str(t.get("frequency")), f"{t.get('pages_found')} pages"] for t in extracted]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        f"Keyword & Topic Intelligence Report: {project.name}",
        f"Target Domain: {project.domain} | Extracted Topics: {len(extracted)}",
        headers,
        rows,
        [140, 110, 80, 70, 100]
    )
    proj_name = sanitize_filename_part(project.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Keywords-{ts}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/internal-links/report.pdf")
@router.get("/reports/internal-links")
def get_internal_links_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    links = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        crawl_dir = normalize_stored_path(latest.get("path"))
        links_file = os.path.join(crawl_dir, "internal_links.json")
        if os.path.exists(links_file):
            links = json.load(open(links_file))

    headers = ["Source Page", "Target Page", "Anchor Text"]
    rows = [[l.get("source"), l.get("target"), l.get("anchor_text") or "(No text)"] for l in links]

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        f"Internal Link Graph Report: {project.name}",
        f"Target Domain: {project.domain} | Total Mapped Internal Links: {len(links)}",
        headers,
        rows,
        [200, 200, 100]
    )
    proj_name = sanitize_filename_part(project.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Internal-Links-{ts}.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})


@router.post("/builder")
@router.post("/reports/builder")
def generate_custom_report_builder(
    project_id: str,
    payload: dict = {},
    db: Session = Depends(get_db)
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    sections = payload.get("sections", ["Executive Summary", "SEO Health", "Technical Audit"])
    brand_name = payload.get("brand_name", "SEO Intelligence Platform")
    report_title = payload.get("report_title", "Custom SEO Executive Audit Report")
    fmt = payload.get("format", "pdf").lower()

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join(settings.CRAWL_DATA_DIR, safe_domain, "latest.json")

    pages = []
    issues = []
    if os.path.exists(latest_path):
        try:
            latest = json.load(open(latest_path))
            crawl_dir = normalize_stored_path(latest.get("path"))
            pages_file = os.path.join(crawl_dir, "pages.json")
            if os.path.exists(pages_file):
                pages = json.load(open(pages_file))
            issues_file = os.path.join(crawl_dir, "issues.json")
            if os.path.exists(issues_file):
                issues = json.load(open(issues_file))
        except Exception as e:
            from app.config.logger import get_logger
            get_logger("reports").warning(f"Failed to load crawl snapshot for report builder: {e}")


    from app.services.audit_rules import evaluate_site_audit_rules
    from app.services.report_builder_service import generate_custom_pdf_report, generate_csv_report_package

    audit_eval = evaluate_site_audit_rules(pages)

    if fmt == "zip":
        zip_bytes = generate_csv_report_package(project.name, project.domain, pages, [], issues)
        filename = f"{sanitize_filename_part(project.name)}-CSV-Package.zip"
        return Response(content=zip_bytes, media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})

    pdf_bytes = generate_custom_pdf_report(
        project.name,
        project.domain,
        sections,
        audit_eval,
        brand_name,
        report_title
    )
    filename = f"{sanitize_filename_part(project.name)}-Custom-Report.pdf"
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})

