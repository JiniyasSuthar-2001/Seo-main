import os
import json
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any, List

from app.config.database import get_db
from app.config.auth import get_current_user_id
from app.config.settings import settings
from app.config.permissions import get_user_membership
from app.models.project import Project
from app.llm.seo_analyst import SEOAnalystAgent
from app.llm.llm_provider import GroqProviderAdapter, GeminiProviderAdapter, get_llm_provider_for_user, AIProviderException
from app.llm.ollama_adapter import OllamaProviderAdapter
from app.llm.ai_service import AIService
from app.services.keyword_discovery import KeywordDiscoveryService
from app.services.competitor_engine import CompetitorEngineService

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    current_page: Optional[str] = None

class AnalysisRequest(BaseModel):
    project_id: str
    preferred_provider: Optional[str] = None

class PreferenceRequest(BaseModel):
    provider: str
    model: Optional[str] = None

class ProblemSolutionRequest(BaseModel):
    rule_id: Optional[str] = None
    title: str
    category: Optional[str] = "Website Health"
    severity: Optional[str] = "notice"
    description: Optional[str] = None
    recommendation: Optional[str] = None
    affected_urls: Optional[List[str]] = []
    evidence_text: Optional[str] = None

def _get_project_or_404(project_id: str, db: Session, user_id: str) -> Project:
    get_user_membership(db, user_id, project_id)
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.domain:
        raise HTTPException(status_code=400, detail="This project has no website URL configured.")
    return project

from fastapi import Query

@router.get("/providers")
@router.get("/providers-matrix")
@router.get("/providers-matrix/")
def get_ai_providers_matrix(
    user_id: Optional[str] = Depends(get_current_user_id), 
    db: Session = Depends(get_db)
):
    """
    Returns full diagnostic status matrix for all 5 provider types:
    Ollama (local), Groq (platform default), OpenAI, Gemini, Claude (customer BYO keys).
    Guarantees NO API keys or raw credentials are exposed.
    """
    return AIService.get_provider_status_matrix(user_id=user_id, db=db)

@router.post("/set-active-provider")
@router.post("/set-active-provider/")
def set_active_provider(
    provider: str = Query("groq"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    from app.models.user import User
    user = db.query(User).filter(User.id == user_id).first()
    if user and hasattr(user, "preferred_ai_provider"):
        user.preferred_ai_provider = provider
        db.commit()
    return {"status": "success", "message": f"Active AI provider preference set to {provider}.", "provider": provider}

@router.get("/status")
def get_ai_status(user_id: Optional[str] = Depends(get_current_user_id), db: Session = Depends(get_db)):
    provider = get_llm_provider_for_user(user_id, db)
    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")

    if provider:
        p_name = getattr(provider, "provider_name", type(provider).__name__.replace("ProviderAdapter", "").lower())
        return {
            "provider": p_name,
            "configured": True,
            "available": True,
            "model": getattr(provider, "model", "default"),
            "groq_configured": bool(groq_key and groq_key.strip())
        }
    return {
        "provider": "none",
        "configured": False,
        "available": False,
        "reason": "No AI provider configured. Ollama is offline, platform Groq API key is not set, and no customer API key is connected."
    }

@router.post("/ollama/status")
def get_ollama_status(body: dict = Body(default={})):
    base_url = body.get("base_url") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    model = body.get("model") or os.environ.get("OLLAMA_MODEL") or "llama3.2:3b"
    adapter = OllamaProviderAdapter(base_url=base_url, model=model)
    try:
        res = adapter.test_connection(timeout=3.0)
        return res
    except AIProviderException as e:
        return {
            "status": "error",
            "provider": "ollama",
            "available": False,
            "message": e.message
        }

@router.post("/ollama/test")
def test_ollama_connection(body: dict = Body(default={})):
    base_url = body.get("base_url") or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    model = body.get("model") or os.environ.get("OLLAMA_MODEL") or "llama3.2:3b"
    adapter = OllamaProviderAdapter(base_url=base_url, model=model)
    try:
        res = adapter.test_connection(timeout=5.0)
        return {
            "status": "connected",
            "provider": "ollama",
            "model": res.get("selected_model", model),
            "installed_models": res.get("installed_models", []),
            "hardware_fit": res.get("hardware_fit", "OPTIMAL"),
            "hardware_badge": res.get("hardware_badge", "Suitable for this computer"),
            "message": res.get("message", "Ollama local AI is connected.")
        }
    except AIProviderException as e:
        return {
            "status": "error",
            "provider": "ollama",
            "available": False,
            "message": e.message
        }

class GroqTestRequest(BaseModel):
    model: Optional[str] = None

@router.get("/groq/status")
def get_groq_status():
    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    if groq_key and groq_key.strip():
        try:
            adapter = GroqProviderAdapter(api_key=groq_key)
            models = adapter.fetch_available_models(timeout=5.0)
            active_model = adapter.model or (models[0]["id"] if models else "openai/gpt-oss-120b")
            return {
                "provider": "groq",
                "configured": True,
                "available": True if models else True,
                "model": active_model,
                "available_models": models,
                "description": "Groq Platform AI is available."
            }
        except Exception:
            return {
                "provider": "groq",
                "configured": True,
                "available": True,
                "model": settings.GROQ_MODEL or "openai/gpt-oss-120b",
                "available_models": [],
                "description": "Groq Platform AI is configured."
            }
    return {
        "provider": "groq",
        "configured": False,
        "available": False,
        "model": None,
        "available_models": [],
        "reason": "Groq API key is not configured in backend environment."
    }

@router.post("/groq/test")
def test_groq_connection(
    req_body: Optional[GroqTestRequest] = None,
    user_id: str = Depends(get_current_user_id)
):
    groq_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY")
    selected_model = req_body.model if req_body and req_body.model else None

    if not groq_key or not groq_key.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "status": "error",
                "provider": "groq",
                "configured": False,
                "available": False,
                "message": "Groq API key is not configured in backend environment."
            }
        )

    try:
        adapter = GroqProviderAdapter(api_key=groq_key, model=selected_model)
        result = adapter.test_connection(timeout=15.0)
        return {
            "status": "connected",
            "provider": "groq",
            "model": result.get("model"),
            "available_models": result.get("available_models", []),
            "message": result.get("message", "Groq connection successful.")
        }
    except AIProviderException as e:
        raise HTTPException(
            status_code=e.status_code if e.status_code else 502,
            detail={
                "status": "error",
                "provider": "groq",
                "configured": True,
                "available": False,
                "message": e.message
            }
        )
    except Exception as ex:
        raise HTTPException(
            status_code=502,
            detail={
                "status": "error",
                "provider": "groq",
                "configured": True,
                "available": False,
                "message": f"Groq connection failed: {str(ex)[:120]}"
            }
        )

@router.get("/gemini/status")
def get_gemini_status():
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    model = settings.GEMINI_MODEL or "models/gemini-flash-latest"
    
    if api_key and api_key.strip():
        return {
            "provider": "gemini",
            "configured": True,
            "available": True,
            "model": model
        }
    return {
        "provider": "gemini",
        "configured": False,
        "available": False,
        "reason": "Gemini API key is not configured"
    }

@router.post("/gemini/test")
def test_gemini_connection(user_id: str = Depends(get_current_user_id)):
    api_key = settings.GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY")
    model = settings.GEMINI_MODEL or "models/gemini-flash-latest"

    if not api_key or not api_key.strip():
        return {
            "status": "error",
            "provider": "gemini",
            "configured": False,
            "available": False,
            "message": "Gemini API key is not configured in backend environment."
        }

    try:
        adapter = GeminiProviderAdapter(api_key=api_key, model=model)
        result = adapter.test_connection(timeout=15.0)
        return {
            "status": "connected",
            "provider": "gemini",
            "model": model,
            "message": result.get("message", "Gemini connection successful.")
        }
    except AIProviderException as e:
        return {
            "status": "error",
            "provider": "gemini",
            "configured": True,
            "available": False,
            "message": e.message
        }
    except Exception as ex:
        return {
            "status": "error",
            "provider": "gemini",
            "configured": True,
            "available": False,
            "message": f"Gemini connection failed: {str(ex)[:120]}"
        }

@router.post("/keywords/discover/{project_id}")
@router.post("/{project_id}/keywords/discover")
def discover_project_keywords(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Extracts candidate keyword opportunities from actual crawled HTML pages.
    All candidate suggestions are explicitly tagged with 'is_ai_suggested: True'.
    """
    _get_project_or_404(project_id, db, user_id)
    return KeywordDiscoveryService.discover_candidate_keywords(project_id, db)

@router.get("/competitors/discover/{project_id}")
@router.get("/{project_id}/competitors/discover")
def discover_project_competitors(
    project_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Discovers competitor domains from real Search Console SERP query evidence or crawled outbound links.
    """
    _get_project_or_404(project_id, db, user_id)
    return CompetitorEngineService.discover_competitors_from_evidence(project_id, db)

@router.post("/seo-analysis")
def perform_seo_analysis(
    req: AnalysisRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    project = _get_project_or_404(req.project_id, db, user_id)
    agent = SEOAnalystAgent()
    try:
        return agent.analyze_project(project.id, domain=project.domain, user_id=user_id, db=db)
    except AIProviderException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/{project_id}/ai/analyze")
def analyze_project_ai(
    project_id: str, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    project = _get_project_or_404(project_id, db, user_id)
    agent = SEOAnalystAgent()
    try:
        return agent.analyze_project(project.id, domain=project.domain, user_id=user_id, db=db)
    except AIProviderException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.get("/{project_id}/ai/insights")
def get_project_insights(
    project_id: str, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    project = _get_project_or_404(project_id, db, user_id)
    agent = SEOAnalystAgent()
    try:
        return agent.analyze_project(project.id, domain=project.domain, user_id=user_id, db=db)
    except AIProviderException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

@router.post("/{project_id}/ai/chat")
def chat_with_project_ai(
    project_id: str, 
    request: ChatRequest, 
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    project = _get_project_or_404(project_id, db, user_id)
    agent = SEOAnalystAgent()
    try:
        return agent.chat_with_data(request.query, key=project.id, domain=project.domain, user_id=user_id, db=db)
    except AIProviderException as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

PROBLEM_SOLUTION_CACHE: Dict[str, Dict[str, Any]] = {}

@router.post("/{project_id}/ai/problem-solution")
def get_problem_ai_solution(
    project_id: str,
    payload: ProblemSolutionRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    project = _get_project_or_404(project_id, db, user_id)

    # 1. Check cache first for instant repeat response
    cache_key = f"{project_id}:{payload.rule_id or payload.title}"
    if cache_key in PROBLEM_SOLUTION_CACHE:
        return PROBLEM_SOLUTION_CACHE[cache_key]

    affected_urls = payload.affected_urls or []
    first_url = affected_urls[0] if affected_urls else None

    # 2. Get active AI provider via provider selection cascade
    provider = AIService.get_provider(user_id=user_id, db=db)

    page_solutions: Dict[str, str] = {}
    default_solution = None

    if provider:
        try:
            sys_instructions = (
                "You are an expert SEO Technical Advisor. Analyze the provided website audit issue and affected URLs "
                "to generate concise, page-specific, 1-3 sentence evidence-grounded AI solutions for each affected page. "
                "Do NOT invent unverified evidence, HTTP status codes, or fake metadata. "
                "Respond ONLY with a valid JSON object matching this schema:\n"
                "{\n"
                '  "page_solutions": {\n'
                '     "URL_HERE": "Concise 1-3 sentence solution tailored specifically to this page URL and finding"\n'
                '  },\n'
                '  "default_solution": "Short concise solution applicable to pages missing specific URL entries"\n'
                "}"
            )

            user_prompt = (
                f"Website Domain: {project.domain}\n"
                f"Problem Title: {payload.title}\n"
                f"Rule ID: {payload.rule_id or 'N/A'}\n"
                f"Category: {payload.category or 'Website Check'}\n"
                f"Severity: {payload.severity or 'Notice'}\n"
                f"Description: {payload.description or 'No description'}\n"
                f"Recommended Action: {payload.recommendation or 'N/A'}\n"
                f"Evidence Text: {payload.evidence_text or 'N/A'}\n"
                f"Affected URLs List: {json.dumps(affected_urls[:15])}"
            )

            context_data = {
                "website_domain": project.domain,
                "title": payload.title,
                "rule_id": payload.rule_id,
                "category": payload.category,
                "severity": payload.severity,
                "description": payload.description,
                "recommendation": payload.recommendation,
                "affected_urls": affected_urls[:15],
                "evidence_text": payload.evidence_text
            }

            ai_res = provider.analyze(sys_instructions, user_prompt, context_data, timeout=20.0)
            if isinstance(ai_res, dict):
                raw_sol = ai_res.get("page_solutions")
                if isinstance(raw_sol, dict):
                    page_solutions = {str(k): str(v) for k, v in raw_sol.items() if v}
                default_solution = ai_res.get("default_solution")
        except Exception as ai_err:
            print(f"[AI PROBLEM SOLUTION ERROR] Provider execution error: {ai_err}", flush=True)

    # Evidence-grounded fallback generator per URL if provider errored out or missed entries
    title_lower = (payload.title or "").lower()
    
    def generate_url_fallback(url_str: str) -> str:
        if "broken" in title_lower or "4xx" in title_lower or "5xx" in title_lower or "404" in title_lower:
            return "Restore this page if it should exist, or implement a relevant 301 redirect to the closest valid destination. Verify the final URL returns HTTP 200."
        elif "title" in title_lower:
            return "Add a unique, relevant <title> tag (50–60 characters) that accurately describes this page's content and primary topic."
        elif "description" in title_lower:
            return "Add a unique meta description (150–160 characters) summarizing the specific content on this page with a clear call to action."
        elif "h1" in title_lower:
            return "Add one clear <h1> heading that accurately represents the primary topic of this page. Avoid adding multiple competing H1 headings."
        elif "alt" in title_lower or "image" in title_lower:
            return "Add descriptive alt attributes to content images on this page explaining their visual purpose and topic relevance."
        elif "schema" in title_lower or "structured data" in title_lower or "json-ld" in title_lower:
            return "Add structured data appropriate to this page's type (e.g. Organization, Product, or Article) matching its real content."
        elif "canonical" in title_lower:
            return "Add a canonical link element pointing to the preferred indexable URL for this page."
        elif "link" in title_lower:
            return "Update the source page to point to the correct live URL, or restore the destination page if it was removed intentionally."
        else:
            return payload.recommendation or f"Review page HTML and server headers to resolve {payload.title}."

    if not default_solution:
        default_solution = generate_url_fallback(first_url or project.domain)

    # Ensure every affected URL has a page solution
    for u in affected_urls:
        if u not in page_solutions or not page_solutions[u]:
            page_solutions[u] = generate_url_fallback(u)

    res_body = {
        "status": "success",
        "title": payload.title,
        "category": payload.category,
        "affected_count": len(affected_urls),
        "page_solutions": page_solutions,
        "default_solution": default_solution
    }

    PROBLEM_SOLUTION_CACHE[cache_key] = res_body
    return res_body
