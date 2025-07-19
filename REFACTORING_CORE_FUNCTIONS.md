# MindSearch Core Functions Refactoring

## Overview

This document outlines the refactoring of MindSearch core functions to address the issues identified in ISSUE.md, particularly:
- Node processing failures with memory structure issues
- Incompatibility with different OpenAI models (especially gpt-4o-mini)
- Poor error handling in WebSearchGraph execution
- Tight coupling between components

## Key Improvements

### 1. Enhanced Model Support (`models.py`)

**Before:**
- Only supported `gpt-4-turbo` hardcoded
- No flexibility for different model configurations

**After:**
- Support for multiple OpenAI models:
  - `gpt4` / `gpt4-turbo`: GPT-4 Turbo
  - `gpt4-mini`: GPT-4 Preview with reduced context
  - `gpt35`: GPT-3.5 Turbo
  - `gpt4o`: GPT-4 Optimized
  - `gpt4o-mini`: GPT-4 Optimized Mini (cost-effective)
- Configurable parameters per model (max_tokens, temperature)
- `get_model_config()` function for dynamic model selection

### 2. Robust Memory Structure Handling (`mindsearch_agent.py`)

**Before:**
- Hard-coded memory structure expectations
- Failed when memory structure didn't match exact format
- No error recovery

**After:**
- `_extract_search_result()`: Flexible extraction from multiple paths
- Better error handling with try-catch blocks
- Graceful degradation when data is missing
- Support for different memory structures from various models

### 3. Modular WebSearchGraph (`web_search_graph.py`)

**New Implementation Features:**
- `SearchNode` class for better node management
- State tracking (pending, searching, completed, failed)
- Proper error handling and recovery
- Configurable timeout and worker management
- Clean separation of concerns

**Key Methods:**
- `add_node()`: Returns initial response
- `wait_for_searches()`: Proper async handling
- `get_graph_state()`: Complete state inspection
- Resource cleanup in `__del__`

### 4. Improved ExecutionAction (`execution_action.py`)

**New Features:**
- Code extraction and validation
- Security checks for dangerous operations
- Better error messages
- Support for streaming updates
- Automatic graph instance creation

### 5. Compatibility Layer (`graph_compatibility.py`)

**Purpose:**
- Smooth transition between old and new implementations
- Automatic fallback mechanisms
- Wrapper classes for both WebSearchGraph and ExecutionAction
- Helper functions for instance creation

## Usage Examples

### Using Different Models

```bash
# Use GPT-4o Mini (cost-effective)
export MODEL_NAME=gpt4o-mini
python -m mindsearch.terminal

# Use GPT-3.5 Turbo
export MODEL_NAME=gpt35
python -m mindsearch.terminal

# Use GPT-4 Turbo (default)
python -m mindsearch.app --model_format gpt4
```

### API Server with New Models

```bash
# Start with GPT-4o Mini
python -m mindsearch.app --model_format gpt4o-mini --search_engine DuckDuckGoSearch

# Start with GPT-3.5 Turbo
python -m mindsearch.app --model_format gpt35 --search_engine DuckDuckGoSearch
```

## Migration Guide

### For Developers

1. **Update Model References:**
   ```python
   # Old way
   from mindsearch.agent.models import gpt4
   
   # New way
   from mindsearch.agent.models import get_model_config
   model_config = get_model_config("gpt4o-mini")
   ```

2. **Use Compatibility Layer:**
   ```python
   from mindsearch.agent.graph_compatibility import get_compatible_graph
   
   # Automatically uses best available implementation
   graph = get_compatible_graph(prefer_legacy=False)
   ```

3. **Handle Memory Structure Flexibly:**
   - Don't assume fixed memory indices
   - Use the new extraction helpers
   - Add proper error handling

## Benefits

1. **Cost Reduction**: Support for cheaper models like gpt4o-mini
2. **Better Reliability**: Improved error handling prevents crashes
3. **Flexibility**: Easy to add new models or search engines
4. **Maintainability**: Modular design makes debugging easier
5. **Backward Compatibility**: Existing code continues to work

## Known Limitations

1. Search execution still needs actual searcher implementation
2. Some models may have different response formats requiring adjustments
3. The compatibility layer adds a small overhead

## Next Steps

1. Implement actual search functionality in `ModularWebSearchGraph`
2. Add unit tests for new components
3. Performance optimization for large graphs
4. Add support for more LLM providers beyond OpenAI