import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.llm.context_builder import LLMContextBuilder
from app.llm.provider import EvidenceReasoningProvider, get_llm_provider
from app.llm.llm_provider import LLMProvider, AIProviderException

SYSTEM_ANALYSIS_PROMPT = """You are an expert SEO Intelligence Analyst auditing website evidence.
Your task is to analyze the provided SEO crawl metrics and findings and produce structured insights and action recommendations.

CRITICAL CONSTRAINTS:
1. You MUST NOT invent, guess, or modify any numerical data, HTTP status codes, page titles, or URLs not present in the evidence.
2. Every finding MUST cite exact evidence provided in the context.
3. If specific metrics or data are missing, state 'Data not available.'
4. Output MUST be valid JSON strictly adhering to the following schema:

{
  "summary": "High-level strategic analysis summary of the website SEO state",
  "findings": [
    {
      "finding": "Descriptive title of the finding",
      "category": "technical_seo | content_structure | content_quality | executive_summary",
      "severity": "Critical | Warning | Notice",
      "confidence": 0.95,
      "evidence": [{"type": "affected_url | page_url | total_crawled", "value": "..."}],
      "impact": "Detailed explanation of business and search engine indexing impact",
      "recommendation": "Actionable fix recommendation",
      "affected_urls": ["url1", "url2"]
    }
  ],
  "actions": [
    {
      "priority": "High | Medium | Low",
      "title": "Action title",
      "description": "Step-by-step resolution path"
    }
  ]
}
"""

SYSTEM_CHAT_PROMPT = """You are an AI SEO Assistant answering questions about a website audit.
Answer the user's question accurately using ONLY the provided crawl context.
Do NOT invent numbers, rankings, or facts not present in the context.
If the information is not in the context, explicitly say: 'Data not available in the latest crawl snapshot.'
"""

class SEOAnalystAgent:
    def __init__(self):
        self.context_builder = LLMContextBuilder()
        self.deterministic_engine = EvidenceReasoningProvider()

    def analyze_project(self, domain: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        context = self.context_builder.build_project_context(domain)
        
        if not context.get("has_data"):
            return {
                "status": "empty",
                "message": "No crawl data available to analyze.",
                "insights": []
            }

        # Check if real LLM Provider is configured for user
        llm_provider = get_llm_provider(user_id, db)

        if not llm_provider:
            # Deterministic evidence reasoning pass (AI Not Configured)
            deterministic_findings = self.deterministic_engine.analyze(context)
            return {
                "status": "AI_NOT_CONFIGURED",
                "provider": "none",
                "is_llm_generated": False,
                "message": "No active LLM provider configured. Configure OpenAI, Claude, or Gemini in Settings -> Integrations to enable real LLM analysis.",
                "domain": domain,
                "crawl_id": context.get("crawl_id"),
                "timestamp": context.get("timestamp"),
                "total_pages_analyzed": context.get("pages_count"),
                "total_findings": len(deterministic_findings),
                "insights": deterministic_findings
            }

        # Real External LLM API Call
        try:
            user_prompt = f"Analyze the following SEO evidence snapshot for domain '{domain}':"
            llm_result = llm_provider.analyze(
                system_instructions=SYSTEM_ANALYSIS_PROMPT,
                user_prompt=user_prompt,
                context_data=context
            )

            findings = llm_result.get("findings", [])
            actions = llm_result.get("actions", [])
            summary = llm_result.get("summary", "")

            return {
                "status": "AI_ANALYSIS_COMPLETE",
                "provider": getattr(llm_provider, "__class__", {}).__name__.replace("ProviderAdapter", "").lower(),
                "is_llm_generated": True,
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
            # Re-raise controlled application-level AI provider errors without falling back to fake LLM output
            raise
        except Exception as e:
            raise AIProviderException(f"Failed to process AI analysis: {e}", status_code=502, code="LLM_EXECUTION_FAILED")

    def chat_with_data(self, domain: str, query: str, user_id: Optional[str] = None, db: Optional[Session] = None) -> Dict[str, Any]:
        context = self.context_builder.build_project_context(domain)
        
        llm_provider = get_llm_provider(user_id, db)

        if not llm_provider:
            answer = self.deterministic_engine.chat(query, context)
            return {
                "status": "AI_NOT_CONFIGURED",
                "provider": "none",
                "is_llm_generated": False,
                "query": query,
                "answer": answer,
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
            return {
                "status": "SUCCESS",
                "provider": getattr(llm_provider, "__class__", {}).__name__.replace("ProviderAdapter", "").lower(),
                "is_llm_generated": True,
                "query": query,
                "answer": answer,
                "context_used": {
                    "domain": domain,
                    "pages_analyzed": context.get("pages_count", 0),
                    "has_data": context.get("has_data", False)
                }
            }
        except AIProviderException:
            raise
        except Exception as e:
            raise AIProviderException(f"Failed to process AI chat query: {e}", status_code=502, code="LLM_CHAT_FAILED")
