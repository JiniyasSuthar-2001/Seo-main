from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseCrawlerProvider(ABC):
    @abstractmethod
    async def crawl(self, start_url: str, max_pages: int = 100) -> Dict[str, Any]:
        pass

class BaseKeywordProvider(ABC):
    @abstractmethod
    def extract_content_keywords(self, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        pass

class BaseAutocompleteProvider(ABC):
    @abstractmethod
    def get_suggestions(self, query: str) -> List[str]:
        pass

class BaseSearchConsoleProvider(ABC):
    @abstractmethod
    def get_search_analytics(self, site_url: str, days: int = 30) -> List[Dict[str, Any]]:
        pass

class BasePageSpeedProvider(ABC):
    @abstractmethod
    def analyze_url(self, url: str, strategy: str = "mobile") -> Dict[str, Any]:
        pass

class BaseSERPProvider(ABC):
    @abstractmethod
    def check_rankings(self, keywords: List[str], domain: str) -> List[Dict[str, Any]]:
        pass

class BaseBacklinkProvider(ABC):
    @abstractmethod
    def get_backlinks(self, domain: str) -> List[Dict[str, Any]]:
        pass
