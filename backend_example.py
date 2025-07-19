#!/usr/bin/env python3
"""
MindSearch Backend Client Example

A comprehensive example of how to interact with the MindSearch API,
including streaming responses, error handling, and configuration options.
"""

import json
import argparse
import logging
import time
from typing import Optional, Dict, Any, Iterator
from urllib.parse import urlparse

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MindSearchClient:
    """Client for interacting with the MindSearch API."""
    
    def __init__(self, 
                 base_url: str = "http://localhost:8002",
                 timeout: int = 60):
        """
        Initialize the MindSearch client.
        
        Args:
            base_url: Base URL of the MindSearch API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        
        # Validate URL
        try:
            parsed = urlparse(base_url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid base URL format")
        except Exception as e:
            raise ValueError(f"Invalid base URL: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health status of the API.
        
        Returns:
            Health status information
            
        Raises:
            requests.RequestException: If health check fails
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Health check failed: {e}")
            raise
    
    def search(self, 
               query: str, 
               session_id: Optional[int] = None,
               agent_config: Optional[Dict] = None) -> Iterator[Dict[str, Any]]:
        """
        Perform a search query with streaming response.
        
        Args:
            query: Search query string
            session_id: Optional session ID for conversation continuity
            agent_config: Optional agent configuration overrides
            
        Yields:
            Streaming response data
            
        Raises:
            requests.RequestException: If request fails
            ValueError: If response format is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        # Prepare request data
        data = {
            "inputs": query.strip(),
            "agent_cfg": agent_config or {}
        }
        
        if session_id is not None:
            data["session_id"] = session_id
        
        headers = {"Content-Type": "application/json"}
        
        try:
            logger.info(f"Starting search: {query[:100]}...")
            
            response = self.session.post(
                f"{self.base_url}/solve",
                headers=headers,
                data=json.dumps(data),
                timeout=self.timeout,
                stream=True
            )
            response.raise_for_status()
            
            # Process streaming response
            message_count = 0
            for chunk in response.iter_lines(
                chunk_size=8192, 
                decode_unicode=True, 
                delimiter='\n'
            ):
                if not chunk or chunk.isspace():
                    continue
                
                # Handle SSE format
                if chunk.startswith("data: "):
                    chunk = chunk[6:]  # Remove "data: " prefix
                elif chunk.startswith(": ping"):
                    logger.debug("Received ping")
                    continue
                else:
                    continue
                
                try:
                    # Parse JSON data
                    response_data = json.loads(chunk)
                    message_count += 1
                    
                    # Add metadata
                    response_data["_client_message_count"] = message_count
                    response_data["_timestamp"] = time.time()
                    
                    yield response_data
                    
                except json.JSONDecodeError as e:
                    logger.warning(f"Failed to parse response chunk: {e}")
                    continue
            
            logger.info(f"Search completed, processed {message_count} messages")
            
        except requests.RequestException as e:
            logger.error(f"Search request failed: {e}")
            raise
    
    def search_simple(self, query: str) -> Dict[str, Any]:
        """
        Perform a simple search and return the final result.
        
        Args:
            query: Search query string
            
        Returns:
            Final search result
            
        Raises:
            requests.RequestException: If request fails
            TimeoutError: If search takes too long
        """
        start_time = time.time()
        final_result = None
        
        for response_data in self.search(query):
            final_result = response_data
            
            # Check for timeout
            if time.time() - start_time > self.timeout:
                raise TimeoutError(f"Search exceeded timeout of {self.timeout} seconds")
        
        if final_result is None:
            raise ValueError("No response received from search")
        
        return final_result
    
    def close(self):
        """Close the session."""
        self.session.close()


def format_search_result(result: Dict[str, Any], verbose: bool = False) -> str:
    """
    Format search result for display.
    
    Args:
        result: Search result data
        verbose: Whether to include verbose information
        
    Returns:
        Formatted result string
    """
    lines = []
    
    # Extract response data
    response_data = result.get("response", {})
    current_node = response_data.get("current_node", "unknown")
    response_content = response_data.get("response", {})
    
    # Header
    lines.append("=" * 60)
    lines.append(f"Search Result (Node: {current_node})")
    lines.append("=" * 60)
    
    # Content
    if isinstance(response_content, dict):
        content = response_content.get("content", "")
        if content:
            lines.append("Content:")
            lines.append(f"  {content}")
        
        # References
        if "formatted" in response_content:
            formatted = response_content["formatted"]
            if isinstance(formatted, dict) and "ref2url" in formatted:
                refs = formatted["ref2url"]
                if refs:
                    lines.append(f"\nReferences ({len(refs)} sources):")
                    for idx, url in refs.items():
                        lines.append(f"  [[{idx}]] {url}")
                else:
                    lines.append("\nReferences: None found")
    else:
        lines.append(f"Content: {response_content}")
    
    # Verbose information
    if verbose:
        lines.append(f"\nMetadata:")
        lines.append(f"  Session ID: {result.get('session_id', 'N/A')}")
        lines.append(f"  Message Count: {result.get('message_count', 'N/A')}")
        lines.append(f"  Timestamp: {result.get('_timestamp', 'N/A')}")
        
        # Graph information
        adjacency_list = response_data.get("adjacency_list", {})
        all_nodes = response_data.get("all_nodes", {})
        if adjacency_list or all_nodes:
            lines.append(f"\nGraph Information:")
            lines.append(f"  Total nodes: {len(all_nodes)}")
            lines.append(f"  Adjacency entries: {len(adjacency_list)}")
    
    lines.append("=" * 60)
    return "\n".join(lines)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="MindSearch API Client Example",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python backend_example.py "What is the weather in New York?"
  python backend_example.py --url http://remote-server:8002 "AI news"
  python backend_example.py --verbose --stream "Latest tech developments"
        """
    )
    
    parser.add_argument(
        "query",
        nargs="?",
        default="What is the weather like today in New York?",
        help="Search query to execute"
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8002",
        help="MindSearch API base URL (default: http://localhost:8002)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="Request timeout in seconds (default: 60)"
    )
    
    parser.add_argument(
        "--session-id",
        type=int,
        help="Session ID for conversation continuity"
    )
    
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Show streaming responses (default: show final result only)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--health-check",
        action="store_true",
        help="Perform health check only"
    )
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create client
    try:
        client = MindSearchClient(
            base_url=args.url,
            timeout=args.timeout
        )
        logger.info(f"Connected to MindSearch API at {args.url}")
    except ValueError as e:
        logger.error(f"Failed to create client: {e}")
        return 1
    
    try:
        # Health check
        if args.health_check:
            try:
                health = client.health_check()
                print("Health Check Results:")
                print(json.dumps(health, indent=2))
                return 0
            except requests.RequestException as e:
                logger.error(f"Health check failed: {e}")
                return 1
        
        # Perform search
        if args.stream:
            # Streaming mode
            print(f"Searching (streaming): {args.query}")
            print("-" * 60)
            
            try:
                for i, result in enumerate(client.search(
                    args.query, 
                    session_id=args.session_id
                ), 1):
                    print(f"\n--- Stream {i} ---")
                    print(format_search_result(result, args.verbose))
                    
            except (requests.RequestException, ValueError, TimeoutError) as e:
                logger.error(f"Streaming search failed: {e}")
                return 1
        else:
            # Simple mode
            print(f"Searching: {args.query}")
            
            try:
                result = client.search_simple(args.query)
                print(format_search_result(result, args.verbose))
                
            except (requests.RequestException, ValueError, TimeoutError) as e:
                logger.error(f"Search failed: {e}")
                return 1
        
    finally:
        client.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
