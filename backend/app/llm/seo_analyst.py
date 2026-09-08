import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.llm.context_builder import LLMContextBuilder
from app.llm.provider import EvidenceReasoningProvider, get_llm_provider
from app.llm.llm_provider import LLMProvider, AIProviderException

SYSTEM_ANALYSIS_PROMPT = """You are an expert SEO Intelligence Analyst auditing website evidence.
Your job is to analyze real SEO data, find opportunities, prioritize work, and recommend actionable solutions based ONLY on available evidence.

AI WORKING GUIDELINES:
1. REAL DATA FIRST: You are an analyst, not the source of SEO data. The source of truth is crawler data, audit results, GSC, ranking providers, and user data.
2. NEVER FABRICATE DATA: Never invent rankings, search volume, traffic, CTR, impressions, backlinks, competitors, authority, difficulty, or scores. If data is missing, state 'Data unavailable'.
3. SEPARATE FACTS FROM SUGGESTIONS: Clearly distinguish measured SEO facts from AI suggestions. Label non-measured ideas as 'AI Suggested'.
4. EVIDENCE STRUCTURE: Every finding must state Issue, Evidence, Why it matters, Recommended Action, Priority, and Affected URL.
5. DETERMINISTIC ENGINE: Factual SEO checks (status codes, title tags, canonicals) come from the crawler engine. Explain them without altering factual results.
6. REAL KEYWORDS ONLY: Do not invent ranking positions or volume for keywords.
7. REAL COMPETITORS ONLY: Analyze real competitor domains from evidence only.
8. NO UNFOUNDED CAUSATION: State 'The metric changed after this event' rather than asserting causation without proof.
9. PRIORITIZATION: Classify issues logically as Critical, High, Medium, or Low based on business impact and technical severity.
10. ACTIONABLE SOLUTIONS: Provide concrete steps, target URLs, and suggested anchor text rather than generic advice.
11. SIMPLE LANGUAGE: Explain technical SEO simply: What is wrong? Why does it matter? What should I do?

Output MUST be valid JSON strictly adhering to the following schema:
{
  "summary": "High-level strategic analysis summary of the website SEO state",
  "findings": [
    {
      "finding": "Descriptive title of the finding",
      "category": "technical_seo | content_structure | content_quality | executive_summary",
      "severity": "Critical | High | Medium | Low",
      "confidence": 0.95,
      "evidence": [{"type": "affected_url | page_url | total_crawled", "value": "..."}],
      "impact": "Detailed explanation of business and search engine snippet impact",
      "recommendation": "Actionable fix recommendation",
      "affected_urls": ["url1", "url2"]
    }
  ],
  "actions": [
    {
      "priority": "Critical | High | Medium | Low",
      "title": "Action title",
      "description": "Step-by-step resolution path with target URLs and anchor recommendations"
    }
  ]
}
"""

SYSTEM_CHAT_PROMPT = """You are an AI SEO Assistant answering questions about a specific website project.

AI WORKING GUIDELINES:
1. Use ONLY the provided crawl context and project data.
2. Do NOT invent numbers, rankings, backlinks, search volume, or facts.
3. If data is missing or unmeasured, explicitly say: 'Data unavailable'.
4. Clearly label generated ideas or recommendations as 'AI Suggested'.
5. Avoid claiming causation without evidence.
6. Provide clear, simple explanations and actionable next steps.
"""

class SEOAnalystAgent:
    def __init__(self):
        self.context_builder = LLMContextBuilder()
        self.deterministic_engine = EvidenceReasoningProvider()

    def analyze_project(self, key: Optional[str] = None, domain: Optional[str] = None, user_id: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        target_key = key or domain
        context = self.context_builder.build_project_context(target_key, domain)
        
        if not context.get("has_data"):
            return {
                "status": "empty",
                "message": "No crawl data available to analyze.",
                "insights": []
            }

        # Check for active LLM Provider (user override or platform credentials)
        llm_provider = get_llm_provider(user_id, db)

        if not llm_provider:
            return {
                "status": "AI_TEMPORARILY_UNAVAILABLE",
                "provider": "none",
                "is_llm_generated": False,
                "message": "AI analysis is temporarily unavailable. Your deterministic SEO analysis is still available.",
                "summary": "AI analysis is temporarily unavailable. Your deterministic SEO analysis is still available.",
                "domain": domain,
                "crawl_id": context.get("crawl_id"),
                "timestamp": context.get("timestamp"),
                "total_pages_analyzed": context.get("pages_count"),
                "total_findings": 0,
                "insights": [],
                "actions": []
            }

        # Real External LLM API Call
        try:
            user_prompt = f"Analyze the following real SEO evidence snapshot for domain '{domain}':"
            llm_result = llm_provider.analyze(
                system_instructions=SYSTEM_ANALYSIS_PROMPT,
                user_prompt=user_prompt,
                context_data=context
            )

            findings = llm_result.get("findings", [])
            actions = llm_result.get("actions", [])
            summary = llm_result.get("summary", "")

            p_name = getattr(llm_provider, "__class__", {}).__name__.replace("ProviderAdapter", "").lower()
            return {
                "status": "AI_ANALYSIS_COMPLETE",
                "provider": p_name,
                "is_llm_generated": True,
                "provenance": {
                    "source_type": "ai_analysis",
                    "source_label": "AI Analysis",
                    "badge_text": "AI Analysis",
                    "provider_info": p_name,
                    "evidence_grounded": True
                },
                "domain": domain,
                "crawl_id": context.get("crawl_id"),
                "timestamp": context.get("timestamp"),
                "total_pages_analyzed": context.get("pages_count"),
                "summary": summary,
                "total_findings": len(findings),
                "insights": findings,
                "actions": actions
            }
        except AIProviderException:
            raise
        except Exception as e:
            raise AIProviderException(f"Failed to process AI analysis: {e}", status_code=502, code="LLM_EXECUTION_FAILED")

    def chat_with_data(self, query: str, key: Optional[str] = None, domain: Optional[str] = None, user_id: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        target_key = key or domain
        context = self.context_builder.build_project_context(target_key, domain)
        
        llm_provider = get_llm_provider(user_id, db)

        if not llm_provider:
            return {
                "status": "AI_TEMPORARILY_UNAVAILABLE",
                "provider": "none",
                "is_llm_generated": False,
                "query": query,
                "answer": "AI analysis is temporarily unavailable. Your deterministic SEO analysis is still available.",
                "context_used": {
                    "domain": domain,
                    "pages_analyzed": context.get("pages_count", 0),
                    "has_data": context.get("has_data", False)
                }
            }

        try:
            answer = llm_provider.chat(
                system_instructions=SYSTEM_CHAT_PROMPT,
                query=query,
                context_data=context
            )
            p_name = getattr(llm_provider, "__class__", {}).__name__.replace("ProviderAdapter", "").lower()
            return {
                "status": "SUCCESS",
                "provider": p_name,
                "is_llm_generated": True,
                "provenance": {
                    "source_type": "ai_analysis",
                    "source_label": "AI Analysis",
                    "badge_text": "AI Analysis",
                    "provider_info": p_name,
                    "evidence_grounded": True
                },
                "query": query,
                "answer": answer,
                "context_used": {
                    "domain": domain,
                    "pages_analyzed": context.get("pages_count", 0),
                    "has_data": context.get("has_data", False)
                }
            }
        except AIProviderException as e:
            if e.status_code == 401 or getattr(e, "code", "") == "AUTH_FAILED":
                return {
                    "status": "AI_TEMPORARILY_UNAVAILABLE",
                    "provider": "none",
                    "is_llm_generated": False,
                    "query": query,
                    "answer": "AI provider authentication is currently unavailable. Your deterministic SEO analysis is still available.",
                    "context_used": {
                        "domain": domain,
                        "pages_analyzed": context.get("pages_count", 0),
                        "has_data": context.get("has_data", False)
                    }
                }
            raise
