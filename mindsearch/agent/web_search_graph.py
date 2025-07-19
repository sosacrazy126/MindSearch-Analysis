"""
Modular WebSearchGraph implementation with improved error handling and flexibility.
"""
import asyncio
import logging
import queue
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, Future
from copy import deepcopy
from typing import Dict, List, Optional, Any, Callable, Union, Tuple

from lagent.schema import AgentMessage, AgentStatusCode


class SearchNode:
    """Represents a node in the search graph."""
    
    def __init__(self, name: str, content: str, node_type: str = "search"):
        self.name = name
        self.content = content
        self.type = node_type
        self.response: Optional[Dict[str, Any]] = None
        self.memory: Dict[str, Any] = {}
        self.state: str = "pending"  # pending, searching, completed, failed
        self.error: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation."""
        return {
            "content": self.content,
            "type": self.type,
            "response": self.response,
            "memory": self.memory,
            "state": self.state,
            "error": self.error
        }


class ModularWebSearchGraph:
    """
    A more modular and robust implementation of WebSearchGraph.
    
    This implementation provides:
    - Better error handling
    - Modular node management
    - Flexible search execution
    - Improved state tracking
    """
    
    def __init__(self, 
                 max_workers: int = 10,
                 timeout: int = 60,
                 searcher_factory: Optional[Callable] = None):
        """
        Initialize the search graph.
        
        Args:
            max_workers: Maximum number of concurrent search workers
            timeout: Timeout for search operations in seconds
            searcher_factory: Factory function to create searcher instances
        """
        self.nodes: Dict[str, SearchNode] = {}
        self.adjacency_list: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.timeout = timeout
        self.searcher_factory = searcher_factory
        self._search_futures: Dict[str, Future] = {}
        self._search_results: queue.Queue = queue.Queue()
        
    def add_root_node(self, node_content: str, node_name: str = "root") -> None:
        """Add the root node to the graph."""
        node = SearchNode(node_name, node_content, "root")
        node.state = "completed"
        self.nodes[node_name] = node
        
    def add_node(self, node_name: str, node_content: str) -> Optional[str]:
        """
        Add a search node and optionally start searching.
        
        Args:
            node_name: Name of the node
            node_content: Search query content
            
        Returns:
            Initial response or None
        """
        if node_name in self.nodes:
            logging.warning(f"Node {node_name} already exists")
            return None
            
        node = SearchNode(node_name, node_content, "search")
        self.nodes[node_name] = node
        
        # Start search if searcher is available
        if self.searcher_factory:
            self._start_search(node)
            
        return f"Search started for: {node_content}"
        
    def add_response_node(self, node_name: str = "response") -> None:
        """Add a response node to indicate completion."""
        node = SearchNode(node_name, "Final response", "response")
        node.state = "completed"
        self.nodes[node_name] = node
        
    def add_edge(self, start_node: str, end_node: str) -> None:
        """Add an edge between two nodes."""
        if start_node not in self.nodes:
            raise ValueError(f"Start node {start_node} not found")
        if end_node not in self.nodes:
            raise ValueError(f"End node {end_node} not found")
            
        edge = {
            "name": end_node,
            "state": 1  # 1: in progress, 2: not started, 3: completed
        }
        self.adjacency_list[start_node].append(edge)
        
    def node(self, node_name: str) -> Dict[str, Any]:
        """Get node information."""
        if node_name not in self.nodes:
            return {"error": f"Node {node_name} not found"}
            
        node = self.nodes[node_name]
        node_dict = node.to_dict()
        
        # Add adjacency information
        if node_name in self.adjacency_list:
            node_dict["adjacency"] = [edge["name"] for edge in self.adjacency_list[node_name]]
            
        return node_dict
        
    def reset(self) -> None:
        """Reset the graph to initial state."""
        self.nodes.clear()
        self.adjacency_list.clear()
        self._search_futures.clear()
        # Clear the queue
        while not self._search_results.empty():
            try:
                self._search_results.get_nowait()
            except queue.Empty:
                break
                
    def _start_search(self, node: SearchNode) -> None:
        """Start an asynchronous search for a node."""
        if not self.searcher_factory:
            logging.warning("No searcher factory provided")
            node.state = "failed"
            node.error = "No searcher available"
            return
            
        def search_task():
            try:
                node.state = "searching"
                searcher = self.searcher_factory()
                # Perform search - this is a placeholder for actual search logic
                result = self._perform_search(searcher, node.content)
                node.response = result
                node.state = "completed"
                self._search_results.put((node.name, result, None))
            except Exception as e:
                node.state = "failed"
                node.error = str(e)
                self._search_results.put((node.name, None, e))
                
        future = self.executor.submit(search_task)
        self._search_futures[node.name] = future
        
    def _perform_search(self, searcher: Any, query: str) -> Dict[str, Any]:
        """
        Perform the actual search operation.
        
        This is a placeholder that should be overridden or configured
        based on the actual searcher implementation.
        """
        # Placeholder implementation
        return {
            "content": f"Search results for: {query}",
            "ref2url": {},
            "status": "completed"
        }
        
    def wait_for_searches(self, timeout: Optional[int] = None) -> List[Tuple[str, Any, Any]]:
        """
        Wait for all pending searches to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            List of (node_name, result, error) tuples
        """
        results = []
        timeout = timeout or self.timeout
        
        # Wait for all futures to complete
        for node_name, future in self._search_futures.items():
            try:
                future.result(timeout=timeout)
            except Exception as e:
                logging.error(f"Search for {node_name} failed: {e}")
                
        # Collect all results
        while not self._search_results.empty():
            try:
                results.append(self._search_results.get_nowait())
            except queue.Empty:
                break
                
        return results
        
    def get_graph_state(self) -> Dict[str, Any]:
        """Get the current state of the entire graph."""
        return {
            "nodes": {name: node.to_dict() for name, node in self.nodes.items()},
            "adjacency_list": dict(self.adjacency_list),
            "pending_searches": list(self._search_futures.keys()),
            "completed_nodes": [name for name, node in self.nodes.items() if node.state == "completed"],
            "failed_nodes": [name for name, node in self.nodes.items() if node.state == "failed"]
        }
        
    def __del__(self):
        """Cleanup resources."""
        self.executor.shutdown(wait=False)