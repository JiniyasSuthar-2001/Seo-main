from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.config.database import get_db
from app.models.project import Project
from app.config.utils import get_sanitized_domain
from app.providers.nlp_keywords import NLPKeywordExtractor
from app.providers.google_autocomplete import GoogleAutocompleteProvider
import os
import json

router = APIRouter()
nlp_extractor = NLPKeywordExtractor()
autocomplete_provider = GoogleAutocompleteProvider()

@router.get("")
@router.get("/")
def get_keywords(project_id: str, limit: int = Query(50), offset: int = Query(0), db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.domain:
        return {"content_keywords": [], "gsc_keywords": [], "total": 0}

    domain = project.domain
    safe_domain = get_sanitized_domain(domain)
    
    # 1. Load latest crawl pages
    latest_path = os.path.join("data", "websites", safe_domain, "latest.json")
    pages = []
    if os.path.exists(latest_path):
        try:
            with open(latest_path, "r") as f:
                latest = json.load(f)
            pages_file = os.path.join(latest.get("path"), "pages.json")
            if os.path.exists(pages_file):
                with open(pages_file, "r") as pf:
                    pages = json.load(pf)
        except Exception as e:
            print(f"[KEYWORDS API] Error loading pages: {e}", flush=True)

    # 2. Extract content terms using NLP engine
    extracted_terms = nlp_extractor.extract_content_keywords(pages)
    
    return {
        "domain": domain,
        "content_keywords": extracted_terms[offset : offset + limit],
        "total_extracted_terms": len(extracted_terms),
        "source": "Local Open-Source NLP Content Extraction"
    }

@router.get("/autocomplete")
def get_keyword_suggestions(q: str = Query(...)):
    if not q or not q.strip():
        return {"query": q, "suggestions": []}
        
    suggestions = autocomplete_provider.get_suggestions(q)
    return {
        "query": q,
        "suggestions": suggestions,
        "source": "Google Autocomplete API"
    }
