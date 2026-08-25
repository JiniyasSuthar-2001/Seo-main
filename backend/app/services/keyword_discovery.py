import re
import math
from typing import Dict, Any, List, Optional
from collections import Counter
from sqlalchemy.orm import Session

from app.models.page import Page
from app.models.keyword import Keyword
from app.config.logger import get_logger

logger = get_logger(__name__)

# Stopwords list for clean keyword extraction
STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's",
    "her", "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm",
    "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't",
    "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours",
    "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there",
    "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", "weren't",
    "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's",
    "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours", "yourself",
    "yourselves", "home", "page", "website", "online", "welcome", "click", "here", "view", "more", "privacy", "policy"
}


class KeywordDiscoveryService:
    """
    Real Candidate Keyword Discovery Engine.
    Extracts candidate terms from actual crawled website page content (Titles, H1-H3, Meta tags).
    Classifies intent and topic relevance cleanly.
    Guarantees ALL AI/Extracted suggestions are labeled as 'AI Suggested'.
    Never fabricates search volume, CPC, or ranking positions.
    """

    @classmethod
    def discover_candidate_keywords(
        cls, 
        project_id: str, 
        db: Session, 
        limit: int = 30
    ) -> Dict[str, Any]:
        """
        Extracts candidate keywords directly from the project's crawled HTML pages.
        """
        pages = db.query(Page).filter(
            Page.project_id == project_id,
            Page.status_code == 200
        ).limit(100).all()

        if not pages:
            return {
                "project_id": project_id,
                "status": "NO_CRAWLED_PAGES",
                "message": "No crawled HTML pages found. Please run a website crawl to discover keyword candidates.",
                "candidate_keywords": []
            }

        candidate_counts = Counter()
        page_term_map = {}

        for page in pages:
            url_path = page.url or ""
            text_corpus = []

            if page.title:
                text_corpus.append(page.title.lower())
                text_corpus.append(page.title.lower()) # Double weight for Title

            if page.h1:
                text_corpus.append(page.h1.lower())
                text_corpus.append(page.h1.lower()) # Double weight for H1

            if page.meta_description:
                text_corpus.append(page.meta_description.lower())

            full_text = " ".join(text_corpus)
            words = re.findall(r'[a-zA-Z0-9]{3,}', full_text)
            filtered_words = [w for w in words if w not in STOPWORDS]

            # Extract 2-gram and 3-gram phrases
            phrases = []
            for i in range(len(filtered_words) - 1):
                phrase2 = f"{filtered_words[i]} {filtered_words[i+1]}"
                phrases.append(phrase2)
                if i < len(filtered_words) - 2:
                    phrase3 = f"{filtered_words[i]} {filtered_words[i+1]} {filtered_words[i+2]}"
                    phrases.append(phrase3)

            for term in phrases:
                candidate_counts[term] += 1
                if term not in page_term_map:
                    page_term_map[term] = page.url

        most_common = candidate_counts.most_common(limit)
        results = []

        for term, count in most_common:
            intent = cls._classify_intent(term)
            results.append({
                "keyword": term,
                "term_frequency": count,
                "associated_url": page_term_map.get(term, ""),
                "intent": intent,
                "is_ai_suggested": True,
                "source_label": "AI Suggested / Content Extracted",
                "ranking_position": None,  # Explicitly null - no fabricated ranking
                "search_volume": None      # Explicitly null - no fabricated volume
            })

        return {
            "project_id": project_id,
            "status": "SUCCESS",
            "total_candidates": len(results),
            "candidate_keywords": results
        }

    @classmethod
    def _classify_intent(cls, term: str) -> str:
        """Determines search intent based on phrase lexical signals."""
        t = term.lower()
        if any(w in t for w in ["buy", "price", "cost", "order", "quote", "pricing", "hire", "shop"]):
            return "Transactional"
        elif any(w in t for w in ["best", "top", "review", "vs", "comparison", "alternative"]):
            return "Commercial"
        elif any(w in t for w in ["login", "signin", "contact", "about", "support", "location", "address"]):
            return "Navigational"
        else:
            return "Informational"
