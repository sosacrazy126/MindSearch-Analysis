"""Main MindSearch LangGraph implementation."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Optional
import os

from .state import MindSearchState
from .nodes import (
    initialize_state,
    plan_search,
    execute_searches,
    synthesize_answer,
    error_handler,
    should_retry,
    has_search_results
)


def create_mindsearch_graph(checkpointer: Optional[SqliteSaver] = None):
    """Create the MindSearch graph with all nodes and edges."""
    
    # Create the graph
    workflow = StateGraph(MindSearchState)
    
    # Add nodes
    workflow.add_node("initialize", initialize_state)
    workflow.add_node("plan_search", plan_search)
    workflow.add_node("execute_searches", execute_searches)
    workflow.add_node("synthesize_answer", synthesize_answer)
    workflow.add_node("error_handler", error_handler)
    
    # Define the flow
    workflow.set_entry_point("initialize")
    
    # Linear flow with error handling
    workflow.add_edge("initialize", "plan_search")
    workflow.add_edge("plan_search", "execute_searches")
    
    # After search, check if we have results
    workflow.add_conditional_edges(
        "execute_searches",
        has_search_results,
        {
            "synthesize": "synthesize_answer",
            "retry": "error_handler",
            "end": END
        }
    )
    
    # After synthesis, check for errors
    workflow.add_conditional_edges(
        "synthesize_answer",
        should_retry,
        {
            "retry": "error_handler",
            "continue": END
        }
    )
    
    # Error handler can retry the search
    workflow.add_edge("error_handler", "plan_search")
    
    # Compile the graph
    if checkpointer:
        return workflow.compile(checkpointer=checkpointer)
    else:
        return workflow.compile()


class MindSearchAgent:
    """High-level interface for MindSearch using LangGraph."""
    
    def __init__(self, use_memory: bool = False):
        """Initialize the MindSearch agent.
        
        Args:
            use_memory: If True, enables checkpointing for resumable searches
        """
        self.checkpointer = None
        if use_memory:
            # Use in-memory SQLite for checkpointing
            self.checkpointer = SqliteSaver.from_conn_string(":memory:")
        
        self.graph = create_mindsearch_graph(self.checkpointer)
    
    async def search(self, query: str, max_searches: int = 10) -> dict:
        """Execute a search query.
        
        Args:
            query: The search query
            max_searches: Maximum number of sub-searches to perform
            
        Returns:
            Dictionary containing the answer, references, and metadata
        """
        # Initial state
        initial_state = {
            "query": query,
            "max_searches": max_searches,
            "search_plan": [],
            "sub_queries": [],
            "current_sub_query": 0,
            "search_results": {},
            "raw_results": {},
            "final_answer": "",
            "references": {},
            "confidence_score": 0.0,
            "searches_completed": 0,
            "visit_count": {},
            "errors": [],
            "retry_count": 0
        }
        
        # Run the graph
        config = {"recursion_limit": 25}
        if self.checkpointer:
            config["configurable"] = {"thread_id": query}
        
        final_state = await self.graph.ainvoke(initial_state, config)
        
        # Return formatted result
        return {
            "answer": final_state.get("final_answer", "No answer generated"),
            "references": final_state.get("references", {}),
            "confidence": final_state.get("confidence_score", 0.0),
            "sub_queries": final_state.get("sub_queries", []),
            "errors": final_state.get("errors", []),
            "searches_completed": final_state.get("searches_completed", 0)
        }
    
    async def stream_search(self, query: str, max_searches: int = 10):
        """Stream search results as they're generated.
        
        Yields state updates as the search progresses.
        """
        initial_state = {
            "query": query,
            "max_searches": max_searches,
            "search_plan": [],
            "sub_queries": [],
            "current_sub_query": 0,
            "search_results": {},
            "raw_results": {},
            "final_answer": "",
            "references": {},
            "confidence_score": 0.0,
            "searches_completed": 0,
            "visit_count": {},
            "errors": [],
            "retry_count": 0
        }
        
        config = {"recursion_limit": 25}
        if self.checkpointer:
            config["configurable"] = {"thread_id": query}
        
        async for state in self.graph.astream(initial_state, config):
            yield state
    
    def visualize(self, output_path: str = "mindsearch_graph.png"):
        """Generate a visualization of the graph.
        
        Args:
            output_path: Path to save the visualization
        """
        try:
            # Get the graph structure
            graph_image = self.graph.get_graph().draw_mermaid_png()
            
            # Save to file
            with open(output_path, "wb") as f:
                f.write(graph_image)
            
            print(f"Graph visualization saved to {output_path}")
            
        except Exception as e:
            print(f"Error generating visualization: {e}")
            # Generate text representation as fallback
            print("\nGraph structure:")
            print("initialize -> plan_search -> execute_searches -> synthesize_answer -> END")
            print("With error handling: error_handler -> plan_search (retry loop)")


# Convenience function for quick searches
async def search(query: str, use_memory: bool = False) -> dict:
    """Convenience function for one-off searches.
    
    Args:
        query: The search query
        use_memory: Whether to enable checkpointing
        
    Returns:
        Search results dictionary
    """
    agent = MindSearchAgent(use_memory=use_memory)
    return await agent.search(query)