import re
from typing import List, Dict, Any
from collections import Counter

INTENT_PATTERNS = {
    "transactional": [r"\bbuy\b", r"\border\b", r"\bpricing\b", r"\bprice\b", r"\bdiscount\b", r"\bcoupon\b", r"\bcheckout\b", r"\bshop\b", r"\bstore\b"],
    "commercial": [r"\bbest\b", r"\btop\b", r"\breview\b", r"\breviews\b", r"\bvs\b", r"\bcompare\b", r"\bcomparison\b", r"\bfeatures\b"],
    "local": [r"\bnear me\b", r"\bsydney\b", r"\bmelbourne\b", r"\bbrisbane\b", r"\bperth\b", r"\badelaide\b", r"\bau\b", r"\blocal\b"],
    "navigational": [r"\blogin\b", r"\bsignin\b", r"\bcontact\b", r"\babout\b", r"\bportal\b", r"\bsupport\b", r"\bhelp\b"],
    "informational": [r"\bhow\b", r"\bwhat\b", r"\bwhy\b", r"\bguide\b", r"\btips\b", r"\btutorial\b", r"\bexamples\b", r"\bdefinition\b"]
}

def classify_search_intent(keyword_text: str) -> Dict[str, Any]:
    """
    Classifies search intent using deterministic keyword text analysis.
    Returns primary intent, confidence score, and explanation.
    """
    if not keyword_text:
        return {"intent": "Informational", "confidence": 0.5, "explanation": "Default classification for unassigned query"}

    text = keyword_text.lower().strip()

    for intent, patterns in INTENT_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, text):
                return {
                    "intent": intent.capitalize(),
                    "confidence": 0.90,
                    "explanation": f"Query contains intent marker matching '{intent}' rules."
                }

    return {
        "intent": "Informational",
        "confidence": 0.70,
        "explanation": "Query evaluated as general informational search intent."
    }

def detect_keyword_cannibalization(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Detects potential keyword cannibalization candidates when multiple pages target identical primary titles/keywords.
    """
    title_map: Dict[str, List[str]] = {}
    for p in pages:
        t = (p.get("title") or "").strip().lower()
        u = p.get("url")
        if t and len(t) > 5 and u:
            title_map.setdefault(t, []).append(u)

    cannibalization_issues = []
    for title, urls in title_map.items():
        if len(urls) > 1:
            cannibalization_issues.append({
                "title": title,
                "competing_urls_count": len(urls),
                "urls": urls
            })

    return cannibalization_issues
