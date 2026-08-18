import os
import json
from typing import Dict, Any, List

class BaseLLMProvider:
    def analyze(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError
        
    def chat(self, query: str, context: Dict[str, Any]) -> str:
        raise NotImplementedError

class EvidenceReasoningProvider(BaseLLMProvider):
    """
    High-accuracy, offline-capable evidence reasoning engine.
    Parses exact context data to build structured findings with confidence scores
    and evidence links without hallucinating raw facts.
    """
    def analyze(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not context.get("has_data"):
            return []

        findings = []
        issues = context.get("issues_sample", [])
        pages = context.get("pages_sample", [])

        # 1. Technical Health Audit Finding
        critical_issues = [i for i in issues if i.get("severity") == "Critical"]
        if critical_issues:
            findings.append({
                "finding": f"Critical Technical SEO Vulnerabilities Detected ({len(critical_issues)} issues)",
                "category": "technical_seo",
                "severity": "Critical",
                "confidence": 0.98,
                "evidence": [
                    {"type": "affected_url", "value": i.get("affected_url")} for i in critical_issues[:3]
                ],
                "impact": "Critical status errors or missing titles directly prevent search engine indexing and harm keyword rankings.",
                "recommendation": "Fix status code errors and ensure every page renders a valid HTML <title> tag.",
                "affected_urls": [i.get("affected_url") for i in critical_issues[:5]]
            })

        # 2. Content & Heading Hierarchy Analysis
        missing_h1_pages = [p for p in pages if not p.get("h1")]
        if missing_h1_pages:
            findings.append({
                "finding": f"Structural Heading Hierarchy Deficit ({len(missing_h1_pages)} pages missing H1)",
                "category": "content_structure",
                "severity": "Warning",
                "confidence": 0.92,
                "evidence": [
                    {"type": "page_url", "value": p.get("url")} for p in missing_h1_pages[:3]
                ],
                "impact": "Search crawlers rely on H1 tags to understand primary page topics and index relevance.",
                "recommendation": "Add a single, target-keyword-aligned <h1> tag to each affected page.",
                "affected_urls": [p.get("url") for p in missing_h1_pages[:5]]
            })

        # 3. Thin Content Detection
        thin_pages = [p for p in pages if (p.get("word_count") or 0) < 150 and p.get("status_code") == 200]
        if thin_pages:
            findings.append({
                "finding": f"Thin Body Content Warning ({len(thin_pages)} pages below 150 words)",
                "category": "content_quality",
                "severity": "Notice",
                "confidence": 0.89,
                "evidence": [
                    {"type": "page_url", "value": p.get("url"), "word_count": p.get("word_count")} for p in thin_pages[:3]
                ],
                "impact": "Low text volume may result in search engines classifying pages as low quality.",
                "recommendation": "Expand body text to provide substantial value for visitors and search crawlers.",
                "affected_urls": [p.get("url") for p in thin_pages[:5]]
            })

        # 4. Overall Health Overview
        if not findings:
            findings.append({
                "finding": "Clean Technical & On-Page SEO Base",
                "category": "executive_summary",
                "severity": "Notice",
                "confidence": 0.95,
                "evidence": [{"type": "total_crawled", "value": context.get("pages_count")}],
                "impact": "No critical architectural flaws detected in the latest crawl snapshot.",
                "recommendation": "Focus on expanding content coverage and acquiring quality backlinks.",
                "affected_urls": []
            })

        return findings

    def chat(self, query: str, context: Dict[str, Any]) -> str:
        if not context.get("has_data"):
            return "No crawl dataset has been loaded for this project yet. Please run a website crawl first so I can analyze your evidence."

        q_lower = query.lower()
        pages = context.get("pages_sample", [])
        issues = context.get("issues_sample", [])
        domain = context.get("domain")

        if "critical" in q_lower or "issue" in q_lower or "problem" in q_lower or "error" in q_lower:
            criticals = [i for i in issues if i.get("severity") == "Critical"]
            warnings = [i for i in issues if i.get("severity") == "Warning"]
            if not issues:
                return f"Based on the latest crawl snapshot for **{domain}**, zero technical issues were detected across **{context.get('pages_count')}** pages."
            
            resp = f"Based on the crawl facts for **{domain}**, I detected **{len(issues)} total issue(s)** ({len(criticals)} Critical, {len(warnings)} Warnings):\n\n"
            for iss in issues[:5]:
                resp += f"- **[{iss.get('severity')}] {iss.get('issue_type')}**: `{iss.get('affected_url')}` — {iss.get('details')}\n"
            return resp

        if "page" in q_lower or "url" in q_lower or "crawl" in q_lower:
            resp = f"The latest crawl of **{domain}** successfully fetched **{context.get('pages_count')} page(s)**.\n\nSample crawled URLs:\n"
            for p in pages[:5]:
                resp += f"- `{p.get('url')}` (HTTP {p.get('status_code')}) — Title: *{p.get('title') or 'Missing'}*\n"
            return resp

        if "backlink" in q_lower or "link" in q_lower:
            return f"The crawler extracted **{context.get('links_sample_count', 0)} internal link relationships** across the website. *Note: External backlink tracking requires importing an external backlink CSV dataset.*"

        return f"I have analyzed the **{context.get('pages_count')} pages** and **{context.get('issues_count')} technical findings** from the latest crawl of **{domain}**. You can ask me about critical issues, page titles, internal link structure, or recommended fixes."

def get_llm_provider() -> BaseLLMProvider:
    return EvidenceReasoningProvider()
