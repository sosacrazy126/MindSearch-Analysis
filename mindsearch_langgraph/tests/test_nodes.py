"""Tests for LangGraph node implementations."""

import pytest
import asyncio
from datetime import datetime

from src.nodes import (
    initialize_state, plan_search, execute_searches,
    synthesize_answer, error_handler, should_retry,
    has_search_results
)
from src.state import MindSearchState


@pytest.mark.unit
class TestNodes:
    """Test individual node functions."""
    
    @pytest.mark.asyncio
    async def test_initialize_state_node(self):
        """Test state initialization node."""
        initial = {"query": "test query", "max_searches": 15}
        
        state = await initialize_state(initial)
        
        # Verify all fields initialized
        assert state["query"] == "test query"
        assert state["max_searches"] == 15  # Should preserve custom value
        assert state["search_plan"] == []
        assert state["sub_queries"] == []
        assert state["current_sub_query"] == 0
        assert state["search_results"] == {}
        assert state["final_answer"] == ""
        assert state["references"] == {}
        assert state["confidence_score"] == 0.0
        assert state["searches_completed"] == 0
        assert state["visit_count"] == {}
        assert state["errors"] == []
        assert state["retry_count"] == 0
    
    @pytest.mark.asyncio
    async def test_plan_search_node(self, sample_state):
        """Test search planning node."""
        sample_state["query"] = "Python vs JavaScript"
        
        state = await plan_search(sample_state)
        
        # Should decompose query
        assert len(state["sub_queries"]) > 0
        assert len(state["search_plan"]) > 0
        assert state["sub_queries"] == state["search_plan"]
        
        # Should track visit
        assert "plan_search" in state["visit_count"]
        assert state["visit_count"]["plan_search"] == 1
        
        # Multiple visits should increment counter
        state = await plan_search(state)
        assert state["visit_count"]["plan_search"] == 2
    
    @pytest.mark.asyncio
    async def test_plan_search_error_handling(self, sample_state):
        """Test plan_search error handling."""
        # Simulate error by using invalid query type
        sample_state["query"] = None  # This will cause an error
        
        state = await plan_search(sample_state)
        
        # Should handle error gracefully
        assert len(state["errors"]) > 0
        assert "plan_search" in state["errors"][0]
        
        # Should fallback to using original query
        assert state["sub_queries"] == [None]  # Fallback behavior
    
    @pytest.mark.asyncio
    async def test_execute_searches_node(self, sample_state):
        """Test search execution node."""
        sample_state["sub_queries"] = ["Python programming", "JavaScript basics"]
        
        state = await execute_searches(sample_state)
        
        # Should execute searches
        assert state["searches_completed"] > 0
        assert len(state["search_results"]) > 0
        
        # Should have results for each sub-query
        for sub_query in sample_state["sub_queries"]:
            assert sub_query in state["search_results"]
            assert len(state["search_results"][sub_query]) > 0
        
        # Should track visit
        assert "execute_searches" in state["visit_count"]
        assert state["visit_count"]["execute_searches"] == 1
    
    @pytest.mark.asyncio
    async def test_execute_searches_max_limit(self, sample_state):
        """Test that execute_searches respects max_searches limit."""
        sample_state["sub_queries"] = [f"query_{i}" for i in range(20)]
        sample_state["max_searches"] = 5
        
        state = await execute_searches(sample_state)
        
        # Should not exceed max_searches
        assert state["searches_completed"] <= state["max_searches"]
        assert len(state["search_results"]) <= state["max_searches"]
    
    @pytest.mark.asyncio
    async def test_execute_searches_already_completed(self, sample_state):
        """Test that execute_searches doesn't re-run if already completed."""
        sample_state["sub_queries"] = ["test query"]
        sample_state["searches_completed"] = 1
        sample_state["search_results"] = {"test query": [{"title": "Existing"}]}
        
        original_results = sample_state["search_results"].copy()
        
        state = await execute_searches(sample_state)
        
        # Should not execute again
        assert state["search_results"] == original_results
        assert state["searches_completed"] == 1
    
    @pytest.mark.asyncio
    async def test_synthesize_answer_node(self, sample_state):
        """Test answer synthesis node."""
        sample_state["query"] = "What is Python?"
        sample_state["search_results"] = {
            "Python programming": [
                {
                    "title": "Python Language",
                    "url": "https://python.org",
                    "snippet": "Python is a programming language",
                    "source": "test",
                    "timestamp": datetime.now()
                }
            ]
        }
        
        state = await synthesize_answer(sample_state)
        
        # Should synthesize answer
        assert len(state["final_answer"]) > 0
        assert state["confidence_score"] > 0.0
        assert len(state["references"]) > 0
        
        # Should track visit
        assert "synthesize_answer" in state["visit_count"]
        assert state["visit_count"]["synthesize_answer"] == 1
    
    @pytest.mark.asyncio
    async def test_synthesize_answer_no_results(self, sample_state):
        """Test synthesis with no search results."""
        sample_state["query"] = "test query"
        sample_state["search_results"] = {}
        
        state = await synthesize_answer(sample_state)
        
        # Should handle gracefully
        assert "couldn't find" in state["final_answer"].lower()
        assert state["confidence_score"] == 0.0
        assert len(state["references"]) == 0
    
    @pytest.mark.asyncio
    async def test_error_handler_node(self, sample_state):
        """Test error handler node."""
        sample_state["errors"] = ["Test error 1", "Test error 2"]
        sample_state["retry_count"] = 0
        
        state = await error_handler(sample_state)
        
        # Should increment retry count
        assert state["retry_count"] == 1
        
        # Should clear errors for retry
        assert len(state["errors"]) == 0
        
        # Should reset search state
        assert state["searches_completed"] == 0
        assert state["search_results"] == {}
    
    @pytest.mark.asyncio
    async def test_error_handler_max_retries(self, sample_state):
        """Test error handler respects retry limit."""
        sample_state["errors"] = ["Test error"]
        sample_state["retry_count"] = 3  # Already at max
        
        state = await error_handler(sample_state)
        
        # Should not increment beyond max
        assert state["retry_count"] == 3
        
        # Errors should remain
        assert len(state["errors"]) == 1
    
    def test_should_retry_logic(self, sample_state):
        """Test retry decision logic."""
        # No errors, should continue
        sample_state["errors"] = []
        sample_state["retry_count"] = 0
        assert should_retry(sample_state) == "continue"
        
        # Has errors, under retry limit
        sample_state["errors"] = ["error"]
        sample_state["retry_count"] = 1
        assert should_retry(sample_state) == "retry"
        
        # Has errors, at retry limit
        sample_state["errors"] = ["error"]
        sample_state["retry_count"] = 3
        assert should_retry(sample_state) == "continue"
    
    def test_has_search_results_logic(self, sample_state):
        """Test search results check logic."""
        # Has results
        sample_state["search_results"] = {"query": [{"result": "data"}]}
        sample_state["retry_count"] = 0
        assert has_search_results(sample_state) == "synthesize"
        
        # No results, can retry
        sample_state["search_results"] = {}
        sample_state["retry_count"] = 1
        assert has_search_results(sample_state) == "retry"
        
        # No results, max retries
        sample_state["search_results"] = {}
        sample_state["retry_count"] = 3
        assert has_search_results(sample_state) == "end"


@pytest.mark.integration
class TestNodeIntegration:
    """Test node interactions and workflows."""
    
    @pytest.mark.asyncio
    async def test_full_node_flow(self, sample_state):
        """Test complete flow through all nodes."""
        # Initialize
        state = await initialize_state({"query": "What is machine learning?"})
        
        # Plan
        state = await plan_search(state)
        assert len(state["sub_queries"]) > 0
        
        # Execute searches
        state = await execute_searches(state)
        assert len(state["search_results"]) > 0
        
        # Synthesize
        state = await synthesize_answer(state)
        assert len(state["final_answer"]) > 0
        assert state["confidence_score"] > 0.0
        
        # Verify visit counts
        assert state["visit_count"]["plan_search"] == 1
        assert state["visit_count"]["execute_searches"] == 1
        assert state["visit_count"]["synthesize_answer"] == 1
    
    @pytest.mark.asyncio
    async def test_error_retry_flow(self, sample_state):
        """Test error and retry flow."""
        # Simulate error in search
        sample_state["errors"] = ["Search failed"]
        sample_state["retry_count"] = 0
        
        # Error handler should prepare for retry
        state = await error_handler(sample_state)
        assert state["retry_count"] == 1
        assert len(state["errors"]) == 0
        
        # Should be able to retry planning
        state = await plan_search(state)
        assert len(state["sub_queries"]) > 0
        
        # And continue with execution
        state = await execute_searches(state)
        assert state["searches_completed"] > 0
    
    @pytest.mark.asyncio
    async def test_loop_prevention(self, sample_state):
        """Test that nodes prevent infinite loops."""
        # Simulate multiple visits to same node
        for i in range(5):
            sample_state = await plan_search(sample_state)
        
        # Visit count should track all visits
        assert sample_state["visit_count"]["plan_search"] == 5
        
        # In real graph, this would trigger loop prevention
        # The graph itself would prevent further visits
        
        # Test with multiple nodes
        for i in range(3):
            sample_state = await execute_searches(sample_state)
            sample_state = await synthesize_answer(sample_state)
        
        assert sample_state["visit_count"]["execute_searches"] == 3
        assert sample_state["visit_count"]["synthesize_answer"] == 3
    
    @pytest.mark.asyncio
    async def test_parallel_search_execution(self, sample_state, performance_timer):
        """Test that searches execute in parallel."""
        # Multiple sub-queries
        sample_state["sub_queries"] = [
            "query 1", "query 2", "query 3", "query 4", "query 5"
        ]
        
        # Time the execution
        performance_timer.start("parallel_execution")
        state = await execute_searches(sample_state)
        duration = performance_timer.stop("parallel_execution")
        
        # Should complete quickly due to parallel execution
        assert duration < 1.0  # Should be fast with mock engines
        assert len(state["search_results"]) == 5
        assert state["searches_completed"] == 5
    
    @pytest.mark.asyncio
    async def test_state_immutability_pattern(self, sample_state):
        """Test that nodes follow immutability patterns."""
        original_query = sample_state["query"]
        original_errors = sample_state["errors"].copy()
        
        # Each node should return new state, not modify in place
        new_state = await plan_search(sample_state)
        
        # Original should be unchanged
        assert sample_state["query"] == original_query
        assert sample_state["errors"] == original_errors
        
        # New state should have updates
        assert new_state["visit_count"].get("plan_search", 0) > 0
        assert len(new_state["sub_queries"]) > 0


@pytest.mark.unit
class TestNodeHelpers:
    """Test helper functions used by nodes."""
    
    def test_visit_counting_logic(self):
        """Test visit counting implementation."""
        state = {"visit_count": {}}
        
        # First visit
        node_name = "test_node"
        state["visit_count"][node_name] = state["visit_count"].get(node_name, 0) + 1
        assert state["visit_count"][node_name] == 1
        
        # Subsequent visits
        state["visit_count"][node_name] = state["visit_count"].get(node_name, 0) + 1
        assert state["visit_count"][node_name] == 2
        
        # Multiple nodes
        state["visit_count"]["other_node"] = 1
        assert len(state["visit_count"]) == 2
    
    def test_search_completion_tracking(self):
        """Test search completion tracking logic."""
        state = {
            "searches_completed": 0,
            "max_searches": 5,
            "sub_queries": ["q1", "q2", "q3", "q4", "q5", "q6"]
        }
        
        # Simulate search execution
        for i, query in enumerate(state["sub_queries"]):
            if state["searches_completed"] < state["max_searches"]:
                state["searches_completed"] += 1
        
        # Should not exceed max
        assert state["searches_completed"] == 5
        assert state["searches_completed"] <= state["max_searches"]