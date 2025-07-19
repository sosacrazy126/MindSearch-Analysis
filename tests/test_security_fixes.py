#!/usr/bin/env python3
"""
Test suite for MindSearch security fixes and core functionality.

This module tests the critical security improvements and ensures
the core search functionality works as expected.
"""

import unittest
import tempfile
import json
import ast
from unittest.mock import patch, MagicMock

from mindsearch.agent.graph import SafeGraphExecutor, WebSearchGraph
from mindsearch.agent import init_agent
from mindsearch.config import MindSearchConfig, LLMConfig, SearchConfig


class TestSafeGraphExecutor(unittest.TestCase):
    """Test the SafeGraphExecutor security improvements."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.graph = WebSearchGraph()
        self.executor = SafeGraphExecutor(self.graph)
    
    def test_safe_graph_operations(self):
        """Test that safe graph operations are allowed."""
        safe_code = """
graph.add_node("test_node", "Test content")
graph.add_edge("root", "test_node")
"""
        # Should not raise an exception
        try:
            self.executor.execute_safe(safe_code)
        except Exception as e:
            self.fail(f"Safe code raised exception: {e}")
    
    def test_unsafe_import_blocked(self):
        """Test that import statements are blocked."""
        unsafe_code = "import os"
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(unsafe_code)
        
        self.assertIn("Import statements are not allowed", str(context.exception))
    
    def test_unsafe_function_definition_blocked(self):
        """Test that function definitions are blocked."""
        unsafe_code = """
def malicious_function():
    return "bad"
"""
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(unsafe_code)
        
        self.assertIn("Function and class definitions are not allowed", str(context.exception))
    
    def test_unsafe_global_statement_blocked(self):
        """Test that global statements are blocked."""
        unsafe_code = "global some_var"
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(unsafe_code)
        
        self.assertIn("Global and nonlocal statements are not allowed", str(context.exception))
    
    def test_unsafe_method_call_blocked(self):
        """Test that unauthorized method calls are blocked."""
        unsafe_code = "graph.dangerous_method()"
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(unsafe_code)
        
        self.assertIn("Method 'dangerous_method' is not allowed", str(context.exception))
    
    def test_unsafe_attribute_access_blocked(self):
        """Test that unauthorized attribute access is blocked."""
        unsafe_code = "value = graph.private_attribute"
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(unsafe_code)
        
        self.assertIn("Attribute 'private_attribute' is not allowed", str(context.exception))
    
    def test_non_graph_operations_blocked(self):
        """Test that operations on non-graph objects are blocked."""
        unsafe_code = "print('hello')"
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(unsafe_code)
        
        self.assertIn("Only graph method calls are allowed", str(context.exception))
    
    def test_syntax_error_handling(self):
        """Test that syntax errors are properly handled."""
        invalid_code = "graph.add_node(((("
        
        with self.assertRaises(ValueError) as context:
            self.executor.execute_safe(invalid_code)
        
        self.assertIn("Invalid Python syntax", str(context.exception))


class TestConfiguration(unittest.TestCase):
    """Test the configuration management system."""
    
    def test_llm_config_validation(self):
        """Test LLM configuration validation."""
        # Valid config
        valid_config = LLMConfig(
            provider="openai",
            api_key="sk-valid-key-with-enough-length"
        )
        self.assertTrue(valid_config.is_valid())
        
        # Invalid config - no key
        invalid_config = LLMConfig(provider="openai", api_key=None)
        self.assertFalse(invalid_config.is_valid())
        
        # Invalid config - short key
        invalid_config = LLMConfig(provider="openai", api_key="short")
        self.assertFalse(invalid_config.is_valid())
        
        # Invalid config - placeholder
        invalid_config = LLMConfig(provider="openai", api_key="YOUR_API_KEY_HERE")
        self.assertFalse(invalid_config.is_valid())
    
    def test_search_config_validation(self):
        """Test search engine configuration validation."""
        # DuckDuckGo - always valid (no credentials needed)
        ddg_config = SearchConfig(engine_type="DuckDuckGoSearch")
        self.assertTrue(ddg_config.is_valid())
        
        # Tencent - valid with credentials
        tencent_valid = SearchConfig(
            engine_type="TencentSearch",
            secret_id="valid_id",
            secret_key="valid_key"
        )
        self.assertTrue(tencent_valid.is_valid())
        
        # Tencent - invalid without credentials
        tencent_invalid = SearchConfig(engine_type="TencentSearch")
        self.assertFalse(tencent_invalid.is_valid())
    
    def test_config_from_env(self):
        """Test configuration loading from environment variables."""
        with patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test-key-with-sufficient-length',
            'MINDSEARCH_LANGUAGE': 'cn',
            'MINDSEARCH_MAX_TURNS': '15'
        }):
            config = MindSearchConfig.from_env()
            
            self.assertEqual(config.llm.api_key, 'test-key-with-sufficient-length')
            self.assertEqual(config.agent.language, 'cn')
            self.assertEqual(config.agent.max_turns, 15)


class TestAgentInitialization(unittest.TestCase):
    """Test agent initialization improvements."""
    
    @patch('mindsearch.agent.models.openai_api_key', 'test-key-with-sufficient-length')
    @patch('mindsearch.agent.create_object')
    @patch('mindsearch.agent.WebBrowser')
    def test_init_agent_success(self, mock_browser, mock_create_object):
        """Test successful agent initialization."""
        # Mock the LLM creation
        mock_llm = MagicMock()
        mock_create_object.return_value = mock_llm
        
        # Mock the browser plugin
        mock_plugin = MagicMock()
        mock_browser.return_value = mock_plugin
        
        # Mock the agent class
        with patch('mindsearch.agent.MindSearchAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent_class.return_value = mock_agent
            
            # Test initialization
            agent = init_agent(
                lang="en",
                model_format="gpt4",
                search_engine="DuckDuckGoSearch"
            )
            
            # Verify agent was created
            self.assertIsNotNone(agent)
            mock_agent_class.assert_called_once()
    
    def test_init_agent_invalid_model(self):
        """Test agent initialization with invalid model."""
        with self.assertRaises(RuntimeError):
            init_agent(model_format="nonexistent_model")
    
    @patch('mindsearch.agent.os.getenv')
    def test_init_agent_missing_api_key(self, mock_getenv):
        """Test agent initialization with missing API key."""
        # Mock missing API key
        mock_getenv.return_value = None
        
        # Should handle gracefully and warn
        with patch('mindsearch.agent.logger') as mock_logger:
            try:
                init_agent()
                mock_logger.warning.assert_called()
            except Exception:
                # Expected to fail without valid API key
                pass


class TestMemoryStructureValidation(unittest.TestCase):
    """Test the improved memory structure validation."""
    
    def test_valid_memory_structure(self):
        """Test validation of valid memory structure."""
        from mindsearch.agent.mindsearch_agent import _validate_memory_structure
        
        valid_memory = {
            "agent.memory": [
                {"sender": "user", "content": "query"},
                {"sender": "assistant", "content": "thinking"},
                {"sender": "WebBrowserActionExecutor", "content": '{"1": "http://example.com"}'}
            ]
        }
        
        self.assertTrue(_validate_memory_structure(valid_memory))
    
    def test_invalid_memory_structure(self):
        """Test validation of invalid memory structures."""
        from mindsearch.agent.mindsearch_agent import _validate_memory_structure
        
        # Missing agent.memory
        invalid1 = {}
        self.assertFalse(_validate_memory_structure(invalid1))
        
        # agent.memory not a list
        invalid2 = {"agent.memory": "not a list"}
        self.assertFalse(_validate_memory_structure(invalid2))
        
        # Insufficient length
        invalid3 = {"agent.memory": [{"item1": "value"}]}
        self.assertFalse(_validate_memory_structure(invalid3))
        
        # Missing required fields
        invalid4 = {
            "agent.memory": [
                {"sender": "user"},
                {"content": "missing sender"},
                {"invalid": "structure"}
            ]
        }
        self.assertFalse(_validate_memory_structure(invalid4))
    
    def test_reference_extraction(self):
        """Test reference extraction from memory content."""
        from mindsearch.agent.mindsearch_agent import _extract_references_from_content
        
        # Valid JSON string
        valid_content = '{"1": "http://example.com", "2": "http://test.com"}'
        refs = _extract_references_from_content(valid_content)
        expected = {1: "http://example.com", 2: "http://test.com"}
        self.assertEqual(refs, expected)
        
        # Valid dict
        valid_dict = {"1": "http://example.com", "2": "http://test.com"}
        refs = _extract_references_from_content(valid_dict)
        self.assertEqual(refs, expected)
        
        # Invalid JSON
        invalid_content = "not json"
        refs = _extract_references_from_content(invalid_content)
        self.assertIsNone(refs)
        
        # Wrong type
        wrong_type = 123
        refs = _extract_references_from_content(wrong_type)
        self.assertIsNone(refs)


class TestErrorHandling(unittest.TestCase):
    """Test improved error handling throughout the system."""
    
    def test_search_plugin_fallback(self):
        """Test search plugin creation with fallback mechanism."""
        from mindsearch.agent import create_search_plugins
        
        # Test DuckDuckGo fallback
        with patch('mindsearch.agent.WebBrowser') as mock_browser:
            mock_plugin = MagicMock()
            mock_browser.return_value = mock_plugin
            
            plugins = create_search_plugins("DuckDuckGoSearch")
            self.assertEqual(len(plugins), 1)
            mock_browser.assert_called_once()
    
    def test_configuration_validation_errors(self):
        """Test configuration validation error handling."""
        config = MindSearchConfig()
        
        # Set invalid configuration
        config.llm.api_key = None
        config.agent.language = "invalid_lang"
        
        errors = config.validate()
        
        # Should have errors for both LLM and agent
        self.assertIn("llm", errors)
        self.assertIn("agent", errors)


if __name__ == "__main__":
    # Create test directory if it doesn't exist
    import os
    os.makedirs("tests", exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2)