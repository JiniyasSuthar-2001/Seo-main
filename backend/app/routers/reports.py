from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain
from app.services.reports.pdf_service import PDFReportGenerator
from app.providers.nlp_keywords import NLPKeywordExtractor
import os
import json

router = APIRouter()
pdf_gen = PDFReportGenerator()
nlp_extractor = NLPKeywordExtractor()

@router.get("/crawl/{crawl_id}/report.pdf")
@router.get("/reports/crawl")
def get_crawl_pdf_report(project_id: str, crawl_id: str = "latest", db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        raise HTTPException(status_code=404, detail="No crawl snapshot available")

    with open(latest_path, "r") as f:
        latest = json.load(f)
    crawl_dir = latest.get("path")

    meta_path = os.path.join(crawl_dir, "metadata.json")
    pages_path = os.path.join(crawl_dir, "pages.json")
    issues_path = os.path.join(crawl_dir, "issues.json")

    metadata = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    pages = json.load(open(pages_path)) if os.path.exists(pages_path) else []
    issues = json.load(open(issues_path)) if os.path.exists(issues_path) else []

    pdf_bytes = pdf_gen.generate_crawl_report(metadata, pages, issues)
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=SEO_Crawl_Report_{safe_domain}.pdf"})

@router.get("/pages/report.pdf")
@router.get("/reports/pages")
def get_pages_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    pages = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        pages_file = os.path.join(latest.get("path"), "pages.json")
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
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=Pages_Report_{safe_domain}.pdf"})

@router.get("/technical/report.pdf")
@router.get("/reports/technical")
def get_technical_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    issues = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        issues_file = os.path.join(latest.get("path"), "issues.json")
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
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=Technical_Report_{safe_domain}.pdf"})

@router.get("/keywords/report.pdf")
@router.get("/reports/keywords")
def get_keywords_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    pages = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        pages_file = os.path.join(latest.get("path"), "pages.json")
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
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=Keywords_Report_{safe_domain}.pdf"})

@router.get("/internal-links/report.pdf")
@router.get("/reports/internal-links")
def get_internal_links_pdf_report(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    safe_domain = get_sanitized_domain(project.domain)
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    links = []
    if os.path.exists(latest_path):
        latest = json.load(open(latest_path))
        links_file = os.path.join(latest.get("path"), "internal_links.json")
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
    return Response(content=pdf_bytes, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=Internal_Links_Report_{safe_domain}.pdf"})
