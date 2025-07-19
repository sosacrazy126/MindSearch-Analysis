"""LangGraph node implementations for MindSearch."""

import asyncio
from typing import Dict, Any
from datetime import datetime

from .state import MindSearchState
from .search_engines import SearchEngineManager
from .llm_utils import LLMManager


# Initialize shared resources
search_manager = SearchEngineManager()
llm_manager = LLMManager()


async def initialize_state(state: MindSearchState) -> MindSearchState:
    """Initialize the state with default values."""
    state["search_plan"] = []
    state["sub_queries"] = []
    state["current_sub_query"] = 0
    state["search_results"] = {}
    state["raw_results"] = {}
    state["final_answer"] = ""
    state["references"] = {}
    state["confidence_score"] = 0.0
    state["max_searches"] = state.get("max_searches", 10)
    state["searches_completed"] = 0
    state["visit_count"] = {}
    state["errors"] = []
    state["retry_count"] = 0
    
    return state


async def plan_search(state: MindSearchState) -> MindSearchState:
    """Decompose the query into sub-queries."""
    try:
        # Track node visits for loop prevention
        state["visit_count"]["plan_search"] = state["visit_count"].get("plan_search", 0) + 1
        
        # Decompose the query
        sub_queries = await llm_manager.decompose_query(state["query"])
        
        # Update state
        state["sub_queries"] = sub_queries
        state["search_plan"] = sub_queries.copy()
        
        print(f"Decomposed '{state['query']}' into {len(sub_queries)} sub-queries")
        
    except Exception as e:
        state["errors"].append(f"Error in plan_search: {str(e)}")
        # Fallback: use original query
        state["sub_queries"] = [state["query"]]
        state["search_plan"] = [state["query"]]
    
    return state


async def execute_searches(state: MindSearchState) -> MindSearchState:
    """Execute searches for all sub-queries in parallel."""
    try:
        # Track node visits
        state["visit_count"]["execute_searches"] = state["visit_count"].get("execute_searches", 0) + 1
        
        # Check if we've already searched
        if state["searches_completed"] > 0:
            return state
        
        # Execute all searches in parallel
        search_tasks = []
        for sub_query in state["sub_queries"]:
            if state["searches_completed"] >= state["max_searches"]:
                break
            search_tasks.append(search_manager.search(sub_query))
        
        # Wait for all searches to complete
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        # Process results
        for i, (sub_query, result) in enumerate(zip(state["sub_queries"], results)):
            if isinstance(result, Exception):
                state["errors"].append(f"Search error for '{sub_query}': {str(result)}")
                state["search_results"][sub_query] = []
            else:
                # Convert SearchResult TypedDict to regular dict for state storage
                state["search_results"][sub_query] = [
                    dict(r) for r in result
                ]
                state["searches_completed"] += 1
        
        print(f"Completed {state['searches_completed']} searches")
        
    except Exception as e:
        state["errors"].append(f"Error in execute_searches: {str(e)}")
    
    return state


async def synthesize_answer(state: MindSearchState) -> MindSearchState:
    """Synthesize the final answer from search results."""
    try:
        # Track node visits
        state["visit_count"]["synthesize_answer"] = state["visit_count"].get("synthesize_answer", 0) + 1
        
        # Check if we have any results to synthesize
        if not state["search_results"]:
            state["final_answer"] = "I couldn't find any information about your query."
            state["confidence_score"] = 0.0
            return state
        
        # Synthesize answer
        answer, references, confidence = await llm_manager.synthesize_answer(
            state["query"],
            state["search_results"]
        )
        
        # Update state
        state["final_answer"] = answer
        state["references"] = references
        state["confidence_score"] = confidence
        
        print(f"Synthesized answer with confidence: {confidence}")
        
    except Exception as e:
        state["errors"].append(f"Error in synthesize_answer: {str(e)}")
        # Fallback answer
        state["final_answer"] = "I found some information but encountered an error while synthesizing the answer."
        state["confidence_score"] = 0.1
    
    return state


async def error_handler(state: MindSearchState) -> MindSearchState:
    """Handle errors and retry logic."""
    if state["errors"] and state["retry_count"] < 3:
        state["retry_count"] += 1
        print(f"Retrying due to errors: {state['errors']}")
        # Clear errors for retry
        state["errors"] = []
        # Reset some state for retry
        state["searches_completed"] = 0
        state["search_results"] = {}
    
    return state


def should_retry(state: MindSearchState) -> str:
    """Determine if we should retry after an error."""
    if state["errors"] and state["retry_count"] < 3:
        return "retry"
    return "continue"


def has_search_results(state: MindSearchState) -> str:
    """Check if we have search results to synthesize."""
    if state["search_results"]:
        return "synthesize"
    elif state["retry_count"] < 3:
        return "retry"
    else:
        return "end"