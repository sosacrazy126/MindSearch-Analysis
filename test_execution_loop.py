#!/usr/bin/env python3
"""Focused test to diagnose the infinite loop in ExecutionAction."""

import os
import sys
import json
import asyncio
from typing import Dict, Any, List, Optional
from collections import defaultdict

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import mock modules before any lagent imports
try:
    import mock_lagent
except ImportError:
    pass

# Mock the dependencies to avoid installation issues
class MockAgentMessage:
    def __init__(self, content="", sender="", receiver=""):
        self.content = content
        self.sender = sender
        self.receiver = receiver
        self.stream_state = "end"

class MockAgentStatusCode:
    END = "END"
    STREAM_ING = "STREAM_ING"

class MockModelStatusCode:
    END = "END"

# Replace the imports with mocks
sys.modules['lagent.schema'] = type(sys)('lagent.schema')
sys.modules['lagent.schema'].AgentMessage = MockAgentMessage
sys.modules['lagent.schema'].AgentStatusCode = MockAgentStatusCode
sys.modules['lagent.schema'].ModelStatusCode = MockModelStatusCode

# Now we can import the actual classes
from mindsearch.agent.graph import ExecutionAction, WebSearchGraph

class DiagnosticExecutionAction(ExecutionAction):
    """Instrumented ExecutionAction to track execution flow."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.execution_history = []
        self.node_visits = defaultdict(int)
        self.max_iterations = 20  # Prevent infinite loops in testing
        
    async def __call__(self, agent_state: Dict[str, Any], model: Any) -> Dict[str, Any]:
        """Track each execution and detect loops."""
        iteration = len(self.execution_history)
        
        # Safety check
        if iteration >= self.max_iterations:
            print(f"\n🚨 STOPPED: Reached max iterations ({self.max_iterations})")
            return {
                'response': "STOPPED: Max iterations reached",
                'state': MockAgentStatusCode.END
            }
        
        # Log the current state
        current_node = agent_state.get('adj', {}).get('1', {}).get('name', 'unknown')
        self.node_visits[current_node] += 1
        
        execution_record = {
            'iteration': iteration,
            'node': current_node,
            'visit_count': self.node_visits[current_node],
            'agent_state_keys': list(agent_state.keys()),
            'adj_keys': list(agent_state.get('adj', {}).keys()) if 'adj' in agent_state else [],
            'memory_keys': list(agent_state.get('memory', {}).keys()) if 'memory' in agent_state else []
        }
        
        self.execution_history.append(execution_record)
        
        print(f"\n--- Iteration {iteration} ---")
        print(f"Current Node: {current_node}")
        print(f"Visit Count: {self.node_visits[current_node]}")
        print(f"Agent State Keys: {execution_record['agent_state_keys']}")
        print(f"Adjacency Keys: {execution_record['adj_keys']}")
        print(f"Memory Keys: {execution_record['memory_keys']}")
        
        # Check for loops
        if self.node_visits[current_node] > 3:
            print(f"\n⚠️  WARNING: Node '{current_node}' visited {self.node_visits[current_node]} times!")
            
        # Call the parent implementation
        try:
            result = await super().__call__(agent_state, model)
            
            # Log the result
            print(f"Result type: {type(result)}")
            if isinstance(result, dict):
                print(f"Result keys: {list(result.keys())}")
                if 'response' in result:
                    print(f"Response preview: {str(result['response'])[:100]}...")
                if 'state' in result:
                    print(f"State: {result.get('state')}")
                    
            return result
            
        except Exception as e:
            print(f"\n❌ ERROR in ExecutionAction: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'response': f"ERROR: {str(e)}",
                'state': MockAgentStatusCode.END
            }

class DiagnosticWebSearchGraph(WebSearchGraph):
    """Instrumented WebSearchGraph to track graph operations."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.graph_operations = []
        
    def __call__(self, query: str, agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """Track graph generation."""
        operation = {
            'query': query,
            'agent_state_keys': list(agent_state.keys())
        }
        self.graph_operations.append(operation)
        
        print(f"\n📊 WebSearchGraph called with query: '{query}'")
        print(f"Agent state keys: {operation['agent_state_keys']}")
        
        try:
            result = super().__call__(query, agent_state)
            
            print(f"Graph result type: {type(result)}")
            if isinstance(result, dict):
                print(f"Graph result keys: {list(result.keys())}")
                if 'adj' in result:
                    print(f"Generated nodes: {list(result['adj'].keys())}")
                    
            return result
            
        except Exception as e:
            print(f"\n❌ ERROR in WebSearchGraph: {type(e).__name__}: {str(e)}")
            import traceback
            traceback.print_exc()
            return agent_state

def test_execution_loop():
    """Test the ExecutionAction to understand the infinite loop."""
    print("🔍 Testing ExecutionAction Loop Behavior\n")
    
    # Create a minimal agent state
    agent_state = {
        'adj': {
            '1': {
                'name': 'test_node',
                'content': 'Test content',
                'status': 0
            }
        },
        'memory': {},
        'current_node': '1'
    }
    
    # Create instrumented instances
    graph = DiagnosticWebSearchGraph()
    
    action = DiagnosticExecutionAction(
        search_engine=graph,
        max_turn=10
    )
    
    # Mock model that returns simple responses
    class MockModel:
        async def __call__(self, messages, **kwargs):
            return MockAgentMessage(
                content="Mock response",
                sender="model",
                receiver="user"
            )
    
    model = MockModel()
    
    # Run the test
    print("Starting execution loop test...\n")
    
    async def run_test():
        for i in range(5):  # Run a few iterations
            print(f"\n{'='*50}")
            print(f"MAIN LOOP ITERATION {i}")
            print(f"{'='*50}")
            
            result = await action(agent_state, model)
            
            # Check if we should stop
            if result.get('state') == MockAgentStatusCode.END:
                print("\n✅ Execution ended normally")
                break
                
            # Update agent_state if needed (this might be part of the problem)
            # In the real system, this would be done by the agent
            
        # Print summary
        print("\n" + "="*50)
        print("EXECUTION SUMMARY")
        print("="*50)
        
        print(f"\nTotal iterations: {len(action.execution_history)}")
        print(f"\nNode visit counts:")
        for node, count in action.node_visits.items():
            print(f"  - {node}: {count} visits")
            
        # Check for infinite loop pattern
        if any(count > 3 for count in action.node_visits.values()):
            print("\n🚨 INFINITE LOOP DETECTED!")
            print("The same node was visited multiple times without progression.")
            
        # Analyze the pattern
        if len(action.execution_history) > 2:
            print("\n📈 Execution Pattern:")
            for record in action.execution_history[-5:]:  # Last 5 iterations
                print(f"  Iteration {record['iteration']}: Node '{record['node']}' (visit #{record['visit_count']})")
    
    # Run the async test
    asyncio.run(run_test())

if __name__ == "__main__":
    test_execution_loop()