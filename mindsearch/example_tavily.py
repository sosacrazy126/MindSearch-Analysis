#!/usr/bin/env python3
"""
Example script demonstrating how to use Tavily search with MindSearch.

Before running this script:
1. Install dependencies: pip install -r requirements.txt
2. Set your API keys:
   export OPENAI_API_KEY='your-openai-api-key'
   export TAVILY_API_KEY='your-tavily-api-key'
"""

import os
import sys
from mindsearch.agent import init_agent

def main():
    # Check for required API keys
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not found in environment variables.")
        print("Please set your OpenAI API key using: export OPENAI_API_KEY='your-api-key'")
        sys.exit(1)
    
    if not os.environ.get("TAVILY_API_KEY"):
        print("Error: TAVILY_API_KEY not found in environment variables.")
        print("Please set your Tavily API key using: export TAVILY_API_KEY='your-api-key'")
        sys.exit(1)
    
    # Initialize agent with Tavily search
    print("Initializing MindSearch agent with Tavily search engine...")
    agent = init_agent(
        model_format="gpt4",  # or "gpt4o-mini", "gpt3.5"
        search_engine="TavilySearch",
        use_async=False
    )
    
    # Example queries
    queries = [
        "What are the latest developments in quantum computing in 2024?",
        "Who won the 2024 Nobel Prize in Physics and what was their contribution?",
        "What is the current weather in Tokyo, Japan?",
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}\n")
        
        try:
            # Run the agent
            agent_return = None
            for agent_return in agent(query):
                if hasattr(agent_return, 'sender') and agent_return.sender:
                    print(f"[{agent_return.sender}]", end=" ")
                if hasattr(agent_return, 'content') and agent_return.content:
                    content = agent_return.content
                    if isinstance(content, dict):
                        if 'response' in content:
                            print(f"Response: {content['response'][:200]}...")
                        elif 'current_node' in content:
                            print(f"Processing: {content['current_node']}")
                    else:
                        print(f"{str(content)[:200]}...")
            
            # Print final result
            if agent_return:
                print(f"\n{'='*60}")
                print("FINAL RESULT:")
                print(f"{'='*60}")
                if hasattr(agent_return, 'content'):
                    print(agent_return.content)
                if hasattr(agent_return, 'formatted') and agent_return.formatted:
                    if 'ref2url' in agent_return.formatted:
                        print("\nReferences:")
                        for ref, url in agent_return.formatted['ref2url'].items():
                            print(f"  [{ref}] {url}")
                            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()