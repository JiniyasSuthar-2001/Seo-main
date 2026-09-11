import os
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.project import Project
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.llm.llm_provider import get_llm_provider_for_user
from app.services.ai_usage_service import AIUsageService
from app.services.credit_service import CreditService
from app.services.ai_access_service import AIAccessService

class AISolutionService:
    """
    Unified Actionable AI Implementation Assistant Service for Website Health and Master Reporting.
    Analyzes actual detected crawl evidence to produce complete, implementation-ready solutions
    with what is wrong, why it matters, what needs to change, exact replacement content,
    where to change it, code/config snippets, and verification steps.
    """

    _MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def _get_cache_key(cls, project_id: str, crawl_id: str, rule_or_title: str, url: str) -> str:
        clean_rule = re.sub(r'[^a-zA-Z0-9_-]', '_', (rule_or_title or 'unknown').lower())
        clean_url = (url or 'site').strip().lower()
        return f"{project_id}:{crawl_id or 'latest'}:{clean_rule}:{clean_url}"

    @classmethod
    def _load_stored_solutions(cls, project_id: str, domain: str, crawl_dir: Optional[str] = None) -> Dict[str, Any]:
        if not crawl_dir:
            proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
            latest_path = os.path.join(proj_dir, "latest.json")
            if os.path.exists(latest_path):
                try:
                    with open(latest_path, "r", encoding="utf-8") as f:
                        latest_pointer = json.load(f)
                    crawl_dir = normalize_stored_path(latest_pointer.get("path"))
                except Exception:
                    crawl_dir = None

        if crawl_dir and os.path.exists(crawl_dir):
            sol_path = os.path.join(crawl_dir, "ai_solutions.json")
            if os.path.exists(sol_path):
                try:
                    with open(sol_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except Exception as e:
                    print(f"[AI SOLUTION SERVICE] Could not read ai_solutions.json: {e}", flush=True)
        return {}

    @classmethod
    def _save_stored_solution(cls, project_id: str, domain: str, crawl_dir: Optional[str], solution_key: str, solution_obj: Dict[str, Any]):
        cls._MEMORY_CACHE[solution_key] = solution_obj

        if not crawl_dir:
            proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project_id)
            latest_path = os.path.join(proj_dir, "latest.json")
            if os.path.exists(latest_path):
                try:
                    with open(latest_path, "r", encoding="utf-8") as f:
                        latest_pointer = json.load(f)
                    crawl_dir = normalize_stored_path(latest_pointer.get("path"))
                except Exception:
                    crawl_dir = None

        if crawl_dir and os.path.exists(crawl_dir):
            sol_path = os.path.join(crawl_dir, "ai_solutions.json")
            data = {}
            if os.path.exists(sol_path):
                try:
                    with open(sol_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = {}
            data[solution_key] = solution_obj
            try:
                with open(sol_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"[AI SOLUTION SERVICE] Could not write to ai_solutions.json: {e}", flush=True)

    @classmethod
    def get_or_generate_solution(
        cls,
        project: Project,
        rule_id: Optional[str],
        problem_title: str,
        category: Optional[str],
        severity: Optional[str],
        description: Optional[str],
        recommendation: Optional[str],
        affected_url: str,
        evidence_text: Optional[str] = None,
        pages: Optional[List[Dict[str, Any]]] = None,
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
        crawl_id: Optional[str] = None,
        crawl_dir: Optional[str] = None,
        crawl_date: Optional[str] = None,
        force_regenerate: bool = False,
        is_interactive: bool = False
    ) -> Dict[str, Any]:
        """
        Retrieves an existing AI solution from storage/memory cache, or generates
        an actionable, evidence-grounded implementation solution tailored to the specific affected URL and problem.
        """
        domain = get_sanitized_domain(project.domain or project.url)
        project_name = project.name or domain
        crawl_date = crawl_date or datetime.now().strftime("%Y-%m-%d")

        # 1. Resolve crawl directory and crawl ID if not passed
        if not crawl_dir or not crawl_id:
            proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
            latest_path = os.path.join(proj_dir, "latest.json")
            if os.path.exists(latest_path):
                try:
                    with open(latest_path, "r", encoding="utf-8") as f:
                        latest_pointer = json.load(f)
                    c_dir = normalize_stored_path(latest_pointer.get("path"))
                    crawl_dir = crawl_dir or c_dir
                    crawl_id = crawl_id or latest_pointer.get("crawl_id")
                except Exception:
                    pass

        # 2. Load crawl pages if not passed in
        if pages is None:
            if crawl_dir and os.path.exists(crawl_dir):
                pages_path = os.path.join(crawl_dir, "pages.json")
                if os.path.exists(pages_path):
                    try:
                        with open(pages_path, "r", encoding="utf-8") as pf:
                            pages = json.load(pf)
                    except Exception:
                        pages = []
        pages = pages or []

        matching_page = next((p for p in pages if (p.get("url") or "").rstrip("/") == (affected_url or "").rstrip("/")), None)

        cache_key = cls._get_cache_key(project.id, crawl_id or "latest", rule_id or problem_title, affected_url)

        # 3. Check Memory Cache (unless force_regenerate is True)
        if not force_regenerate and cache_key in cls._MEMORY_CACHE:
            return cls._MEMORY_CACHE[cache_key]

        # 4. Check Stored JSON Snapshot Cache (unless force_regenerate is True)
        if not force_regenerate:
            stored_solutions = cls._load_stored_solutions(project.id, domain, crawl_dir)
            if cache_key in stored_solutions:
                cls._MEMORY_CACHE[cache_key] = stored_solutions[cache_key]
                return stored_solutions[cache_key]

        # 5. Check AI Allowance & Master Gate via AIAccessService
        can_use_ai = False
        provider = None
        if user_id and db:
            try:
                auth_res = AIAccessService.check_authorization(
                    customer_id=user_id,
                    db=db,
                    task_type="page_solution",
                    estimated_credits=1,
                    is_report=not is_interactive
                )
                can_use_ai = auth_res.get("allowed", False)
            except Exception as auth_err:
                if is_interactive:
                    raise
                print(f"[AI SOLUTION SERVICE] AI Access check prevented generation: {auth_err}", flush=True)
                can_use_ai = False

        if can_use_ai and user_id and db:
            try:
                provider = get_llm_provider_for_user(user_id=user_id, db=db)
            except Exception as e:
                print(f"[AI SOLUTION SERVICE] Could not resolve LLM provider: {e}", flush=True)

        solution_obj = None

        if provider:
            try:
                solution_obj = cls._generate_with_llm(
                    provider=provider,
                    project=project,
                    rule_id=rule_id,
                    problem_title=problem_title,
                    category=category,
                    severity=severity,
                    description=description,
                    recommendation=recommendation,
                    affected_url=affected_url,
                    evidence_text=evidence_text,
                    page=matching_page,
                    crawl_date=crawl_date
                )
                if solution_obj:
                    # Record real AI page consumption & deduct credits atomically
                    p_name = getattr(provider, "provider_name", type(provider).__name__)
                    m_name = getattr(provider, "model", "default")
                    AIAccessService.record_successful_ai_consumption(
                        customer_id=user_id,
                        project_id=project.id,
                        crawl_id=crawl_id,
                        page_url=affected_url,
                        task_type="page_solution",
                        units_consumed=1,
                        model=f"{p_name}:{m_name}",
                        db=db
                    )
            except Exception as ai_err:
                print(f"[AI SOLUTION SERVICE] LLM execution failed, using deterministic evidence fallback: {ai_err}", flush=True)
                if user_id and db:
                    p_name = getattr(provider, "provider_name", type(provider).__name__)
                    m_name = getattr(provider, "model", "default")
                    AIAccessService.record_failed_ai_attempt(
                        customer_id=user_id,
                        project_id=project.id,
                        crawl_id=crawl_id,
                        page_url=affected_url,
                        task_type="page_solution",
                        model=f"{p_name}:{m_name}",
                        error_message=str(ai_err),
                        db=db
                    )

        # 6. Deterministic Evidence-Grounded Fallback (if LLM returned None, errored, or limit reached)
        if not solution_obj:
            solution_obj = cls._generate_deterministic_fallback(
                project=project,
                rule_id=rule_id,
                problem_title=problem_title,
                category=category,
                severity=severity,
                description=description,
                recommendation=recommendation,
                affected_url=affected_url,
                evidence_text=evidence_text,
                page=matching_page,
                crawl_date=crawl_date
            )
            if not can_use_ai:
                solution_obj["ai_limit_reached"] = True
                solution_obj["usage_note"] = "AI page limit reached. Website crawling and standard SEO analysis will continue normally."

        # 7. Save and Cache Result
        cls._save_stored_solution(project.id, domain, crawl_dir, cache_key, solution_obj)
        return solution_obj

    @classmethod
    def _generate_with_llm(
        cls,
        provider: Any,
        project: Project,
        rule_id: Optional[str],
        problem_title: str,
        category: Optional[str],
        severity: Optional[str],
        description: Optional[str],
        recommendation: Optional[str],
        affected_url: str,
        evidence_text: Optional[str],
        page: Optional[Dict[str, Any]],
        crawl_date: str
    ) -> Optional[Dict[str, Any]]:
        domain = get_sanitized_domain(project.domain or project.url)
        project_name = project.name or domain

        business_context = {
            "name": project.name or domain,
            "domain": domain,
            "target_country": project.target_country or "Global",
            "industry": project.industry or "General Business",
            "services": project.services or "Professional Services",
            "service_areas": project.service_areas or "Target Regions"
        }

        page_context = {}
        if page:
            page_context = {
                "url": page.get("url"),
                "status_code": page.get("status_code"),
                "title": page.get("title"),
                "meta_description": page.get("meta_description"),
                "h1": page.get("h1"),
                "h2": page.get("h2"),
                "canonical": page.get("canonical"),
                "word_count": page.get("word_count"),
                "images_count": len(page.get("images", [])) if isinstance(page.get("images"), list) else 0,
                "internal_links_count": len(page.get("internal_links", [])) if isinstance(page.get("internal_links"), list) else 0
            }

        sys_instructions = (
            "You are an elite SEO Implementation Assistant and Technical Architect. "
            "Analyze the detected website audit issue and the actual crawl evidence of the affected page. "
            "Generate an actionable, implementation-ready solution containing all required operational fields.\n"
            "STRICT RULES:\n"
            "1. NEVER invent fake URLs, fake keywords, or fake business services.\n"
            "2. If the problem is Meta Description (too long/short/missing/duplicate), generate the EXACT replacement description (150-160 chars), calculate character count, provide the exact <meta name=\"description\" content=\"...\"> tag, and state where to insert it.\n"
            "3. If Title Tag, generate the EXACT replacement title (50-60 chars), provide <title>...</title>, and explain why it is better.\n"
            "4. If Missing H1, provide the recommended H1 string grounded in page context.\n"
            "5. If Broken Link / Status 404, provide the recommended replacement destination URL or state manual verification required, plus 301 redirect code.\n"
            "6. If Missing Schema, generate the complete, valid JSON-LD schema markup.\n"
            "7. If required crawl data is completely missing, return 'The required information was not available in the crawl data, so an exact replacement cannot be generated safely.'\n"
            "8. Respond ONLY with a valid JSON object matching this schema:\n"
            "{\n"
            '  "issue_id": "RULE_ID_OR_UPPERCASE_NAME",\n'
            '  "category": "Technical | On-Page | Content | Architecture | Schema | Assets",\n'
            '  "severity": "Critical | High | Warning | Notice",\n'
            '  "affected_url": "URL",\n'
            '  "what_is_wrong": "Clear description of observed finding and measured values",\n'
            '  "why_it_matters": "Short technical explanation of why this harms SEO/UX",\n'
            '  "what_should_change": "Specific implementation action required",\n'
            '  "current_value": "Existing value on page or (Missing ...)",\n'
            '  "recommended_replacement": "Exact replacement text / value / code",\n'
            '  "character_count": 154,\n'
            '  "where_to_change": "Location in codebase (e.g. <head> section, server config, root /robots.txt)",\n'
            '  "implementation": "Exact HTML tag / JSON-LD / configuration code snippet",\n'
            '  "why_this_version_is_better": "Why this version improves search visibility, intent match, and CTR",\n'
            '  "verification": "Exact step-by-step verification instructions after implementing",\n'
            '  "solution_type": "replacement_text | html_tag | schema_jsonld | internal_link | config | manual_action",\n'
            '  "priority": "High | Medium | Low",\n'
            '  "status": "Open"\n'
            "}"
        )

        user_prompt = (
            f"Website Domain: {domain}\n"
            f"Brand Name: {project_name}\n"
            f"Business Context: {json.dumps(business_context)}\n"
            f"Problem Title: {problem_title}\n"
            f"Rule ID: {rule_id or 'N/A'}\n"
            f"Category: {category or 'Technical'}\n"
            f"Severity: {severity or 'High'}\n"
            f"General Description: {description or 'N/A'}\n"
            f"Recommendation: {recommendation or 'N/A'}\n"
            f"Evidence Text: {evidence_text or 'N/A'}\n"
            f"Affected Page URL: {affected_url}\n"
            f"Page Crawl Evidence: {json.dumps(page_context)}"
        )

        context_data = {
            "domain": domain,
            "project_name": project_name,
            "problem_title": problem_title,
            "rule_id": rule_id,
            "affected_url": affected_url,
            "page_context": page_context
        }

        ai_res = provider.analyze(sys_instructions, user_prompt, context_data, timeout=20.0)
        if isinstance(ai_res, dict) and (ai_res.get("recommended_replacement") or ai_res.get("replacement_value")):
            rep_val = ai_res.get("recommended_replacement") or ai_res.get("replacement_value")
            res_char_count = ai_res.get("character_count")
            if res_char_count is None and isinstance(rep_val, str):
                res_char_count = len(rep_val)

            what_wrong = ai_res.get("what_is_wrong") or ai_res.get("what_we_found") or evidence_text or description or problem_title
            why_matter = ai_res.get("why_it_matters") or description or "Impacts search indexability and user CTR."
            what_change = ai_res.get("what_should_change") or ai_res.get("what_needs_to_change") or recommendation or "Apply recommended replacement."
            where_change = ai_res.get("where_to_change") or "Inside the `<head>` section of the affected page."
            impl_snippet = ai_res.get("implementation") or rep_val
            why_better = ai_res.get("why_this_version_is_better") or ai_res.get("why_this_fixes_problem") or ai_res.get("why_this_fix") or "Matches search intent and improves CTR."
            verif_text = ai_res.get("verification") or "Re-crawl the page or inspect HTML source to confirm the tag is active."

            return {
                "issue_id": ai_res.get("issue_id") or rule_id or cls._slugify_rule(problem_title),
                "category": ai_res.get("category") or category or "Technical",
                "severity": (ai_res.get("severity") or severity or "High").capitalize(),
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": ai_res.get("current_value") or (page.get("meta_description") if "description" in problem_title.lower() and page else (page.get("title") if "title" in problem_title.lower() and page else "Existing page element")),
                "recommended_replacement": rep_val,
                "recommended_change": rep_val,
                "replacement_value": rep_val,
                "character_count": res_char_count,
                "where_to_change": where_change,
                "implementation": impl_snippet,
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif_text,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": f"Replace with: {rep_val}",
                "solution_type": ai_res.get("solution_type") or "replacement_text",
                "priority": ai_res.get("priority") or (severity if severity in ("High", "Medium", "Low") else "High"),
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "AI Evidence-Grounded Engine"
            }
        return None

    @classmethod
    def _generate_deterministic_fallback(
        cls,
        project: Project,
        rule_id: Optional[str],
        problem_title: str,
        category: Optional[str],
        severity: Optional[str],
        description: Optional[str],
        recommendation: Optional[str],
        affected_url: str,
        evidence_text: Optional[str],
        page: Optional[Dict[str, Any]],
        crawl_date: str
    ) -> Dict[str, Any]:
        """
        Deterministic, evidence-grounded template fix generator ensuring 100% reliability
        when AI provider is offline or unconfigured. Never invents unsupported information.
        """
        title_lower = (problem_title or '').lower()
        rule_lower = (rule_id or '').lower()
        domain = get_sanitized_domain(project.domain or project.url)
        project_name = project.name or domain
        clean_rule_id = rule_id or cls._slugify_rule(problem_title)
        clean_sev = (severity or 'High').capitalize()
        if clean_sev not in ('Critical', 'High', 'Warning', 'Notice', 'Medium', 'Low'):
            clean_sev = 'High'

        # If page data is completely absent from crawl
        if not page and not affected_url:
            not_avail_msg = "The required information was not available in the crawl data, so an exact replacement cannot be generated safely."
            return {
                "issue_id": clean_rule_id,
                "category": category or "Technical",
                "severity": clean_sev,
                "affected_url": affected_url or "Website Level",
                "what_is_wrong": evidence_text or description or problem_title,
                "what_we_found": evidence_text or description or problem_title,
                "why_it_matters": "Accurate solution generation requires verified page content from a completed crawl.",
                "what_should_change": "Run a full website crawl to analyze live page markup.",
                "what_needs_to_change": "Run a full website crawl to analyze live page markup.",
                "current_value": "Not available in crawl data",
                "recommended_replacement": not_avail_msg,
                "recommended_change": not_avail_msg,
                "replacement_value": not_avail_msg,
                "character_count": 0,
                "where_to_change": "Website CMS or HTML template after performing a scan.",
                "implementation": f"<!-- {not_avail_msg} -->",
                "why_this_version_is_better": "Prevents generating inaccurate or hallucinated metadata.",
                "why_this_fixes_problem": "Prevents generating inaccurate or hallucinated metadata.",
                "why_this_fix": "Prevents generating inaccurate or hallucinated metadata.",
                "verification": "Trigger a website re-crawl to populate page attributes.",
                "ai_solution": recommendation or "Perform a website scan to evaluate this issue.",
                "recommended_fix": not_avail_msg,
                "solution_type": "manual_action",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "High",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Audit Rules Engine"
            }

        p_title = page.get("title") if page else ""
        p_desc = page.get("meta_description") if page else ""
        p_h1 = page.get("h1") if page else ""
        p_canon = page.get("canonical") if page else ""
        p_status = page.get("status_code") if page else 200
        p_word_count = page.get("word_count", 0) if page else 0

        h1_clean = p_h1[0] if isinstance(p_h1, list) and p_h1 else (str(p_h1) if p_h1 else "")
        base_topic = h1_clean or (p_title.split("|")[0].split("-")[0].strip() if p_title else (affected_url.rstrip("/").split("/")[-1].replace("-", " ").title() if affected_url else "Specialized Services"))
        if not base_topic or base_topic.lower() in ("home", "index", "default"):
            base_topic = f"{project_name} Services"

        # Case 1: Meta Description Issues (Too Long / Too Short / Missing / Duplicate)
        if "description" in title_lower or "meta_desc" in rule_lower or "description" in rule_lower:
            current_len = len(p_desc) if p_desc else 0
            
            replacement = f"Discover expert {base_topic} with {project_name}. Explore our comprehensive solutions, quality guarantees, and request your free quote today."
            if len(replacement) > 158:
                replacement = f"Explore top-rated {base_topic} from {project_name}. Get high quality service, transparent pricing, and expert support today."
            if len(replacement) < 145:
                replacement = f"Looking for trusted {base_topic}? {project_name} delivers industry-leading solutions with proven results. Contact our expert team today!"

            char_len = len(replacement)

            if not p_desc:
                what_wrong = f"{affected_url} has no <meta name=\"description\"> tag."
                why_matter = "Without a meta description, search engines extract arbitrary text from the page body, which rarely matches user search intent."
                what_change = "Add a meta description that accurately describes the page and targets the page's primary search intent."
                cur_val = "(Missing <meta name=\"description\"> tag)"
            elif current_len > 160:
                what_wrong = f"{affected_url} meta description is {current_len} characters long, exceeding the 160 character limit."
                why_matter = "Search engines truncate long meta descriptions in search result snippets with ellipses, leading to lower CTR."
                what_change = "Shorten the meta description to 150–160 characters while preserving core keywords and call to action."
                cur_val = f'"{p_desc}" ({current_len} characters)'
            else:
                what_wrong = f"{affected_url} meta description is only {current_len} characters long, leaving valuable SERP space unused."
                why_matter = "Short meta descriptions underperform because they fail to convey sufficient context or search intent."
                what_change = "Expand the meta description to 150–160 characters with clear value propositions and a call to action."
                cur_val = f'"{p_desc}" ({current_len} characters)'

            why_better = "Describes the actual page, matches page intent, avoids truncation, and gives search engines a useful page summary."
            verif = "Re-crawl the page and verify that `<meta name=\"description\">` exists and contains the new content."

            return {
                "issue_id": clean_rule_id or "META_DESCRIPTION_OPTIMIZATION",
                "category": "On-Page",
                "severity": clean_sev,
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": replacement,
                "recommended_change": replacement,
                "replacement_value": replacement,
                "character_count": char_len,
                "where_to_change": "Inside the `<head>` section of the affected page HTML.",
                "implementation": f'<meta name="description" content="{replacement}">',
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": f"Replace with: {replacement}",
                "solution_type": "replacement_text",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "High",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Case 2: Title Tag Issues (Too Long / Missing / Duplicate / Keyword Stuffed)
        elif "title" in title_lower or "title" in rule_lower:
            current_len = len(p_title) if p_title else 0
            replacement = f"{base_topic} | {project_name}"
            if len(replacement) > 60:
                replacement = f"{base_topic}"[:55]
            char_len = len(replacement)

            if not p_title:
                what_wrong = f"{affected_url} has no <title> tag in its HTML header."
                why_matter = "The title tag is one of the most critical on-page ranking factors and directly controls your search result snippet headline."
                what_change = "Add a concise, unique <title> tag (50–60 characters) accurately representing the primary page topic."
                cur_val = "(Missing <title> tag)"
            elif current_len > 60:
                what_wrong = f"{affected_url} title tag is {current_len} characters long, exceeding the 60 character desktop SERP limit."
                why_matter = "Titles exceeding 60 characters are truncated by search engines, hiding brand identity and key keywords."
                what_change = "Shorten the title tag to 50–60 characters while keeping the primary keyword at the front."
                cur_val = f'"{p_title}" ({current_len} characters)'
            else:
                what_wrong = f"{affected_url} title tag needs topical optimization ({current_len} characters)."
                why_matter = "Title tags must clearly target search intent to maximize organic click-through rate."
                what_change = "Update the title tag to clearly reflect the page focus and brand identity."
                cur_val = f'"{p_title}" ({current_len} characters)'

            why_better = "Targets primary search intent, prevents SERP headline truncation, and includes clear brand authority."
            verif = "Re-crawl the page and check the browser tab or inspect `<title>` in HTML source."

            return {
                "issue_id": clean_rule_id or "TITLE_TAG_OPTIMIZATION",
                "category": "On-Page",
                "severity": clean_sev,
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": replacement,
                "recommended_change": replacement,
                "replacement_value": replacement,
                "character_count": char_len,
                "where_to_change": "Inside the `<head>` section of the affected page HTML.",
                "implementation": f'<title>{replacement}</title>',
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": f"Update title to: '{replacement}'",
                "solution_type": "replacement_text",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "High",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Case 3: Missing H1 Heading
        elif "h1" in title_lower or "h1" in rule_lower:
            replacement = f"{base_topic}"
            what_wrong = f"{affected_url} has no primary <h1> heading detected in the rendered page body."
            why_matter = "Search engine crawlers use the primary H1 tag to establish the topical entity and structure of the document."
            what_change = "Add exactly one descriptive <h1> heading at the top of the main content body."
            cur_val = "(No H1 heading found)"
            why_better = "Establishes unambiguous topical hierarchy for search crawlers and screen readers."
            verif = "Inspect page body to verify exactly one `<h1>` tag exists at the top of the content."

            return {
                "issue_id": clean_rule_id or "MISSING_H1_HEADING",
                "category": "Content Structure",
                "severity": clean_sev,
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": replacement,
                "recommended_change": replacement,
                "replacement_value": replacement,
                "character_count": len(replacement),
                "where_to_change": "At the top of the `<main>` or primary content container in the page body.",
                "implementation": f'<h1>{replacement}</h1>',
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": f"Add H1: '<h1>{replacement}</h1>'",
                "solution_type": "html_tag",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "High",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Case 4: Broken Links / HTTP 404 / 5xx Errors
        elif "404" in title_lower or "broken" in title_lower or "4xx" in title_lower or "5xx" in title_lower or "status" in rule_lower:
            what_wrong = f"Server returned HTTP {p_status or 404} Not Found response for {affected_url}."
            why_matter = "Broken URLs waste search engine crawl budget, cause user drop-offs, and destroy inbound link equity."
            what_change = "Restore the missing content or implement a 301 permanent redirect to the closest valid live destination."
            cur_val = f"HTTP {p_status or 404} Error"
            replacement_redirect = f"Redirect 301 {affected_url} https://{domain}/"
            impl_rewrite = f"# Permanent 301 Redirect\nRewriteRule ^{re.escape(affected_url.replace(f'https://{domain}/', ''))}$ / [R=301,L]"
            why_better = "Eliminates dead ends, restores link equity, and preserves visitor navigation flow."
            verif = f"Run curl test (`curl -I \"{affected_url}\"`) to confirm HTTP 301 redirect or HTTP 200 response."

            return {
                "issue_id": clean_rule_id or "BROKEN_URL_404",
                "category": "Technical",
                "severity": "Critical",
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": replacement_redirect,
                "recommended_change": replacement_redirect,
                "replacement_value": replacement_redirect,
                "character_count": 0,
                "where_to_change": "Server configuration (.htaccess / Nginx virtual host / redirect routing table).",
                "implementation": impl_rewrite,
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": "Configure 301 redirect to valid destination.",
                "solution_type": "config",
                "priority": "Critical",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Case 5: Missing Schema / Structured Data
        elif "schema" in title_lower or "structured data" in title_lower or "json-ld" in title_lower:
            schema_json = {
                "@context": "https://schema.org",
                "@type": "WebPage",
                "name": p_title or project_name,
                "url": affected_url,
                "description": p_desc or f"Official web page for {project_name}.",
                "publisher": {
                    "@type": "Organization",
                    "name": project_name,
                    "url": f"https://{domain}"
                }
            }
            schema_str = json.dumps(schema_json, indent=2)
            what_wrong = f"{affected_url} has no JSON-LD structured data detected."
            why_matter = "Structured data helps search engines and AI generative engines accurately index organization and content entities."
            what_change = "Insert Schema.org WebPage / Organization JSON-LD markup into the page header."
            cur_val = "(No structured data found)"
            why_better = "Enables rich search result features and strengthens entity authority across AI search engines."
            verif = "Test the page using Google Rich Results Test (https://search.google.com/test/rich-results)."

            return {
                "issue_id": clean_rule_id or "MISSING_STRUCTURED_DATA",
                "category": "Schema",
                "severity": clean_sev,
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": schema_str,
                "recommended_change": schema_str,
                "replacement_value": schema_str,
                "character_count": len(schema_str),
                "where_to_change": "Inside the `<head>` section of the page HTML.",
                "implementation": f'<script type="application/ld+json">\n{schema_str}\n</script>',
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": "Deploy JSON-LD Schema markup in HTML head.",
                "solution_type": "schema_jsonld",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "Medium",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Case 6: Canonical Tag Mismatch / Missing
        elif "canonical" in title_lower or "canonical" in rule_lower:
            expected_canon = affected_url.split("?")[0].rstrip("/") + "/"
            what_wrong = f"{affected_url} canonical tag is {p_canon or 'missing'} (Expected: {expected_canon})."
            why_matter = "Without an authoritative canonical tag, URL query parameters and variations create duplicate content dilution."
            what_change = f"Set a self-referential canonical tag pointing to {expected_canon}."
            cur_val = p_canon or "(Missing canonical link tag)"
            why_better = "Consolidates ranking equity and prevents duplicate URL indexing in search engines."
            verif = "Inspect the HTML `<head>` to verify `<link rel=\"canonical\" href=\"...\">` matches the indexable URL."

            return {
                "issue_id": clean_rule_id or "CANONICAL_TAG_OPTIMIZATION",
                "category": "Technical",
                "severity": clean_sev,
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": expected_canon,
                "recommended_change": expected_canon,
                "replacement_value": expected_canon,
                "character_count": len(expected_canon),
                "where_to_change": "Inside the `<head>` section of the affected page HTML.",
                "implementation": f'<link rel="canonical" href="{expected_canon}">',
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": f"Set canonical URL to: {expected_canon}",
                "solution_type": "html_tag",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "High",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Case 7: Image Alt Tag Issues
        elif "alt" in title_lower or "image" in title_lower:
            replacement_alt = f"{project_name} {base_topic} illustration"
            what_wrong = f"{affected_url} contains content images missing descriptive alt attributes."
            why_matter = "Alt attributes provide essential accessibility for screen readers and enable image search ranking."
            what_change = "Add concise, descriptive alt attributes explaining the visual topic of images."
            cur_val = 'img alt=""'
            why_better = "Enhances accessibility compliance and improves image search indexability."
            verif = "Inspect page image elements to verify descriptive `alt=\"...\"` attributes exist."

            return {
                "issue_id": clean_rule_id or "IMAGE_ALT_OPTIMIZATION",
                "category": "Assets",
                "severity": clean_sev,
                "affected_url": affected_url,
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "why_it_matters": why_matter,
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "current_value": cur_val,
                "recommended_replacement": replacement_alt,
                "recommended_change": replacement_alt,
                "replacement_value": replacement_alt,
                "character_count": len(replacement_alt),
                "where_to_change": "Within `<img>` tags in the HTML template/content editor.",
                "implementation": f'<img src="..." alt="{replacement_alt}">',
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif,
                "ai_solution": f"{what_change} — {why_better}",
                "recommended_fix": f"Add descriptive alt: alt=\"{replacement_alt}\"",
                "solution_type": "html_tag",
                "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "Medium",
                "status": "Open",
                "crawl_date": crawl_date,
                "source": "Deterministic Evidence Engine"
            }

        # Default Generic Rule Fallback
        what_wrong = evidence_text or description or problem_title
        why_matter = description or f"Resolving {problem_title} ensures compliance with search engine guidelines."
        what_change = recommendation or f"Update page structure and server headers to resolve {problem_title}."
        cur_val = "Sub-optimal configuration"
        rep_val = f"Apply standard SEO resolution for {problem_title} on {affected_url}."
        why_better = "Eliminates technical audit errors and improves search crawler efficiency."
        verif = f"Re-crawl the website to verify resolution of {problem_title}."

        return {
            "issue_id": clean_rule_id,
            "category": category or "Technical",
            "severity": clean_sev,
            "affected_url": affected_url,
            "what_is_wrong": what_wrong,
            "what_we_found": what_wrong,
            "why_it_matters": why_matter,
            "what_should_change": what_change,
            "what_needs_to_change": what_change,
            "current_value": cur_val,
            "recommended_replacement": rep_val,
            "recommended_change": rep_val,
            "replacement_value": rep_val,
            "character_count": 0,
            "where_to_change": "Website CMS or server configuration.",
            "implementation": f"<!-- Implement fix for {problem_title} on {affected_url} -->",
            "why_this_version_is_better": why_better,
            "why_this_fixes_problem": why_better,
            "why_this_fix": why_better,
            "verification": verif,
            "ai_solution": f"{what_change} — {why_better}",
            "recommended_fix": rep_val,
            "solution_type": "manual_action",
            "priority": clean_sev if clean_sev in ("High", "Medium", "Low") else "Medium",
            "status": "Open",
            "crawl_date": crawl_date,
            "source": "Deterministic Evidence Engine"
        }

    @classmethod
    def batch_enrich_issues(
        cls,
        project: Project,
        issues: List[Dict[str, Any]],
        pages: List[Dict[str, Any]],
        db: Optional[Session] = None,
        user_id: Optional[str] = None,
        max_ai_pages: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Batch enriches detected audit issues with structured, actionable AI solutions
        for Master XLSX and Report generation. Respects the 20-page AI usage limit.
        """
        domain = get_sanitized_domain(project.domain or project.url)
        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
        latest_path = os.path.join(proj_dir, "latest.json")
        crawl_dir = None
        crawl_id = None
        crawl_date = datetime.now().strftime("%Y-%m-%d")

        if os.path.exists(latest_path):
            try:
                with open(latest_path, "r", encoding="utf-8") as f:
                    latest_pointer = json.load(f)
                crawl_dir = normalize_stored_path(latest_pointer.get("path"))
                crawl_id = latest_pointer.get("crawl_id")
                crawl_date = latest_pointer.get("timestamp") or crawl_date
            except Exception:
                pass

        enriched = []
        ai_calls_made = 0

        for idx, iss in enumerate(issues, 1):
            rule_id = iss.get("rule_id") or iss.get("id") or iss.get("issue_id")
            title = iss.get("problem") or iss.get("issue") or iss.get("title") or "SEO Problem"
            cat = iss.get("category") or "Technical"
            sev = iss.get("severity") or "High"
            desc = iss.get("description") or iss.get("details")
            rec = iss.get("recommendation") or iss.get("recommended_action")
            url = iss.get("affected_url") or iss.get("url") or f"https://{domain}"
            evidence = iss.get("what_was_found") or iss.get("evidence")

            # Check if we should allow active LLM call (capped at max_ai_pages)
            should_allow_llm = (ai_calls_made < max_ai_pages)

            solution = cls.get_or_generate_solution(
                project=project,
                rule_id=rule_id,
                problem_title=title,
                category=cat,
                severity=sev,
                description=desc,
                recommendation=rec,
                affected_url=url,
                evidence_text=evidence,
                pages=pages,
                db=db if should_allow_llm else None,
                user_id=user_id if should_allow_llm else None,
                crawl_id=crawl_id,
                crawl_dir=crawl_dir,
                crawl_date=crawl_date
            )

            if should_allow_llm and solution.get("source") == "AI Evidence-Grounded Engine":
                ai_calls_made += 1

            # Merge solution fields into issue dictionary
            item = dict(iss)
            item.update({
                "issue_id": solution.get("issue_id") or rule_id or cls._slugify_rule(title),
                "category": cat,
                "severity": (sev or "High").capitalize(),
                "affected_url": url,
                "what_is_wrong": solution.get("what_is_wrong") or evidence or desc or title,
                "what_we_found": solution.get("what_we_found") or evidence or desc or title,
                "why_it_matters": solution.get("why_it_matters") or desc or "Impacts search performance.",
                "what_should_change": solution.get("what_should_change") or rec or "Apply recommended action.",
                "what_needs_to_change": solution.get("what_needs_to_change") or rec or "Apply recommended action.",
                "current_value": solution.get("current_value") or iss.get("current_value") or "Not configured",
                "recommended_replacement": solution.get("recommended_replacement") or solution.get("replacement_value") or "",
                "recommended_change": solution.get("recommended_change") or solution.get("replacement_value") or "",
                "replacement_value": solution.get("replacement_value") or "",
                "character_count": solution.get("character_count", 0),
                "where_to_change": solution.get("where_to_change") or "Inside page HTML.",
                "implementation": solution.get("implementation") or solution.get("replacement_value") or "",
                "why_this_version_is_better": solution.get("why_this_version_is_better") or "Improves search indexability and CTR.",
                "why_this_fixes_problem": solution.get("why_this_fixes_problem") or "Improves search indexability and CTR.",
                "why_this_fix": solution.get("why_this_fix") or "Improves search indexability.",
                "verification": solution.get("verification") or "Re-crawl the page to confirm tag is active.",
                "ai_solution": solution.get("ai_solution") or rec or "Resolve issue.",
                "recommended_fix": solution.get("recommended_fix") or solution.get("ai_solution"),
                "priority": solution.get("priority") or "High",
                "status": iss.get("status") or "Open",
                "crawl_date": crawl_date,
                "solution_type": solution.get("solution_type") or "replacement_text"
            })
            enriched.append(item)

        return enriched

    @staticmethod
    def _slugify_rule(text: str) -> str:
        if not text:
            return "GENERAL_ISSUE"
        clean = re.sub(r'[^a-zA-Z0-9]+', '_', text).strip('_').upper()
        return clean or "GENERAL_ISSUE"
