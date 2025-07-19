#!/usr/bin/env python3
"""
Refactored terminal interface for MindSearch with robust fallback mechanisms.
This version integrates the new search engines, safe execution, and memory handling.
"""

import os
import sys
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Check for dependencies before importing
try:
    from lagent.actions import WebBrowser
    from lagent.agents.stream import get_plugin_prompt
    from lagent.llms import GPTAPI
    from lagent.prompts import InterpreterParser, PluginParser
    LAGENT_AVAILABLE = True
except ImportError:
    logger.warning("Lagent not available, using fallback mode")
    LAGENT_AVAILABLE = False

# Import our refactored components
from mindsearch.agent.search_engines import (
    SearchEngineManager, 
    create_search_manager_with_cache,
    MockSearchEngine
)
from mindsearch.agent.memory_handler import RobustMemoryHandler, MemoryAdapter
from mindsearch.agent.safe_execution import SafeExecutionAction

# Import existing components
from mindsearch.agent.mindsearch_agent import MindSearchAgent
from mindsearch.agent.mindsearch_prompt import (
    FINAL_RESPONSE_EN,
    GRAPH_PROMPT_EN,
    searcher_context_template_en,
    searcher_input_template_en,
    searcher_system_prompt_en,
)
from mindsearch.agent.models import get_model_config


class RobustMindSearchTerminal:
    """Enhanced terminal interface with fallback mechanisms."""
    
    def __init__(self):
        self.search_manager = None
        self.agent = None
        self.fallback_mode = False
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        return {
            'model_name': os.environ.get("MODEL_NAME", "gpt4o-mini"),
            'openai_api_key': os.environ.get("OPENAI_API_KEY"),

            'search_engine': os.environ.get("SEARCH_ENGINE", "DuckDuckGo"),
            'enable_fallback': os.environ.get("ENABLE_FALLBACK", "true").lower() == "true",
            'max_node_visits': int(os.environ.get("MAX_NODE_VISITS", "3")),
            'execution_timeout': float(os.environ.get("EXECUTION_TIMEOUT", "30.0")),
            'cache_ttl': int(os.environ.get("CACHE_TTL", "3600"))
        }
    
    def _validate_config(self) -> bool:
        """Validate configuration and set fallback mode if needed."""
        if not self.config['openai_api_key']:
            logger.error("OPENAI_API_KEY not found in environment variables.")
            if self.config['enable_fallback']:
                logger.warning("Entering fallback mode with mock responses")
                self.fallback_mode = True
                return True
            else:
                print("Error: OPENAI_API_KEY required. Set with: export OPENAI_API_KEY='your-key'")
                return False
        return True
    
    def _initialize_search_manager(self):
        """Initialize the search manager with fallback engines."""
        logger.info("Initializing search manager...")
        
        # Create search manager with caching
        self.search_manager = create_search_manager_with_cache(
            cache_ttl=self.config['cache_ttl']
        )
        
        # Log available engines
        status = self.search_manager.get_status()
        logger.info(f"Available search engines: {list(status.keys())}")
    
    def _initialize_agent(self):
        """Initialize the MindSearch agent with robust components."""
        if self.fallback_mode:
            logger.info("Initializing in fallback mode...")
            self._initialize_fallback_agent()
            return
        
        logger.info(f"Initializing agent with model: {self.config['model_name']}")
        
        # Get model configuration
        model_config = get_model_config(self.config['model_name'])
        
        # Create LLM instance
        llm = GPTAPI(
            model_type=model_config["model_type"],
            key=model_config["key"],
            api_base=model_config["api_base"],
            max_new_tokens=model_config.get("max_new_tokens", 2048),
            temperature=model_config.get("temperature", 0.7),
        )
        
        # Create plugins based on configuration
        plugins = self._create_plugins()
        
        # Create agent with safe execution
        date = datetime.now().strftime("The current date is %Y-%m-%d.")
        
        self.agent = MindSearchAgent(
            llm=llm,
            template=date,
            output_format=InterpreterParser(template=GRAPH_PROMPT_EN),
            searcher_cfg=dict(
                llm=llm,
                plugins=plugins,
                template=date,
                output_format=PluginParser(
                    template=searcher_system_prompt_en,
                    tool_info=get_plugin_prompt(plugins) if plugins else "",
                ),
                user_input_template=searcher_input_template_en,
                user_context_template=searcher_context_template_en,
            ),
            summary_prompt=FINAL_RESPONSE_EN,
            max_turn=self.config['max_node_visits'],
        )
        
        # Wrap with safe execution if available
        if hasattr(self.agent, 'execution_action'):
            logger.info("Wrapping execution with SafeExecutionAction")
            self.agent.execution_action = SafeExecutionAction(
                search_engine=self.search_manager,
                max_turn=10,
                max_node_visits=self.config['max_node_visits'],
                execution_timeout=self.config['execution_timeout'],
                enable_fallback=self.config['enable_fallback']
            )
    
    def _create_plugins(self):
        """Create search plugins based on configuration."""
        plugins = []
        

        
        # Fallback to DuckDuckGo
        if not plugins and LAGENT_AVAILABLE:
            try:
                plugins.append(WebBrowser(searcher_type="DuckDuckGoSearch", topk=6))
                logger.info("Using DuckDuckGo search")
            except Exception as e:
                logger.warning(f"Failed to initialize DuckDuckGo: {e}")
        
        if not plugins:
            logger.warning("No search plugins available, will use search manager directly")
        
        return plugins
    
    def _initialize_fallback_agent(self):
        """Initialize a minimal fallback agent."""
        logger.info("Creating fallback agent with mock responses")
        
        # Create a simple fallback agent
        class FallbackAgent:
            def __init__(self, search_manager):
                self.search_manager = search_manager
            
            async def process_query(self, query: str) -> Dict[str, Any]:
                """Process query using search manager directly."""
                results = await self.search_manager.search(query, max_results=5)
                
                if results:
                    content = "Based on the search results:\n\n"
                    references = {}
                    
                    for i, result in enumerate(results, 1):
                        content += f"{i}. {result.title}\n"
                        content += f"   {result.snippet}\n\n"
                        references[str(i)] = result.url
                    
                    return {
                        'content': content,
                        'references': references,
                        'status': 'success'
                    }
                else:
                    return {
                        'content': "I couldn't find specific information about your query.",
                        'references': {},
                        'status': 'no_results'
                    }
        
        self.agent = FallbackAgent(self.search_manager)
    
    async def process_query(self, query: str):
        """Process a query with full error handling and fallback."""
        logger.info(f"Processing query: {query}")
        
        # Validate and correct memory if needed
        memory = RobustMemoryHandler.create_default_memory()
        
        try:
            if self.fallback_mode:
                # Use fallback agent
                result = await self.agent.process_query(query)
                self._display_fallback_result(result)
            else:
                # Use full agent
                await self._process_with_full_agent(query, memory)
                
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            
            if self.config['enable_fallback']:
                logger.info("Attempting fallback search...")
                await self._fallback_search(query)
            else:
                print(f"\nError: {e}")
                print("Enable fallback mode by setting: export ENABLE_FALLBACK=true")
    
    async def _process_with_full_agent(self, query: str, memory: Dict[str, Any]):
        """Process query with the full MindSearch agent."""
        agent_return = None
        
        for agent_return in self.agent(query):
            if hasattr(agent_return, 'sender'):
                print(f"\n[{agent_return.sender}]")
            
            if hasattr(agent_return, 'content') and agent_return.content:
                # Clean up the content for display
                content = str(agent_return.content)
                if len(content) > 500:
                    content = content[:500] + "..."
                print(content)
            
            # Update memory with agent state if available
            if hasattr(agent_return, 'agent_state'):
                memory = MemoryAdapter.from_agent_state(agent_return.agent_state)
                memory = RobustMemoryHandler.validate_and_correct(memory)
        
        # Display final results
        if agent_return:
            self._display_final_result(agent_return, memory)
        else:
            print("\nNo results returned")
            if self.config['enable_fallback']:
                await self._fallback_search(query)
    
    async def _fallback_search(self, query: str):
        """Perform a direct search using the search manager."""
        print("\n[Fallback Search]")
        results = await self.search_manager.search(query, max_results=5)
        
        if results:
            print(f"\nFound {len(results)} results:\n")
            for i, result in enumerate(results, 1):
                print(f"{i}. {result.title}")
                print(f"   Source: {result.url}")
                print(f"   {result.snippet}\n")
        else:
            print("No results found even with fallback search.")
    
    def _display_final_result(self, agent_return, memory: Dict[str, Any]):
        """Display the final result with references."""
        print("\n" + "="*60)
        print("FINAL RESULT")
        print("="*60)
        
        if hasattr(agent_return, 'content'):
            print(f"\n{agent_return.content}")
        
        # Display references
        references = {}
        if hasattr(agent_return, 'formatted') and agent_return.formatted:
            if 'ref2url' in agent_return.formatted:
                references = agent_return.formatted['ref2url']
        
        if not references:
            # Try to get references from memory
            references = memory.get('references', {})
        
        if references:
            print("\nReferences:")
            for ref_id, url in references.items():
                print(f"  [{ref_id}] {url}")
        else:
            print("\nNo references available.")
        
        # Display memory summary
        summary = RobustMemoryHandler.summarize_memory(memory)
        print(f"\nExecution Summary:")
        print(f"  - Nodes processed: {summary['total_nodes']}")
        print(f"  - Completed nodes: {summary['nodes_by_status']['completed']}")
        print(f"  - References found: {summary['references_count']}")
    
    def _display_fallback_result(self, result: Dict[str, Any]):
        """Display results from fallback agent."""
        print("\n" + "="*60)
        print("SEARCH RESULTS (Fallback Mode)")
        print("="*60)
        
        print(f"\n{result['content']}")
        
        if result['references']:
            print("\nReferences:")
            for ref_id, url in result['references'].items():
                print(f"  [{ref_id}] {url}")
        
        print(f"\nStatus: {result['status']}")
    
    async def run_interactive(self):
        """Run in interactive mode."""
        print("\n" + "="*60)
        print("MindSearch Terminal (Refactored Edition)")
        print("="*60)
        print(f"Model: {self.config['model_name']}")
        print(f"Search: {self.config['search_engine']}")
        print(f"Fallback: {'Enabled' if self.config['enable_fallback'] else 'Disabled'}")
        print(f"Mode: {'Fallback' if self.fallback_mode else 'Normal'}")
        print("="*60)
        print("\nType 'exit' or 'quit' to end the session.")
        print("Type 'status' to see system status.")
        print("Type 'clear' to clear the screen.\n")
        
        while True:
            try:
                query = input("\nEnter your query: ").strip()
                
                if query.lower() in ['exit', 'quit']:
                    print("Goodbye!")
                    break
                
                if query.lower() == 'status':
                    self._show_status()
                    continue
                
                if query.lower() == 'clear':
                    os.system('clear' if os.name == 'posix' else 'cls')
                    continue
                
                if query:
                    await self.process_query(query)
                
            except KeyboardInterrupt:
                print("\n\nInterrupted. Type 'exit' to quit.")
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                print(f"\nError: {e}")
    
    def _show_status(self):
        """Show system status."""
        print("\n" + "="*40)
        print("SYSTEM STATUS")
        print("="*40)
        
        # Search engine status
        if self.search_manager:
            status = self.search_manager.get_status()
            print("\nSearch Engines:")
            for engine, info in status.items():
                available = "✓" if info['available'] else "✗"
                print(f"  {available} {engine} (failures: {info['failure_count']})")
        
        # Configuration
        print("\nConfiguration:")
        print(f"  - Model: {self.config['model_name']}")
        print(f"  - Fallback Mode: {self.fallback_mode}")
        print(f"  - Max Node Visits: {self.config['max_node_visits']}")
        print(f"  - Execution Timeout: {self.config['execution_timeout']}s")
        print(f"  - Cache TTL: {self.config['cache_ttl']}s")
    
    async def run_single_query(self, query: str):
        """Run a single query (non-interactive mode)."""
        print(f"\nQuery: {query}")
        print("-" * 60)
        await self.process_query(query)


async def main():
    """Main entry point."""
    terminal = RobustMindSearchTerminal()
    
    # Validate configuration
    if not terminal._validate_config():
        return 1
    
    # Initialize components
    terminal._initialize_search_manager()
    terminal._initialize_agent()
    
    # Check if a query was provided as command line argument
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        await terminal.run_single_query(query)
    else:
        # Run in interactive mode
        await terminal.run_interactive()
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)