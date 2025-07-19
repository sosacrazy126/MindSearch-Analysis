"""State definitions for MindSearch LangGraph implementation."""

from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime


class SearchResult(TypedDict):
    """Individual search result structure."""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: datetime


class MindSearchState(TypedDict):
    """Main state for the MindSearch graph."""
    # Input
    query: str
    
    # Planning phase
    search_plan: List[str]
    sub_queries: List[str]
    
    # Search phase
    current_sub_query: int
    search_results: Dict[str, List[SearchResult]]
    raw_results: Dict[str, Any]
    
    # Synthesis phase
    final_answer: str
    references: Dict[int, str]
    confidence_score: float
    
    # Control flow
    max_searches: int
    searches_completed: int
    visit_count: Dict[str, int]
    
    # Error handling
    errors: List[str]
    retry_count: int