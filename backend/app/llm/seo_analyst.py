from typing import Dict, Any, List
from app.llm.context_builder import LLMContextBuilder
from app.llm.provider import get_llm_provider

class SEOAnalystAgent:
    def __init__(self):
        self.context_builder = LLMContextBuilder()
        self.provider = get_llm_provider()

    def analyze_project(self, domain: str) -> Dict[str, Any]:
        context = self.context_builder.build_project_context(domain)
        
        if not context.get("has_data"):
            return {
                "status": "empty",
                "message": "No crawl data available to analyze.",
                "insights": []
            }

        findings = self.provider.analyze(context)
        
        return {
            "status": "success",
            "domain": domain,
            "crawl_id": context.get("crawl_id"),
            "timestamp": context.get("timestamp"),
            "total_pages_analyzed": context.get("pages_count"),
            "total_findings": len(findings),
            "insights": findings
        }

    def chat_with_data(self, domain: str, query: str) -> Dict[str, Any]:
        context = self.context_builder.build_project_context(domain)
        answer = self.provider.chat(query, context)
        
        return {
            "query": query,
            "answer": answer,
            "context_used": {
                "domain": domain,
                "pages_analyzed": context.get("pages_count", 0),
                "has_data": context.get("has_data", False)
            }
        }
