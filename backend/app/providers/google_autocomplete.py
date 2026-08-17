import urllib.request
import urllib.parse
import json
from typing import List
from app.providers.base import BaseAutocompleteProvider

class GoogleAutocompleteProvider(BaseAutocompleteProvider):
    def get_suggestions(self, query: str) -> List[str]:
        if not query or not query.strip():
            return []

        encoded_q = urllib.parse.quote(query.strip())
        url = f"https://suggestqueries.google.com/complete/search?client=chrome&q={encoded_q}"
        
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )
        
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    if isinstance(data, list) and len(data) > 1:
                        return data[1]  # List of suggested search phrases
        except Exception as e:
            print(f"[AUTOCOMPLETE] Failed to fetch Google autocomplete for '{query}': {e}", flush=True)
            
        return []
