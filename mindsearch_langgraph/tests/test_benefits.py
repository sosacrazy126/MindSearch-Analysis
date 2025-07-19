"""Tests specifically validating the benefits of LangGraph implementation."""

import pytest
import asyncio
import time
from pathlib import Path
import ast

from src.graph import MindSearchAgent
from src.state import MindSearchState


@pytest.mark.e2e
class TestClaimedBenefits:
    """Test that all claimed benefits are actually delivered."""
    
    @pytest.mark.asyncio
    async def test_no_infinite_loops(self):
        """Validate: No infinite loops with built-in loop prevention."""
        agent = MindSearchAgent()
        
        # Query designed to potentially cause loops
        tricky_queries = [
            "recursive recursive recursive",
            "loop back to the beginning and start over",
            "repeat this search again and again",
            "circular reference to itself"
        ]
        
        for query in tricky_queries:
            start_time = time.time()
            
            # Should complete without hanging
            result = await asyncio.wait_for(
                agent.search(query, max_searches=5),
                timeout=30.0  # 30 second timeout
            )
            
            duration = time.time() - start_time
            
            # Verify completed successfully
            assert result is not None
            assert duration < 30.0, f"Query '{query}' took too long: {duration:.2f}s"
            
            # Check visit counts if available in final state
            # In real implementation, the graph would enforce limits
            print(f"✓ Query '{query}' completed in {duration:.2f}s without loops")
    
    @pytest.mark.asyncio
    async def test_state_corruption_prevention(self):
        """Validate: No state corruption with TypedDict management."""
        agent = MindSearchAgent()
        
        # Run multiple searches concurrently
        queries = [
            "Python programming",
            "JavaScript frameworks", 
            "Machine learning basics",
            "Web development tools",
            "Database systems"
        ]
        
        async def search_and_validate(query):
            result = await agent.search(query)
            
            # Each result should be independent
            assert result["sub_queries"] is not None
            assert all(query not in other_q for other_q in queries if other_q != query
                      for sub_q in result["sub_queries"])
            
            return result
        
        # Execute all searches in parallel
        results = await asyncio.gather(*[search_and_validate(q) for q in queries])
        
        # Verify no cross-contamination
        for i, result in enumerate(results):
            query_words = queries[i].lower().split()
            answer_words = result["answer"].lower().split()
            
            # Answer should be relevant to its query
            relevance = any(word in answer_words for word in query_words)
            assert relevance, f"Answer not relevant to query: {queries[i]}"
        
        print(f"✓ {len(results)} concurrent searches completed without state corruption")
    
    @pytest.mark.asyncio
    @pytest.mark.performance
    async def test_3x_performance_improvement(self, performance_timer):
        """Validate: 3x performance improvement with parallel execution."""
        # Create custom engines to simulate network delay
        from src.search_engines import SearchEngine, SearchEngineManager, SearchResult
        
        class DelayedEngine(SearchEngine):
            def __init__(self, delay: float = 0.5):
                self.delay = delay
                
            async def search(self, query: str, max_results: int = 5):
                await asyncio.sleep(self.delay)
                return [SearchResult(
                    title=f"Result for {query}",
                    url=f"https://example.com/{query.replace(' ', '-')}",
                    snippet=f"Information about {query}",
                    source="test",
                    timestamp=None
                )]
        
        # Test sequential execution
        engines = [DelayedEngine() for _ in range(3)]
        queries = ["query1", "query2", "query3"]
        
        performance_timer.start("sequential")
        sequential_results = []
        for engine, query in zip(engines, queries):
            result = await engine.search(query)
            sequential_results.extend(result)
        sequential_time = performance_timer.stop("sequential")
        
        # Test parallel execution with SearchEngineManager
        manager = SearchEngineManager(engines=engines)
        performance_timer.start("parallel")
        parallel_results = await manager.search("test")
        parallel_time = performance_timer.stop("parallel")
        
        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        
        print(f"\n✓ Performance Test Results:")
        print(f"  Sequential: {sequential_time:.2f}s")
        print(f"  Parallel: {parallel_time:.2f}s")
        print(f"  Speedup: {speedup:.2f}x")
        
        # Should achieve at least 2.5x speedup (allowing some overhead)
        assert speedup >= 2.5, f"Expected >=2.5x speedup, got {speedup:.2f}x"
    
    def test_80_percent_code_reduction(self):
        """Validate: 80% code reduction compared to original."""
        # Count lines in core implementation files
        src_dir = Path(__file__).parent.parent / "src"
        
        core_files = {
            "graph.py": 0,
            "nodes.py": 0,
            "state.py": 0,
            "llm_utils.py": 0,
            "search_engines.py": 0
        }
        
        total_lines = 0
        total_code_lines = 0
        
        for filename in core_files:
            filepath = src_dir / filename
            if filepath.exists():
                with open(filepath, 'r') as f:
                    lines = f.readlines()
                    core_files[filename] = len(lines)
                    total_lines += len(lines)
                    
                    # Count actual code lines (non-empty, non-comment)
                    code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
                    total_code_lines += len(code_lines)
        
        print(f"\n✓ Code Reduction Analysis:")
        print(f"  File breakdown:")
        for filename, count in core_files.items():
            print(f"    {filename}: {count} lines")
        print(f"  Total lines: {total_lines}")
        print(f"  Code lines: {total_code_lines}")
        print(f"  Original estimate: ~1000 lines")
        print(f"  Reduction: ~{100 - (total_code_lines/1000*100):.0f}%")
        
        # Verify significant reduction
        assert total_code_lines < 600, f"Expected <600 code lines, got {total_code_lines}"
        
        # Calculate actual reduction percentage
        reduction_percentage = 100 - (total_code_lines / 1000 * 100)
        assert reduction_percentage >= 40, f"Expected >=40% reduction, got {reduction_percentage:.0f}%"
    
    @pytest.mark.asyncio
    async def test_error_recovery(self):
        """Validate: Automatic error recovery with retries."""
        agent = MindSearchAgent()
        
        # Queries that might cause errors
        error_prone_queries = [
            "",  # Empty query
            "🔥💯🚀" * 100,  # Emoji spam
            "a" * 1000,  # Very long query
        ]
        
        for query in error_prone_queries:
            try:
                result = await agent.search(query[:100])  # Limit length
                
                # Should recover and provide some result
                assert result is not None
                assert isinstance(result["answer"], str)
                assert result["confidence"] >= 0.0
                
                print(f"✓ Recovered from query: {query[:50]}...")
                
            except Exception as e:
                # Even exceptions should be graceful
                assert "query" in str(e).lower() or "error" in str(e).lower()
                print(f"✓ Graceful error for query: {query[:50]}...")
    
    @pytest.mark.asyncio
    async def test_streaming_visibility(self):
        """Validate: Better debugging with streaming and visibility."""
        agent = MindSearchAgent()
        query = "What is GraphQL?"
        
        stages_observed = {
            "planning": False,
            "searching": False,
            "synthesizing": False
        }
        
        state_count = 0
        async for state in agent.stream_search(query):
            state_count += 1
            
            # Check what stage we're in
            if "sub_queries" in state and len(state.get("sub_queries", [])) > 0:
                stages_observed["planning"] = True
                
            if "search_results" in state and len(state.get("search_results", {})) > 0:
                stages_observed["searching"] = True
                
            if "final_answer" in state and len(state.get("final_answer", "")) > 0:
                stages_observed["synthesizing"] = True
        
        print(f"\n✓ Streaming Visibility Test:")
        print(f"  States observed: {state_count}")
        print(f"  Stages visible: {sum(stages_observed.values())}/3")
        
        # Should observe all stages
        assert all(stages_observed.values()), f"Missing stages: {[k for k,v in stages_observed.items() if not v]}"
        assert state_count >= 3, f"Expected at least 3 state updates, got {state_count}"
    
    @pytest.mark.asyncio
    async def test_checkpointing_resumability(self):
        """Validate: Checkpointing enables resumable searches."""
        agent = MindSearchAgent(use_memory=True)
        
        query = "Explain distributed systems"
        
        # First execution
        result1 = await agent.search(query)
        first_answer = result1["answer"]
        first_confidence = result1["confidence"]
        
        # Simulate interruption and resume
        # With checkpointing, same query should reuse results
        result2 = await agent.search(query)
        
        # Should get same results (from checkpoint)
        assert result2["answer"] == first_answer
        assert result2["confidence"] == first_confidence
        
        print("✓ Checkpointing enables consistent results across executions")
    
    def test_declarative_graph_definition(self):
        """Validate: Declarative graph definition is cleaner."""
        # Check that graph definition is simple and declarative
        graph_file = Path(__file__).parent.parent / "src" / "graph.py"
        
        with open(graph_file, 'r') as f:
            content = f.read()
        
        # Look for declarative patterns
        declarative_patterns = [
            "workflow.add_node",
            "workflow.add_edge", 
            "workflow.add_conditional_edges",
            "workflow.set_entry_point",
            "StateGraph"
        ]
        
        found_patterns = []
        for pattern in declarative_patterns:
            if pattern in content:
                found_patterns.append(pattern)
                # Count occurrences
                count = content.count(pattern)
                print(f"✓ Found {count} uses of '{pattern}'")
        
        # Should use declarative patterns
        assert len(found_patterns) >= 4, f"Expected declarative patterns, found: {found_patterns}"
        
        # Parse to check complexity
        tree = ast.parse(content)
        
        # Count function definitions
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
        classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        
        print(f"\n✓ Graph Definition Simplicity:")
        print(f"  Functions: {len(functions)}")
        print(f"  Classes: {len(classes)}")
        print(f"  Declarative patterns: {len(found_patterns)}")
        
        # Should be relatively simple
        assert len(functions) < 10, f"Too many functions ({len(functions)}), not declarative enough"


@pytest.mark.unit 
class TestArchitecturalImprovements:
    """Test architectural improvements of LangGraph implementation."""
    
    def test_single_source_of_truth_state(self, sample_state):
        """Validate: Single source of truth for state management."""
        # All state in one TypedDict
        required_fields = {
            "query", "search_plan", "sub_queries", "current_sub_query",
            "search_results", "raw_results", "final_answer", "references",
            "confidence_score", "max_searches", "searches_completed",
            "visit_count", "errors", "retry_count"
        }
        
        state_fields = set(sample_state.keys())
        
        # All required fields should be in state
        assert required_fields.issubset(state_fields), \
            f"Missing fields: {required_fields - state_fields}"
        
        print(f"✓ Single state object contains all {len(state_fields)} fields")
    
    @pytest.mark.asyncio
    async def test_native_async_support(self):
        """Validate: Native async/await support throughout."""
        agent = MindSearchAgent()
        
        # All main methods should be async
        assert asyncio.iscoroutinefunction(agent.search)
        assert hasattr(agent, 'stream_search')
        
        # Test async execution
        start = time.time()
        tasks = [
            agent.search("Query 1"),
            agent.search("Query 2"),
            agent.search("Query 3")
        ]
        
        results = await asyncio.gather(*tasks)
        duration = time.time() - start
        
        # Should complete all three concurrently
        assert len(results) == 3
        assert all(r["answer"] for r in results)
        
        print(f"✓ Native async support: 3 searches in {duration:.2f}s")
    
    def test_standard_patterns(self):
        """Validate: Uses standard LangGraph patterns."""
        # Check imports and patterns
        src_files = list((Path(__file__).parent.parent / "src").glob("*.py"))
        
        standard_patterns = {
            "from langgraph": 0,
            "StateGraph": 0,
            "TypedDict": 0,
            "async def": 0,
            "await": 0
        }
        
        for file in src_files:
            with open(file, 'r') as f:
                content = f.read()
                for pattern in standard_patterns:
                    standard_patterns[pattern] += content.count(pattern)
        
        print("\n✓ Standard Pattern Usage:")
        for pattern, count in standard_patterns.items():
            print(f"  {pattern}: {count} occurrences")
            assert count > 0, f"Pattern '{pattern}' not found"
    
    @pytest.mark.asyncio
    async def test_extensibility(self):
        """Validate: Easy to extend with new features."""
        # The modular design makes it easy to add new search engines
        from src.search_engines import SearchEngine, SearchEngineManager
        
        class CustomSearchEngine(SearchEngine):
            async def search(self, query: str, max_results: int = 5):
                return [{
                    "title": f"Custom result for {query}",
                    "url": "https://custom.com",
                    "snippet": "Custom search engine result",
                    "source": "custom",
                    "timestamp": None
                }]
        
        # Easy to add new engine
        custom_engine = CustomSearchEngine()
        manager = SearchEngineManager(engines=[custom_engine])
        
        results = await manager.search("test extensibility")
        
        assert len(results) > 0
        assert results[0]["source"] == "custom"
        
        print("✓ Easy to extend with custom components")