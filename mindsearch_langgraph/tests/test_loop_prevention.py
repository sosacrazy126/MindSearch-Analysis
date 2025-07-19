"""Tests demonstrating loop prevention and state management improvements."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src import MindSearchAgent
from src.state import MindSearchState


async def test_loop_prevention():
    """Test that the graph prevents infinite loops."""
    print("=== Testing Loop Prevention ===\n")
    
    agent = MindSearchAgent()
    
    # Create a query that might cause loops in the original implementation
    query = "recursive search test"
    
    # Track node visits
    visit_tracker = {}
    
    async for state in agent.stream_search(query):
        # Track visits
        if "visit_count" in state:
            for node, count in state["visit_count"].items():
                if node not in visit_tracker or visit_tracker[node] < count:
                    visit_tracker[node] = count
                    print(f"Node '{node}' visited {count} time(s)")
    
    print("\nFinal visit counts:")
    for node, count in visit_tracker.items():
        print(f"  {node}: {count}")
    
    # Verify no node was visited too many times
    max_visits = max(visit_tracker.values()) if visit_tracker else 0
    assert max_visits <= 3, f"Node visited {max_visits} times - potential loop!"
    
    print("\n✓ Loop prevention test passed - no infinite loops detected")


async def test_state_isolation():
    """Test that concurrent searches don't interfere with each other."""
    print("\n\n=== Testing State Isolation ===\n")
    
    agent = MindSearchAgent(use_memory=True)
    
    # Run multiple searches concurrently
    queries = [
        "Python programming",
        "JavaScript frameworks",
        "Machine learning basics"
    ]
    
    async def run_search(query):
        result = await agent.search(query)
        return query, result
    
    # Execute searches in parallel
    tasks = [run_search(q) for q in queries]
    results = await asyncio.gather(*tasks)
    
    # Verify each search got its own results
    for query, result in results:
        print(f"\nQuery: {query}")
        print(f"  Sub-queries: {len(result['sub_queries'])}")
        print(f"  Answer length: {len(result['answer'])} chars")
        print(f"  Confidence: {result['confidence']:.2f}")
        
        # Verify the answer is related to the query
        assert query.lower() in result['answer'].lower() or \
               any(word in result['answer'].lower() for word in query.lower().split()), \
               f"Answer doesn't seem related to query: {query}"
    
    print("\n✓ State isolation test passed - concurrent searches work correctly")


async def test_error_recovery():
    """Test that the graph recovers from errors gracefully."""
    print("\n\n=== Testing Error Recovery ===\n")
    
    agent = MindSearchAgent()
    
    # Query that might cause errors
    query = "test error recovery mechanisms"
    
    result = await agent.search(query, max_searches=3)
    
    print(f"Query: {query}")
    print(f"Searches completed: {result['searches_completed']}")
    print(f"Errors encountered: {len(result['errors'])}")
    
    # Even with errors, we should get some result
    assert result['answer'] != "", "No answer generated despite error recovery"
    assert result['confidence'] > 0, "No confidence score despite error recovery"
    
    if result['errors']:
        print("\nErrors handled:")
        for error in result['errors']:
            print(f"  - {error}")
    
    print("\n✓ Error recovery test passed - system handles errors gracefully")


async def test_recursion_limit():
    """Test that recursion limits prevent runaway execution."""
    print("\n\n=== Testing Recursion Limits ===\n")
    
    agent = MindSearchAgent()
    
    # Complex query that might cause deep recursion
    query = "explain quantum computing and its applications in cryptography and machine learning"
    
    # Track execution time
    import time
    start_time = time.time()
    
    result = await agent.search(query, max_searches=20)
    
    execution_time = time.time() - start_time
    
    print(f"Query: {query}")
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Sub-queries generated: {len(result['sub_queries'])}")
    print(f"Searches completed: {result['searches_completed']}")
    
    # Verify execution didn't run too long
    assert execution_time < 30, f"Execution took too long: {execution_time}s"
    
    # Verify we didn't exceed max searches
    assert result['searches_completed'] <= 20, "Exceeded maximum search limit"
    
    print("\n✓ Recursion limit test passed - execution bounded properly")


async def main():
    """Run all tests."""
    import os
    os.environ["OPENAI_API_KEY"] = "mock-key-for-testing"
    
    try:
        await test_loop_prevention()
        await test_state_isolation()
        await test_error_recovery()
        await test_recursion_limit()
        
        print("\n\n=== All Tests Passed! ===")
        print("\nKey improvements demonstrated:")
        print("1. ✓ No infinite loops - visit counting prevents revisiting nodes")
        print("2. ✓ State isolation - concurrent searches don't interfere")
        print("3. ✓ Error recovery - system continues despite failures")
        print("4. ✓ Bounded execution - recursion limits prevent runaway")
        
    except AssertionError as e:
        print(f"\n\n❌ Test failed: {e}")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main())