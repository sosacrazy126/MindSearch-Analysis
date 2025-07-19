"""
Patch for terminal.py to integrate robust fallback mechanisms.
This shows the minimal changes needed to add fallback support.
"""

# Add these imports at the top of terminal.py after existing imports:
"""
import asyncio
import logging
from mindsearch.agent.search_engines import MockSearchEngine, SearchEngineManager
from mindsearch.agent.memory_handler import RobustMemoryHandler

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
"""

# Add this function before the main execution block:
def create_fallback_search_manager():
    """Create a search manager with fallback to mock engine."""
    manager = SearchEngineManager()
    # Ensure mock engine is always available
    if len(manager.engines) < 2:
        manager.add_engine(MockSearchEngine())
    return manager

# Replace the agent initialization section with:
def initialize_agent_with_fallback():
    """Initialize agent with fallback support."""
    try:
        # Existing agent initialization code...
        agent = MindSearchAgent(
            llm=llm,
            template=date,
            output_format=InterpreterParser(template=GRAPH_PROMPT_EN),
            searcher_cfg=dict(
                llm=llm,
                plugins=plugins,
                template=date,
                output_format=PluginParser(
                    template=searcher_system_prompt_en,
                    tool_info=get_plugin_prompt(plugins),
                ),
                user_input_template=searcher_input_template_en,
                user_context_template=searcher_context_template_en,
            ),
            summary_prompt=FINAL_RESPONSE_EN,
            max_turn=10,
        )
        
        # Add fallback search manager
        agent._fallback_search_manager = create_fallback_search_manager()
        
        return agent, False  # agent, is_fallback_mode
        
    except Exception as e:
        logger.error(f"Failed to initialize full agent: {e}")
        logger.info("Initializing fallback agent...")
        
        # Create minimal fallback agent
        class FallbackAgent:
            def __init__(self):
                self.search_manager = create_fallback_search_manager()
            
            def __call__(self, query):
                # Run async search synchronously
                loop = asyncio.new_event_loop()
                results = loop.run_until_complete(
                    self.search_manager.search(query, max_results=5)
                )
                loop.close()
                
                # Format results
                class FallbackReturn:
                    def __init__(self, content, refs):
                        self.sender = "FallbackAgent"
                        self.content = content
                        self.formatted = {"ref2url": refs}
                
                if results:
                    content = "Search Results:\n\n"
                    refs = {}
                    for i, r in enumerate(results, 1):
                        content += f"{i}. {r.title}\n   {r.snippet}\n\n"
                        refs[str(i)] = r.url
                    yield FallbackReturn(content, refs)
                else:
                    yield FallbackReturn("No results found.", {})
        
        return FallbackAgent(), True

# Update the main execution block:
"""
# Replace:
agent = MindSearchAgent(...)

# With:
agent, is_fallback = initialize_agent_with_fallback()

if is_fallback:
    print("⚠️  Running in fallback mode with limited functionality")

# Wrap the query execution in better error handling:
try:
    query = "What is the weather like today in New York?"
    print(f"Query: {query}")
    print("Starting search...")
    
    agent_return = None
    for agent_return in agent(query):
        if hasattr(agent_return, 'sender'):
            print(f"Step: {agent_return.sender}")
        if hasattr(agent_return, 'content') and agent_return.content:
            print(f"Content: {agent_return.content}")
    
    if agent_return:
        print("\n=== Final Result ===")
        print(f"Sender: {agent_return.sender}")
        if hasattr(agent_return, 'content'):
            print(f"Content: {agent_return.content}")
        if hasattr(agent_return, 'formatted') and agent_return.formatted:
            if 'ref2url' in agent_return.formatted:
                refs = agent_return.formatted['ref2url']
                if refs:
                    print(f"References: {refs}")
                else:
                    print("References: {} (No references found)")
                    
                    # Try fallback search if no references
                    if not is_fallback and hasattr(agent, '_fallback_search_manager'):
                        print("\nAttempting fallback search...")
                        loop = asyncio.new_event_loop()
                        fallback_results = loop.run_until_complete(
                            agent._fallback_search_manager.search(query, max_results=3)
                        )
                        loop.close()
                        
                        if fallback_results:
                            print("Fallback results:")
                            for i, r in enumerate(fallback_results, 1):
                                print(f"  [{i}] {r.title}")
                                print(f"      {r.url}")
    else:
        print("No results returned")
        
except Exception as e:
    print(f"Error during execution: {e}")
    import traceback
    traceback.print_exc()
    
    # Try fallback search on error
    print("\nAttempting fallback search due to error...")
    try:
        fallback_manager = create_fallback_search_manager()
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(
            fallback_manager.search(query, max_results=5)
        )
        loop.close()
        
        if results:
            print("\nFallback Search Results:")
            for i, r in enumerate(results, 1):
                print(f"{i}. {r.title}")
                print(f"   URL: {r.url}")
                print(f"   {r.snippet}\n")
        else:
            print("No fallback results available.")
    except Exception as fe:
        print(f"Fallback search also failed: {fe}")
"""

# Add this at the very end for interactive mode:
"""
# Optional: Add interactive mode
if __name__ == "__main__" and len(sys.argv) == 1:
    print("\nNo query provided. Enter 'exit' to quit.")
    while True:
        try:
            user_query = input("\nEnter query: ").strip()
            if user_query.lower() == 'exit':
                break
            if user_query:
                # Re-run with new query
                # ... (repeat the execution block with user_query)
        except KeyboardInterrupt:
            print("\nExiting...")
            break
"""