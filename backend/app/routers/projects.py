import os
import json
import shutil
import re
import io
import zipfile
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body, Response
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain, normalize_stored_path
from app.services.reports.pdf_service import PDFReportGenerator
from app.services.reports.export_service import CSVExportService

router = APIRouter()
pdf_gen = PDFReportGenerator()

def get_export_timestamp() -> str:
    return datetime.now().strftime("%d-%m-%y-%I-%M-%p")

def sanitize_filename_part(name: str) -> str:
    if not name:
        return "SEO-Project"
    cleaned = re.sub(r'[^\w\s-]', '', name).strip()
    result = re.sub(r'[-\s]+', '-', cleaned)
    return result or "SEO-Project"

def get_project_metrics(domain: str) -> dict:
    safe_domain = get_sanitized_domain(domain)
    website_dir = os.path.join("data", "websites", safe_domain)
    latest_path = os.path.join(website_dir, "latest.json")
    
    metrics = {
        "last_crawl": None,
        "crawl_status": "No Crawls",
        "pages_count": 0,
        "issues_count": 0,
        "critical_issues": 0,
        "warnings": 0,
        "keywords_count": 0,
        "backlinks_count": 0,
        "internal_links_count": 0,
        "has_crawled": False
    }

    if not os.path.exists(latest_path):
        return metrics

    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
        
        crawl_dir = normalize_stored_path(latest.get("path"))
        if crawl_dir and os.path.exists(crawl_dir):
            metadata_path = os.path.join(crawl_dir, "metadata.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as mf:
                    meta = json.load(mf)
                    metrics["last_crawl"] = meta.get("timestamp")
                    metrics["crawl_status"] = "Completed"
                    metrics["pages_count"] = meta.get("pages_crawled", 0)
                    metrics["issues_count"] = meta.get("total_issues", 0)
                    metrics["critical_issues"] = meta.get("critical_issues", 0)
                    metrics["warnings"] = meta.get("warning_issues", 0)
                    metrics["internal_links_count"] = meta.get("internal_links_count", 0)
                    metrics["has_crawled"] = True

            # Count keywords if keywords.json exists
            keywords_path = os.path.join(crawl_dir, "keywords.json")
            if os.path.exists(keywords_path):
                with open(keywords_path, "r") as kf:
                    kw_data = json.load(kf)
                    metrics["keywords_count"] = len(kw_data) if isinstance(kw_data, list) else 0

            # Count backlinks if backlinks.json exists
            backlinks_path = os.path.join(crawl_dir, "backlinks.json")
            if os.path.exists(backlinks_path):
                with open(backlinks_path, "r") as bf:
                    bl_data = json.load(bf)
                    metrics["backlinks_count"] = len(bl_data) if isinstance(bl_data, list) else 0
    except Exception as e:
        print(f"[PROJECTS ROUTER] Exception loading metrics for {domain}: {e}", flush=True)

    return metrics

def load_project_full_datasets(domain: str):
    safe_domain = get_sanitized_domain(domain)
    website_dir = os.path.join("data", "websites", safe_domain)
    latest_path = os.path.join(website_dir, "latest.json")

    metadata, pages, keywords, rankings, backlinks, internal_links, competitors, issues, crawls = {}, [], [], [], [], [], [], [], []

    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            if crawl_dir and os.path.exists(crawl_dir):
                meta_p = os.path.join(crawl_dir, "metadata.json")
                pages_p = os.path.join(crawl_dir, "pages.json")
                issues_p = os.path.join(crawl_dir, "issues.json")
                links_p = os.path.join(crawl_dir, "internal_links.json")
                kw_p = os.path.join(crawl_dir, "keywords.json")
                bl_p = os.path.join(crawl_dir, "backlinks.json")
                rk_p = os.path.join(crawl_dir, "rankings.json")
                comp_p = os.path.join(crawl_dir, "competitors.json")

                if os.path.exists(meta_p): metadata = json.load(open(meta_p))
                if os.path.exists(pages_p): pages = json.load(open(pages_p))
                if os.path.exists(issues_p): issues = json.load(open(issues_p))
                if os.path.exists(links_p): internal_links = json.load(open(links_p))
                if os.path.exists(kw_p): keywords = json.load(open(kw_p))
                if os.path.exists(bl_p): backlinks = json.load(open(bl_p))
                if os.path.exists(rk_p): rankings = json.load(open(rk_p))
                if os.path.exists(comp_p): competitors = json.load(open(comp_p))
        except Exception as e:
            print(f"[PROJECT DATASET LOAD ERROR] {e}", flush=True)

    crawls_dir = os.path.join(website_dir, "crawls")
    if os.path.exists(crawls_dir):
        try:
            for folder in os.listdir(crawls_dir):
                meta_path = os.path.join(crawls_dir, folder, "metadata.json")
                if os.path.exists(meta_path):
                    crawls.append(json.load(open(meta_path)))
        except Exception:
            pass

    return metadata, pages, keywords, rankings, backlinks, internal_links, competitors, issues, crawls

@router.get("")
@router.get("/")
def get_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    result = []
    for p in projects:
        m = get_project_metrics(p.domain)
        p_dict = {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "domain": p.domain,
            "description": p.description or "",
            "industry": p.industry or "",
            "notes": p.notes or "",
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            **m
        }
        result.append(p_dict)
    return result

@router.get("/all/pdf")
def get_all_projects_pdf(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    headers = ["Project Name", "Domain", "Pages", "Issues", "Keywords", "Status"]
    rows = []
    for p in projects:
        m = get_project_metrics(p.domain)
        rows.append([
            p.name,
            p.domain,
            str(m.get("pages_count", 0)),
            str(m.get("issues_count", 0)),
            str(m.get("keywords_count", 0)),
            m.get("crawl_status", "No Crawls")
        ])

    pdf_bytes = pdf_gen.generate_simple_table_pdf(
        "Consolidated SEO Projects Overview",
        f"Total Projects Managed: {len(projects)} | Exported: {datetime.utcnow().strftime('%d %b %Y')}",
        headers,
        rows,
        [120, 140, 50, 50, 60, 80]
    )
    ts = get_export_timestamp()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"SEO-Projects-Summary-Report-{ts}.pdf\""}
    )

@router.get("/all/export")
def get_all_projects_zip_export(db: Session = Depends(get_db)):
    projects = db.query(Project).all()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in projects:
            p_folder = sanitize_filename_part(p.name)
            meta, pages, keywords, rankings, backlinks, links, comps, issues, crawls = load_project_full_datasets(p.domain)
            zf.writestr(f"{p_folder}/project_summary.csv", CSVExportService.generate_project_summary_csv(p.name, p.domain, p.url, meta, pages, keywords, issues))
            zf.writestr(f"{p_folder}/pages.csv", CSVExportService.generate_pages_csv(pages))
            zf.writestr(f"{p_folder}/keywords.csv", CSVExportService.generate_keywords_csv(keywords))
            zf.writestr(f"{p_folder}/rankings.csv", CSVExportService.generate_rankings_csv(rankings))
            zf.writestr(f"{p_folder}/backlinks.csv", CSVExportService.generate_backlinks_csv(backlinks))
            zf.writestr(f"{p_folder}/internal_links.csv", CSVExportService.generate_internal_links_csv(links))
            zf.writestr(f"{p_folder}/competitors.csv", CSVExportService.generate_competitors_csv(comps))
            zf.writestr(f"{p_folder}/technical_issues.csv", CSVExportService.generate_technical_issues_csv(issues))
            zf.writestr(f"{p_folder}/crawl_history.csv", CSVExportService.generate_crawl_history_csv(crawls))

    zip_buffer.seek(0)
    ts = get_export_timestamp()
    return Response(
        content=zip_buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"SEO-Projects-Export-{ts}.zip\""}
    )

@router.post("")
@router.post("/")
def create_project(payload: dict = Body(...), db: Session = Depends(get_db)):
    url_val = (payload.get('url') or payload.get('domain') or '').strip()
    name_val = (payload.get('name') or 'New SEO Project').strip()
    description = payload.get('description', '').strip()
    industry = payload.get('industry', '').strip()
    notes = payload.get('notes', '').strip()

    if not url_val:
        raise HTTPException(status_code=400, detail="Website URL or domain is required.")

    if not url_val.startswith(("http://", "https://")):
        url_val = "https://" + url_val

    safe_domain = get_sanitized_domain(url_val)

    existing = db.query(Project).all()
    for proj in existing:
        if get_sanitized_domain(proj.url) == safe_domain:
            return {
                "status": "exists",
                "message": f"Project for '{safe_domain}' already exists.",
                "project": {
                    "id": proj.id,
                    "name": proj.name,
                    "url": proj.url,
                    "domain": proj.domain,
                    "description": proj.description or "",
                    "industry": proj.industry or "",
                    "notes": proj.notes or "",
                    "created_at": proj.created_at.isoformat() if proj.created_at else None,
                    **get_project_metrics(proj.domain)
                }
            }

    new_proj = Project(
        name=name_val,
        url=url_val,
        description=description,
        industry=industry,
        notes=notes
    )
    db.add(new_proj)
    db.commit()
    db.refresh(new_proj)

    m = get_project_metrics(new_proj.domain)
    return {
        "status": "created",
        "message": "Project created successfully.",
        "project": {
            "id": new_proj.id,
            "name": new_proj.name,
            "url": new_proj.url,
            "domain": new_proj.domain,
            "description": new_proj.description or "",
            "industry": new_proj.industry or "",
            "notes": new_proj.notes or "",
            "created_at": new_proj.created_at.isoformat() if new_proj.created_at else None,
            **m
        }
    }

@router.get("/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    m = get_project_metrics(p.domain)
    return {
        "id": p.id,
        "name": p.name,
        "url": p.url,
        "domain": p.domain,
        "description": p.description or "",
        "industry": p.industry or "",
        "notes": p.notes or "",
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        **m
    }

@router.get("/{project_id}/report.pdf")
def get_project_pdf_report(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    meta, pages, keywords, rankings, backlinks, links, comps, issues, crawls = load_project_full_datasets(p.domain)
    pdf_bytes = pdf_gen.generate_full_project_pdf(
        project_name=p.name,
        project_url=p.url,
        metadata=meta,
        pages=pages,
        keywords=keywords,
        rankings=rankings,
        backlinks=backlinks,
        internal_links=links,
        competitors=comps,
        issues=issues,
        crawls=crawls
    )

    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Report-{ts}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""}
    )

@router.get("/{project_id}/export")
def get_project_zip_export(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    meta, pages, keywords, rankings, backlinks, links, comps, issues, crawls = load_project_full_datasets(p.domain)
    zip_bytes = CSVExportService.generate_project_zip_export(
        project_name=p.name,
        domain=p.domain,
        url=p.url,
        metadata=meta,
        pages=pages,
        keywords=keywords,
        rankings=rankings,
        backlinks=backlinks,
        internal_links=links,
        competitors=comps,
        issues=issues,
        crawls=crawls
    )

    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Data-{ts}.zip"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""}
    )

# MODULE-LEVEL CSV EXPORTS
@router.get("/{project_id}/pages/export.csv")
def export_project_pages_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, pages, _, _, _, _, _, _, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_pages_csv(pages)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Pages-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/{project_id}/keywords/export.csv")
def export_project_keywords_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, _, keywords, _, _, _, _, _, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_keywords_csv(keywords)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Keywords-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/{project_id}/rankings/export.csv")
def export_project_rankings_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, _, _, rankings, _, _, _, _, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_rankings_csv(rankings)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Rankings-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/{project_id}/backlinks/export.csv")
def export_project_backlinks_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, _, _, _, backlinks, _, _, _, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_backlinks_csv(backlinks)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Backlinks-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/{project_id}/internal-links/export.csv")
def export_project_internal_links_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, _, _, _, _, links, _, _, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_internal_links_csv(links)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Internal-Links-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/{project_id}/technical/export.csv")
def export_project_technical_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, _, _, _, _, _, _, issues, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_technical_issues_csv(issues)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Technical-Issues-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.get("/{project_id}/competitors/export.csv")
def export_project_competitors_csv(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(status_code=404, detail="Project not found")
    _, _, _, _, _, _, comps, _, _ = load_project_full_datasets(p.domain)
    csv_data = CSVExportService.generate_competitors_csv(comps)
    proj_name = sanitize_filename_part(p.name)
    ts = get_export_timestamp()
    safe_filename = f"{proj_name}-SEO-Competitors-{ts}.csv"
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{safe_filename}\""})

@router.put("/{project_id}")
def update_project(project_id: str, payload: dict = Body(...), db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    if 'name' in payload and payload['name'].strip():
        p.name = payload['name'].strip()
    if 'url' in payload and payload['url'].strip():
        new_url = payload['url'].strip()
        if not new_url.startswith(("http://", "https://")):
            new_url = "https://" + new_url
        p.url = new_url
    if 'description' in payload:
        p.description = payload['description'].strip()
    if 'industry' in payload:
        p.industry = payload['industry'].strip()
    if 'notes' in payload:
        p.notes = payload['notes'].strip()

    p.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(p)

    m = get_project_metrics(p.domain)
    return {
        "status": "updated",
        "project": {
            "id": p.id,
            "name": p.name,
            "url": p.url,
            "domain": p.domain,
            "description": p.description or "",
            "industry": p.industry or "",
            "notes": p.notes or "",
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
            **m
        }
    }

@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Project not found")

    domain = p.domain
    safe_domain = get_sanitized_domain(domain)

    db.delete(p)
    db.commit()

    website_dir = os.path.join("data", "websites", safe_domain)
    if os.path.exists(website_dir):
        try:
            shutil.rmtree(website_dir)
        except Exception as e:
            print(f"[PROJECTS API] Error deleting storage directory {website_dir}: {e}", flush=True)

    return {"status": "success", "message": f"Project '{p.name}' and all associated datasets deleted cleanly."}

@router.get("/{project_id}/summary")
def get_project_summary(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p or not p.domain:
        return {"status": "empty", "message": "Project not found or website domain unconfigured."}

    safe_domain = get_sanitized_domain(p.domain)
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    if not os.path.exists(latest_path):
        return {"status": "empty", "message": "No crawl data available yet."}
        
    try:
        with open(latest_path, "r") as f:
            latest = json.load(f)
        crawl_dir = normalize_stored_path(latest.get("path"))
        metadata_path = os.path.join(crawl_dir, "metadata.json")
        if os.path.exists(metadata_path):
            with open(metadata_path, "r") as mf:
                return {"status": "success", "latest_crawl": json.load(mf)}
    except Exception as e:
        print(f"[PROJECTS API] Exception reading snapshot: {e}", flush=True)
        
    return {"status": "error", "message": "Failed to read crawl data"}

@router.get("/{project_id}/crawls")
def get_project_crawls(project_id: str, db: Session = Depends(get_db)):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p or not p.domain:
        return []

    safe_domain = get_sanitized_domain(p.domain)
    crawls_dir = os.path.join("data", "websites", safe_domain, "crawls")

    if not os.path.exists(crawls_dir):
        return []

    crawls = []
    for folder in os.listdir(crawls_dir):
        meta_path = os.path.join(crawls_dir, folder, "metadata.json")
        if os.path.exists(meta_path):
            try:
                crawls.append(json.load(open(meta_path)))
            except Exception:
                pass

    crawls.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return crawls
