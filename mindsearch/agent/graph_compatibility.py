"""
Compatibility layer to support both old and new WebSearchGraph implementations.
"""
import logging
from typing import Dict, Any, Optional, Union

from .graph import WebSearchGraph as LegacyWebSearchGraph, ExecutionAction as LegacyExecutionAction
from .web_search_graph import ModularWebSearchGraph
from .execution_action import ImprovedExecutionAction


class CompatibleWebSearchGraph:
    """
    A wrapper that can use either the legacy or new WebSearchGraph implementation.
    """
    
    def __init__(self, use_legacy: bool = False, **kwargs):
        """
        Initialize with either legacy or new implementation.
        
        Args:
            use_legacy: If True, use the legacy implementation
            **kwargs: Additional arguments passed to the implementation
        """
        self.use_legacy = use_legacy
        
        if use_legacy:
            self._impl = LegacyWebSearchGraph()
        else:
            # Extract relevant kwargs for new implementation
            new_kwargs = {
                'max_workers': kwargs.get('max_workers', 10),
                'timeout': kwargs.get('timeout', 60),
                'searcher_factory': kwargs.get('searcher_factory', None)
            }
            self._impl = ModularWebSearchGraph(**new_kwargs)
            
    def __getattr__(self, name):
        """Delegate attribute access to the underlying implementation."""
        return getattr(self._impl, name)
        
    def add_node(self, node_name: str, node_content: str) -> Optional[str]:
        """Add a node with compatibility handling."""
        if self.use_legacy:
            return self._impl.add_node(node_name, node_content)
        else:
            # New implementation returns initial response
            return self._impl.add_node(node_name, node_content)
            
    def node(self, node_name: str) -> Dict[str, Any]:
        """Get node information with compatibility handling."""
        if self.use_legacy:
            # Legacy returns the node dict directly
            return self._impl.nodes.get(node_name, {})
        else:
            # New implementation has a node() method
            return self._impl.node(node_name)


class CompatibleExecutionAction:
    """
    A wrapper that can use either the legacy or new ExecutionAction implementation.
    """
    
    def __init__(self, use_legacy: bool = False, **kwargs):
        """
        Initialize with either legacy or new implementation.
        
        Args:
            use_legacy: If True, use the legacy implementation
            **kwargs: Additional arguments passed to the implementation
        """
        self.use_legacy = use_legacy
        
        if use_legacy:
            self._impl = LegacyExecutionAction(**kwargs)
        else:
            self._impl = ImprovedExecutionAction(**kwargs)
            
    def __getattr__(self, name):
        """Delegate attribute access to the underlying implementation."""
        return getattr(self._impl, name)
        
    def run(self, command: str, local_dict: Dict[str, Any], global_dict: Dict[str, Any], stream_graph: bool = False):
        """Run with compatibility handling."""
        # Ensure WebSearchGraph is available in the namespace
        if not self.use_legacy:
            # For new implementation, use CompatibleWebSearchGraph
            local_dict["WebSearchGraph"] = lambda: CompatibleWebSearchGraph(use_legacy=False)
            global_dict["WebSearchGraph"] = lambda: CompatibleWebSearchGraph(use_legacy=False)
            
        return self._impl.run(command, local_dict, global_dict, stream_graph)


def get_compatible_graph(prefer_legacy: bool = False, **kwargs) -> Union[LegacyWebSearchGraph, ModularWebSearchGraph]:
    """
    Get a WebSearchGraph instance with automatic fallback.
    
    Args:
        prefer_legacy: If True, prefer legacy implementation
        **kwargs: Arguments for the graph
        
    Returns:
        WebSearchGraph instance
    """
    if prefer_legacy:
        try:
            return LegacyWebSearchGraph()
        except Exception as e:
            logging.warning(f"Failed to create legacy graph: {e}, falling back to new implementation")
            return ModularWebSearchGraph(**kwargs)
    else:
        try:
            return ModularWebSearchGraph(**kwargs)
        except Exception as e:
            logging.warning(f"Failed to create new graph: {e}, falling back to legacy implementation")
            return LegacyWebSearchGraph()


def get_compatible_execution_action(prefer_legacy: bool = False, **kwargs) -> Union[LegacyExecutionAction, ImprovedExecutionAction]:
    """
    Get an ExecutionAction instance with automatic fallback.
    
    Args:
        prefer_legacy: If True, prefer legacy implementation
        **kwargs: Arguments for the action
        
    Returns:
        ExecutionAction instance
    """
    if prefer_legacy:
        try:
            return LegacyExecutionAction(**kwargs)
        except Exception as e:
            logging.warning(f"Failed to create legacy action: {e}, falling back to new implementation")
            return ImprovedExecutionAction(**kwargs)
    else:
        try:
            return ImprovedExecutionAction(**kwargs)
        except Exception as e:
            logging.warning(f"Failed to create new action: {e}, falling back to legacy implementation")
            return LegacyExecutionAction(**kwargs)