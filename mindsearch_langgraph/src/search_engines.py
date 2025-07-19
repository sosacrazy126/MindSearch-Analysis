"""Search engine implementations for MindSearch LangGraph."""

import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup
import json
from tenacity import retry, stop_after_attempt, wait_exponential

from .state import SearchResult


class SearchEngine:
    """Base search engine interface."""
    
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute a search query and return results."""
        raise NotImplementedError


class DuckDuckGoSearchEngine(SearchEngine):
    """DuckDuckGo search implementation."""
    
    def __init__(self):
        self.base_url = "https://api.duckduckgo.com/"
        
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using DuckDuckGo API."""
        async with aiohttp.ClientSession() as session:
            params = {
                'q': query,
                'format': 'json',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            try:
                async with session.get(self.base_url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_results(data, max_results)
                    else:
                        return []
            except Exception as e:
                print(f"Search error: {e}")
                return []
    
    def _parse_results(self, data: Dict[str, Any], max_results: int) -> List[SearchResult]:
        """Parse DuckDuckGo API response."""
        results = []
        
        # Parse instant answer if available
        if data.get('AbstractText'):
            results.append(SearchResult(
                title=data.get('Heading', 'DuckDuckGo Result'),
                url=data.get('AbstractURL', ''),
                snippet=data.get('AbstractText', ''),
                source='duckduckgo',
                timestamp=datetime.now()
            ))
        
        # Parse related topics
        for topic in data.get('RelatedTopics', [])[:max_results - len(results)]:
            if isinstance(topic, dict) and 'Text' in topic:
                results.append(SearchResult(
                    title=topic.get('Text', '').split(' - ')[0][:100],
                    url=topic.get('FirstURL', ''),
                    snippet=topic.get('Text', ''),
                    source='duckduckgo',
                    timestamp=datetime.now()
                ))
        
        return results[:max_results]


class MockSearchEngine(SearchEngine):
    """Mock search engine for testing."""
    
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Return mock search results."""
        await asyncio.sleep(0.1)  # Simulate network delay
        
        results = []
        for i in range(min(3, max_results)):
            results.append(SearchResult(
                title=f"Result {i+1} for: {query}",
                url=f"https://example.com/{query.replace(' ', '-')}/{i+1}",
                snippet=f"This is a mock search result for '{query}'. It contains relevant information about the topic.",
                source='mock',
                timestamp=datetime.now()
            ))
        
        return results


class SearchEngineManager:
    """Manages multiple search engines and aggregates results."""
    
    def __init__(self, engines: Optional[List[SearchEngine]] = None):
        self.engines = engines or [MockSearchEngine()]  # Default to mock for testing
        
    async def search(self, query: str, max_results_per_engine: int = 5) -> List[SearchResult]:
        """Search across all engines and aggregate results."""
        tasks = [engine.search(query, max_results_per_engine) for engine in self.engines]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten and filter out errors
        all_results = []
        for results in results_lists:
            if isinstance(results, list):
                all_results.extend(results)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result['url'] not in seen_urls:
                seen_urls.add(result['url'])
                unique_results.append(result)
        
        return unique_results