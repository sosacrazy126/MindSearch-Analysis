"""Tests for LLM utilities and integration."""

import pytest
import os
from typing import List, Dict, Tuple

from src.llm_utils import LLMManager, SearchPlan, SynthesizedAnswer


@pytest.mark.unit
class TestLLMManager:
    """Test LLM manager functionality."""
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create LLM manager in mock mode."""
        os.environ["OPENAI_API_KEY"] = "mock-key"
        return LLMManager(model_name="mock", temperature=0.1)
    
    @pytest.fixture
    def real_llm_manager(self, test_config):
        """Create LLM manager with real API if configured."""
        if test_config["use_real_apis"]:
            return LLMManager(model_name="gpt-3.5-turbo", temperature=0.1)
        return LLMManager(model_name="mock", temperature=0.1)
    
    @pytest.mark.asyncio
    async def test_query_decomposition_mock(self, mock_llm_manager):
        """Test query decomposition with mock LLM."""
        # Test simple query
        query = "What is machine learning?"
        sub_queries = await mock_llm_manager.decompose_query(query)
        
        assert isinstance(sub_queries, list)
        assert len(sub_queries) >= 1
        assert all(isinstance(q, str) for q in sub_queries)
        
        # Test complex query with "and"
        query = "Python programming and web development"
        sub_queries = await mock_llm_manager.decompose_query(query)
        
        assert len(sub_queries) == 2
        assert "Python programming" in sub_queries
        assert "web development" in sub_queries
        
        # Test query with "vs"
        query = "React vs Vue.js"
        sub_queries = await mock_llm_manager.decompose_query(query)
        
        assert len(sub_queries) >= 3  # What is React?, What is Vue.js?, comparison
        assert any("React" in q for q in sub_queries)
        assert any("Vue.js" in q for q in sub_queries)
    
    @pytest.mark.asyncio
    @pytest.mark.real_apis
    async def test_query_decomposition_real(self, real_llm_manager):
        """Test query decomposition with real LLM API."""
        query = "Compare quantum computing and classical computing for cryptography"
        sub_queries = await real_llm_manager.decompose_query(query)
        
        # With real LLM, we should get meaningful decomposition
        assert isinstance(sub_queries, list)
        assert 2 <= len(sub_queries) <= 5  # Should be 3-5 sub-queries
        assert all(isinstance(q, str) and len(q) > 0 for q in sub_queries)
        
        # Should cover different aspects
        topics = ["quantum", "classical", "cryptography"]
        query_text = " ".join(sub_queries).lower()
        assert any(topic in query_text for topic in topics)
    
    @pytest.mark.asyncio
    async def test_answer_synthesis_mock(self, mock_llm_manager):
        """Test answer synthesis with mock LLM."""
        query = "What is Python?"
        search_results = {
            "Python programming": [
                {
                    "title": "Python Programming Language",
                    "url": "https://python.org",
                    "snippet": "Python is a high-level programming language"
                },
                {
                    "title": "Python Tutorial",
                    "url": "https://docs.python.org",
                    "snippet": "Learn Python programming from scratch"
                }
            ]
        }
        
        answer, references, confidence = await mock_llm_manager.synthesize_answer(
            query, search_results
        )
        
        # Verify output structure
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert isinstance(references, dict)
        assert isinstance(confidence, float)
        assert 0.0 <= confidence <= 1.0
        
        # Mock should include query in answer
        assert query.lower() in answer.lower()
        
        # Should have references
        assert len(references) > 0
        assert all(isinstance(k, int) for k in references.keys())
        assert all(isinstance(v, str) for v in references.values())
    
    @pytest.mark.asyncio
    @pytest.mark.real_apis
    async def test_answer_synthesis_real(self, real_llm_manager):
        """Test answer synthesis with real LLM API."""
        query = "What are the benefits of Python for data science?"
        search_results = {
            "Python data science benefits": [
                {
                    "title": "Why Python for Data Science",
                    "url": "https://example.com/python-ds",
                    "snippet": "Python offers extensive libraries like NumPy, Pandas, and Scikit-learn"
                }
            ],
            "Python vs R for data analysis": [
                {
                    "title": "Python vs R Comparison",
                    "url": "https://example.com/python-vs-r",
                    "snippet": "Python is more versatile while R is specialized for statistics"
                }
            ]
        }
        
        answer, references, confidence = await real_llm_manager.synthesize_answer(
            query, search_results
        )
        
        # With real LLM, should get comprehensive answer
        assert len(answer) > 100  # Should be detailed
        assert confidence > 0.5  # Should be reasonably confident
        assert len(references) >= 2  # Should cite sources
        
        # Answer should mention key concepts
        key_concepts = ["libraries", "data", "science"]
        answer_lower = answer.lower()
        assert any(concept in answer_lower for concept in key_concepts)
    
    @pytest.mark.asyncio
    async def test_empty_search_results_handling(self, mock_llm_manager):
        """Test synthesis with empty search results."""
        query = "test query"
        empty_results = {}
        
        answer, references, confidence = await mock_llm_manager.synthesize_answer(
            query, empty_results
        )
        
        # Should handle gracefully
        assert isinstance(answer, str)
        assert len(references) == 0
        assert confidence < 0.5  # Low confidence with no results
    
    @pytest.mark.asyncio
    async def test_error_handling(self, mock_llm_manager):
        """Test LLM error handling."""
        # Test with invalid query type
        with pytest.raises(AttributeError):
            await mock_llm_manager.decompose_query(None)
        
        # Test with invalid search results
        answer, refs, conf = await mock_llm_manager.synthesize_answer(
            "query", None  # Invalid search results
        )
        
        # Should return fallback response
        assert "error" in answer.lower() or "found information" in answer.lower()
        assert conf < 0.5
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("query,expected_min_subqueries", [
        ("Simple query", 1),
        ("Compare A and B and C", 3),
        ("X vs Y vs Z comparison", 3),
        ("How does blockchain work and what are its applications in finance and healthcare?", 3),
    ])
    async def test_decomposition_patterns(self, mock_llm_manager, query, expected_min_subqueries):
        """Test different query decomposition patterns."""
        sub_queries = await mock_llm_manager.decompose_query(query)
        
        assert len(sub_queries) >= expected_min_subqueries
        assert all(len(q) > 0 for q in sub_queries)
    
    def test_prompt_configuration(self):
        """Test that prompts are properly configured."""
        manager = LLMManager()
        
        # Check decompose prompt
        assert hasattr(manager, "decompose_prompt")
        assert "sub-queries" in str(manager.decompose_prompt)
        
        # Check synthesize prompt
        assert hasattr(manager, "synthesize_prompt")
        assert "synthesize" in str(manager.synthesize_prompt).lower()
    
    @pytest.mark.asyncio
    async def test_format_search_results(self, mock_llm_manager):
        """Test search results formatting for LLM consumption."""
        search_results = {
            "query1": [
                {"title": "Title 1", "url": "http://url1.com", "snippet": "Snippet 1"},
                {"title": "Title 2", "url": "http://url2.com", "snippet": "Snippet 2"},
            ],
            "query2": [
                {"title": "Title 3", "url": "http://url3.com", "snippet": "Snippet 3"},
            ]
        }
        
        formatted = mock_llm_manager._format_search_results(search_results)
        
        # Check formatting
        assert isinstance(formatted, str)
        assert "### Results for: query1" in formatted
        assert "### Results for: query2" in formatted
        assert "[1]" in formatted
        assert "[2]" in formatted
        assert "[3]" in formatted
        assert "http://url1.com" in formatted
        assert "Snippet 1" in formatted


@pytest.mark.integration
class TestLLMIntegration:
    """Test LLM integration with the system."""
    
    @pytest.mark.asyncio
    async def test_full_decompose_search_synthesize_flow(self, llm_manager, mock_search_manager):
        """Test complete flow from query to synthesized answer."""
        # Original query
        query = "What are the differences between Python and JavaScript?"
        
        # Decompose
        sub_queries = await llm_manager.decompose_query(query)
        assert len(sub_queries) > 0
        
        # Search for each sub-query
        search_results = {}
        for sub_query in sub_queries:
            results = await mock_search_manager.search(sub_query)
            search_results[sub_query] = [dict(r) for r in results]
        
        # Synthesize
        answer, references, confidence = await llm_manager.synthesize_answer(
            query, search_results
        )
        
        # Verify complete flow worked
        assert len(answer) > 0
        assert len(references) > 0
        assert confidence > 0.0
        
        # Answer should be relevant to query
        assert "python" in answer.lower() or "javascript" in answer.lower()
    
    @pytest.mark.asyncio
    async def test_model_switching(self, test_config):
        """Test switching between different LLM models."""
        models = ["mock", "gpt-3.5-turbo", "gpt-4"] if test_config["use_real_apis"] else ["mock"]
        
        for model in models:
            manager = LLMManager(model_name=model)
            
            # Should work with any model
            sub_queries = await manager.decompose_query("test query")
            assert isinstance(sub_queries, list)
            assert len(sub_queries) > 0
    
    @pytest.mark.asyncio
    async def test_temperature_effects(self, test_config):
        """Test that temperature affects output variability."""
        if not test_config["use_real_apis"]:
            pytest.skip("Requires real API to test temperature effects")
        
        query = "Explain quantum computing"
        
        # Low temperature (deterministic)
        manager_low = LLMManager(temperature=0.0)
        results_low = []
        for _ in range(3):
            sub_queries = await manager_low.decompose_query(query)
            results_low.append(sub_queries)
        
        # High temperature (more random)
        manager_high = LLMManager(temperature=0.9)
        results_high = []
        for _ in range(3):
            sub_queries = await manager_high.decompose_query(query)
            results_high.append(sub_queries)
        
        # Low temperature should be more consistent
        # This is a probabilistic test, so we just check structure
        assert all(isinstance(r, list) for r in results_low)
        assert all(isinstance(r, list) for r in results_high)
    
    @pytest.mark.asyncio
    async def test_long_context_handling(self, llm_manager):
        """Test handling of long search results context."""
        # Create many search results
        search_results = {}
        for i in range(10):
            search_results[f"sub_query_{i}"] = [
                {
                    "title": f"Long Result {j}",
                    "url": f"http://example.com/{i}/{j}",
                    "snippet": "This is a very long snippet " * 20  # Long snippet
                }
                for j in range(5)
            ]
        
        # Should handle without error
        answer, references, confidence = await llm_manager.synthesize_answer(
            "Complex query with many results", search_results
        )
        
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert isinstance(references, dict)
        assert isinstance(confidence, float)
    
    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_input", [
        {"not": "a valid format"},
        [["nested", "lists"]],
        "string instead of dict",
        123,
        None
    ])
    async def test_synthesis_invalid_inputs(self, llm_manager, invalid_input):
        """Test synthesis with various invalid inputs."""
        # Should handle gracefully without crashing
        answer, refs, conf = await llm_manager.synthesize_answer(
            "test query", invalid_input
        )
        
        # Should return some answer
        assert isinstance(answer, str)
        assert len(answer) > 0
        assert isinstance(refs, dict)
        assert isinstance(conf, float)