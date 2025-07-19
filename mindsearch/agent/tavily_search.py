"""
Tavily search integration for MindSearch.
"""
import os
from typing import List, Dict, Any, Optional, Union
from tavily import TavilyClient
from lagent.actions.base_action import BaseAction, ActionReturn
from lagent.schema import ActionStatusCode


class TavilySearch(BaseAction):
    """Tavily search action for MindSearch agent."""
    
    def __init__(self, 
                 api_key: Optional[str] = None,
                 search_depth: str = "basic",
                 include_answer: bool = True,
                 include_raw_content: bool = False,
                 max_results: int = 5,
                 include_domains: Optional[List[str]] = None,
                 exclude_domains: Optional[List[str]] = None):
        """Initialize Tavily search action.
        
        Args:
            api_key: Tavily API key. If None, will try to get from TAVILY_API_KEY env var
            search_depth: "basic" or "advanced" search depth
            include_answer: Whether to include AI-generated answer
            include_raw_content: Whether to include raw page content
            max_results: Maximum number of results to return
            include_domains: List of domains to include in search
            exclude_domains: List of domains to exclude from search
        """
        super().__init__()
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not self.api_key:
            raise ValueError("Tavily API key not provided. Set TAVILY_API_KEY environment variable or pass api_key parameter.")
        
        self.client = TavilyClient(api_key=self.api_key)
        self.search_depth = search_depth
        self.include_answer = include_answer
        self.include_raw_content = include_raw_content
        self.max_results = max_results
        self.include_domains = include_domains
        self.exclude_domains = exclude_domains
        
    @property
    def name(self) -> str:
        """Return the name of the action."""
        return "TavilySearch"
    
    def search(self, query: Union[str, List[str]]) -> ActionReturn:
        """Perform Tavily search.
        
        Args:
            query: Search query string or list of queries
            
        Returns:
            ActionReturn with search results
        """
        try:
            if isinstance(query, list):
                # Handle multiple queries
                all_results = []
                for q in query:
                    response = self.client.search(
                        query=q,
                        search_depth=self.search_depth,
                        include_answer=self.include_answer,
                        include_raw_content=self.include_raw_content,
                        max_results=self.max_results,
                        include_domains=self.include_domains,
                        exclude_domains=self.exclude_domains
                    )
                    all_results.append({
                        "query": q,
                        "results": response.get("results", []),
                        "answer": response.get("answer", "") if self.include_answer else None
                    })
                return ActionReturn(
                    status=ActionStatusCode.SUCCESS,
                    results=all_results
                )
            else:
                # Single query
                response = self.client.search(
                    query=query,
                    search_depth=self.search_depth,
                    include_answer=self.include_answer,
                    include_raw_content=self.include_raw_content,
                    max_results=self.max_results,
                    include_domains=self.include_domains,
                    exclude_domains=self.exclude_domains
                )
                return ActionReturn(
                    status=ActionStatusCode.SUCCESS,
                    results=response
                )
        except Exception as e:
            return ActionReturn(
                status=ActionStatusCode.API_ERROR,
                error=f"Tavily search failed: {str(e)}"
            )
    
    def select(self, index: List[int]) -> ActionReturn:
        """Select specific results by index (for compatibility with WebBrowser interface).
        
        Args:
            index: List of indices to select
            
        Returns:
            ActionReturn indicating this method is not implemented for Tavily
        """
        return ActionReturn(
            status=ActionStatusCode.API_ERROR,
            error="Select method not implemented for TavilySearch. Results are returned directly from search."
        )
    
    def __call__(self, query: Union[str, List[str]]) -> ActionReturn:
        """Make the action callable.
        
        Args:
            query: Search query string or list of queries
            
        Returns:
            ActionReturn with search results
        """
        return self.search(query)


class AsyncTavilySearch(TavilySearch):
    """Async version of TavilySearch for compatibility with AsyncMindSearchAgent."""
    
    async def search(self, query: Union[str, List[str]]) -> ActionReturn:
        """Async wrapper for search method."""
        # Tavily client doesn't have native async support yet,
        # so we'll run it in a thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, super().search, query)
    
    async def select(self, index: List[int]) -> ActionReturn:
        """Async wrapper for select method."""
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, super().select, index)
    
    async def __call__(self, query: Union[str, List[str]]) -> ActionReturn:
        """Make the action callable asynchronously."""
        return await self.search(query)