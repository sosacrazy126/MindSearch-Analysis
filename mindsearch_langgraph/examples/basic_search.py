"""Basic example of using MindSearch with LangGraph."""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import MindSearchAgent, search


async def basic_search_example():
    """Demonstrate basic search functionality."""
    print("=== MindSearch LangGraph Basic Example ===\n")
    
    # Create an agent
    agent = MindSearchAgent(use_memory=True)
    
    # Example query
    query = "What are the differences between Python and JavaScript?"
    
    print(f"Query: {query}\n")
    print("Processing...")
    
    # Execute search
    result = await agent.search(query, max_searches=5)
    
    # Display results
    print("\n=== Results ===")
    print(f"\nAnswer:\n{result['answer']}")
    print(f"\nConfidence: {result['confidence']:.2f}")
    print(f"\nSub-queries used: {result['sub_queries']}")
    print(f"\nSearches completed: {result['searches_completed']}")
    
    if result['references']:
        print("\nReferences:")
        for ref_num, url in result['references'].items():
            print(f"  [{ref_num}] {url}")
    
    if result['errors']:
        print("\nErrors encountered:")
        for error in result['errors']:
            print(f"  - {error}")


async def streaming_example():
    """Demonstrate streaming search functionality."""
    print("\n\n=== MindSearch LangGraph Streaming Example ===\n")
    
    agent = MindSearchAgent()
    query = "weather in New York City today"
    
    print(f"Query: {query}\n")
    print("Streaming results...\n")
    
    async for state_update in agent.stream_search(query):
        # Show progress
        if "sub_queries" in state_update and state_update["sub_queries"]:
            print(f"✓ Decomposed into {len(state_update['sub_queries'])} sub-queries")
        
        if "searches_completed" in state_update and state_update["searches_completed"] > 0:
            print(f"✓ Completed {state_update['searches_completed']} searches")
        
        if "final_answer" in state_update and state_update["final_answer"]:
            print(f"✓ Generated final answer")
    
    # Get final result
    result = await agent.search(query)
    print(f"\nFinal Answer:\n{result['answer']}")


async def quick_search_example():
    """Demonstrate the convenience function."""
    print("\n\n=== Quick Search Example ===\n")
    
    query = "MindSearch vs LangGraph comparison"
    print(f"Query: {query}\n")
    
    # Use the convenience function
    result = await search(query)
    
    print(f"Answer:\n{result['answer']}")
    print(f"\nConfidence: {result['confidence']:.2f}")


async def visualization_example():
    """Demonstrate graph visualization."""
    print("\n\n=== Graph Visualization Example ===\n")
    
    agent = MindSearchAgent()
    
    # Generate visualization
    agent.visualize("mindsearch_graph.png")
    
    print("Graph structure has been saved/displayed")


async def main():
    """Run all examples."""
    # Set mock API key for testing
    os.environ["OPENAI_API_KEY"] = "mock-key-for-testing"
    
    try:
        await basic_search_example()
        await streaming_example()
        await quick_search_example()
        await visualization_example()
    except KeyboardInterrupt:
        print("\n\nExamples interrupted by user")
    except Exception as e:
        print(f"\n\nError running examples: {e}")


if __name__ == "__main__":
    asyncio.run(main())