"""Safe Execution Action with Loop Protection and Fallback Mechanisms."""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from collections import defaultdict
import json

from lagent.schema import AgentMessage, AgentStatusCode, ModelStatusCode

logger = logging.getLogger(__name__)


class ExecutionTracker:
    """Tracks execution history and detects loops."""
    
    def __init__(self, max_node_visits: int = 3, loop_detection_window: int = 10):
        self.max_node_visits = max_node_visits
        self.loop_detection_window = loop_detection_window
        self.node_visits = defaultdict(int)
        self.execution_history = []
        self.start_time = datetime.now()
    
    def record_visit(self, node_name: str, state: Dict[str, Any]) -> Dict[str, Any]:
        """Record a node visit and return analytics."""
        self.node_visits[node_name] += 1
        
        record = {
            'timestamp': datetime.now(),
            'node': node_name,
            'visit_count': self.node_visits[node_name],
            'total_visits': sum(self.node_visits.values()),
            'unique_nodes': len(self.node_visits),
            'state_summary': self._summarize_state(state)
        }
        
        self.execution_history.append(record)
        
        # Detect loops
        loop_info = self._detect_loops()
        record['loop_detected'] = loop_info['detected']
        record['loop_pattern'] = loop_info['pattern']
        
        return record
    
    def _summarize_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of the agent state."""
        summary = {
            'has_adj': 'adj' in state,
            'has_memory': 'memory' in state,
            'adj_count': len(state.get('adj', {})),
            'memory_count': len(state.get('memory', {}))
        }
        
        if 'adj' in state and state['adj']:
            summary['nodes'] = list(state['adj'].keys())
            summary['node_names'] = [
                node.get('name', 'unnamed') 
                for node in state['adj'].values()
            ]
        
        return summary
    
    def _detect_loops(self) -> Dict[str, Any]:
        """Detect execution loops in recent history."""
        if len(self.execution_history) < self.loop_detection_window:
            return {'detected': False, 'pattern': None}
        
        # Get recent node visits
        recent_nodes = [
            record['node'] 
            for record in self.execution_history[-self.loop_detection_window:]
        ]
        
        # Check for simple loops (same node repeated)
        for node, count in self.node_visits.items():
            if count > self.max_node_visits:
                return {
                    'detected': True,
                    'pattern': f'Node "{node}" visited {count} times'
                }
        
        # Check for cyclic patterns
        pattern = self._find_cyclic_pattern(recent_nodes)
        if pattern:
            return {
                'detected': True,
                'pattern': f'Cyclic pattern: {" -> ".join(pattern)}'
            }
        
        return {'detected': False, 'pattern': None}
    
    def _find_cyclic_pattern(self, nodes: List[str], min_cycle_length: int = 2) -> Optional[List[str]]:
        """Find cyclic patterns in node visits."""
        if len(nodes) < min_cycle_length * 2:
            return None
        
        # Check for patterns of different lengths
        for cycle_length in range(min_cycle_length, len(nodes) // 2 + 1):
            for start in range(len(nodes) - cycle_length * 2 + 1):
                pattern = nodes[start:start + cycle_length]
                next_pattern = nodes[start + cycle_length:start + cycle_length * 2]
                
                if pattern == next_pattern:
                    return pattern
        
        return None
    
    def get_execution_time(self) -> float:
        """Get total execution time in seconds."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def should_terminate(self, max_time: float = 30.0) -> bool:
        """Check if execution should be terminated."""
        # Time limit exceeded
        if self.get_execution_time() > max_time:
            logger.warning(f"Execution time limit exceeded: {self.get_execution_time():.2f}s > {max_time}s")
            return True
        
        # Loop detected
        loop_info = self._detect_loops()
        if loop_info['detected']:
            logger.warning(f"Loop detected: {loop_info['pattern']}")
            return True
        
        return False


class SafeExecutionAction:
    """ExecutionAction with loop protection and fallback mechanisms."""
    
    def __init__(
        self,
        search_engine,
        max_turn: int = 10,
        max_node_visits: int = 3,
        execution_timeout: float = 30.0,
        enable_fallback: bool = True
    ):
        self.search_engine = search_engine
        self.max_turn = max_turn
        self.max_node_visits = max_node_visits
        self.execution_timeout = execution_timeout
        self.enable_fallback = enable_fallback
        self.tracker = None
        self.fallback_cache = {}
    
    def _reset_tracker(self):
        """Reset the execution tracker."""
        self.tracker = ExecutionTracker(
            max_node_visits=self.max_node_visits,
            loop_detection_window=self.max_turn
        )
    
    async def __call__(self, agent_state: Dict[str, Any], model: Any) -> Dict[str, Any]:
        """Execute with loop protection and timeout."""
        # Initialize tracker if needed
        if self.tracker is None:
            self._reset_tracker()
        
        # Get current node
        current_node = self._get_current_node(agent_state)
        
        # Record visit
        visit_info = self.tracker.record_visit(current_node, agent_state)
        logger.info(f"Executing node: {current_node} (visit #{visit_info['visit_count']})")
        
        # Check if we should terminate
        if self.tracker.should_terminate(self.execution_timeout):
            logger.warning("Execution terminated due to loop or timeout")
            return self._create_termination_response(agent_state, visit_info)
        
        # Try normal execution with timeout
        try:
            result = await asyncio.wait_for(
                self._execute_node(agent_state, model, current_node),
                timeout=self.execution_timeout / self.max_turn  # Per-node timeout
            )
            
            # Cache successful result
            if self.enable_fallback and result.get('response'):
                self.fallback_cache[current_node] = result
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Node execution timeout: {current_node}")
            return self._create_timeout_response(agent_state, current_node)
        except Exception as e:
            logger.error(f"Node execution error: {e}")
            return self._create_error_response(agent_state, current_node, str(e))
    
    def _get_current_node(self, agent_state: Dict[str, Any]) -> str:
        """Extract current node from agent state."""
        # Try different ways to get current node
        if 'current_node' in agent_state:
            return agent_state['current_node']
        
        # Check adjacency list
        adj = agent_state.get('adj', {})
        if adj:
            # Find node with status 0 (pending) or lowest status
            pending_nodes = [
                (node_id, node.get('name', f'node_{node_id}'))
                for node_id, node in adj.items()
                if node.get('status', 0) == 0
            ]
            
            if pending_nodes:
                return pending_nodes[0][1]
            
            # Return first node if no pending
            first_node = list(adj.values())[0]
            return first_node.get('name', 'unknown')
        
        return 'unknown'
    
    async def _execute_node(
        self, 
        agent_state: Dict[str, Any], 
        model: Any, 
        node_name: str
    ) -> Dict[str, Any]:
        """Execute a single node with error handling."""
        try:
            # This is where the actual execution would happen
            # For now, we'll create a mock implementation
            
            # Check if this is a search node
            if 'search' in node_name.lower() or 'weather' in node_name.lower():
                # Use search engine
                query = agent_state.get('query', node_name)
                search_results = await self.search_engine.search(query)
                
                if search_results:
                    response_text = self._format_search_results(search_results)
                    references = {
                        str(i+1): result.url 
                        for i, result in enumerate(search_results[:5])
                    }
                else:
                    response_text = f"No search results found for: {query}"
                    references = {}
                
                return {
                    'response': response_text,
                    'references': references,
                    'state': AgentStatusCode.END
                }
            
            # For other nodes, generate a response
            messages = self._prepare_messages(agent_state, node_name)
            response = await model(messages)
            
            return {
                'response': response.content if hasattr(response, 'content') else str(response),
                'state': AgentStatusCode.STREAM_ING
            }
            
        except Exception as e:
            logger.error(f"Error executing node {node_name}: {e}")
            raise
    
    def _format_search_results(self, results: List[Any]) -> str:
        """Format search results into readable text."""
        if not results:
            return "No results found."
        
        formatted = []
        for i, result in enumerate(results[:5], 1):
            formatted.append(f"{i}. {result.title}")
            formatted.append(f"   {result.snippet}")
            formatted.append(f"   Source: {result.url}")
            formatted.append("")
        
        return "\n".join(formatted)
    
    def _prepare_messages(self, agent_state: Dict[str, Any], node_name: str) -> List[Dict]:
        """Prepare messages for model input."""
        messages = []
        
        # Add system message
        messages.append({
            'role': 'system',
            'content': f'You are processing node "{node_name}" in a search graph.'
        })
        
        # Add context from agent state
        if 'query' in agent_state:
            messages.append({
                'role': 'user',
                'content': f'Query: {agent_state["query"]}'
            })
        
        # Add memory context if available
        memory = agent_state.get('memory', {})
        if memory:
            context = json.dumps(memory, indent=2)
            messages.append({
                'role': 'assistant',
                'content': f'Current context:\n{context}'
            })
        
        return messages
    
    def _create_termination_response(
        self, 
        agent_state: Dict[str, Any], 
        visit_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create response when execution is terminated."""
        if self.enable_fallback and self.fallback_cache:
            # Try to use cached response
            current_node = visit_info['node']
            if current_node in self.fallback_cache:
                logger.info(f"Using cached response for {current_node}")
                return self.fallback_cache[current_node]
        
        # Generate summary response
        summary = self._generate_summary(agent_state, visit_info)
        
        return {
            'response': summary,
            'state': AgentStatusCode.END,
            'terminated': True,
            'reason': 'loop_detected' if visit_info.get('loop_detected') else 'timeout'
        }
    
    def _create_timeout_response(
        self, 
        agent_state: Dict[str, Any], 
        node_name: str
    ) -> Dict[str, Any]:
        """Create response for timeout."""
        return {
            'response': f"Processing timeout at node: {node_name}. Partial results may be available.",
            'state': AgentStatusCode.END,
            'terminated': True,
            'reason': 'timeout'
        }
    
    def _create_error_response(
        self, 
        agent_state: Dict[str, Any], 
        node_name: str, 
        error: str
    ) -> Dict[str, Any]:
        """Create response for errors."""
        return {
            'response': f"Error processing node {node_name}: {error}",
            'state': AgentStatusCode.END,
            'terminated': True,
            'reason': 'error',
            'error': error
        }
    
    def _generate_summary(
        self, 
        agent_state: Dict[str, Any], 
        visit_info: Dict[str, Any]
    ) -> str:
        """Generate a summary of the execution."""
        lines = []
        
        # Add query if available
        if 'query' in agent_state:
            lines.append(f"Query: {agent_state['query']}")
            lines.append("")
        
        # Add execution summary
        lines.append("Execution Summary:")
        lines.append(f"- Total node visits: {visit_info['total_visits']}")
        lines.append(f"- Unique nodes: {visit_info['unique_nodes']}")
        lines.append(f"- Execution time: {self.tracker.get_execution_time():.2f}s")
        
        if visit_info.get('loop_detected'):
            lines.append(f"- Loop pattern: {visit_info['loop_pattern']}")
        
        # Add any cached results
        if self.fallback_cache:
            lines.append("\nAvailable results:")
            for node, result in self.fallback_cache.items():
                if result.get('response'):
                    preview = result['response'][:100] + "..." if len(result['response']) > 100 else result['response']
                    lines.append(f"- {node}: {preview}")
        
        return "\n".join(lines)
    
    def reset(self):
        """Reset the execution action."""
        self._reset_tracker()
        self.fallback_cache.clear()
        logger.info("SafeExecutionAction reset")