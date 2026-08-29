from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db, SessionLocal
from app.models.project import Project
from app.models.crawl_session import CrawlSession
from app.crawler.crawler import SEOCrawler
from app.services.crawl_storage import CrawlStorage
from app.config.utils import get_sanitized_domain
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import asyncio
import os
import json

router = APIRouter()

class CrawlRequest(BaseModel):
    url: Optional[str] = None
    scope_type: Optional[str] = "entire_domain"
    max_pages: Optional[int] = 5000
    max_depth: Optional[int] = 0
    respect_robots_txt: Optional[bool] = True
    crawl_delay_ms: Optional[int] = 500
    request_timeout: Optional[float] = 20.0
    user_agent: Optional[str] = "SEO-Intelligence-Bot/1.0 (Mozilla/5.0 Compatible)"
    include_patterns: Optional[List[str]] = []
    exclude_patterns: Optional[List[str]] = []
    ignore_utm_params: Optional[bool] = True
    follow_redirects: Optional[bool] = True

async def run_crawl_task(session_id: str, start_url: str, options: Optional[Dict[str, Any]] = None):
    db = SessionLocal()
    opts = options or {}

    def update_db_progress(crawled: int, discovered: int):
        try:
            db_progress = SessionLocal()
            cs = db_progress.query(CrawlSession).filter(CrawlSession.id == session_id).first()
            if cs:
                cs.pages_crawled = crawled
                cs.pages_discovered = max(discovered, crawled, 1)
                db_progress.commit()
            db_progress.close()
        except Exception as p_err:
            print(f"[CRAWL PROGRESS DB UPDATE ERROR] {p_err}", flush=True)

    try:
        crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
        if not crawl_session:
            return
            
        print(f"[CRAWL] Started crawl task for session {session_id} on {start_url}", flush=True)
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
            progress_callback=update_db_progress
        )

        results = await crawler.start()
        
        # Save snapshot to disk
        storage = CrawlStorage()
        project = db.query(Project).filter(Project.id == crawl_session.project_id).first() if crawl_session else None
        target_domain = (project.domain if project and project.domain else (project.url if project and project.url else start_url))
        crawl_dir = storage.save_crawl_snapshot(target_domain, session_id, results, domain=target_domain)
        
        # Determine status
        raw_status = results.get("status", "completed")
        if raw_status == "completed_with_errors":
            crawl_status = "completed_with_errors"
        elif raw_status in ("completed", "access_denied"):
            crawl_status = "completed"
        else:
            crawl_status = "failed"

        crawl_session.status = crawl_status
        crawl_session.pages_crawled = len(results.get("pages", []))
        crawl_session.pages_discovered = max(len(results.get("pages", [])), 1)
        crawl_session.issues_found = len(results.get("issues", []))
        db.commit()
        print(f"[CRAWL COMPLETED] Session {session_id} status: '{crawl_status}'. Saved {len(results.get('pages', []))} pages to {crawl_dir}", flush=True)

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
                    db.query(ActionOpportunity).filter(ActionOpportunity.project_id == project.id).delete()
                    for item in generated:
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
                            status="Open"
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
        
    return {
        "status": crawl_session.status,
        "pages_discovered": crawl_session.pages_discovered,
        "pages_crawled": crawl_session.pages_crawled,
        "issues_found": crawl_session.issues_found
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
    history = storage.get_crawl_history(domain)
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
    history = storage.get_crawl_history(project.domain)
    csv_str = CSVExportService.generate_crawl_history_csv(history)
    filename = build_export_filename(project.domain, "crawl-history", "csv")
    record_report_generation(db, project, "Crawl History CSV", "csv", filename, None, "Crawl Engine Logs")
    return Response(content=csv_str.encode("utf-8"), media_type="text/csv", headers={"Content-Disposition": f"attachment; filename=\"{filename}\""})
