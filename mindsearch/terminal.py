#!/usr/bin/env python3
"""
MindSearch Terminal Interface

A command-line interface for the MindSearch AI-powered information retrieval system.
"""

import os
import sys
import argparse
import logging
from datetime import datetime

from mindsearch.agent import init_agent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MindSearch Terminal Interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python terminal.py "What is the weather in New York?"
  python terminal.py --lang en --model gpt4 "Latest AI developments"
  python terminal.py --search-engine DuckDuckGoSearch "Python best practices"
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        help="Search query to execute"
    )
    
    parser.add_argument(
        "--lang",
        choices=["en", "cn"],
        default="en",
        help="Language for responses (default: en)"
    )
    
    parser.add_argument(
        "--model",
        default="gpt4",
        help="Model configuration to use (default: gpt4)"
    )
    
    parser.add_argument(
        "--search-engine",
        choices=["DuckDuckGoSearch", "TencentSearch"],
        default="DuckDuckGoSearch",
        help="Search engine to use (default: DuckDuckGoSearch)"
    )
    
    parser.add_argument(
        "--max-turns",
        type=int,
        default=10,
        help="Maximum number of search turns (default: 10)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Enter interactive mode"
    )
    
    return parser.parse_args()


def validate_environment():
    """Validate required environment variables."""
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        logger.error("OPENAI_API_KEY not found in environment variables")
        logger.error("Please set your OpenAI API key using: export OPENAI_API_KEY='your-api-key'")
        return False
    
    logger.info("Environment validation passed")
    return True


def execute_search(agent, query, verbose=False):
    """Execute a search query using the agent."""
    if not query or not query.strip():
        logger.warning("Empty query provided")
        return None
    
    logger.info(f"Executing search: {query}")
    
    try:
        results = []
        step_count = 0
        
        for agent_return in agent(query):
            step_count += 1
            
            if verbose and hasattr(agent_return, 'sender'):
                logger.info(f"Step {step_count}: {agent_return.sender}")
            
            if hasattr(agent_return, 'content') and agent_return.content:
                if verbose:
                    logger.info(f"Content: {str(agent_return.content)[:100]}...")
                
            results.append(agent_return)
        
        return results[-1] if results else None
        
    except KeyboardInterrupt:
        logger.info("Search interrupted by user")
        return None
    except Exception as e:
        logger.error(f"Error during search execution: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return None


def display_results(result, verbose=False):
    """Display search results in a formatted way."""
    if not result:
        print("No results returned")
        return
    
    print("\n" + "="*60)
    print("SEARCH RESULTS")
    print("="*60)
    
    # Display sender information
    if hasattr(result, 'sender'):
        print(f"Sender: {result.sender}")
    
    # Display main content
    if hasattr(result, 'content'):
        print(f"\nContent:")
        if isinstance(result.content, dict):
            for key, value in result.content.items():
                print(f"  {key}: {value}")
        else:
            print(f"  {result.content}")
    
    # Display references if available
    if hasattr(result, 'formatted') and result.formatted:
        if isinstance(result.formatted, dict) and 'ref2url' in result.formatted:
            refs = result.formatted['ref2url']
            if refs:
                print(f"\nReferences ({len(refs)} sources):")
                for idx, url in refs.items():
                    print(f"  [[{idx}]] {url}")
            else:
                print("\nReferences: None found")
        
        # Display graph information if verbose
        if verbose and 'node' in result.formatted:
            nodes = result.formatted['node']
            print(f"\nGraph Information:")
            print(f"  Total nodes: {len(nodes)}")
            for name, node_data in nodes.items():
                if name not in ['root', 'response']:
                    print(f"  - {name}: {node_data.get('type', 'unknown')}")
    
    print("="*60)


def interactive_mode(agent, verbose=False):
    """Run in interactive mode for multiple queries."""
    print("\n" + "="*60)
    print("MindSearch Interactive Mode")
    print("Type 'quit' or 'exit' to end, 'help' for commands")
    print("="*60)
    
    while True:
        try:
            query = input("\nSearch Query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if query.lower() == 'help':
                print("Available commands:")
                print("  help     - Show this help")
                print("  quit/exit- Exit interactive mode")
                print("  Any other text will be treated as a search query")
                continue
            
            if not query:
                print("Please enter a search query")
                continue
            
            print(f"\nSearching for: {query}")
            result = execute_search(agent, query, verbose)
            display_results(result, verbose)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except EOFError:
            print("\nGoodbye!")
            break


def main():
    """Main function."""
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.getLogger('mindsearch').setLevel(logging.DEBUG)
    
    # Validate environment
    if not validate_environment():
        sys.exit(1)
    
    # Initialize agent
    try:
        logger.info(f"Initializing agent with model: {args.model}, language: {args.lang}")
        agent = init_agent(
            lang=args.lang,
            model_format=args.model,
            search_engine=args.search_engine,
            use_async=False
        )
        logger.info("Agent initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize agent: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)
    
    # Run interactive mode or single query
    if args.interactive:
        interactive_mode(agent, args.verbose)
    else:
        # Use provided query or default
        query = args.query or "What is the weather like today in New York?"
        result = execute_search(agent, query, args.verbose)
        display_results(result, args.verbose)


if __name__ == "__main__":
    main()
