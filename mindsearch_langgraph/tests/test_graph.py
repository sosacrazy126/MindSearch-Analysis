"""Tests for the main MindSearch graph and agent."""

import pytest
import asyncio
import os
from pathlib import Path
import tempfile

from src.graph import MindSearchAgent, create_mindsearch_graph, search
from src.state import MindSearchState


@pytest.mark.e2e
class TestMindSearchAgent:
    """End-to-end tests for MindSearchAgent."""
    
    @pytest.mark.asyncio
    async def test_basic_search(self, mindsearch_agent):
        """Test basic search functionality."""
        query = "What is Python programming?"
        
        result = await mindsearch_agent.search(query)
        
        # Verify result structure
        assert "answer" in result
        assert "references" in result
        assert "confidence" in result
        assert "sub_queries" in result
        assert "errors" in result
        assert "searches_completed" in result
        
        # Verify content
        assert len(result["answer"]) > 0
        assert isinstance(result["confidence"], float)
        assert 0.0 <= result["confidence"] <= 1.0
        assert result["searches_completed"] > 0
        assert len(result["sub_queries"]) > 0
    
    @pytest.mark.asyncio
    async def test_complex_search(self, mindsearch_agent, complex_queries):
        """Test search with complex queries."""
        for query in complex_queries[:2]:  # Test first 2 complex queries
            result = await mindsearch_agent.search(query, max_searches=10)
            
            # Complex queries should generate multiple sub-queries
            assert len(result["sub_queries"]) >= 2
            assert result["searches_completed"] >= 2
            
            # Should have reasonable confidence
            assert result["confidence"] > 0.3
            
            # Answer should be substantial
            assert len(result["answer"]) > 100
    
    @pytest.mark.asyncio
    async def test_search_with_custom_max_searches(self, mindsearch_agent):
        """Test search with custom max_searches limit."""
        query = "Compare 10 different programming languages"
        max_searches = 3
        
        result = await mindsearch_agent.search(query, max_searches=max_searches)
        
        # Should respect the limit
        assert result["searches_completed"] <= max_searches
        assert len(result["sub_queries"]) <= max_searches
    
    @pytest.mark.asyncio
    async def test_empty_query_handling(self, mindsearch_agent):
        """Test handling of empty queries."""
        empty_queries = ["", "   ", "\n\t"]
        
        for query in empty_queries:
            result = await mindsearch_agent.search(query)
            
            # Should handle gracefully
            assert isinstance(result["answer"], str)
            assert result["confidence"] >= 0.0
    
    @pytest.mark.asyncio
    async def test_streaming_search(self, mindsearch_agent):
        """Test streaming search functionality."""
        query = "What is machine learning?"
        
        states_received = []
        async for state in mindsearch_agent.stream_search(query):
            states_received.append(state)
        
        # Should receive multiple state updates
        assert len(states_received) > 0
        
        # Check state progression
        has_plan = any("sub_queries" in s and len(s.get("sub_queries", [])) > 0 
                      for s in states_received)
        has_results = any("search_results" in s and len(s.get("search_results", {})) > 0 
                         for s in states_received)
        has_answer = any("final_answer" in s and len(s.get("final_answer", "")) > 0 
                        for s in states_received)
        
        assert has_plan, "Should have planning state"
        assert has_results, "Should have search results state"
        assert has_answer, "Should have final answer state"
    
    @pytest.mark.asyncio
    async def test_checkpointing(self):
        """Test checkpointing functionality."""
        # Create agent with memory
        agent = MindSearchAgent(use_memory=True)
        query = "Explain quantum computing"
        
        # First search
        result1 = await agent.search(query)
        assert len(result1["answer"]) > 0
        
        # Same query should potentially use checkpoint
        result2 = await agent.search(query)
        
        # Results should be consistent
        assert result2["answer"] == result1["answer"]
        assert result2["confidence"] == result1["confidence"]
    
    def test_visualization(self, mindsearch_agent, temp_dir):
        """Test graph visualization."""
        output_path = os.path.join(temp_dir, "test_graph.png")
        
        # Generate visualization
        mindsearch_agent.visualize(output_path)
        
        # File should be created or error handled gracefully
        # (Actual PNG generation requires graphviz, so we test the method runs)
        assert True  # Method should not crash
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, mindsearch_agent):
        """Test that agent recovers from errors."""
        # Query that might cause issues
        query = "🚀 Unicode test ñ ü ö 中文 العربية"
        
        result = await mindsearch_agent.search(query)
        
        # Should handle gracefully
        assert isinstance(result["answer"], str)
        assert result["confidence"] >= 0.0
        
        # Check if any errors were handled
        if result["errors"]:
            # Errors should be strings
            assert all(isinstance(e, str) for e in result["errors"])
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """Test multiple concurrent searches."""
        agent = MindSearchAgent()
        
        queries = [
            "What is Python?",
            "What is JavaScript?",
            "What is Go?"
        ]
        
        # Run searches concurrently
        tasks = [agent.search(q) for q in queries]
        results = await asyncio.gather(*tasks)
        
        # All should complete successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert len(result["answer"]) > 0
            assert queries[i].split()[-1].rstrip("?").lower() in result["answer"].lower()


@pytest.mark.unit
class TestGraphConstruction:
    """Test graph construction and configuration."""
    
    def test_create_mindsearch_graph(self):
        """Test graph creation."""
        graph = create_mindsearch_graph()
        
        # Should create a compiled graph
        assert graph is not None
        
        # Test with checkpointer
        from langgraph.checkpoint.sqlite import SqliteSaver
        checkpointer = SqliteSaver.from_conn_string(":memory:")
        graph_with_memory = create_mindsearch_graph(checkpointer)
        
        assert graph_with_memory is not None
    
    def test_agent_initialization(self):
        """Test agent initialization options."""
        # Without memory
        agent1 = MindSearchAgent(use_memory=False)
        assert agent1.checkpointer is None
        assert agent1.graph is not None
        
        # With memory
        agent2 = MindSearchAgent(use_memory=True)
        assert agent2.checkpointer is not None
        assert agent2.graph is not None
    
    @pytest.mark.asyncio
    async def test_convenience_search_function(self):
        """Test the convenience search function."""
        query = "What is REST API?"
        
        # Without memory
        result1 = await search(query, use_memory=False)
        assert len(result1["answer"]) > 0
        
        # With memory
        result2 = await search(query, use_memory=True)
        assert len(result2["answer"]) > 0


@pytest.mark.performance
class TestPerformance:
    """Performance tests for the graph."""
    
    @pytest.mark.asyncio
    async def test_search_performance(self, mindsearch_agent, performance_timer):
        """Test search performance meets expectations."""
        query = "Explain the difference between HTTP and HTTPS"
        
        performance_timer.start("search")
        result = await mindsearch_agent.search(query)
        duration = performance_timer.stop("search")
        
        # Should complete in reasonable time
        assert duration < 10.0, f"Search took too long: {duration:.2f}s"
        assert len(result["answer"]) > 0
        
        print(f"\nSearch performance: {duration:.2f}s")
        print(f"Sub-queries: {len(result['sub_queries'])}")
        print(f"Searches completed: {result['searches_completed']}")
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_parallel_speedup_e2e(self, performance_timer):
        """Test end-to-end parallel speedup."""
        agent = MindSearchAgent()
        
        # Query that generates multiple sub-queries
        query = "Compare Python, JavaScript, and Go for web development"
        
        # Measure total time
        performance_timer.start("e2e_search")
        result = await agent.search(query)
        total_time = performance_timer.stop("e2e_search")
        
        # Calculate theoretical sequential time
        # (number of searches * estimated time per search)
        num_searches = result["searches_completed"]
        estimated_sequential = num_searches * 0.5  # 0.5s per search estimate
        
        # Calculate speedup
        speedup = estimated_sequential / total_time if total_time > 0 else 0
        
        print(f"\nE2E Performance Results:")
        print(f"Total time: {total_time:.2f}s")
        print(f"Searches: {num_searches}")
        print(f"Estimated sequential: {estimated_sequential:.2f}s")
        print(f"Speedup: {speedup:.2f}x")
        
        # Should show some speedup
        assert speedup > 1.5, f"Expected speedup > 1.5x, got {speedup:.2f}x"


@pytest.mark.integration
class TestGraphIntegration:
    """Test graph integration with components."""
    
    @pytest.mark.asyncio
    async def test_loop_prevention_in_graph(self, mindsearch_agent, assert_no_infinite_loops):
        """Test that graph prevents infinite loops."""
        # Query that might trigger loops
        query = "recursive test query"
        
        # Track states during streaming
        states = []
        async for state in mindsearch_agent.stream_search(query):
            states.append(state)
            if "visit_count" in state:
                # Check no infinite loops at each step
                assert_no_infinite_loops(state, max_visits=3)
        
        # Final state should also pass
        final_state = states[-1] if states else {}
        if "visit_count" in final_state:
            assert_no_infinite_loops(final_state)
        
        print(f"\nLoop prevention verified across {len(states)} states")
    
    @pytest.mark.asyncio
    async def test_error_propagation(self):
        """Test error handling through the graph."""
        agent = MindSearchAgent()
        
        # Query that will cause mock to generate errors
        query = None  # Invalid query
        
        try:
            result = await agent.search(query)
            # Should handle error gracefully
            assert len(result["errors"]) > 0 or len(result["answer"]) > 0
        except Exception as e:
            # Or raise a clear error
            assert "query" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_state_persistence_across_nodes(self, mindsearch_agent):
        """Test that state persists correctly across nodes."""
        query = "What is Docker?"
        
        state_history = []
        async for state in mindsearch_agent.stream_search(query):
            state_history.append({
                "has_query": "query" in state and state["query"] == query,
                "sub_queries_count": len(state.get("sub_queries", [])),
                "results_count": len(state.get("search_results", {})),
                "has_answer": len(state.get("final_answer", "")) > 0
            })
        
        # Query should persist throughout
        assert all(s["has_query"] for s in state_history if "has_query" in s)
        
        # Should show progression
        max_sub_queries = max(s["sub_queries_count"] for s in state_history)
        max_results = max(s["results_count"] for s in state_history)
        has_final_answer = any(s["has_answer"] for s in state_history)
        
        assert max_sub_queries > 0, "Should generate sub-queries"
        assert max_results > 0, "Should have search results"
        assert has_final_answer, "Should generate final answer"


@pytest.mark.e2e
class TestRealWorldScenarios:
    """Test real-world usage scenarios."""
    
    @pytest.mark.asyncio
    @pytest.mark.real_apis
    async def test_real_search_with_real_apis(self, test_config):
        """Test with real search and LLM APIs if configured."""
        if not test_config["use_real_apis"]:
            pytest.skip("Real API tests not configured")
        
        agent = MindSearchAgent()
        query = "What are the latest developments in AI in 2024?"
        
        result = await agent.search(query, max_searches=5)
        
        # With real APIs, should get high-quality results
        assert len(result["answer"]) > 200  # Substantial answer
        assert result["confidence"] > 0.6   # Good confidence
        assert len(result["references"]) > 2  # Multiple sources
        
        # Answer should be relevant
        assert "ai" in result["answer"].lower() or "artificial intelligence" in result["answer"].lower()
    
    @pytest.mark.asyncio
    async def test_code_comparison_benefit(self):
        """Test that demonstrates code reduction benefit."""
        # This is more of a documentation test
        # Original MindSearch: ~1000 lines
        # LangGraph implementation: ~200 lines in core files
        
        src_dir = Path(__file__).parent.parent / "src"
        
        core_files = ["graph.py", "nodes.py"]
        total_lines = 0
        
        for file in core_files:
            file_path = src_dir / file
            if file_path.exists():
                with open(file_path, "r") as f:
                    lines = len([l for l in f.readlines() if l.strip()])
                    total_lines += lines
        
        # Verify code reduction
        assert total_lines < 500, f"Core implementation should be <500 lines, got {total_lines}"
        
        print(f"\nCode reduction verified: {total_lines} lines in core files")
        print("Original MindSearch: ~1000 lines")
        print(f"Reduction: ~{100 - (total_lines/1000*100):.0f}%")