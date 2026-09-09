import os
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.competitor import Competitor
from app.models.keyword import Keyword
from app.config.settings import settings
from app.config.utils import get_sanitized_domain, normalize_stored_path, get_project_storage_dir
from app.services.audit_rules import evaluate_site_audit_rules
from app.services.opportunity_engine import generate_central_opportunities
from app.services.backlink_service import BacklinkDataService
from app.providers.nlp_keywords import NLPKeywordExtractor
from app.services.ai_solution_service import AISolutionService

nlp_extractor = NLPKeywordExtractor()

class MasterReportBuilder:
    """
    Authoritative, single-source-of-truth master report builder.
    Normalizes all factual crawl findings, deterministic audit evaluations,
    and AI recommendations into a unified MasterReport object for any website/project.
    """

    @classmethod
    def build_master_report(
        cls,
        project: Project,
        db: Session,
        user_id: str,
        allow_ai_generation: bool = False
    ) -> Dict[str, Any]:
        """
        Build the master report from stored crawl artifacts.

        allow_ai_generation=False (default):
            Report downloads are READ-ONLY with respect to AI generation.
            Already-persisted AI solutions are included if present in ai_solutions.json.
            No new LLM calls are made. No AI usage is charged.

        allow_ai_generation=True:
            Only set when the user explicitly requests AI enrichment via the
            dedicated AI-solution endpoint. Allows calling the LLM provider and
            recording AI page usage.
        """
        domain = get_sanitized_domain(project.domain or project.url)
        project_name = project.name or domain

        if not domain:
            return cls._build_empty_report(project, "Invalid project URL or domain.")

        proj_dir = get_project_storage_dir(settings.CRAWL_DATA_DIR, domain, project.id)
        latest_path = os.path.join(proj_dir, "latest.json")

        if not os.path.exists(latest_path):
            return cls._build_empty_report(
                project,
                "No completed crawl is available for this website. A Full Website Health Report cannot be generated until a completed crawl exists."
            )

        # 1. Load latest crawl artifacts
        try:
            with open(latest_path, "r", encoding="utf-8") as f:
                latest_pointer = json.load(f)
            crawl_dir = normalize_stored_path(latest_pointer.get("path"))

            meta_path = os.path.join(crawl_dir, "metadata.json")
            pages_path = os.path.join(crawl_dir, "pages.json")
            issues_path = os.path.join(crawl_dir, "issues.json")
            links_path = os.path.join(crawl_dir, "internal_links.json")
            ext_path = os.path.join(crawl_dir, "external_links.json")
            broken_path = os.path.join(crawl_dir, "broken_links.json")

            metadata = {}
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    metadata = json.load(f)

            pages = []
            if os.path.exists(pages_path):
                with open(pages_path, "r", encoding="utf-8") as f:
                    pages = json.load(f)

            raw_issues = []
            if os.path.exists(issues_path):
                with open(issues_path, "r", encoding="utf-8") as f:
                    raw_issues = json.load(f)

            internal_links = []
            if os.path.exists(links_path):
                with open(links_path, "r", encoding="utf-8") as f:
                    internal_links = json.load(f)

            outbound_links = []
            if os.path.exists(ext_path):
                with open(ext_path, "r", encoding="utf-8") as f:
                    outbound_links = json.load(f)

            broken_links = []
            if os.path.exists(broken_path):
                with open(broken_path, "r", encoding="utf-8") as f:
                    broken_links = json.load(f)

            crawl_id = metadata.get("crawl_id") or latest_pointer.get("crawl_id")
            crawl_timestamp = metadata.get("timestamp") or latest_pointer.get("timestamp") or datetime.now().strftime("%Y-%m-%d")
        except Exception as e:
            print(f"[MASTER REPORT ERROR] Failed to load latest crawl artifacts: {e}", flush=True)
            return cls._build_empty_report(project, f"Failed to read completed crawl data: {str(e)}")

        if not pages:
            return cls._build_empty_report(
                project,
                "No completed crawl is available for this website. A Full Website Health Report cannot be generated until a completed crawl exists."
            )

        # 2. Existing Deterministic Health Calculation
        audit_eval = evaluate_site_audit_rules(pages)
        health_score = audit_eval.get("health_score", 100)
        evaluated_issues = audit_eval.get("issues", raw_issues)

        # 3. Enrich issues with AI solutions.
        #    When allow_ai_generation=False (all download paths) we read-only:
        #    stored solutions from ai_solutions.json are attached; no LLM call is made.
        #    When allow_ai_generation=True (explicit user AI action) full generation occurs.
        enriched_issues = AISolutionService.batch_enrich_issues(
            project=project,
            issues=evaluated_issues,
            pages=pages,
            db=db if allow_ai_generation else None,
            user_id=user_id if allow_ai_generation else None,
            max_ai_pages=20 if allow_ai_generation else 0
        )

        # 4. Normalized Problems & Indicator System (🔴 Critical, 🟠 High, 🟡 Warning, 🔵 Informational)
        normalized_problems = cls._normalize_problems(enriched_issues, pages)

        # 4. Extract Keywords
        keywords = nlp_extractor.extract_content_keywords(pages)

        # 5. Central Opportunities Engine
        opportunities = generate_central_opportunities(audit_eval, keywords, pages)

        # 6. Historical Crawl Comparison (Scoped strictly to this project/domain)
        historical_comparison = cls._build_historical_comparison(proj_dir, latest_pointer, pages, evaluated_issues, health_score)

        # 7. Competitor Records from DB
        comp_records = db.query(Competitor).filter(Competitor.project_id == project.id).all() if db else []
        competitors = [{
            "name": c.name or c.domain,
            "domain": c.domain,
            "url": c.url or f"https://{c.domain}",
            "relevance": c.relevance_score or "High",
            "keyword_overlap": c.keyword_overlap or "Not Available",
            "search_appearances": c.search_appearances or "Not Available"
        } for c in comp_records]

        # 8. Inbound Backlinks & Outbound Links
        b_data = BacklinkDataService.get_project_backlink_data(project=project)
        inbound_backlinks = b_data.get("backlinks", [])
        if not outbound_links and b_data.get("outbound_links"):
            outbound_links = b_data.get("outbound_links")

        # 9. Business Context & Optimization Datasets
        business_context = cls._build_business_context(project, pages)
        aeo_data = cls._generate_aeo_data(pages, keywords, normalized_problems)
        geo_data = cls._generate_geo_data(domain, project_name, pages, keywords)

        # 10. AI Analysis Layer (Baseline deterministic assessment)
        ai_analysis = cls._build_ai_analysis(project_name, domain, health_score, len(pages), normalized_problems, opportunities, historical_comparison)

        # 11. AI Enrichment Pass.
        #    Only calls the LLM provider when allow_ai_generation=True.
        #    Report downloads pass allow_ai_generation=False so no LLM call fires here.
        if allow_ai_generation:
            cls._enrich_with_ai(
                normalized_problems=normalized_problems,
                ai_analysis=ai_analysis,
                project_name=project_name,
                domain=domain,
                health_score=health_score,
                pages_count=len(pages),
                business_context=business_context,
                user_id=user_id,
                db=db
            )

        # 12. Phased Improvement Roadmap (NOW, NEXT, 30-60, 60-90, ONGOING)
        next_improvements = cls._build_phased_roadmap(normalized_problems, opportunities, aeo_data, geo_data)

        # 13. Data Limitations (Explicitly documented, no zero penalties)
        data_limitations = [
            {
                "service": "Google Search Console API",
                "status": "Data Not Connected",
                "explanation": "Search performance impressions, CTR, and search queries require connecting your Google Search Console account in Settings -> Integrations."
            },
            {
                "service": "Inbound External Backlinks",
                "status": "Data Not Connected" if not inbound_backlinks else "Connected",
                "explanation": "An inbound backlink dataset is not currently connected. The website scan can identify links found on the website, but cannot discover external referring domains without a connected integration." if not inbound_backlinks else "Inbound backlinks actively imported."
            },
            {
                "service": "PageSpeed Performance API",
                "status": "Not Measured",
                "explanation": "Performance was not measured during this crawl. Core Web Vitals and lab diagnostics require connecting Google PageSpeed API."
            },
            {
                "service": "Search Rankings Tracking",
                "status": "Data Not Connected",
                "explanation": "Ranking data is not currently connected. Daily search position tracking requires configuring rank tracking in Settings."
            },
            {
                "service": "AI Citation Testing",
                "status": "Results Not Available",
                "explanation": "AI citation testing is configured but results are not yet available for this crawl."
            }
        ]

        # 14. Assemble Master Report Object
        return {
            "status": "COMPLETED",
            "project": {
                "id": project.id,
                "name": project_name,
                "domain": domain,
                "url": project.url or f"https://{domain}"
            },
            "business_context": business_context,
            "crawl": {
                "crawl_id": crawl_id,
                "timestamp": crawl_timestamp,
                "status": metadata.get("status", "completed"),
                "pages_crawled": len(pages),
                "successful_pages": sum(1 for p in pages if p.get("status_code") == 200),
                "failed_pages": sum(1 for p in pages if p.get("status_code") != 200),
                "has_crawl": True
            },
            "health": {
                "health_score": health_score,
                "summary": audit_eval.get("summary", {}),
                "category_breakdown": cls._build_category_breakdown(pages, evaluated_issues, health_score),
                "score_explanation": ai_analysis.get("health_score_explanation")
            },
            "checks": {
                "total_checks": len(pages) * 14,
                "evaluated_rules_count": 14,
                "analyzed_pages_count": len(pages),
                "rules_evaluated": [
                    "HTTP Server Status Code Resolution",
                    "Page Title Tag Existence & Length (30-60 chars)",
                    "Meta Description Tag Existence & Length (70-160 chars)",
                    "Primary H1 Heading Structure",
                    "Secondary H2 Heading Hierarchy",
                    "Content Length & Thin Content Check (>=300 words)",
                    "Canonical Link Tag Consistency",
                    "Search Engine Indexability & Robots Directives",
                    "Internal Broken Link Detection",
                    "Outbound Broken Link Detection",
                    "Image Alt Attribute Completeness",
                    "URL Hierarchy & Trailing Slash Consistency",
                    "Structured Data & OpenGraph Metadata",
                    "Security & HTTPS Protocol Consistency"
                ]
            },
            "problems": normalized_problems,
            "affected_pages": pages,
            "technical_seo": cls._build_technical_seo_summary(pages, normalized_problems),
            "on_page_seo": cls._build_on_page_seo_summary(pages, normalized_problems),
            "local_seo": {
                "status": "Not Connected",
                "message": "Local SEO data is not currently connected. Connect Google Business Profile in Settings to view local citation metrics.",
                "records": []
            },
            "content_and_links": {
                "internal_links": internal_links,
                "outbound_links": outbound_links,
                "broken_links": broken_links,
                "internal_links_count": len(internal_links),
                "outbound_links_count": len(outbound_links),
                "broken_links_count": len(broken_links),
                "internal_broken_links_count": sum(1 for b in broken_links if b.get("link_type") == "internal"),
                "external_broken_links_count": sum(1 for b in broken_links if b.get("link_type") == "external")
            },
            "keywords": keywords,
            "rankings": {
                "status": "Not Connected",
                "message": "Ranking data is not currently connected.",
                "records": []
            },
            "backlinks": {
                "status": "Connected" if inbound_backlinks else "Not Connected",
                "message": "Inbound backlinks available." if inbound_backlinks else "No inbound backlink dataset is connected.",
                "inbound_backlinks": inbound_backlinks,
                "outbound_links": outbound_links
            },
            "opportunities": opportunities,
            "aeo": aeo_data,
            "geo": geo_data,
            "ai_citations": {
                "status": "Not Available",
                "message": "AI citation testing is configured but results are not yet available for this crawl.",
                "records": []
            },
            "competitors": competitors,
            "historical_comparison": historical_comparison,
            "next_improvements": next_improvements,
            "data_limitations": data_limitations,
            "ai_analysis": ai_analysis
        }

    @classmethod
    def _normalize_problems(cls, issues: List[Dict[str, Any]], pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized = []
        for idx, iss in enumerate(issues, 1):
            raw_sev = str(iss.get("severity", "Notice")).capitalize()
            
            # Problem Indicator System
            if raw_sev in ("Critical", "Fatal"):
                indicator = "🔴"
                clean_sev = "Critical"
            elif raw_sev in ("High", "Error"):
                indicator = "🟠"
                clean_sev = "High"
            elif raw_sev in ("Warning", "Medium"):
                indicator = "🟡"
                clean_sev = "Warning"
            else:
                indicator = "🔵"
                clean_sev = "Informational"

            issue_id = iss.get("issue_id") or iss.get("rule_id") or f"RULE_{idx}"
            issue_name = iss.get("issue") or iss.get("title") or iss.get("problem") or "SEO Problem"
            url = iss.get("url") or iss.get("affected_url") or "Website Level"
            evidence = iss.get("what_was_found") or iss.get("evidence") or iss.get("details") or iss.get("description") or "Observed in crawl data"
            rec = iss.get("recommendation") or iss.get("recommended_action") or f"Resolve {issue_name} on {url}"
            ai_sol = iss.get("ai_solution") or cls._generate_default_ai_solution(issue_name, url, evidence, pages)
            rec_fix = iss.get("recommended_fix") or ai_sol
            rep_val = iss.get("replacement_value") or iss.get("suggested_change") or ""
            char_count = iss.get("character_count", len(rep_val) if isinstance(rep_val, str) else 0)
            impl = iss.get("implementation") or rep_val or ""
            why_fix = iss.get("why_this_fix") or cls._explain_why_it_matters(issue_name)
            prio = iss.get("priority") or clean_sev
            crawl_dt = iss.get("crawl_date") or datetime.now().strftime("%Y-%m-%d")
            status_val = iss.get("status") or "Open"

            what_wrong = iss.get("what_is_wrong") or evidence
            what_change = iss.get("what_should_change") or iss.get("what_needs_to_change") or rec
            where_change = iss.get("where_to_change") or "Inside page HTML or server configuration."
            why_better = iss.get("why_this_version_is_better") or iss.get("why_this_fixes_problem") or why_fix
            verif_steps = iss.get("verification") or f"Re-crawl the website to verify resolution of {issue_name}."

            normalized.append({
                "id": f"prob_{idx}",
                "issue_id": issue_id,
                "problem": issue_name,
                "severity": clean_sev,
                "indicator": indicator,
                "category": iss.get("category") or ("Technical" if "status" in issue_name.lower() or "404" in issue_name else "On-Page"),
                "affected_url": url,
                "affected_pages_count": iss.get("affected_pages_count", 1),
                "what_is_wrong": what_wrong,
                "what_we_found": what_wrong,
                "what_was_found": what_wrong,
                "current_value": iss.get("current_value") or ("Non-200 Status Code" if "404" in issue_name else "Empty / Incomplete"),
                "expected_value": iss.get("expected_value") or ("HTTP 200 OK" if "404" in issue_name else "Unique, complete metadata"),
                "evidence": evidence,
                "why_it_matters": cls._explain_why_it_matters(issue_name),
                "what_should_change": what_change,
                "what_needs_to_change": what_change,
                "recommended_action": rec,
                "ai_solution": ai_sol,
                "recommended_fix": rec_fix,
                "recommended_replacement": rep_val,
                "recommended_change": rep_val,
                "replacement_value": rep_val,
                "character_count": char_count,
                "where_to_change": where_change,
                "implementation": impl,
                "why_this_version_is_better": why_better,
                "why_this_fixes_problem": why_better,
                "why_this_fix": why_better,
                "verification": verif_steps,
                "priority": prio,
                "crawl_date": crawl_dt,
                "status": status_val,
                "suggested_change": rep_val or ai_sol,
                "future_improvement": iss.get("future_improvement") or cls._suggest_future_prevention(issue_name),
                "source": iss.get("source") or "Automatic Website Check + AI Analysis"
            })
        return normalized

    @staticmethod
    def _explain_why_it_matters(issue_name: str) -> str:
        name_lower = issue_name.lower()
        if "404" in name_lower or "broken" in name_lower:
            return "Broken URLs prevent search engines from indexing content and deliver a poor user experience, leading to lost traffic."
        if "title" in name_lower:
            return "The title tag is one of the most critical on-page ranking factors and directly controls your search result snippet headline."
        if "meta description" in name_lower:
            return "Search engines display meta descriptions in search results; compelling descriptions significantly increase click-through rates (CTR)."
        if "h1" in name_lower:
            return "The primary H1 heading informs search engine crawlers of the core topic and primary search intent of the page."
        if "thin content" in name_lower or "word count" in name_lower:
            return "Pages with fewer than 300 words often struggle to rank because search algorithms view them as having insufficient depth."
        return "Resolving this issue ensures search engines can fully crawl, interpret, and rank your pages accurately."

    @staticmethod
    def _suggest_future_prevention(issue_name: str) -> str:
        name_lower = issue_name.lower()
        if "404" in name_lower or "broken" in name_lower:
            return "Implement automated redirect mapping rules and verify link targets prior to updating site architecture."
        if "title" in name_lower or "meta" in name_lower:
            return "Add a content publishing checklist requiring unique title and meta description fields before publishing pages."
        if "h1" in name_lower:
            return "Enforce CMS template validation requiring exactly one primary H1 heading per template."
        if "thin content" in name_lower:
            return "Set editorial guidelines ensuring all informational landing pages contain at least 400 words of original content."
        return "Schedule regular automated weekly website scans to detect and resolve regressions immediately."

    @classmethod
    def _generate_default_ai_solution(cls, issue_name: str, url: str, evidence: str, pages: List[Dict[str, Any]]) -> str:
        name_lower = issue_name.lower()
        matching_page = next((p for p in pages if p.get("url") == url), None)
        
        if "title" in name_lower:
            if matching_page and matching_page.get("h1"):
                return f"Set title tag to: '{matching_page.get('h1')} | Professional Services' (Target length: 50 characters)."
            return "Write a unique, concise title tag (30-60 characters) incorporating the primary search keyword for this page."

        if "meta description" in name_lower:
            if matching_page and matching_page.get("word_count", 0) > 100:
                title = matching_page.get("title") or "our services"
                return f"Add description: 'Discover expert solutions with {title}. Explore our high quality services, client reviews, and get a quote today.'"
            return "Additional page content is required before a complete replacement can be safely recommended. Add a unique 120-155 character description."

        if "h1" in name_lower:
            if matching_page and matching_page.get("title"):
                clean_title = matching_page.get("title").split("|")[0].split("-")[0].strip()
                return f"Add primary H1 heading: '<h1>{clean_title}</h1>'."
            return "Add a single, descriptive H1 heading at the top of the page clearly stating the primary topic."

        if "404" in name_lower or "broken" in name_lower:
            return f"Implement a 301 Permanent Redirect pointing {url} to the most relevant live category or home page."

        return f"Apply standard SEO best practices to resolve {issue_name}."

    @classmethod
    def _build_category_breakdown(cls, pages: List[Dict[str, Any]], issues: List[Dict[str, Any]], overall_score: int) -> List[Dict[str, Any]]:
        crit_count = sum(1 for i in issues if i.get("severity") in ("Critical", "Fatal"))
        high_count = sum(1 for i in issues if i.get("severity") in ("High", "Error"))
        warn_count = sum(1 for i in issues if i.get("severity") in ("Warning", "Medium"))

        return [
            {
                "category": "Crawlability & Technical Access",
                "status": "Passed" if crit_count == 0 else "Needs Attention",
                "issues_count": crit_count,
                "impact": "Search engine bots can access and index pages.",
                "source": "Automatic Website Check"
            },
            {
                "category": "Technical SEO & HTTP Headers",
                "status": "Passed" if high_count == 0 else "Needs Attention",
                "issues_count": high_count,
                "impact": "Server response codes, redirects, and canonical tags.",
                "source": "Automatic Website Check"
            },
            {
                "category": "Page Content & Metadata",
                "status": "Passed" if warn_count == 0 else "Needs Attention",
                "issues_count": warn_count,
                "impact": "Title tags, meta descriptions, and heading hierarchy.",
                "source": "Automatic Website Check"
            },
            {
                "category": "Internal Links Structure",
                "status": "Audited",
                "issues_count": 0,
                "impact": "Page interconnectivity and anchor text distribution.",
                "source": "Automatic Website Check"
            },
            {
                "category": "PageSpeed Performance",
                "status": "Not Measured",
                "issues_count": 0,
                "impact": "Page load speed was not measured during this crawl.",
                "source": "Data Not Connected"
            },
            {
                "category": "Inbound Backlinks",
                "status": "Not Measured",
                "issues_count": 0,
                "impact": "External referring backlink profiles not connected.",
                "source": "Data Not Connected"
            }
        ]

    @classmethod
    def _build_technical_seo_summary(cls, pages: List[Dict[str, Any]], problems: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "total_urls": len(pages),
            "status_200_urls": sum(1 for p in pages if p.get("status_code") == 200),
            "non_200_urls": sum(1 for p in pages if p.get("status_code") != 200),
            "indexable_urls": sum(1 for p in pages if p.get("status_code") == 200),
            "technical_issues": [p for p in problems if p.get("category") == "Technical"]
        }

    @classmethod
    def _build_on_page_seo_summary(cls, pages: List[Dict[str, Any]], problems: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "missing_titles_count": sum(1 for p in pages if not p.get("title") or p.get("title") == "(Missing Title)"),
            "missing_descriptions_count": sum(1 for p in pages if not p.get("meta_description") or p.get("meta_description") == "(Missing Meta Description)"),
            "missing_h1_count": sum(1 for p in pages if not p.get("h1") or p.get("h1") == "(Missing H1)"),
            "thin_content_count": sum(1 for p in pages if p.get("word_count", 0) < 300),
            "on_page_issues": [p for p in problems if p.get("category") == "On-Page"]
        }

    @classmethod
    def _generate_aeo_data(cls, pages: List[Dict[str, Any]], keywords: List[Dict[str, Any]], problems: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        aeo = []
        for kw in keywords[:6]:
            aeo.append({
                "topic": kw.get("keyword"),
                "opportunity_type": "Direct Answer & FAQ Schema",
                "recommended_action": f"Add an FAQ section answering 'What is {kw.get('keyword')} and how does it work?' with FAQPage JSON-LD schema.",
                "evidence": f"Keyword '{kw.get('keyword')}' appears {kw.get('frequency', 1)} times in page content.",
                "priority": "High"
            })
        if not aeo:
            aeo.append({
                "topic": "General FAQ Schema",
                "opportunity_type": "Structured FAQ",
                "recommended_action": "Add structured FAQ schema markup on core service pages to capture search snippet real estate.",
                "evidence": "Observed site structure",
                "priority": "Medium"
            })
        return aeo

    @classmethod
    def _generate_geo_data(cls, domain: str, project_name: str, pages: List[Dict[str, Any]], keywords: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "area": "Authoritative Brand Mentions",
                "recommendation": f"Ensure {project_name} entity definitions, address, and core services are consistent across all landing pages.",
                "evidence": f"Audited {len(pages)} pages on {domain}",
                "priority": "High"
            },
            {
                "area": "Quotable Statistics & Data Tables",
                "recommendation": "Add structured summary comparison tables and factual data points to increase Generative AI engine citation probability.",
                "evidence": "Content density analysis",
                "priority": "Medium"
            },
            {
                "area": "Entity Consistency",
                "recommendation": "Maintain consistent Organization and LocalBusiness schema properties across headers and footers.",
                "evidence": "Site-wide template structure",
                "priority": "Medium"
            }
        ]

    @classmethod
    def _build_historical_comparison(
        cls,
        proj_dir: str,
        latest_pointer: Dict[str, Any],
        current_pages: List[Dict[str, Any]],
        current_issues: List[Dict[str, Any]],
        current_score: int
    ) -> Dict[str, Any]:
        crawls_dir = os.path.join(proj_dir, "crawls")
        if not os.path.exists(crawls_dir):
            return {
                "has_previous_crawl": False,
                "message": "Historical comparison is not available because no previous completed crawl exists."
            }

        crawl_folders = sorted(os.listdir(crawls_dir))
        if len(crawl_folders) < 2:
            return {
                "has_previous_crawl": False,
                "message": "Historical comparison is not available because no previous completed crawl exists."
            }

        prev_folder = crawl_folders[-2]
        prev_dir = os.path.join(crawls_dir, prev_folder)
        prev_meta_path = os.path.join(prev_dir, "metadata.json")
        prev_issues_path = os.path.join(prev_dir, "issues.json")
        prev_pages_path = os.path.join(prev_dir, "pages.json")

        def _safe_read_json(path, default):
            if not os.path.exists(path):
                return default
            try:
                with open(path, "r", encoding="utf-8") as _f:
                    return json.load(_f)
            except Exception:
                return default

        prev_issues = _safe_read_json(prev_issues_path, [])
        prev_pages = _safe_read_json(prev_pages_path, [])
        prev_meta = _safe_read_json(prev_meta_path, {})

        prev_score = evaluate_site_audit_rules(prev_pages).get("health_score", 100) if prev_pages else 100
        score_delta = current_score - prev_score

        current_issue_keys = {f"{i.get('issue')}__{i.get('url')}" for i in current_issues}
        prev_issue_keys = {f"{i.get('issue')}__{i.get('url')}" for i in prev_issues}

        fixed_count = len(prev_issue_keys - current_issue_keys)
        new_count = len(current_issue_keys - prev_issue_keys)
        remaining_count = len(current_issue_keys & prev_issue_keys)

        return {
            "has_previous_crawl": True,
            "previous_crawl_date": prev_meta.get("timestamp") or prev_folder,
            "previous_score": prev_score,
            "current_score": current_score,
            "score_delta": score_delta,
            "problems_fixed_count": fixed_count,
            "new_problems_count": new_count,
            "remaining_problems_count": remaining_count,
            "previous_pages_count": len(prev_pages),
            "current_pages_count": len(current_pages),
            "ai_trend_summary": f"Health score changed by {score_delta:+d} points. {fixed_count} previous problems were resolved, and {new_count} new findings were detected."
        }

    @classmethod
    def _build_business_context(cls, project: Project, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Builds rich business context from Project model and crawl metadata.
        Uses configured industry, services, service areas, notes.
        Falls back to inferring core topics from crawled page titles/H1s without fabricating unverified services.
        """
        domain = get_sanitized_domain(project.domain or project.url) if project else ""
        brand_name = (project.name if project and project.name else domain) or "Website"

        industry = (getattr(project, "industry", None) or "").strip()
        services_str = (getattr(project, "services", None) or "").strip()
        service_areas_str = (getattr(project, "service_areas", None) or getattr(project, "target_country", None) or "").strip()
        description = (getattr(project, "description", None) or "").strip()
        notes = (getattr(project, "notes", None) or "").strip()

        # If services are not configured, extract top topic keywords from page titles & H1s
        inferred_services = []
        if not services_str and pages:
            seen_topics = set()
            for p in pages:
                h1 = (p.get("h1") or "").strip()
                title = (p.get("title") or "").strip()
                for text in (h1, title):
                    if text:
                        cleaned = text.split("|")[0].split("-")[0].strip()
                        if len(cleaned) > 4 and cleaned.lower() not in seen_topics and len(seen_topics) < 8:
                            seen_topics.add(cleaned.lower())
                            inferred_services.append(cleaned)

        services_list = [s.strip() for s in services_str.split(",") if s.strip()] if services_str else inferred_services

        return {
            "brand_name": brand_name,
            "domain": domain,
            "industry": industry or "Website & Digital Services",
            "services": services_list,
            "service_areas": service_areas_str or ("Australia" if domain.endswith(".au") else "Global / Regional"),
            "description": description,
            "notes": notes,
            "target_country": getattr(project, "target_country", "United States"),
            "target_language": getattr(project, "target_language", "English")
        }

    @classmethod
    def _enrich_with_ai(
        cls,
        normalized_problems: List[Dict[str, Any]],
        ai_analysis: Dict[str, Any],
        project_name: str,
        domain: str,
        health_score: int,
        pages_count: int,
        business_context: Dict[str, Any],
        user_id: Optional[str],
        db: Optional[Session]
    ) -> None:
        """
        Enriches problems and executive analysis using active LLM provider (Groq/Gemini/Claude/OpenAI/Ollama).
        Batches problems together to minimize latency and API cost.
        Grounded strictly in crawl evidence & business context.
        Gracefully preserves deterministic template solutions if AI is unavailable or fails.
        """
        # Ensure default ai_generated is False
        for p in normalized_problems:
            p["ai_generated"] = False
        ai_analysis["ai_generated"] = False

        if not user_id or not db:
            return

        provider = None
        try:
            from app.llm.ai_service import AIService
            provider = AIService.get_provider(user_id=user_id, db=db)
        except Exception as e:
            print(f"[MASTER REPORT AI] Provider resolution error: {e}", flush=True)
            return

        if not provider:
            return

        # Prepare batch problem data (limit to first 30 to control prompt size & latency)
        problems_summary = []
        for p in normalized_problems[:30]:
            problems_summary.append({
                "id": p["id"],
                "problem": p["problem"],
                "severity": p["severity"],
                "category": p["category"],
                "affected_url": p["affected_url"],
                "evidence": p["what_was_found"],
                "current_value": p["current_value"],
                "expected_value": p["expected_value"]
            })

        crit_count = sum(1 for p in normalized_problems if p.get("severity") == "Critical")
        high_count = sum(1 for p in normalized_problems if p.get("severity") == "High")
        warn_count = sum(1 for p in normalized_problems if p.get("severity") == "Warning")

        sys_instructions = (
            "You are a Principal SEO Technical Architect and Advisor generating an authoritative Full Website Health Report. "
            "Your advice must be highly specific, professional, actionable, and strictly grounded in the provided crawl evidence "
            "and business context. "
            "RULES:\n"
            "1. NEVER invent HTTP status codes, fake ranking positions, fake backlinks, or services not in the business context.\n"
            "2. Tailor every ai_solution and future_improvement to the specific page URL, problem finding, and business niche.\n"
            "3. Reference real brand names, core services, and service locations from business_context where appropriate.\n"
            "4. Respond ONLY with a valid JSON object matching this exact schema:\n"
            "{\n"
            '  "executive_assessment": "Comprehensive 3-4 sentence executive overview referencing health score, problem severity counts, and specific business niche.",\n'
            '  "health_score_explanation": "2-3 sentence explanation of score deductions and highest-impact fixes.",\n'
            '  "problem_solutions": {\n'
            '     "prob_1": {\n'
            '        "ai_solution": "1-3 sentence specific fix grounded in the evidence",\n'
            '        "future_improvement": "1 sentence operational or template prevention rule"\n'
            '     }\n'
            '  }\n'
            "}"
        )

        user_prompt = (
            f"Website Domain: {domain}\n"
            f"Brand / Project Name: {project_name}\n"
            f"Business Context: {json.dumps(business_context)}\n"
            f"Audit Health Score: {health_score}/100\n"
            f"Audited Pages Count: {pages_count}\n"
            f"Problem Severity Counts: {crit_count} Critical, {high_count} High, {warn_count} Warning\n"
            f"Audited Problems List:\n{json.dumps(problems_summary, indent=2)}"
        )

        context_data = {
            "domain": domain,
            "project_name": project_name,
            "business_context": business_context,
            "health_score": health_score,
            "problems_count": len(normalized_problems)
        }

        try:
            ai_res = provider.analyze(sys_instructions, user_prompt, context_data, timeout=25.0)
            if isinstance(ai_res, dict):
                # Update executive assessment if provided
                if ai_res.get("executive_assessment"):
                    ai_analysis["executive_assessment"] = str(ai_res["executive_assessment"]).strip()
                    ai_analysis["ai_generated"] = True

                if ai_res.get("health_score_explanation"):
                    ai_analysis["health_score_explanation"] = str(ai_res["health_score_explanation"]).strip()
                    ai_analysis["ai_generated"] = True

                # Update problem solutions
                prob_sols = ai_res.get("problem_solutions")
                if isinstance(prob_sols, dict):
                    for p in normalized_problems:
                        pid = p.get("id")
                        if pid in prob_sols and isinstance(prob_sols[pid], dict):
                            item = prob_sols[pid]
                            if item.get("ai_solution"):
                                p["ai_solution"] = str(item["ai_solution"]).strip()
                                p["suggested_change"] = p["ai_solution"]
                                p["ai_generated"] = True
                            if item.get("future_improvement"):
                                p["future_improvement"] = str(item["future_improvement"]).strip()
                                p["ai_generated"] = True
        except Exception as err:
            print(f"[MASTER REPORT AI ENRICHMENT ERROR] {err}", flush=True)

    @classmethod
    def _build_ai_analysis(
        cls,
        project_name: str,
        domain: str,
        health_score: int,
        pages_count: int,
        problems: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]],
        historical: Dict[str, Any]
    ) -> Dict[str, Any]:
        crit_count = sum(1 for p in problems if p.get("severity") == "Critical")
        high_count = sum(1 for p in problems if p.get("severity") == "High")
        warn_count = sum(1 for p in problems if p.get("severity") == "Warning")

        if health_score >= 90:
            condition = "in excellent technical condition with strong foundation for search indexing"
        elif health_score >= 75:
            condition = "technically sound but constrained by metadata, content length, and on-page optimization issues"
        else:
            condition = "facing significant technical and on-page barriers requiring immediate remediation"

        executive_assessment = (
            f"The website for {project_name} ({domain}) is currently {condition}. "
            f"During the latest audit of {pages_count} HTML pages, the system evaluated all core rules and identified "
            f"{len(problems)} total problems ({crit_count} Critical, {high_count} High, {warn_count} Warning). "
            f"Prioritizing the highest-severity items will produce the fastest improvements in search engine visibility and user engagement."
        )

        health_score_explanation = (
            f"Your website scored {health_score} out of 100 based on verified crawl findings. "
            f"Deductions occurred due to {crit_count} critical technical errors, {high_count} high-priority metadata issues, "
            f"and {warn_count} content warnings. Categories not measured (PageSpeed and Inbound Backlinks) did not penalize your score."
        )

        return {
            "executive_assessment": executive_assessment,
            "health_score_explanation": health_score_explanation,
            "health_score": health_score,
            "confidence": "high",
            "ai_generated": False,
            "priority_action_plan": [
                "1. Resolve critical HTTP 404 broken pages and server errors",
                "2. Add unique 30-60 character meta titles to pages with missing or short titles",
                "3. Write compelling meta descriptions (120-155 characters) for core landing pages",
                "4. Expand thin content pages under 300 words with targeted keyword content",
                "5. Strengthen contextual internal link structure across core service categories"
            ]
        }

    @classmethod
    def _build_phased_roadmap(
        cls,
        problems: List[Dict[str, Any]],
        opportunities: List[Dict[str, Any]],
        aeo: List[Dict[str, Any]],
        geo: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        roadmap = []

        # Phase 1: NOW (0-7 Days)
        crit_probs = [p for p in problems if p.get("severity") in ("Critical", "High")]
        if crit_probs:
            roadmap.append({
                "timeframe": "NOW (0–7 DAYS)",
                "phase": "Critical Technical Fixes & Blockers",
                "action": f"Fix {len(crit_probs)} high-severity technical issues (broken URLs, status codes, and server errors).",
                "evidence": f"Found on {crit_probs[0].get('affected_url')}",
                "expected_benefit": "Restores full crawlability and prevents search engine indexing drop-offs."
            })
        else:
            roadmap.append({
                "timeframe": "NOW (0–7 DAYS)",
                "phase": "Critical Technical Fixes & Blockers",
                "action": "Maintain clean server response codes and verify no broken redirect chains exist.",
                "evidence": "Audit verified 100% 200 OK status codes",
                "expected_benefit": "Guarantees continuous accessibility for search crawlers."
            })

        # Phase 2: NEXT (8-30 Days)
        onpage_probs = [p for p in problems if p.get("category") == "On-Page"]
        roadmap.append({
            "timeframe": "NEXT (8–30 DAYS)",
            "phase": "On-Page Metadata & Heading Optimization",
            "action": f"Rewrite missing/short meta titles and descriptions across {len(onpage_probs) if onpage_probs else 'all'} audited pages.",
            "evidence": "Crawl metadata checks",
            "expected_benefit": "Improves organic search snippet relevance and increases click-through rates."
        })

        # Phase 3: 30-60 DAYS
        roadmap.append({
            "timeframe": "30–60 DAYS",
            "phase": "Content Expansion & Internal Linking",
            "action": "Upgrade thin pages with fewer than 300 words and add contextual anchor text internal links.",
            "evidence": "Word count & internal link distribution",
            "expected_benefit": "Boosts topical authority and distributes link equity across landing pages."
        })

        # Phase 4: 60-90 DAYS
        roadmap.append({
            "timeframe": "60–90 DAYS",
            "phase": "AEO, GEO & Structured Schema Authority",
            "action": "Implement FAQPage JSON-LD schema, direct-answer FAQ sections, and structured comparison tables.",
            "evidence": f"{len(aeo)} Answer Engine opportunities identified",
            "expected_benefit": "Increases eligibility for Google Featured Snippets, People Also Ask, and AI Overviews."
        })

        # Phase 5: ONGOING
        roadmap.append({
            "timeframe": "ONGOING",
            "phase": "Monitoring & Authority Growth",
            "action": "Run automated weekly crawls, track keyword position movements, and acquire relevant industry backlinks.",
            "evidence": "Continuous health tracking",
            "expected_benefit": "Prevents SEO regressions and compound organic search growth over time."
        })

        return roadmap

    @classmethod
    def _build_empty_report(cls, project: Project, message: str) -> Dict[str, Any]:
        domain = get_sanitized_domain(project.domain or project.url) if project else "unknown"
        return {
            "status": "NO_COMPLETED_CRAWL",
            "message": message,
            "project": {
                "id": project.id if project else "N/A",
                "name": project.name if project else "N/A",
                "domain": domain,
                "url": project.url if project else f"https://{domain}"
            },
            "crawl": {
                "crawl_id": None,
                "timestamp": datetime.now().strftime("%Y-%m-%d"),
                "status": "not_available",
                "pages_crawled": 0,
                "successful_pages": 0,
                "failed_pages": 0,
                "has_crawl": False
            },
            "health": {
                "health_score": None,
                "summary": {},
                "category_breakdown": [],
                "score_explanation": message
            },
            "checks": {
                "total_checks": 0,
                "evaluated_rules_count": 0,
                "analyzed_pages_count": 0,
                "rules_evaluated": []
            },
            "problems": [],
            "affected_pages": [],
            "technical_seo": {"total_urls": 0, "status_200_urls": 0, "non_200_urls": 0, "indexable_urls": 0, "technical_issues": []},
            "on_page_seo": {"missing_titles_count": 0, "missing_descriptions_count": 0, "missing_h1_count": 0, "thin_content_count": 0, "on_page_issues": []},
            "local_seo": {"status": "Not Connected", "message": "Local SEO data is not currently connected.", "records": []},
            "content_and_links": {"internal_links": [], "outbound_links": [], "internal_links_count": 0, "outbound_links_count": 0},
            "keywords": [],
            "rankings": {"status": "Not Connected", "message": "Ranking data is not currently connected.", "records": []},
            "backlinks": {"status": "Not Connected", "message": "No inbound backlink dataset is connected.", "inbound_backlinks": [], "outbound_links": []},
            "opportunities": [],
            "aeo": [],
            "geo": [],
            "ai_citations": {"status": "Not Available", "message": "AI citation testing is configured but results are not yet available for this crawl.", "records": []},
            "competitors": [],
            "historical_comparison": {"has_previous_crawl": False, "message": "Historical comparison is not available because no previous completed crawl exists."},
            "next_improvements": [],
            "data_limitations": [],
            "ai_analysis": {
                "executive_assessment": message,
                "health_score_explanation": message,
                "health_score": None,
                "confidence": "none",
                "priority_action_plan": []
            }
        }
