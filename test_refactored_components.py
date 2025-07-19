#!/usr/bin/env python3
"""Test script to verify refactored components work together."""

import asyncio
import logging
import sys
import os
from typing import Dict, Any
import pytest

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import mock modules before any lagent imports
try:
    import mock_lagent
except ImportError:
    logger.warning("Could not import mock_lagent, tests may fail if lagent is not installed")

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import our refactored components
from mindsearch.agent.search_engines import (
    SearchEngineManager, 
    MockSearchEngine,
    create_search_manager_with_cache
)
from mindsearch.agent.memory_handler import (
    RobustMemoryHandler,
    MemoryAdapter
)


@pytest.mark.asyncio
async def test_search_engines():
    """Test the search engine abstraction layer."""
    print("\n" + "="*60)
    print("Testing Search Engine Abstraction Layer")
    print("="*60)
    
    # Create search manager
    manager = create_search_manager_with_cache(cache_ttl=60)
    
    # Test queries
    test_queries = [
        "weather in New York",
        "latest technology news",
        "Python programming tips"
    ]
    
    for query in test_queries:
        print(f"\nSearching for: '{query}'")
        results = await manager.search(query, max_results=3)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   URL: {result.url}")
                print(f"   Source: {result.source}")
                print(f"   Snippet: {result.snippet[:100]}...")
        else:
            print("No results found")
    
    # Test cache hit
    print("\n\nTesting cache (searching again for first query):")
    results = await manager.search(test_queries[0], max_results=3)
    print(f"Cache test: Found {len(results)} results")
    
    # Show engine status
    print("\n\nEngine Status:")
    status = manager.get_status()
    for engine, info in status.items():
        print(f"- {engine}: Available={info['available']}, Failures={info['failure_count']}")


def test_memory_handler():
    """Test the robust memory handler."""
    print("\n" + "="*60)
    print("Testing Robust Memory Handler")
    print("="*60)
    
    # Test 1: Create and validate empty memory
    print("\n1. Testing empty memory creation:")
    memory = RobustMemoryHandler.create_default_memory()
    print(f"Default memory structure: {list(memory.keys())}")
    
    # Test 2: Add nodes
    print("\n2. Testing node addition:")
    memory = RobustMemoryHandler.add_node(memory, "1", {
        "name": "search_weather",
        "content": "Search for weather in New York",
        "status": 0
    })
    memory = RobustMemoryHandler.add_node(memory, "2", {
        "name": "analyze_results",
        "content": "Analyze search results",
        "status": 0,
        "dependencies": ["1"]
    })
    print(f"Added {len(memory['nodes'])} nodes")
    
    # Test 3: Update node status
    print("\n3. Testing node status update:")
    memory = RobustMemoryHandler.update_node_status(memory, "1", 2, "Weather data retrieved")
    print(f"Node 1 status: {memory['nodes']['1']['status']}")
    print(f"Node 1 result: {memory['nodes']['1']['result']}")
    
    # Test 4: Get pending nodes
    print("\n4. Testing pending nodes retrieval:")
    pending = RobustMemoryHandler.get_pending_nodes(memory)
    print(f"Pending nodes: {pending}")
    
    # Test 5: Memory summary
    print("\n5. Testing memory summary:")
    summary = RobustMemoryHandler.summarize_memory(memory)
    for key, value in summary.items():
        print(f"- {key}: {value}")
    
    # Test 6: Validate corrupted memory
    print("\n6. Testing corrupted memory validation:")
    corrupted = {
        "nodes": "not a dict",  # Wrong type
        "missing_fields": True  # Missing required fields
    }
    fixed = RobustMemoryHandler.validate_and_correct(corrupted)
    print(f"Fixed memory has all required fields: {set(fixed.keys()) == set(memory.keys())}")
    
    # Test 7: Memory adapter
    print("\n7. Testing memory adapter:")
    agent_state = {
        "adj": {
            "1": {"name": "test_node", "status": 0},
            "2": {"name": "another_node", "status": 1}
        },
        "memory": {"context": "test"},
        "current_node": "1"
    }
    converted_memory = MemoryAdapter.from_agent_state(agent_state)
    print(f"Converted {len(agent_state['adj'])} nodes from agent state")
    
    # Convert back
    new_agent_state = MemoryAdapter.to_agent_state(converted_memory)
    print(f"Converted back to agent state with {len(new_agent_state['adj'])} nodes")


@pytest.mark.asyncio
async def test_integration():
    """Test integration of components."""
    print("\n" + "="*60)
    print("Testing Component Integration")
    print("="*60)
    
    # Create components
    search_manager = SearchEngineManager()
    memory = RobustMemoryHandler.create_default_memory()
    
    # Simulate a search workflow
    query = "weather forecast tomorrow"
    
    # Add search node
    memory = RobustMemoryHandler.add_node(memory, "1", {
        "name": "search_weather",
        "content": f"Search for: {query}",
        "status": 0
    })
    
    # Execute search
    print(f"\nExecuting search for: '{query}'")
    memory = RobustMemoryHandler.update_node_status(memory, "1", 1)  # Processing
    
    results = await search_manager.search(query, max_results=3)
    
    if results:
        # Update memory with results
        result_text = f"Found {len(results)} results"
        memory = RobustMemoryHandler.update_node_status(memory, "1", 2, result_text)
        
        # Add references
        for i, result in enumerate(results):
            memory = RobustMemoryHandler.add_reference(memory, str(i+1), result.url)
        
        print(f"Search completed: {result_text}")
        print(f"Added {len(results)} references to memory")
    else:
        memory = RobustMemoryHandler.update_node_status(memory, "1", 2, "No results found")
        print("Search completed: No results")
    
    # Show final memory state
    print("\nFinal memory summary:")
    summary = RobustMemoryHandler.summarize_memory(memory)
    for key, value in summary.items():
        print(f"- {key}: {value}")


async def main():
    """Run all tests."""
    print("🚀 Testing Refactored MindSearch Components\n")
    
    try:
        # Test individual components
        await test_search_engines()
        test_memory_handler()
        await test_integration()
        
        print("\n\n✅ All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n\n❌ Tests failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)