"""Robust Memory Handler for Structure Validation and Auto-correction."""

import logging
from typing import Dict, Any, List, Optional, Union
import json
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryStructureError(Exception):
    """Raised when memory structure is invalid and cannot be corrected."""
    pass


class RobustMemoryHandler:
    """Handles memory structure validation, correction, and management."""
    
    # Expected memory structure schema
    MEMORY_SCHEMA = {
        'nodes': dict,  # node_id -> node_data
        'edges': dict,  # edge_id -> edge_data
        'current_node': (str, type(None)),
        'history': list,
        'context': dict,
        'references': dict
    }
    
    # Node structure schema
    NODE_SCHEMA = {
        'name': str,
        'content': str,
        'status': int,  # 0: pending, 1: processing, 2: completed
        'result': (str, type(None)),
        'timestamp': (str, type(None)),
        'dependencies': list
    }
    
    @classmethod
    def validate_and_correct(cls, memory: Any) -> Dict[str, Any]:
        """Validate and correct memory structure."""
        # Handle None or non-dict memory
        if memory is None:
            logger.warning("Memory is None, creating default structure")
            return cls.create_default_memory()
        
        if not isinstance(memory, dict):
            logger.warning(f"Memory is not a dict (type: {type(memory)}), creating default")
            return cls.create_default_memory()
        
        # Start with a copy to avoid modifying original
        corrected = memory.copy()
        
        # Ensure all required fields exist with correct types
        for field, expected_type in cls.MEMORY_SCHEMA.items():
            if field not in corrected:
                logger.info(f"Adding missing field: {field}")
                corrected[field] = cls._get_default_value(expected_type)
            else:
                # Validate type
                if not cls._validate_type(corrected[field], expected_type):
                    logger.warning(f"Correcting type for field {field}")
                    corrected[field] = cls._get_default_value(expected_type)
        
        # Validate and correct nodes
        corrected['nodes'] = cls._validate_nodes(corrected.get('nodes', {}))
        
        # Validate and correct edges
        corrected['edges'] = cls._validate_edges(corrected.get('edges', {}))
        
        # Ensure history is a list of valid entries
        corrected['history'] = cls._validate_history(corrected.get('history', []))
        
        # Validate references
        corrected['references'] = cls._validate_references(corrected.get('references', {}))
        
        return corrected
    
    @classmethod
    def create_default_memory(cls) -> Dict[str, Any]:
        """Create a default memory structure."""
        return {
            'nodes': {},
            'edges': {},
            'current_node': None,
            'history': [],
            'context': {},
            'references': {}
        }
    
    @classmethod
    def _get_default_value(cls, expected_type):
        """Get default value for a type."""
        if expected_type == dict:
            return {}
        elif expected_type == list:
            return []
        elif expected_type == str:
            return ""
        elif expected_type == int:
            return 0
        elif isinstance(expected_type, tuple):
            # For Union types, use the first non-None type
            for t in expected_type:
                if t is not type(None):
                    return cls._get_default_value(t)
            return None
        else:
            return None
    
    @classmethod
    def _validate_type(cls, value: Any, expected_type) -> bool:
        """Validate if value matches expected type."""
        if isinstance(expected_type, tuple):
            # Union type
            return any(isinstance(value, t) for t in expected_type)
        else:
            return isinstance(value, expected_type)
    
    @classmethod
    def _validate_nodes(cls, nodes: Any) -> Dict[str, Dict[str, Any]]:
        """Validate and correct nodes structure."""
        if not isinstance(nodes, dict):
            logger.warning("Nodes is not a dict, creating empty dict")
            return {}
        
        validated_nodes = {}
        
        for node_id, node_data in nodes.items():
            if not isinstance(node_data, dict):
                logger.warning(f"Node {node_id} is not a dict, skipping")
                continue
            
            # Ensure all required node fields
            validated_node = {}
            for field, expected_type in cls.NODE_SCHEMA.items():
                if field in node_data:
                    if cls._validate_type(node_data[field], expected_type):
                        validated_node[field] = node_data[field]
                    else:
                        validated_node[field] = cls._get_default_value(expected_type)
                else:
                    validated_node[field] = cls._get_default_value(expected_type)
            
            # Preserve any additional fields
            for field, value in node_data.items():
                if field not in cls.NODE_SCHEMA:
                    validated_node[field] = value
            
            validated_nodes[str(node_id)] = validated_node
        
        return validated_nodes
    
    @classmethod
    def _validate_edges(cls, edges: Any) -> Dict[str, Dict[str, Any]]:
        """Validate and correct edges structure."""
        if not isinstance(edges, dict):
            return {}
        
        validated_edges = {}
        
        for edge_id, edge_data in edges.items():
            if not isinstance(edge_data, dict):
                continue
            
            # Ensure edge has required fields
            validated_edge = {
                'from': edge_data.get('from', ''),
                'to': edge_data.get('to', ''),
                'type': edge_data.get('type', 'default')
            }
            
            # Preserve additional fields
            for field, value in edge_data.items():
                if field not in ['from', 'to', 'type']:
                    validated_edge[field] = value
            
            validated_edges[str(edge_id)] = validated_edge
        
        return validated_edges
    
    @classmethod
    def _validate_history(cls, history: Any) -> List[Dict[str, Any]]:
        """Validate and correct history entries."""
        if not isinstance(history, list):
            return []
        
        validated_history = []
        
        for entry in history:
            if isinstance(entry, dict):
                # Ensure basic fields
                validated_entry = {
                    'timestamp': entry.get('timestamp', datetime.now().isoformat()),
                    'action': entry.get('action', 'unknown'),
                    'node': entry.get('node', ''),
                    'data': entry.get('data', {})
                }
                validated_history.append(validated_entry)
            elif isinstance(entry, str):
                # Convert string entries to proper format
                validated_history.append({
                    'timestamp': datetime.now().isoformat(),
                    'action': 'note',
                    'node': '',
                    'data': {'message': entry}
                })
        
        return validated_history
    
    @classmethod
    def _validate_references(cls, references: Any) -> Dict[str, str]:
        """Validate and correct references."""
        if not isinstance(references, dict):
            return {}
        
        validated_refs = {}
        
        for key, value in references.items():
            # Ensure both key and value are strings
            validated_refs[str(key)] = str(value) if value is not None else ""
        
        return validated_refs
    
    @classmethod
    def add_node(cls, memory: Dict[str, Any], node_id: str, node_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add a node to memory with validation."""
        memory = cls.validate_and_correct(memory)
        
        # Validate node data
        validated_node = {}
        for field, expected_type in cls.NODE_SCHEMA.items():
            if field in node_data:
                validated_node[field] = node_data[field]
            else:
                validated_node[field] = cls._get_default_value(expected_type)
        
        # Add timestamp if not present
        if not validated_node.get('timestamp'):
            validated_node['timestamp'] = datetime.now().isoformat()
        
        memory['nodes'][str(node_id)] = validated_node
        
        # Add to history
        memory['history'].append({
            'timestamp': datetime.now().isoformat(),
            'action': 'add_node',
            'node': str(node_id),
            'data': {'name': validated_node.get('name', '')}
        })
        
        return memory
    
    @classmethod
    def update_node_status(cls, memory: Dict[str, Any], node_id: str, status: int, result: Optional[str] = None) -> Dict[str, Any]:
        """Update node status in memory."""
        memory = cls.validate_and_correct(memory)
        
        node_id = str(node_id)
        if node_id in memory['nodes']:
            memory['nodes'][node_id]['status'] = status
            if result is not None:
                memory['nodes'][node_id]['result'] = result
            memory['nodes'][node_id]['timestamp'] = datetime.now().isoformat()
            
            # Add to history
            memory['history'].append({
                'timestamp': datetime.now().isoformat(),
                'action': 'update_status',
                'node': node_id,
                'data': {'status': status, 'has_result': result is not None}
            })
        
        return memory
    
    @classmethod
    def set_current_node(cls, memory: Dict[str, Any], node_id: Optional[str]) -> Dict[str, Any]:
        """Set the current active node."""
        memory = cls.validate_and_correct(memory)
        
        memory['current_node'] = str(node_id) if node_id is not None else None
        
        # Add to history
        memory['history'].append({
            'timestamp': datetime.now().isoformat(),
            'action': 'set_current',
            'node': str(node_id) if node_id else '',
            'data': {}
        })
        
        return memory
    
    @classmethod
    def add_reference(cls, memory: Dict[str, Any], ref_id: str, url: str) -> Dict[str, Any]:
        """Add a reference URL to memory."""
        memory = cls.validate_and_correct(memory)
        
        memory['references'][str(ref_id)] = str(url)
        
        return memory
    
    @classmethod
    def get_pending_nodes(cls, memory: Dict[str, Any]) -> List[str]:
        """Get list of pending nodes."""
        memory = cls.validate_and_correct(memory)
        
        pending = []
        for node_id, node_data in memory['nodes'].items():
            if node_data.get('status', 0) == 0:
                pending.append(node_id)
        
        return pending
    
    @classmethod
    def get_completed_nodes(cls, memory: Dict[str, Any]) -> List[str]:
        """Get list of completed nodes."""
        memory = cls.validate_and_correct(memory)
        
        completed = []
        for node_id, node_data in memory['nodes'].items():
            if node_data.get('status', 0) == 2:
                completed.append(node_id)
        
        return completed
    
    @classmethod
    def summarize_memory(cls, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of the memory state."""
        memory = cls.validate_and_correct(memory)
        
        # Count nodes by status
        status_counts = defaultdict(int)
        for node_data in memory['nodes'].values():
            status = node_data.get('status', 0)
            status_counts[status] += 1
        
        return {
            'total_nodes': len(memory['nodes']),
            'total_edges': len(memory['edges']),
            'current_node': memory['current_node'],
            'nodes_by_status': {
                'pending': status_counts[0],
                'processing': status_counts[1],
                'completed': status_counts[2]
            },
            'history_length': len(memory['history']),
            'references_count': len(memory['references'])
        }
    
    @classmethod
    def export_memory(cls, memory: Dict[str, Any], include_history: bool = False) -> str:
        """Export memory to JSON string."""
        memory = cls.validate_and_correct(memory)
        
        export_data = {
            'nodes': memory['nodes'],
            'edges': memory['edges'],
            'current_node': memory['current_node'],
            'references': memory['references'],
            'context': memory['context']
        }
        
        if include_history:
            export_data['history'] = memory['history']
        
        return json.dumps(export_data, indent=2)
    
    @classmethod
    def import_memory(cls, json_str: str) -> Dict[str, Any]:
        """Import memory from JSON string."""
        try:
            data = json.loads(json_str)
            return cls.validate_and_correct(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return cls.create_default_memory()


class MemoryAdapter:
    """Adapter to convert between different memory formats."""
    
    @staticmethod
    def from_agent_state(agent_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert agent state to standard memory format."""
        memory = RobustMemoryHandler.create_default_memory()
        
        # Convert adjacency list to nodes
        if 'adj' in agent_state and isinstance(agent_state['adj'], dict):
            for node_id, node_data in agent_state['adj'].items():
                if isinstance(node_data, dict):
                    memory = RobustMemoryHandler.add_node(
                        memory,
                        node_id,
                        {
                            'name': node_data.get('name', f'node_{node_id}'),
                            'content': node_data.get('content', ''),
                            'status': node_data.get('status', 0),
                            'result': node_data.get('result'),
                            'dependencies': node_data.get('dependencies', [])
                        }
                    )
        
        # Convert memory field if present
        if 'memory' in agent_state and isinstance(agent_state['memory'], dict):
            memory['context'] = agent_state['memory']
        
        # Set current node
        if 'current_node' in agent_state:
            memory = RobustMemoryHandler.set_current_node(memory, agent_state['current_node'])
        
        return memory
    
    @staticmethod
    def to_agent_state(memory: Dict[str, Any], base_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Convert standard memory format to agent state."""
        if base_state is None:
            agent_state = {}
        else:
            agent_state = base_state.copy()
        
        # Convert nodes to adjacency list
        adj = {}
        for node_id, node_data in memory['nodes'].items():
            adj[node_id] = {
                'name': node_data['name'],
                'content': node_data['content'],
                'status': node_data['status'],
                'result': node_data.get('result')
            }
        
        agent_state['adj'] = adj
        agent_state['memory'] = memory['context']
        agent_state['current_node'] = memory['current_node']
        
        return agent_state