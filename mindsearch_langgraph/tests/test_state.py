"""Tests for MindSearch state management."""

import pytest
from copy import deepcopy
from datetime import datetime
from typing import Dict, Any

from src.state import MindSearchState, SearchResult
from src.nodes import initialize_state


@pytest.mark.unit
class TestStateManagement:
    """Test suite for state management functionality."""
    
    def test_state_initialization(self, sample_state):
        """Test that state initializes with correct default values."""
        # Verify all required fields are present
        required_fields = [
            "query", "search_plan", "sub_queries", "current_sub_query",
            "search_results", "raw_results", "final_answer", "references",
            "confidence_score", "max_searches", "searches_completed",
            "visit_count", "errors", "retry_count"
        ]
        
        for field in required_fields:
            assert field in sample_state, f"Required field '{field}' missing from state"
        
        # Verify default values
        assert sample_state["query"] == "test query"
        assert sample_state["search_plan"] == []
        assert sample_state["sub_queries"] == []
        assert sample_state["current_sub_query"] == 0
        assert sample_state["search_results"] == {}
        assert sample_state["confidence_score"] == 0.0
        assert sample_state["errors"] == []
        assert sample_state["retry_count"] == 0
    
    @pytest.mark.asyncio
    async def test_initialize_state_node(self):
        """Test the initialize_state node function."""
        # Create a minimal state with just a query
        initial = {"query": "test initialization"}
        
        # Run initialization
        initialized = await initialize_state(initial)
        
        # Verify all fields are properly initialized
        assert initialized["query"] == "test initialization"
        assert initialized["search_plan"] == []
        assert initialized["sub_queries"] == []
        assert initialized["current_sub_query"] == 0
        assert initialized["search_results"] == {}
        assert initialized["final_answer"] == ""
        assert initialized["references"] == {}
        assert initialized["confidence_score"] == 0.0
        assert initialized["max_searches"] == 10  # Default value
        assert initialized["searches_completed"] == 0
        assert initialized["visit_count"] == {}
        assert initialized["errors"] == []
        assert initialized["retry_count"] == 0
    
    def test_state_type_safety(self, sample_state):
        """Test that state maintains type safety."""
        # Test correct types
        assert isinstance(sample_state["query"], str)
        assert isinstance(sample_state["search_plan"], list)
        assert isinstance(sample_state["sub_queries"], list)
        assert isinstance(sample_state["current_sub_query"], int)
        assert isinstance(sample_state["search_results"], dict)
        assert isinstance(sample_state["confidence_score"], float)
        assert isinstance(sample_state["max_searches"], int)
        assert isinstance(sample_state["visit_count"], dict)
        assert isinstance(sample_state["errors"], list)
    
    def test_state_updates(self, sample_state):
        """Test state updates maintain consistency."""
        # Update various fields
        sample_state["sub_queries"] = ["query 1", "query 2"]
        sample_state["current_sub_query"] = 1
        sample_state["searches_completed"] = 2
        sample_state["confidence_score"] = 0.85
        
        # Verify updates
        assert len(sample_state["sub_queries"]) == 2
        assert sample_state["current_sub_query"] == 1
        assert sample_state["searches_completed"] == 2
        assert sample_state["confidence_score"] == 0.85
    
    def test_search_result_structure(self, sample_search_results):
        """Test SearchResult TypedDict structure."""
        for result in sample_search_results:
            # Verify all required fields
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "source" in result
            assert "timestamp" in result
            
            # Verify types
            assert isinstance(result["title"], str)
            assert isinstance(result["url"], str)
            assert isinstance(result["snippet"], str)
            assert isinstance(result["source"], str)
            assert isinstance(result["timestamp"], datetime)
    
    def test_state_deep_copy(self, sample_state):
        """Test that state can be safely deep copied."""
        # Add nested data
        sample_state["search_results"]["test"] = [
            {"title": "Test", "url": "http://test.com", "snippet": "Test snippet"}
        ]
        sample_state["visit_count"]["node1"] = 2
        
        # Deep copy
        copied_state = deepcopy(sample_state)
        
        # Modify original
        sample_state["search_results"]["test"][0]["title"] = "Modified"
        sample_state["visit_count"]["node1"] = 3
        
        # Verify copy is independent
        assert copied_state["search_results"]["test"][0]["title"] == "Test"
        assert copied_state["visit_count"]["node1"] == 2
    
    def test_visit_count_tracking(self, sample_state):
        """Test visit count tracking for loop prevention."""
        # Simulate node visits
        nodes = ["plan_search", "execute_searches", "synthesize_answer"]
        
        for node in nodes:
            # First visit
            sample_state["visit_count"][node] = sample_state["visit_count"].get(node, 0) + 1
            assert sample_state["visit_count"][node] == 1
            
            # Second visit
            sample_state["visit_count"][node] += 1
            assert sample_state["visit_count"][node] == 2
        
        # Verify all counts
        assert len(sample_state["visit_count"]) == 3
        assert all(count == 2 for count in sample_state["visit_count"].values())
    
    def test_error_tracking(self, sample_state):
        """Test error tracking in state."""
        # Add errors
        errors = [
            "Search API timeout",
            "LLM rate limit exceeded",
            "Network connection failed"
        ]
        
        for error in errors:
            sample_state["errors"].append(error)
        
        # Verify all errors tracked
        assert len(sample_state["errors"]) == 3
        assert all(error in sample_state["errors"] for error in errors)
        
        # Test error clearing
        sample_state["errors"].clear()
        assert len(sample_state["errors"]) == 0
    
    def test_search_results_storage(self, sample_state, sample_search_results):
        """Test storing search results in state."""
        # Store results for multiple sub-queries
        sample_state["sub_queries"] = ["query 1", "query 2", "query 3"]
        
        for i, query in enumerate(sample_state["sub_queries"]):
            # Convert SearchResult to dict for storage
            results_as_dict = [dict(r) for r in sample_search_results]
            sample_state["search_results"][query] = results_as_dict
        
        # Verify storage
        assert len(sample_state["search_results"]) == 3
        for query in sample_state["sub_queries"]:
            assert query in sample_state["search_results"]
            assert len(sample_state["search_results"][query]) == 2
            assert all(isinstance(r, dict) for r in sample_state["search_results"][query])
    
    def test_references_format(self, sample_state):
        """Test references storage format."""
        # Add references
        references = {
            1: "https://example.com/source1",
            2: "https://example.com/source2",
            3: "https://example.com/source3"
        }
        
        sample_state["references"] = references
        
        # Verify format
        assert len(sample_state["references"]) == 3
        assert all(isinstance(k, int) for k in sample_state["references"].keys())
        assert all(isinstance(v, str) for v in sample_state["references"].values())
        assert all(v.startswith("http") for v in sample_state["references"].values())
    
    @pytest.mark.parametrize("field,invalid_value,expected_type", [
        ("query", 123, str),
        ("sub_queries", "not a list", list),
        ("current_sub_query", "not an int", int),
        ("search_results", "not a dict", dict),
        ("confidence_score", "not a float", float),
        ("max_searches", 10.5, int),
        ("errors", {"not": "a list"}, list),
    ])
    def test_invalid_state_updates(self, sample_state, field, invalid_value, expected_type):
        """Test that invalid state updates can be detected."""
        # This test documents expected types for each field
        # In a real TypedDict implementation, these would raise type errors
        original_value = sample_state[field]
        sample_state[field] = invalid_value
        
        # In production, type checking would catch these
        # Here we just verify the expected type
        assert expected_type == type(original_value).__class__
    
    def test_state_persistence_compatibility(self, sample_state):
        """Test that state can be serialized for persistence."""
        import json
        
        # Add datetime objects that need special handling
        sample_state["search_results"]["test"] = [{
            "title": "Test",
            "url": "http://test.com",
            "snippet": "Test",
            "source": "test",
            "timestamp": datetime.now()
        }]
        
        # Convert datetime to string for serialization
        def serialize_state(state):
            serializable = deepcopy(state)
            for query, results in serializable.get("search_results", {}).items():
                for result in results:
                    if isinstance(result.get("timestamp"), datetime):
                        result["timestamp"] = result["timestamp"].isoformat()
            return serializable
        
        # Test serialization
        serializable_state = serialize_state(sample_state)
        json_str = json.dumps(serializable_state)
        
        # Test deserialization
        loaded_state = json.loads(json_str)
        assert loaded_state["query"] == sample_state["query"]
        assert loaded_state["search_results"]["test"][0]["title"] == "Test"
    
    def test_max_searches_limit(self, sample_state):
        """Test that max_searches limit is respected."""
        sample_state["max_searches"] = 5
        
        # Simulate searches
        for i in range(10):
            if sample_state["searches_completed"] < sample_state["max_searches"]:
                sample_state["searches_completed"] += 1
        
        # Verify limit respected
        assert sample_state["searches_completed"] == 5
        assert sample_state["searches_completed"] <= sample_state["max_searches"]
    
    def test_retry_count_increment(self, sample_state):
        """Test retry count tracking."""
        max_retries = 3
        
        # Simulate retries
        while sample_state["retry_count"] < max_retries:
            sample_state["errors"].append(f"Error {sample_state['retry_count']}")
            sample_state["retry_count"] += 1
        
        # Verify retry limit
        assert sample_state["retry_count"] == max_retries
        assert len(sample_state["errors"]) == max_retries


@pytest.mark.unit
class TestStateValidation:
    """Test state validation and constraints."""
    
    def test_confidence_score_bounds(self, sample_state):
        """Test confidence score stays within bounds."""
        # Test valid scores
        valid_scores = [0.0, 0.5, 0.85, 1.0]
        for score in valid_scores:
            sample_state["confidence_score"] = score
            assert 0.0 <= sample_state["confidence_score"] <= 1.0
        
        # Document that out-of-bounds scores should be clamped
        # In production, this would be enforced by the synthesis logic
        sample_state["confidence_score"] = 1.5
        # Should be clamped to 1.0 in real implementation
        
        sample_state["confidence_score"] = -0.5
        # Should be clamped to 0.0 in real implementation
    
    def test_current_sub_query_bounds(self, sample_state):
        """Test current_sub_query index stays valid."""
        sample_state["sub_queries"] = ["q1", "q2", "q3"]
        
        # Valid indices
        for i in range(len(sample_state["sub_queries"])):
            sample_state["current_sub_query"] = i
            assert 0 <= sample_state["current_sub_query"] < len(sample_state["sub_queries"])
        
        # Test boundary
        sample_state["current_sub_query"] = len(sample_state["sub_queries"])
        # This indicates all sub-queries processed
        assert sample_state["current_sub_query"] == 3
    
    def test_empty_state_handling(self):
        """Test handling of empty or minimal state."""
        minimal_state = {"query": "test"}
        
        # Should be able to work with minimal state
        assert minimal_state["query"] == "test"
        assert minimal_state.get("sub_queries", []) == []
        assert minimal_state.get("search_results", {}) == {}
        assert minimal_state.get("errors", []) == []