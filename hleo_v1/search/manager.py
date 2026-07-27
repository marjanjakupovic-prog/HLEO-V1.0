from typing import List

from search.bing import BingSearch
from search.searxng import SearXNGSearch
from search.deduplicator import URLDeduplicator
from search.websearch import WebSearch

class SearchManager:

    def __init__(self, brave_api_key: str = "", bing_api_key: str = ""):
        self.bing = BingSearch(bing_api_key)
        self.searxng = SearXNGSearch()
        self.deduplicator = URLDeduplicator()
        self.web = WebSearch()

    def search(self, query: str) -> List[str]:
        urls = []

        urls.extend(self.bing.search(query))
        urls.extend(self.searxng.search(query))
        urls.extend(self.web.search(query))
        
        return self.deduplicator.deduplicate(urls)