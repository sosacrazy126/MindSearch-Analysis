"""Search Engine Abstraction Layer with Fallback Mechanisms."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import random

logger = logging.getLogger(__name__)


class SearchResult:
    """Standardized search result format."""
    
    def __init__(self, title: str, url: str, snippet: str, source: str = "unknown"):
        self.title = title
        self.url = url
        self.snippet = snippet
        self.source = source
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'url': self.url,
            'snippet': self.snippet,
            'source': self.source,
            'timestamp': self.timestamp.isoformat()
        }


class SearchEngineInterface(ABC):
    """Abstract interface for search engines."""
    
    def __init__(self, name: str):
        self.name = name
        self.is_available = True
        self.failure_count = 0
        self.max_failures = 3
    
    @abstractmethod
    async def _perform_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Implement the actual search logic."""
        pass
    
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search with error handling and availability checking."""
        if not self.is_available:
            logger.warning(f"{self.name} is currently unavailable")
            return []
        
        try:
            logger.info(f"{self.name}: Searching for '{query}'")
            results = await self._perform_search(query, max_results)
            self.failure_count = 0  # Reset on success
            return results
        except Exception as e:
            self.failure_count += 1
            logger.error(f"{self.name} search failed: {e}")
            
            if self.failure_count >= self.max_failures:
                self.is_available = False
                logger.error(f"{self.name} disabled after {self.max_failures} failures")
            
            return []
    
    def reset(self):
        """Reset the engine availability."""
        self.is_available = True
        self.failure_count = 0


class DuckDuckGoEngine(SearchEngineInterface):
    """DuckDuckGo search engine implementation."""
    
    def __init__(self):
        super().__init__("DuckDuckGo")
        self._ddg_search = None
    
    def _init_ddg(self):
        """Lazy initialization of DuckDuckGo search."""
        if self._ddg_search is None:
            try:
                from duckduckgo_search import DDGS
                self._ddg_search = DDGS()
            except ImportError:
                logger.error("duckduckgo_search not installed")
                self.is_available = False
    
    async def _perform_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform DuckDuckGo search."""
        self._init_ddg()
        
        if not self._ddg_search:
            return []
        
        # Run in executor to avoid blocking
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: list(self._ddg_search.text(query, max_results=max_results))
        )
        
        return [
            SearchResult(
                title=r.get('title', ''),
                url=r.get('link', ''),
                snippet=r.get('body', ''),
                source='duckduckgo'
            )
            for r in results
        ]


class GoogleSearchEngine(SearchEngineInterface):
    """Google Custom Search API implementation."""
    
    def __init__(self, api_key: Optional[str] = None, cx: Optional[str] = None):
        super().__init__("Google")
        self.api_key = api_key
        self.cx = cx  # Custom search engine ID
        
        if not api_key or not cx:
            logger.warning("Google Search API credentials not provided")
            self.is_available = False
    
    async def _perform_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Perform Google search using Custom Search API."""
        # This is a placeholder - implement actual Google API call
        logger.warning("Google Search not implemented - using mock results")
        return []


class MockSearchEngine(SearchEngineInterface):
    """Mock search engine for testing and fallback."""
    
    def __init__(self):
        super().__init__("MockSearch")
        self.mock_data = self._load_mock_data()
    
    def _load_mock_data(self) -> Dict[str, List[Dict]]:
        """Load predefined mock search results."""
        return {
            'weather': [
                {
                    'title': 'Weather Forecast - Local Weather Updates',
                    'url': 'https://weather.example.com',
                    'snippet': 'Get the latest weather forecast with temperature, humidity, and precipitation data.'
                },
                {
                    'title': 'National Weather Service',
                    'url': 'https://nws.example.com',
                    'snippet': 'Official weather forecasts and warnings from the National Weather Service.'
                }
            ],
            'news': [
                {
                    'title': 'Breaking News - Latest Updates',
                    'url': 'https://news.example.com',
                    'snippet': 'Stay updated with the latest breaking news from around the world.'
                },
                {
                    'title': 'Technology News Today',
                    'url': 'https://technews.example.com',
                    'snippet': 'Latest technology news, reviews, and analysis.'
                }
            ],
            'default': [
                {
                    'title': 'Search Result Example',
                    'url': 'https://example.com',
                    'snippet': 'This is a mock search result for testing purposes.'
                }
            ]
        }
    
    async def _perform_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Return mock search results based on query keywords."""
        query_lower = query.lower()
        
        # Check for known categories
        for category, results in self.mock_data.items():
            if category in query_lower:
                mock_results = results[:max_results]
                break
        else:
            # Use default results
            mock_results = self.mock_data['default'] * max_results
            mock_results = mock_results[:max_results]
        
        # Add some variation to make it more realistic
        search_results = []
        for i, result in enumerate(mock_results):
            search_results.append(SearchResult(
                title=f"{result['title']} - {query}",
                url=f"{result['url']}/search?q={query.replace(' ', '+')}",
                snippet=f"{result['snippet']} Related to: {query}",
                source='mock'
            ))
        
        # Simulate network delay
        await asyncio.sleep(random.uniform(0.1, 0.3))
        
        return search_results


class CachedSearchEngine(SearchEngineInterface):
    """Search engine with caching capabilities."""
    
    def __init__(self, base_engine: SearchEngineInterface, cache_ttl: int = 3600):
        super().__init__(f"Cached{base_engine.name}")
        self.base_engine = base_engine
        self.cache = {}
        self.cache_ttl = cache_ttl  # Cache time-to-live in seconds
    
    def _get_cache_key(self, query: str, max_results: int) -> str:
        """Generate cache key for query."""
        return f"{query}:{max_results}"
    
    def _is_cache_valid(self, timestamp: datetime) -> bool:
        """Check if cached result is still valid."""
        age = (datetime.now() - timestamp).total_seconds()
        return age < self.cache_ttl
    
    async def _perform_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search with caching."""
        cache_key = self._get_cache_key(query, max_results)
        
        # Check cache
        if cache_key in self.cache:
            cached_data = self.cache[cache_key]
            if self._is_cache_valid(cached_data['timestamp']):
                logger.info(f"Cache hit for query: '{query}'")
                return cached_data['results']
        
        # Perform actual search
        results = await self.base_engine.search(query, max_results)
        
        # Cache results
        if results:
            self.cache[cache_key] = {
                'results': results,
                'timestamp': datetime.now()
            }
        
        return results


class SearchEngineManager:
    """Manages multiple search engines with fallback capabilities."""
    
    def __init__(self):
        self.engines = []
        self._initialize_engines()
    
    def _initialize_engines(self):
        """Initialize available search engines."""
        # Primary engine
        self.engines.append(DuckDuckGoEngine())
        
        # Fallback engines
        # Google would be added here if API credentials are available
        # self.engines.append(GoogleSearchEngine(api_key, cx))
        
        # Always available mock engine as last resort
        self.engines.append(MockSearchEngine())
        
        logger.info(f"Initialized {len(self.engines)} search engines")
    
    def add_engine(self, engine: SearchEngineInterface):
        """Add a search engine to the manager."""
        self.engines.append(engine)
        logger.info(f"Added search engine: {engine.name}")
    
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using available engines with fallback."""
        for engine in self.engines:
            try:
                results = await engine.search(query, max_results)
                if results:
                    logger.info(f"Search successful with {engine.name}")
                    return results
            except Exception as e:
                logger.error(f"Unexpected error in {engine.name}: {e}")
                continue
        
        logger.error("All search engines failed")
        return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get status of all search engines."""
        return {
            engine.name: {
                'available': engine.is_available,
                'failure_count': engine.failure_count
            }
            for engine in self.engines
        }
    
    def reset_all(self):
        """Reset all search engines."""
        for engine in self.engines:
            engine.reset()
        logger.info("All search engines reset")


# Convenience function for creating a search manager with caching
def create_search_manager_with_cache(cache_ttl: int = 3600) -> SearchEngineManager:
    """Create a search manager with cached engines."""
    manager = SearchEngineManager()
    
    # Wrap primary engines with caching
    cached_engines = []
    for engine in manager.engines[:-1]:  # All except mock engine
        cached_engine = CachedSearchEngine(engine, cache_ttl)
        cached_engines.append(cached_engine)
    
    # Add mock engine without caching
    cached_engines.append(manager.engines[-1])
    
    # Replace engines with cached versions
    manager.engines = cached_engines
    
    return manager