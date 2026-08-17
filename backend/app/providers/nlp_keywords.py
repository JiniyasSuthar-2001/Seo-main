import re
from collections import Counter
from typing import List, Dict, Any
from app.providers.base import BaseKeywordProvider

STOP_WORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by",
    "can", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing",
    "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't",
    "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself",
    "him", "himself", "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is",
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no",
    "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves",
    "out", "over", "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't",
    "so", "some", "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll",
    "we're", "we've", "were", "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd",
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves", "com", "http", "https", "www",
    "home", "page", "get", "contact", "us", "more", "view", "click", "read"
}

class NLPKeywordExtractor(BaseKeywordProvider):
    def extract_content_keywords(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        word_counter = Counter()
        bigram_counter = Counter()
        url_topic_map = {}

        for page in pages:
            url = page.get("url", "")
            title = page.get("title") or ""
            h1 = page.get("h1") or ""
            desc = page.get("meta_description") or ""

            combined_text = f"{title} {h1} {desc}".lower()
            tokens = [re.sub(r'[^a-z0-9]', '', word) for word in combined_text.split()]
            cleaned_tokens = [w for w in tokens if len(w) > 2 and w not in STOP_WORDS]

            for word in cleaned_tokens:
                word_counter[word] += 1

            for i in range(len(cleaned_tokens) - 1):
                bigram = f"{cleaned_tokens[i]} {cleaned_tokens[i+1]}"
                bigram_counter[bigram] += 1

            if cleaned_tokens:
                url_topic_map[url] = cleaned_tokens[:5]

        extracted_terms = []
        
        # 1. Single terms
        for word, count in word_counter.most_common(30):
            extracted_terms.append({
                "keyword": word.title(),
                "source": "Extracted Content Term",
                "type": "Single Term",
                "frequency": count,
                "pages_found": sum(1 for url, topics in url_topic_map.items() if word in topics)
            })

        # 2. Key phrases (Bigrams)
        for phrase, count in bigram_counter.most_common(20):
            extracted_terms.append({
                "keyword": phrase.title(),
                "source": "Extracted Key Phrase",
                "type": "2-Word Phrase",
                "frequency": count,
                "pages_found": sum(1 for url, topics in url_topic_map.items() if any(t in phrase for t in topics))
            })

        return sorted(extracted_terms, key=lambda x: x["frequency"], reverse=True)
