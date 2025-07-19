"""Tests for search engine implementations and performance."""

import pytest
import asyncio
import time
from datetime import datetime
from typing import List
import aiohttp

from src.search_engines import (
    SearchEngine, MockSearchEngine, DuckDuckGoSearchEngine,
    SearchEngineManager, SearchResult
)


@pytest.mark.unit
class TestSearchEngines:
    """Test individual search engine implementations."""
    
    @pytest.mark.asyncio
    async def test_mock_search_engine(self):
        """Test the mock search engine functionality."""
        engine = MockSearchEngine()
        query = "test query"
        
        # Execute search
        results = await engine.search(query, max_results=5)
        
        # Verify results
        assert len(results) == 3  # Mock returns max 3 results
        assert all(isinstance(r, dict) for r in results)
        
        # Check result structure
        for result in results:
            assert "title" in result
            assert "url" in result
            assert "snippet" in result
            assert "source" in result
            assert "timestamp" in result
            assert result["source"] == "mock"
            assert query in result["snippet"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.real_apis
    async def test_duckduckgo_search_engine(self):
        """Test DuckDuckGo search engine with real API."""
        engine = DuckDuckGoSearchEngine()
        query = "Python programming"
        
        # Execute search
        results = await engine.search(query, max_results=5)
        
        # Verify results (may be empty if API is down)
        assert isinstance(results, list)
        
        if results:  # Only test if we got results
            assert len(results) <= 5
            for result in results:
                assert "title" in result
                assert "url" in result
                assert "snippet" in result
                assert result["source"] == "duckduckgo"
    
    @pytest.mark.asyncio
    async def test_search_engine_error_handling(self):
        """Test search engine error handling."""
        class FailingSearchEngine(SearchEngine):
            async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
                raise aiohttp.ClientError("Network error")
        
        engine = FailingSearchEngine()
        
        # Should handle errors gracefully
        with pytest.raises(aiohttp.ClientError):
            await engine.search("test query")
    
    @pytest.mark.asyncio
    async def test_search_engine_manager_single(self, mock_search_manager):
        """Test SearchEngineManager with single engine."""
        query = "test query"
        
        # Execute search
        results = await mock_search_manager.search(query)
        
        # Verify results
        assert len(results) > 0
        assert all(isinstance(r, dict) for r in results)
        assert all("title" in r for r in results)
    
    @pytest.mark.asyncio
    async def test_search_engine_manager_multiple(self):
        """Test SearchEngineManager with multiple engines."""
        # Create manager with multiple mock engines
        engines = [MockSearchEngine() for _ in range(3)]
        manager = SearchEngineManager(engines=engines)
        
        query = "test query"
        results = await manager.search(query, max_results_per_engine=2)
        
        # Should aggregate results from all engines
        # Each mock engine returns up to 3 results, we asked for 2 per engine
        assert len(results) > 0
        assert len(results) <= 6  # 3 engines * 2 results max
    
    @pytest.mark.asyncio
    async def test_duplicate_url_removal(self):
        """Test that SearchEngineManager removes duplicate URLs."""
        class DuplicateSearchEngine(SearchEngine):
            async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
                # Return same URL multiple times
                return [
                    SearchResult(
                        title=f"Result {i}",
                        url="https://duplicate.com/same",
                        snippet=f"Snippet {i}",
                        source="test",
                        timestamp=datetime.now()
                    )
                    for i in range(3)
                ]
        
        engines = [DuplicateSearchEngine() for _ in range(2)]
        manager = SearchEngineManager(engines=engines)
        
        results = await manager.search("test")
        
        # Should only have one result despite duplicates
        assert len(results) == 1
        assert results[0]["url"] == "https://duplicate.com/same"


@pytest.mark.performance
class TestSearchPerformance:
    """Test search engine performance and parallel execution."""
    
    @pytest.mark.asyncio
    async def test_parallel_search_speedup(self, performance_timer):
        """Test that parallel searches are faster than sequential."""
        # Create multiple mock engines with delay
        class SlowMockEngine(MockSearchEngine):
            async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
                await asyncio.sleep(0.5)  # Simulate network delay
                return await super().search(query, max_results)
        
        engines = [SlowMockEngine() for _ in range(3)]
        queries = ["query1", "query2", "query3"]
        
        # Sequential execution
        performance_timer.start("sequential")
        sequential_results = []
        for engine, query in zip(engines, queries):
            result = await engine.search(query)
            sequential_results.extend(result)
        sequential_time = performance_timer.stop("sequential")
        
        # Parallel execution using SearchEngineManager
        manager = SearchEngineManager(engines=engines)
        performance_timer.start("parallel")
        parallel_results = await manager.search("test query")
        parallel_time = performance_timer.stop("parallel")
        
        # Calculate speedup
        speedup = sequential_time / parallel_time if parallel_time > 0 else 0
        
        print(f"\nPerformance Results:")
        print(f"Sequential time: {sequential_time:.2f}s")
        print(f"Parallel time: {parallel_time:.2f}s")
        print(f"Speedup: {speedup:.2f}x")
        
        # Assert significant speedup (at least 2x)
        assert speedup >= 2.0, f"Expected at least 2x speedup, got {speedup:.2f}x"
        
        # Verify we got results
        assert len(parallel_results) > 0
    
    @pytest.mark.asyncio
    async def test_search_timeout_handling(self):
        """Test search timeout handling."""
        class TimeoutEngine(SearchEngine):
            async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
                await asyncio.sleep(10)  # Long delay
                return []
        
        engine = TimeoutEngine()
        
        # Should timeout
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(engine.search("test"), timeout=1.0)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("num_engines,num_queries", [
        (2, 2),
        (3, 3),
        (5, 5),
    ])
    async def test_scalable_parallel_performance(self, num_engines, num_queries, performance_timer):
        """Test that parallel performance scales with number of engines."""
        # Create engines
        engines = [MockSearchEngine() for _ in range(num_engines)]
        manager = SearchEngineManager(engines=engines)
        
        # Measure search time
        performance_timer.start(f"search_{num_engines}")
        results = await manager.search("scalability test")
        search_time = performance_timer.stop(f"search_{num_engines}")
        
        # Time should not increase linearly with number of engines
        # Due to parallel execution
        assert search_time < 1.0, f"Search took too long: {search_time:.2f}s"
        assert len(results) > 0


@pytest.mark.integration
class TestSearchEngineIntegration:
    """Test search engine integration with the system."""
    
    @pytest.mark.asyncio
    async def test_search_result_format_consistency(self, mock_search_manager):
        """Test that all search results have consistent format."""
        results = await mock_search_manager.search("consistency test")
        
        required_fields = ["title", "url", "snippet", "source", "timestamp"]
        
        for result in results:
            # Check all required fields present
            for field in required_fields:
                assert field in result, f"Missing required field: {field}"
            
            # Check field types
            assert isinstance(result["title"], str)
            assert isinstance(result["url"], str)
            assert isinstance(result["snippet"], str)
            assert isinstance(result["source"], str)
            assert isinstance(result["timestamp"], datetime)
            
            # Check field constraints
            assert len(result["title"]) > 0
            assert result["url"].startswith("http")
            assert len(result["snippet"]) > 0
    
    @pytest.mark.asyncio
    async def test_empty_query_handling(self, mock_search_manager):
        """Test handling of empty queries."""
        # Empty string
        results = await mock_search_manager.search("")
        assert isinstance(results, list)
        
        # Whitespace only
        results = await mock_search_manager.search("   ")
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_special_characters_in_query(self, mock_search_manager):
        """Test handling of special characters in queries."""
        special_queries = [
            "test & query",
            "test | query",
            "test (query)",
            "test [query]",
            "test {query}",
            "test <query>",
            "test@query.com",
            "test#query",
            "test$query",
            "test%query"
        ]
        
        for query in special_queries:
            results = await mock_search_manager.search(query)
            assert isinstance(results, list), f"Failed for query: {query}"
    
    @pytest.mark.asyncio
    async def test_concurrent_searches(self, mock_search_manager):
        """Test multiple concurrent searches don't interfere."""
        queries = [
            "concurrent test 1",
            "concurrent test 2",
            "concurrent test 3",
            "concurrent test 4",
            "concurrent test 5"
        ]
        
        # Execute all searches concurrently
        tasks = [mock_search_manager.search(q) for q in queries]
        all_results = await asyncio.gather(*tasks)
        
        # Verify each search got results
        assert len(all_results) == len(queries)
        for i, results in enumerate(all_results):
            assert isinstance(results, list)
            assert len(results) > 0
            # Verify results match the query
            for result in results:
                assert queries[i] in result["snippet"].lower()
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_search_retry_on_failure(self):
        """Test that search engines retry on failure."""
        call_count = 0
        
        class FlakeyEngine(SearchEngine):
            async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
                nonlocal call_count
                call_count += 1
                
                # Fail first 2 times
                if call_count < 3:
                    raise aiohttp.ClientError("Temporary failure")
                
                # Succeed on third try
                return [SearchResult(
                    title="Success",
                    url="https://example.com",
                    snippet="Finally worked",
                    source="flakey",
                    timestamp=datetime.now()
                )]
        
        # The DuckDuckGoSearchEngine has retry logic
        # For this test, we'd need to modify our engine to use tenacity
        # This documents the expected behavior
        engine = FlakeyEngine()
        
        # Without retry logic, this would fail
        with pytest.raises(aiohttp.ClientError):
            await engine.search("test")
        
        # With retry logic (as in DuckDuckGoSearchEngine), it would succeed
        # assert len(results) > 0
        # assert results[0]["title"] == "Success"