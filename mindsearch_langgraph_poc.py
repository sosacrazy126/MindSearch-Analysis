#!/usr/bin/env python3
"""
Proof of Concept: MindSearch implemented with LangGraph
This shows how much simpler and more robust the implementation would be.
"""

from typing import TypedDict, List, Dict, Literal, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
import operator

# Note: This is a conceptual example. In production, you'd need to:
# pip install langgraph langchain-openai

class MindSearchState(TypedDict):
    """Type-safe state management - no more memory corruption!"""
    query: str
    search_plan: Annotated[List[str], operator.add]  # Auto-append
    search_results: Dict[str, List[Dict]]
    current_step: int
    max_steps: int
    final_answer: str
    references: Dict[int, str]
    error: str

def plan_search(state: MindSearchState) -> MindSearchState:
    """
    Decompose the user query into sub-queries.
    This replaces the complex WebSearchGraph logic.
    """
    # In production, this would use GPT to decompose the query
    # For now, simple example
    if "weather" in state["query"].lower():
        state["search_plan"] = [
            "current weather conditions",
            "weather forecast next 24 hours",
            "weather alerts and warnings"
        ]
    else:
        # Generic decomposition
        state["search_plan"] = [
            f"define {state['query']}",
            f"current news about {state['query']}",
            f"key facts about {state['query']}"
        ]
    
    state["max_steps"] = len(state["search_plan"])
    return state

def should_continue_searching(state: MindSearchState) -> Literal["search", "synthesize"]:
    """
    Conditional edge - prevents infinite loops!
    This is where LangGraph shines vs custom implementation.
    """
    # Check if we've searched all sub-queries
    if state["current_step"] >= state["max_steps"]:
        return "synthesize"
    
    # Check if we've hit an error
    if state.get("error"):
        return "synthesize"
    
    # Continue searching
    return "search"

async def search_web(state: MindSearchState) -> MindSearchState:
    """
    Execute web search for current sub-query.
    Reuses the existing SearchEngineManager.
    """
    try:
        # Import our refactored search engine
        from mindsearch.agent.search_engines import SearchEngineManager
        
        search_manager = SearchEngineManager()
        current_query = state["search_plan"][state["current_step"]]
        
        # Execute search
        results = await search_manager.search(current_query, max_results=3)
        
        # Store results
        state["search_results"][current_query] = [
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet
            }
            for r in results
        ]
        
        # Increment step
        state["current_step"] += 1
        
    except Exception as e:
        state["error"] = f"Search failed: {str(e)}"
    
    return state

def synthesize_answer(state: MindSearchState) -> MindSearchState:
    """
    Synthesize final answer from all search results.
    Much simpler than the current implementation!
    """
    # In production, this would use GPT to synthesize
    # For now, simple aggregation
    
    answer_parts = [f"Based on my search for '{state['query']}':\n"]
    ref_counter = 1
    
    for query, results in state["search_results"].items():
        if results:
            answer_parts.append(f"\n**{query.title()}:**")
            for result in results[:2]:  # Top 2 results per query
                answer_parts.append(f"- {result['snippet']} [{ref_counter}]")
                state["references"][ref_counter] = result["url"]
                ref_counter += 1
    
    if state.get("error"):
        answer_parts.append(f"\n\nNote: Some searches failed: {state['error']}")
    
    state["final_answer"] = "\n".join(answer_parts)
    return state

def create_mindsearch_graph():
    """
    Create the MindSearch workflow.
    This replaces hundreds of lines of custom graph execution code!
    """
    # Define the graph
    workflow = StateGraph(MindSearchState)
    
    # Add nodes - each is a simple function
    workflow.add_node("plan", plan_search)
    workflow.add_node("search", search_web)
    workflow.add_node("synthesize", synthesize_answer)
    
    # Define the flow
    workflow.set_entry_point("plan")
    workflow.add_edge("plan", "search")
    
    # Conditional edge - this prevents infinite loops!
    workflow.add_conditional_edges(
        "search",
        should_continue_searching,
        {
            "search": "search",  # Continue searching
            "synthesize": "synthesize"  # Move to synthesis
        }
    )
    
    workflow.add_edge("synthesize", END)
    
    # Compile with built-in features
    app = workflow.compile(
        # checkpointer=MemorySaver(),  # Enable state persistence
        # debug=True,  # Enable debugging
    )
    
    return app

# Example usage
async def example_usage():
    """Show how simple it is to use."""
    # Create the app
    app = create_mindsearch_graph()
    
    # Initialize state
    initial_state = {
        "query": "What is the weather like in New York today?",
        "search_plan": [],
        "search_results": {},
        "current_step": 0,
        "max_steps": 0,
        "final_answer": "",
        "references": {}
    }
    
    # Run the graph - handles all complexity internally
    result = await app.ainvoke(initial_state)
    
    print("Final Answer:")
    print(result["final_answer"])
    print("\nReferences:")
    for ref_id, url in result["references"].items():
        print(f"[{ref_id}] {url}")
    
    # Or stream the execution for real-time updates
    print("\n\nStreaming execution:")
    async for chunk in app.astream(initial_state):
        print(f"Step: {list(chunk.keys())}")

# Visualization
def visualize_graph():
    """Generate a visual representation of the graph."""
    app = create_mindsearch_graph()
    
    # This would generate a Mermaid diagram
    print(app.get_graph().draw_mermaid())
    
    # Output would be:
    """
    graph TD
        __start__ --> plan
        plan --> search
        search --> search
        search --> synthesize
        synthesize --> __end__
    """

if __name__ == "__main__":
    # Show the graph structure
    print("MindSearch Graph Structure:")
    visualize_graph()
    
    # Note: This is conceptual - actual execution would need async runtime
    print("\n\nThis is a proof of concept showing the simplified structure.")
    print("Key benefits over current implementation:")
    print("1. No more infinite loops - built-in recursion limits")
    print("2. Type-safe state management - no memory corruption")
    print("3. ~80% less code - more maintainable")
    print("4. Built-in debugging and visualization")
    print("5. Streaming and checkpointing out of the box")