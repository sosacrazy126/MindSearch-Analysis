"""Pytest configuration and shared fixtures for MindSearch LangGraph tests."""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.state import MindSearchState, SearchResult
from src.search_engines import SearchEngineManager, MockSearchEngine, DuckDuckGoSearchEngine
from src.llm_utils import LLMManager
from src.graph import MindSearchAgent


# Configuration for test environment
TEST_CONFIG = {
    "use_real_apis": os.getenv("USE_REAL_APIS", "false").lower() == "true",
    "openai_api_key": os.getenv("OPENAI_API_KEY", "test-key"),
    "max_test_duration": 30,  # seconds
    "performance_baseline": {
        "parallel_speedup": 2.5,  # Minimum expected speedup
        "max_search_time": 5.0,   # Maximum time for single search
    }
}


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Provide test configuration."""
    return TEST_CONFIG.copy()


@pytest.fixture
def sample_state() -> MindSearchState:
    """Create a sample MindSearchState for testing."""
    return {
        "query": "test query",
        "search_plan": [],
        "sub_queries": [],
        "current_sub_query": 0,
        "search_results": {},
        "raw_results": {},
        "final_answer": "",
        "references": {},
        "confidence_score": 0.0,
        "max_searches": 10,
        "searches_completed": 0,
        "visit_count": {},
        "errors": [],
        "retry_count": 0
    }


@pytest.fixture
def sample_search_results() -> List[SearchResult]:
    """Create sample search results for testing."""
    return [
        SearchResult(
            title="Test Result 1",
            url="https://example.com/1",
            snippet="This is a test search result about the topic.",
            source="test",
            timestamp=datetime.now()
        ),
        SearchResult(
            title="Test Result 2",
            url="https://example.com/2",
            snippet="Another relevant search result with information.",
            source="test",
            timestamp=datetime.now()
        )
    ]


@pytest.fixture
def mock_search_manager():
    """Create a search manager with mock engines for testing."""
    return SearchEngineManager(engines=[MockSearchEngine()])


@pytest.fixture
def real_search_manager(test_config):
    """Create a search manager with real engines if configured."""
    if test_config["use_real_apis"]:
        return SearchEngineManager(engines=[DuckDuckGoSearchEngine()])
    return SearchEngineManager(engines=[MockSearchEngine()])


@pytest.fixture
def llm_manager(test_config):
    """Create an LLM manager for testing."""
    # Set API key for testing
    os.environ["OPENAI_API_KEY"] = test_config["openai_api_key"]
    return LLMManager(
        model_name="gpt-3.5-turbo" if test_config["use_real_apis"] else "mock",
        temperature=0.1
    )


@pytest.fixture
async def mindsearch_agent(test_config):
    """Create a MindSearchAgent for testing."""
    # Configure based on test settings
    os.environ["OPENAI_API_KEY"] = test_config["openai_api_key"]
    agent = MindSearchAgent(use_memory=True)
    yield agent
    # Cleanup if needed


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def performance_timer():
    """Utility for timing performance tests."""
    class Timer:
        def __init__(self):
            self.times = {}
        
        def start(self, name: str):
            self.times[f"{name}_start"] = datetime.now()
        
        def stop(self, name: str) -> float:
            if f"{name}_start" not in self.times:
                raise ValueError(f"Timer {name} was not started")
            duration = (datetime.now() - self.times[f"{name}_start"]).total_seconds()
            self.times[f"{name}_duration"] = duration
            return duration
        
        def get_duration(self, name: str) -> float:
            return self.times.get(f"{name}_duration", 0.0)
    
    return Timer()


@pytest.fixture
def assert_no_infinite_loops():
    """Fixture to help assert no infinite loops occur."""
    def _assert(state: MindSearchState, max_visits: int = 3):
        for node, count in state.get("visit_count", {}).items():
            assert count <= max_visits, \
                f"Node '{node}' visited {count} times - potential infinite loop!"
    return _assert


@pytest.fixture
def complex_queries():
    """Provide complex queries for testing."""
    return [
        "What are the differences between quantum computing and classical computing in cryptography?",
        "Explain machine learning vs deep learning vs artificial intelligence",
        "Compare Python, JavaScript, and Go for backend development",
        "How does blockchain technology work and what are its applications?",
        "What is the impact of climate change on global agriculture and food security?"
    ]


# Markers for different test categories
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests for individual components")
    config.addinivalue_line("markers", "integration: Integration tests for module interactions")
    config.addinivalue_line("markers", "e2e: End-to-end tests for full workflows")
    config.addinivalue_line("markers", "performance: Performance benchmarks and tests")
    config.addinivalue_line("markers", "real_apis: Tests requiring real API access")
    config.addinivalue_line("markers", "slow: Tests that take longer to run")


# Skip real API tests if not configured
def pytest_collection_modifyitems(config, items):
    """Modify test collection based on configuration."""
    if not TEST_CONFIG["use_real_apis"]:
        skip_real = pytest.mark.skip(reason="Real API tests disabled")
        for item in items:
            if "real_apis" in item.keywords:
                item.add_marker(skip_real)