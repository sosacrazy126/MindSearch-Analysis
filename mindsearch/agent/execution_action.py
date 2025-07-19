"""
Improved ExecutionAction for handling WebSearchGraph operations.
"""
import re
import logging
from typing import Dict, Any, List, Optional, Generator
from copy import deepcopy

from lagent.actions import BaseAction
from lagent.schema import AgentMessage, AgentStatusCode

from .web_search_graph import ModularWebSearchGraph


class ImprovedExecutionAction(BaseAction):
    """
    An improved execution action that handles WebSearchGraph operations
    with better error handling and flexibility.
    """
    
    def __init__(self, 
                 searcher_cfg: Optional[Dict[str, Any]] = None,
                 max_workers: int = 10,
                 timeout: int = 60,
                 name: str = "execution"):
        """
        Initialize the execution action.
        
        Args:
            searcher_cfg: Configuration for searcher agents
            max_workers: Maximum concurrent workers
            timeout: Timeout for operations
            name: Name of the action
        """
        super().__init__(name=name)
        self.searcher_cfg = searcher_cfg or {}
        self.max_workers = max_workers
        self.timeout = timeout
        
    def extract_code(self, text: str) -> str:
        """Extract code from markdown or backtick blocks."""
        # Remove import statements that might conflict
        text = re.sub(r"from ([\w.]+) import WebSearchGraph", "", text)
        text = re.sub(r"import WebSearchGraph", "", text)
        
        # Try to extract from triple backticks first
        triple_match = re.search(r"```(?:python)?\n(.+?)```", text, re.DOTALL)
        if triple_match:
            return triple_match.group(1).strip()
            
        # Try single backticks
        single_match = re.search(r"`([^`]+)`", text, re.DOTALL)
        if single_match:
            return single_match.group(1).strip()
            
        # Return as-is if no code blocks found
        return text.strip()
        
    def validate_code(self, code: str) -> List[str]:
        """
        Validate the code for common issues.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check for required graph operations
        if "graph = " not in code and "WebSearchGraph()" not in code:
            errors.append("Code must create a WebSearchGraph instance")
            
        # Check for dangerous operations
        dangerous_ops = ["__import__", "eval", "exec", "compile", "open", "file"]
        for op in dangerous_ops:
            if op in code and op != "exec":  # We use exec internally
                errors.append(f"Dangerous operation '{op}' not allowed")
                
        return errors
        
    def run(self, 
            command: str, 
            local_dict: Dict[str, Any], 
            global_dict: Dict[str, Any], 
            stream_graph: bool = False) -> Generator[Any, None, Any]:
        """
        Execute the WebSearchGraph command with improved error handling.
        
        Args:
            command: Code to execute
            local_dict: Local variables dictionary
            global_dict: Global variables dictionary
            stream_graph: Whether to stream intermediate results
            
        Yields:
            Intermediate results if streaming
            
        Returns:
            Final results tuple
        """
        try:
            # Extract and validate code
            code = self.extract_code(command)
            errors = self.validate_code(code)
            if errors:
                error_msg = "Code validation failed:\n" + "\n".join(errors)
                logging.error(error_msg)
                raise ValueError(error_msg)
            
            # Create graph instance if not provided
            if "graph" not in local_dict:
                local_dict["graph"] = ModularWebSearchGraph(
                    max_workers=self.max_workers,
                    timeout=self.timeout,
                    searcher_factory=self._create_searcher_factory()
                )
            
            # Ensure WebSearchGraph is available in the namespace
            local_dict["WebSearchGraph"] = ModularWebSearchGraph
            global_dict["WebSearchGraph"] = ModularWebSearchGraph
            
            # Execute the code
            logging.info(f"Executing code:\n{code}")
            exec(code, global_dict, local_dict)
            
            # Extract graph instance
            graph = local_dict.get("graph")
            if not graph:
                raise ValueError("No graph instance found after execution")
            
            # Extract node references from code
            node_refs = self._extract_node_references(code)
            
            # Wait for any pending searches
            if hasattr(graph, 'wait_for_searches'):
                search_results = graph.wait_for_searches()
                for node_name, result, error in search_results:
                    if error:
                        logging.error(f"Search failed for {node_name}: {error}")
                    else:
                        logging.info(f"Search completed for {node_name}")
            
            # Stream intermediate results if requested
            if stream_graph:
                yield from self._stream_graph_updates(graph)
            
            # Prepare final results
            results = []
            for node_ref in node_refs:
                node_data = graph.node(node_ref)
                if "error" not in node_data:
                    results.append(node_data)
                else:
                    logging.warning(f"Node {node_ref} not found")
                    results.append({"error": f"Node {node_ref} not found"})
            
            # Get final graph state
            if hasattr(graph, 'get_graph_state'):
                graph_state = graph.get_graph_state()
            else:
                # Fallback for compatibility
                graph_state = {
                    "nodes": graph.nodes if hasattr(graph, 'nodes') else {},
                    "adjacency_list": dict(graph.adjacency_list) if hasattr(graph, 'adjacency_list') else {}
                }
            
            return results, graph_state.get("nodes", {}), graph_state.get("adjacency_list", {})
            
        except Exception as e:
            logging.error(f"Execution failed: {e}", exc_info=True)
            raise
            
    def _create_searcher_factory(self):
        """Create a factory function for searcher instances."""
        def factory():
            # This is a placeholder - should be configured with actual searcher
            # For now, return a mock searcher
            class MockSearcher:
                def search(self, query):
                    return {
                        "content": f"Mock results for: {query}",
                        "ref2url": {}
                    }
            return MockSearcher()
        return factory
        
    def _extract_node_references(self, code: str) -> List[str]:
        """Extract node references from code."""
        # Match patterns like graph.node("node_name") or graph.node('node_name')
        pattern = r'graph\.node\s*\(\s*["\']([^"\']+)["\']\s*\)'
        matches = re.findall(pattern, code)
        return matches
        
    def _stream_graph_updates(self, graph) -> Generator[AgentMessage, None, None]:
        """Stream graph updates as they occur."""
        if hasattr(graph, 'get_graph_state'):
            state = graph.get_graph_state()
            
            # Yield update for each completed node
            for node_name in state.get("completed_nodes", []):
                if node_name not in ["root", "response"]:
                    yield AgentMessage(
                        sender=self.name,
                        content={"current_node": node_name},
                        formatted={
                            "node": state["nodes"].get(node_name, {}),
                            "adjacency_list": state["adjacency_list"]
                        },
                        stream_state=AgentStatusCode.STREAM_ING
                    )