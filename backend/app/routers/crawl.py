from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db, SessionLocal
from app.models.project import Project
from app.models.crawl_session import CrawlSession
from app.crawler.crawler import SEOCrawler
from app.services.crawl_storage import CrawlStorage
from app.config.utils import get_sanitized_domain, normalize_stored_path
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import os
import json
from datetime import datetime

router = APIRouter()

class CrawlRequest(BaseModel):
    url: Optional[str] = None
    scope_type: Optional[str] = "entire_domain"
    max_pages: Optional[Any] = 5000
    max_depth: Optional[int] = 0
    respect_robots_txt: Optional[bool] = True
    crawl_delay_ms: Optional[int] = 500
    request_timeout: Optional[float] = 20.0
    user_agent: Optional[str] = "SEO-Intelligence-Bot/1.0 (Mozilla/5.0 Compatible)"
    include_patterns: Optional[List[str]] = []
    exclude_patterns: Optional[List[str]] = []
    ignore_utm_params: Optional[bool] = True
    follow_redirects: Optional[bool] = True
    target_countries: Optional[List[str]] = []
    allow_subdomains: Optional[bool] = False
    allow_local_dev: Optional[bool] = False
    js_rendering: Optional[str] = "auto"

async def run_crawl_task(session_id: str, start_url: str, options: Optional[Dict[str, Any]] = None):
    db = SessionLocal()
    opts = options or {}

    def update_db_progress(crawled: int, discovered: int, status_msg: Optional[str] = None):
        try:
            db_progress = SessionLocal()
            cs = db_progress.query(CrawlSession).filter(CrawlSession.id == session_id).first()
            if cs:
                cs.pages_crawled = crawled
                cs.pages_discovered = max(discovered, crawled, 1)
                if status_msg is not None:
                    cs.status_message = status_msg
                db_progress.commit()
            db_progress.close()
        except Exception as p_err:
            print(f"[CRAWL PROGRESS DB UPDATE ERROR] {p_err}", flush=True)

    def check_cancellation() -> bool:
        try:
            db_chk = SessionLocal()
            cs = db_chk.query(CrawlSession).filter(CrawlSession.id == session_id).first()
            is_canc = bool(cs and cs.status in ("cancelling", "cancelled"))
            db_chk.close()
            return is_canc
        except Exception:
            return False

    try:
        crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
        if not crawl_session:
            return
            
        print(f"[CRAWL] Started crawl task for session {session_id} on {start_url} (Target Countries: {opts.get('target_countries', [])})", flush=True)
        crawler = SEOCrawler(
            start_url=start_url,
            max_pages=opts.get("max_pages", 5000),
            request_timeout=float(opts.get("request_timeout", 20.0)),
            scope_type=opts.get("scope_type", "entire_domain"),
            max_depth=opts.get("max_depth", 0),
            respect_robots_txt=opts.get("respect_robots_txt", True),
            crawl_delay_ms=opts.get("crawl_delay_ms", 500),
            user_agent=opts.get("user_agent", "SEO-Intelligence-Bot/1.0 (Mozilla/5.0 Compatible)"),
            include_patterns=opts.get("include_patterns", []),
            exclude_patterns=opts.get("exclude_patterns", []),
            ignore_utm_params=opts.get("ignore_utm_params", True),
            follow_redirects=opts.get("follow_redirects", True),
            target_countries=opts.get("target_countries", []),
            allow_subdomains=opts.get("allow_subdomains", False),
            allow_local_dev=opts.get("allow_local_dev", False),
            js_rendering=opts.get("js_rendering", "auto"),
            progress_callback=update_db_progress,
            cancellation_checker=check_cancellation
        )

        results = await crawler.start()
        
        # Save snapshot to disk
        storage = CrawlStorage()
        project = db.query(Project).filter(Project.id == crawl_session.project_id).first() if crawl_session else None
        target_domain = (project.domain if project and project.domain else (project.url if project and project.url else start_url))
        crawl_dir = storage.save_crawl_snapshot(target_domain, session_id, results, domain=target_domain, project_id=project.id if project else None)
        
        # Determine status
        raw_status = results.get("status", "completed")
        if raw_status in ("cancelled", "blocked_by_robots", "blocked_by_protection", "completed_with_errors", "completed", "failed"):
            crawl_status = raw_status
        elif raw_status == "access_denied":
            crawl_status = "blocked_by_protection"
        else:
            crawl_status = "completed"

        crawl_session.status = crawl_status
        crawl_session.status_message = results.get("status_message", f"Crawl {crawl_status}")
        crawl_session.pages_crawled = len(results.get("pages", []))
        crawl_session.pages_discovered = max(len(results.get("pages", [])), 1)
        crawl_session.issues_found = len(results.get("issues", []))
        crawl_session.completed_at = datetime.utcnow()
        db.commit()
        print(f"[CRAWL FINISHED] Session {session_id} status: '{crawl_status}'. Saved {len(results.get('pages', []))} pages to {crawl_dir}", flush=True)

        # Trigger automatic re-evaluation of opportunities for project
        try:
            if project:
                from app.services.audit_rules import evaluate_site_audit_rules
                from app.services.opportunity_engine import generate_central_opportunities
                from app.models.action_opportunity import ActionOpportunity
                import uuid

                pages = results.get("pages", [])
                if pages:
                    audit_eval = evaluate_site_audit_rules(pages)
                    generated = generate_central_opportunities(audit_eval, [], pages)
                    existing_status_map = {
                        o.title: o.status for o in db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).all()
                    }
                    db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).delete()
                    for item in generated:
                        saved_status = existing_status_map.get(item["title"], "Open")
                        new_opp = ActionOpportunity(
                            id=str(uuid.uuid4()),
                            project_id=project.id,
                            title=item["title"],
                            category=item["category"],
                            priority_score=item["priority_score"],
                            priority_level=item["priority_level"],
                            impact=item["impact"],
                            evidence=item["evidence"],
                            affected_urls_json=json.dumps(item.get("affected_urls", [])),
                            affected_count=item.get("affected_count", 1),
                            recommendation=item["recommendation"],
                            status=saved_status
                        )
                        db.add(new_opp)
                    db.commit()
        except Exception as opp_err:
            print(f"[CRAWL OPPORTUNITIES SYNC ERROR] {opp_err}", flush=True)
        
    except Exception as e:
        print(f"[CRAWL ERROR] Session {session_id} FAILED: {e}", flush=True)
        try:
            crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
            if crawl_session:
                crawl_session.status = "failed"
                crawl_session.completed_at = datetime.utcnow()
                db.commit()
        except Exception:
            pass
    finally:
        db.close()

from app.config.auth import get_current_user_id
from app.config.permissions import get_user_membership

@router.post("/{project_id}/crawl")
async def start_crawl(
    project_id: str,
    request: CrawlRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    
    target_url = request.url
    if not target_url and project and project.domain:
        target_url = project.domain

    if not target_url or not target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, 
            detail="A valid HTTP/HTTPS website URL is required to start crawling."
        )

    options_dict = request.dict()
    print(f"[CRAWL START REQUEST] Project ID: {project_id}, Target URL: {target_url}", flush=True)

    new_session = CrawlSession(
        project_id=project_id,
        status="running",
        pages_discovered=1,
        pages_crawled=0,
        issues_found=0
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)

    background_tasks.add_task(run_crawl_task, new_session.id, target_url, options_dict)
    return {"message": "Crawl started", "session_id": new_session.id, "target_url": target_url}

@router.post("/{project_id}/crawl/{session_id}/cancel")
async def cancel_crawl_session(
    project_id: str,
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id, CrawlSession.project_id == project_id).first()
    if not crawl_session:
        raise HTTPException(status_code=404, detail="Crawl session not found")
        
    if crawl_session.status in ("started", "running", "queued"):
        crawl_session.status = "cancelling"
        db.commit()
        print(f"[CRAWL CANCEL REQUESTED] Session {session_id} set to status 'cancelling'", flush=True)

    return {
        "message": "Crawl cancellation requested",
        "session_id": session_id,
        "status": crawl_session.status
    }

@router.get("/{project_id}/crawl/{session_id}")
async def get_crawl_status(
    project_id: str,
    session_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id, CrawlSession.project_id == project_id).first()
    if not crawl_session:
        raise HTTPException(status_code=404, detail="Crawl session not found")
        
    cfg = {}
    if crawl_session.project and crawl_session.project.crawl_config:
        try:
            cfg = json.loads(crawl_session.project.crawl_config)
        except Exception:
            pass
    max_pages_ceiling = cfg.get("max_pages", 5000)

    duration_seconds = None
    if crawl_session.started_at:
        end_time = crawl_session.completed_at or datetime.utcnow()
        duration_seconds = max(0, int((end_time - crawl_session.started_at).total_seconds()))

    return {
        "id": crawl_session.id,
        "session_id": crawl_session.id,
        "status": crawl_session.status,
        "pages_discovered": crawl_session.pages_discovered,
        "pages_crawled": crawl_session.pages_crawled,
        "issues_found": crawl_session.issues_found,
        "duration_seconds": duration_seconds,
        "started_at": crawl_session.started_at.isoformat() if crawl_session.started_at else None,
        "completed_at": crawl_session.completed_at.isoformat() if crawl_session.completed_at else None,
        "max_pages": max_pages_ceiling,
        "status_message": crawl_session.status_message
    }

@router.get("/{project_id}/crawl/broken-links")
async def get_crawl_broken_links(
    project_id: str,
    link_type: Optional[str] = None,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"broken_links": [], "total": 0, "internal_count": 0, "external_count": 0}

    domain = project.domain
    storage = CrawlStorage()
    website_dir = storage._get_website_folder(domain, domain, project.id)
    latest_path = os.path.join(website_dir, "latest.json")

    broken_links = []
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            crawl_dir = normalize_stored_path(latest.get("path"))
            bl_file = os.path.join(crawl_dir, "broken_links.json")
            if os.path.exists(bl_file):
                with open(bl_file, "r") as bf:
                    broken_links = json.load(bf)
        except Exception as e:
            print(f"[CRAWL API] Error loading broken_links.json: {e}", flush=True)

    internal_count = sum(1 for b in broken_links if b.get("link_type") == "internal")
    external_count = sum(1 for b in broken_links if b.get("link_type") == "external")

    if link_type and link_type.lower() in ("internal", "external"):
        broken_links = [b for b in broken_links if b.get("link_type", "").lower() == link_type.lower()]

    return {
        "domain": domain,
        "broken_links": broken_links,
        "total": len(broken_links),
        "internal_count": internal_count,
        "external_count": external_count
    }

@router.get("/{project_id}/crawl-history")
async def get_crawl_history(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return []
        
    domain = project.domain
    storage = CrawlStorage()
    history = storage.get_crawl_history(domain, project_id=project.id)
    return history

from app.routers.reports import build_export_filename, record_report_generation, CSVExportService
from fastapi import Response

@router.get("/{project_id}/crawl-history/export.csv")
def export_crawl_history_csv(
    project_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        raise HTTPException(status_code=404, detail="Project not found")

    storage = CrawlStorage()
    history = storage.get_crawl_history(project.domain, project_id=project.id)
    csv_str = CSVExportService.generate_crawl_history_csv(history)
    filename = build_export_filename(project.domain, "crawl-history", "csv")
    record_report_generation(db, project, "Crawl History CSV", "csv", filename, None, "Crawl Engine Logs")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})
