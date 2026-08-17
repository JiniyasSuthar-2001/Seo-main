from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.models.crawl_session import CrawlSession
from app.crawler.crawler import SEOCrawler
from app.services.crawl_storage import CrawlStorage
from pydantic import BaseModel
from typing import Optional
import asyncio
import os

router = APIRouter()

class CrawlRequest(BaseModel):
    url: Optional[str] = None

async def run_crawl_task(session_id: str, start_url: str, db: Session):
    crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not crawl_session:
        return
        
    try:
        print(f"[CRAWL] Starting crawl task for session {session_id} on {start_url}", flush=True)
        crawler = SEOCrawler(start_url=start_url, max_pages=1000)
        results = await crawler.start()
        
        # Save & verify snapshot
        storage = CrawlStorage()
        crawl_dir = storage.save_crawl_snapshot(start_url, session_id, results)
        
        # Mark completed only after storage succeeds
        crawl_session.status = "completed"
        crawl_session.pages_crawled = len(results.get("pages", []))
        crawl_session.pages_discovered = len(crawler.queue_status)
        crawl_session.issues_found = len(results.get("issues", []))
        db.commit()
        print(f"[CRAWL SUCCESS] Session {session_id} COMPLETED cleanly.", flush=True)
        
    except Exception as e:
        print(f"[CRAWL ERROR] Session {session_id} FAILED: {e}", flush=True)
        crawl_session.status = "failed"
        db.commit()

@router.post("/{project_id}/crawl")
async def start_crawl(project_id: str, request: CrawlRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    
    # 1. Determine target URL without ever defaulting to hardcoded example.com
    target_url = request.url
    if not target_url and project and project.domain:
        target_url = project.domain

    if not target_url or not target_url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400, 
            detail="A valid HTTP/HTTPS website URL is required to start crawling."
        )

    print(f"[CRAWL REQUEST] Project ID: {project_id}, Target URL: {target_url}", flush=True)

    # 2. Create session
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

    # 3. Add background crawl task
    background_tasks.add_task(run_crawl_task, new_session.id, target_url, db)
    return {"message": "Crawl started", "session_id": new_session.id, "target_url": target_url}

@router.get("/{project_id}/crawl/{session_id}")
async def get_crawl_status(project_id: str, session_id: str, db: Session = Depends(get_db)):
    crawl_session = db.query(CrawlSession).filter(CrawlSession.id == session_id).first()
    if not crawl_session:
        raise HTTPException(status_code=404, detail="Crawl session not found")
        
    return {
        "status": crawl_session.status,
        "pages_discovered": crawl_session.pages_discovered,
        "pages_crawled": crawl_session.pages_crawled,
        "issues_found": crawl_session.issues_found
    }

@router.get("/{project_id}/crawl-history")
async def get_crawl_history(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    domain = project.domain if project else "uisdigital.com"
    
    storage = CrawlStorage()
    history = storage.get_crawl_history(domain)
    return history
