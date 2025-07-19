# Tavily Search Integration for MindSearch

This document describes how to use Tavily search engine with MindSearch.

## Overview

Tavily is an AI-powered search API that provides high-quality search results with AI-generated answers. The integration allows MindSearch to use Tavily as an alternative to DuckDuckGo for web searches.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Get Tavily API Key**
   - Sign up at [Tavily.com](https://tavily.com) to get your API key
   - Set the environment variable:
     ```bash
     export TAVILY_API_KEY='your-tavily-api-key'
     ```

3. **Set OpenAI API Key** (required for the LLM)
   ```bash
   export OPENAI_API_KEY='your-openai-api-key'
   ```

## Usage

### 1. Using terminal.py

The `terminal.py` script now includes Tavily search by default:

```bash
# Set environment variables
export TAVILY_API_KEY='your-tavily-api-key'
export OPENAI_API_KEY='your-openai-api-key'

# Run with Tavily (default)
python mindsearch/terminal.py

# Or explicitly set search engine
export SEARCH_ENGINE=TavilySearch
python mindsearch/terminal.py

# To use DuckDuckGo instead
export SEARCH_ENGINE=DuckDuckGoSearch
python mindsearch/terminal.py
```

### 2. Using the API Server (app.py)

Start the API server with Tavily search:

```bash
# Default (DuckDuckGo)
python mindsearch/app.py

# With Tavily
python mindsearch/app.py --search_engine TavilySearch

# With specific model
python mindsearch/app.py --search_engine TavilySearch --model_format gpt4
```

### 3. Programmatic Usage

```python
from mindsearch.agent import init_agent

# Initialize agent with Tavily
agent = init_agent(
    model_format="gpt4",
    search_engine="TavilySearch",
    use_async=False
)

# Run a query
for response in agent("What is the weather in New York?"):
    print(response.content)
```

### 4. Using the Example Script

Run the provided example:

```bash
python mindsearch/example_tavily.py
```

## Features

The Tavily integration supports:

- **Advanced Search**: Uses Tavily's advanced search depth for better results
- **AI Answers**: Includes AI-generated answers for queries
- **Multiple Queries**: Can handle multiple search queries in parallel
- **Async Support**: Full async/await support for high-performance applications
- **Customizable**: Configure search depth, max results, domain filters, etc.

## Configuration Options

When initializing TavilySearch, you can customize:

```python
from mindsearch.agent.tavily_search import TavilySearch

search = TavilySearch(
    api_key="your-api-key",           # Optional if TAVILY_API_KEY is set
    search_depth="advanced",          # "basic" or "advanced"
    include_answer=True,              # Include AI-generated answer
    include_raw_content=False,        # Include raw page content
    max_results=6,                    # Maximum results per query
    include_domains=["example.com"],  # Optional: limit to specific domains
    exclude_domains=["spam.com"]      # Optional: exclude specific domains
)
```

## Comparison with DuckDuckGo

| Feature | Tavily | DuckDuckGo |
|---------|---------|------------|
| AI Answers | ✓ | ✗ |
| Search Quality | High (AI-optimized) | Good |
| Rate Limits | Based on plan | Unlimited |
| Cost | Paid (with free tier) | Free |
| Privacy | Standard | Privacy-focused |

## Troubleshooting

1. **API Key Error**: Make sure `TAVILY_API_KEY` is set in your environment
2. **Rate Limits**: Check your Tavily plan limits if you get rate limit errors
3. **No Results**: Tavily may return empty results for very specific queries - try rephrasing

## API Reference

See `mindsearch/agent/tavily_search.py` for the complete API documentation.