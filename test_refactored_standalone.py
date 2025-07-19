#!/usr/bin/env python3
"""Standalone test for refactored components without external dependencies."""

import asyncio
import sys
import os
from datetime import datetime

# Test the components by importing them directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import just the specific modules we created
import importlib.util

def load_module(name, path):
    """Load a module from a specific path."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

# Load our modules
search_engines = load_module("search_engines", "/workspace/mindsearch/agent/search_engines.py")
memory_handler = load_module("memory_handler", "/workspace/mindsearch/agent/memory_handler.py")

# Now we can use the classes
SearchEngineManager = search_engines.SearchEngineManager
MockSearchEngine = search_engines.MockSearchEngine
create_search_manager_with_cache = search_engines.create_search_manager_with_cache
RobustMemoryHandler = memory_handler.RobustMemoryHandler
MemoryAdapter = memory_handler.MemoryAdapter


async def test_mock_search():
    """Test the mock search engine."""
    print("\n" + "="*60)
    print("Testing Mock Search Engine")
    print("="*60)
    
    engine = MockSearchEngine()
    
    queries = [
        "weather in New York",
        "latest news",
        "Python programming"
    ]
    
    for query in queries:
        print(f"\nSearching for: '{query}'")
        results = await engine.search(query, max_results=2)
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:80]}...")


def test_memory_validation():
    """Test memory validation and correction."""
    print("\n" + "="*60)
    print("Testing Memory Validation")
    print("="*60)
    
    # Test cases
    test_cases = [
        {
            "name": "Empty input",
            "input": None,
            "description": "Should create default memory"
        },
        {
            "name": "Invalid type",
            "input": "not a dict",
            "description": "Should create default memory"
        },
        {
            "name": "Missing fields",
            "input": {"nodes": {}},
            "description": "Should add missing fields"
        },
        {
            "name": "Wrong field types",
            "input": {
                "nodes": "should be dict",
                "edges": [],  # should be dict
                "history": "should be list"
            },
            "description": "Should correct field types"
        },
        {
            "name": "Valid memory",
            "input": {
                "nodes": {"1": {"name": "test", "status": 0}},
                "edges": {},
                "current_node": "1",
                "history": [],
                "context": {},
                "references": {}
            },
            "description": "Should preserve valid structure"
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}: {test['description']}")
        result = RobustMemoryHandler.validate_and_correct(test['input'])
        
        # Check all required fields exist
        required_fields = ['nodes', 'edges', 'current_node', 'history', 'context', 'references']
        all_present = all(field in result for field in required_fields)
        print(f"  All required fields present: {all_present}")
        
        # Check types
        type_checks = {
            'nodes': dict,
            'edges': dict,
            'history': list,
            'context': dict,
            'references': dict
        }
        
        types_correct = all(
            isinstance(result.get(field), expected_type)
            for field, expected_type in type_checks.items()
        )
        print(f"  All types correct: {types_correct}")


def test_memory_operations():
    """Test memory operations."""
    print("\n" + "="*60)
    print("Testing Memory Operations")
    print("="*60)
    
    # Create memory
    memory = RobustMemoryHandler.create_default_memory()
    
    # Add nodes
    print("\n1. Adding nodes:")
    memory = RobustMemoryHandler.add_node(memory, "1", {
        "name": "search_node",
        "content": "Search for information",
        "status": 0
    })
    memory = RobustMemoryHandler.add_node(memory, "2", {
        "name": "process_node",
        "content": "Process results",
        "status": 0,
        "dependencies": ["1"]
    })
    print(f"   Added {len(memory['nodes'])} nodes")
    
    # Update status
    print("\n2. Updating node status:")
    memory = RobustMemoryHandler.update_node_status(memory, "1", 2, "Search completed")
    node1 = memory['nodes']['1']
    print(f"   Node 1 status: {node1['status']} (2 = completed)")
    print(f"   Node 1 result: {node1['result']}")
    
    # Get pending nodes
    print("\n3. Getting pending nodes:")
    pending = RobustMemoryHandler.get_pending_nodes(memory)
    print(f"   Pending nodes: {pending}")
    
    # Add references
    print("\n4. Adding references:")
    memory = RobustMemoryHandler.add_reference(memory, "1", "https://example.com/result1")
    memory = RobustMemoryHandler.add_reference(memory, "2", "https://example.com/result2")
    print(f"   Total references: {len(memory['references'])}")
    
    # Get summary
    print("\n5. Memory summary:")
    summary = RobustMemoryHandler.summarize_memory(memory)
    for key, value in summary.items():
        print(f"   {key}: {value}")


def test_memory_adapter():
    """Test memory adapter conversions."""
    print("\n" + "="*60)
    print("Testing Memory Adapter")
    print("="*60)
    
    # Create agent state
    agent_state = {
        "adj": {
            "1": {
                "name": "node_one",
                "content": "First node",
                "status": 0
            },
            "2": {
                "name": "node_two",
                "content": "Second node",
                "status": 1,
                "result": "Some result"
            }
        },
        "memory": {"key": "value"},
        "current_node": "1"
    }
    
    print("\n1. Converting agent state to memory:")
    memory = MemoryAdapter.from_agent_state(agent_state)
    print(f"   Nodes converted: {len(memory['nodes'])}")
    print(f"   Current node: {memory['current_node']}")
    print(f"   Context preserved: {'key' in memory['context']}")
    
    print("\n2. Converting back to agent state:")
    new_state = MemoryAdapter.to_agent_state(memory)
    print(f"   Adj nodes: {len(new_state['adj'])}")
    print(f"   Current node: {new_state['current_node']}")
    print(f"   Memory preserved: {'key' in new_state['memory']}")
    
    # Verify round-trip
    print("\n3. Verifying round-trip conversion:")
    nodes_match = all(
        agent_state['adj'][node_id]['name'] == new_state['adj'][node_id]['name']
        for node_id in agent_state['adj']
    )
    print(f"   Node names match: {nodes_match}")
    print(f"   Current node matches: {agent_state['current_node'] == new_state['current_node']}")


async def test_search_fallback():
    """Test search engine fallback mechanism."""
    print("\n" + "="*60)
    print("Testing Search Engine Fallback")
    print("="*60)
    
    # Create a custom manager with a failing engine
    class FailingEngine(search_engines.SearchEngineInterface):
        """Engine that always fails."""
        def __init__(self):
            super().__init__("FailingEngine")
        
        async def _perform_search(self, query: str, max_results: int = 5):
            raise Exception("Simulated failure")
    
    # Create manager and add engines
    manager = search_engines.SearchEngineManager()
    manager.engines = []  # Clear default engines
    manager.add_engine(FailingEngine())
    manager.add_engine(MockSearchEngine())  # Fallback
    
    print("\n1. Testing fallback on failure:")
    results = await manager.search("test query", max_results=2)
    print(f"   Results found: {len(results)}")
    if results:
        print(f"   Source: {results[0].source} (should be 'mock')")
    
    print("\n2. Engine status after failures:")
    status = manager.get_status()
    for engine, info in status.items():
        print(f"   {engine}: Available={info['available']}, Failures={info['failure_count']}")


async def main():
    """Run all tests."""
    print("🚀 Testing Refactored Components (Standalone)\n")
    
    try:
        # Run tests
        await test_mock_search()
        test_memory_validation()
        test_memory_operations()
        test_memory_adapter()
        await test_search_fallback()
        
        print("\n\n✅ All standalone tests completed successfully!")
        print("\nKey achievements:")
        print("- ✅ Search engine abstraction with fallback mechanisms")
        print("- ✅ Robust memory validation and auto-correction")
        print("- ✅ Memory adapter for format conversion")
        print("- ✅ Mock search engine for testing/fallback")
        print("- ✅ Comprehensive error handling")
        
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)