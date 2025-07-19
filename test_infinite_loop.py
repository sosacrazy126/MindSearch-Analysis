#!/usr/bin/env python3
"""Test script to reproduce and diagnose the infinite loop issue in ExecutionAction."""

import os
import sys
import logging
import asyncio
from typing import Dict, Any
import json
import time

# Set up logging to see all debug information
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mindsearch.agent.mindsearch_agent import MindSearchAgent
from mindsearch.agent.graph import WebSearchGraph, ExecutionAction
from lagent.schema import AgentMessage, AgentStatusCode, ModelStatusCode


class InstrumentedExecutionAction(ExecutionAction):
    """Instrumented version of ExecutionAction to track execution flow."""
    
    def __init__(self):
        super().__init__()
        self.execution_count = 0
        self.executed_commands = []
        self.node_history = []
    
    def run(self, command, local_dict, global_dict, stream_graph=False):
        self.execution_count += 1
        logger.info(f"\n{'='*60}")
        logger.info(f"ExecutionAction.run() - Call #{self.execution_count}")
        logger.info(f"Command: {command[:200]}...")
        
        # Track the command
        self.executed_commands.append({
            'count': self.execution_count,
            'command': command,
            'timestamp': time.time()
        })
        
        # Run the original method
        try:
            result = super().run(command, local_dict, global_dict, stream_graph)
            
            # Log the result
            if isinstance(result, tuple) and len(result) >= 2:
                nodes, graph_nodes, adjacency_list = result
                logger.info(f"Result nodes: {[node.get('content', '')[:50] + '...' if node.get('content', '') else 'Empty' for node in nodes]}")
                logger.info(f"Graph nodes keys: {list(graph_nodes.keys())}")
                
                # Track node progression
                current_nodes = list(graph_nodes.keys())
                self.node_history.append({
                    'execution': self.execution_count,
                    'nodes': current_nodes,
                    'timestamp': time.time()
                })
                
                # Check for repetition
                if len(self.node_history) > 1:
                    prev_nodes = self.node_history[-2]['nodes']
                    if set(current_nodes) == set(prev_nodes):
                        logger.warning("⚠️  SAME NODES AS PREVIOUS EXECUTION - POTENTIAL LOOP!")
                
            return result
            
        except Exception as e:
            logger.error(f"Error in ExecutionAction.run(): {e}", exc_info=True)
            raise


class InstrumentedWebSearchGraph(WebSearchGraph):
    """Instrumented version of WebSearchGraph to track node processing."""
    
    def __init__(self):
        super().__init__()
        self.node_add_history = []
        self.queue_history = []
    
    def add_node(self, node_name: str, node_content: str):
        logger.info(f"\n📍 WebSearchGraph.add_node() - Name: '{node_name}', Content: '{node_content[:50]}...'")
        self.node_add_history.append({
            'name': node_name,
            'content': node_content,
            'timestamp': time.time()
        })
        
        # Check for duplicate node names
        duplicate_count = sum(1 for n in self.node_add_history if n['name'] == node_name)
        if duplicate_count > 1:
            logger.warning(f"⚠️  Node '{node_name}' has been added {duplicate_count} times!")
        
        return super().add_node(node_name, node_content)
    
    def add_response_node(self, node_name="response"):
        logger.info(f"\n✅ WebSearchGraph.add_response_node() - Name: '{node_name}'")
        return super().add_response_node(node_name)


def test_simple_query():
    """Test a simple query to see if it gets stuck in a loop."""
    logger.info("\n" + "="*80)
    logger.info("STARTING INFINITE LOOP TEST")
    logger.info("="*80)
    
    # Patch the classes to use instrumented versions
    import mindsearch.agent.graph
    original_execution_action = mindsearch.agent.graph.ExecutionAction
    original_web_search_graph = mindsearch.agent.graph.WebSearchGraph
    
    mindsearch.agent.graph.ExecutionAction = InstrumentedExecutionAction
    mindsearch.agent.graph.WebSearchGraph = InstrumentedWebSearchGraph
    
    try:
        # Initialize the agent
        logger.info("\n🔧 Initializing MindSearchAgent...")
        agent = MindSearchAgent(
            llm=dict(
                type='openai',
                model='gpt-4o-mini',
                api_key=os.getenv('OPENAI_API_KEY'),
                temperature=0.1  # Low temperature for consistency
            ),
            searcher_cfg=dict(
                llm=dict(
                    type='openai',
                    model='gpt-4o-mini',
                    api_key=os.getenv('OPENAI_API_KEY'),
                    temperature=0.1
                ),
                plugins=[dict(type='duckduckgo_search')]
            ),
            max_turn=5  # Limit turns to prevent infinite execution
        )
        
        # Create a simple test query
        query = "What is 2+2?"
        logger.info(f"\n📝 Test Query: '{query}'")
        
        # Track execution
        start_time = time.time()
        message_count = 0
        last_message_time = start_time
        
        # Execute the query
        for message in agent(query):
            message_count += 1
            current_time = time.time()
            time_since_last = current_time - last_message_time
            last_message_time = current_time
            
            logger.info(f"\n📨 Message #{message_count} (after {time_since_last:.2f}s):")
            logger.info(f"  Sender: {message.sender}")
            logger.info(f"  Stream State: {message.stream_state}")
            logger.info(f"  Content: {str(message.content)[:100]}...")
            
            if hasattr(message, 'formatted') and message.formatted:
                if 'tool_type' in message.formatted:
                    logger.info(f"  Tool Type: {message.formatted['tool_type']}")
                if 'node' in message.formatted:
                    logger.info(f"  Nodes: {list(message.formatted['node'].keys())}")
            
            # Safety check - if we've been running for too long
            if current_time - start_time > 30:  # 30 second timeout
                logger.error("⏰ TIMEOUT - Query has been running for over 30 seconds!")
                break
            
            # Check if we're in a loop
            if hasattr(agent, 'action') and hasattr(agent.action, 'execution_count'):
                if agent.action.execution_count > 10:
                    logger.error("🔄 LOOP DETECTED - ExecutionAction called more than 10 times!")
                    break
        
        # Summary
        elapsed_time = time.time() - start_time
        logger.info(f"\n{'='*60}")
        logger.info(f"EXECUTION SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total time: {elapsed_time:.2f}s")
        logger.info(f"Total messages: {message_count}")
        
        if hasattr(agent, 'action'):
            action = agent.action
            if hasattr(action, 'execution_count'):
                logger.info(f"ExecutionAction calls: {action.execution_count}")
                
                # Show command pattern
                if hasattr(action, 'executed_commands') and action.executed_commands:
                    logger.info("\nExecuted Commands:")
                    for cmd in action.executed_commands[-3:]:  # Show last 3
                        logger.info(f"  #{cmd['count']}: {cmd['command'][:100]}...")
                
                # Show node progression
                if hasattr(action, 'node_history') and action.node_history:
                    logger.info("\nNode Progression:")
                    for i, hist in enumerate(action.node_history[-3:]):  # Show last 3
                        logger.info(f"  Execution #{hist['execution']}: {hist['nodes']}")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}", exc_info=True)
    
    finally:
        # Restore original classes
        mindsearch.agent.graph.ExecutionAction = original_execution_action
        mindsearch.agent.graph.WebSearchGraph = original_web_search_graph


if __name__ == "__main__":
    # Ensure we have an API key
    if not os.getenv('OPENAI_API_KEY'):
        logger.error("Please set OPENAI_API_KEY environment variable")
        sys.exit(1)
    
    # Run the test
    test_simple_query()