import os
import sys
from datetime import datetime

from lagent.actions import WebBrowser
from lagent.agents.stream import get_plugin_prompt
from lagent.llms import GPTAPI
from lagent.prompts import InterpreterParser, PluginParser

from mindsearch.agent.mindsearch_agent import MindSearchAgent
from mindsearch.agent.mindsearch_prompt import (
    FINAL_RESPONSE_EN,
    GRAPH_PROMPT_EN,
    searcher_context_template_en,
    searcher_input_template_en,
    searcher_system_prompt_en,
)
from mindsearch.agent.models import get_model_config

# Get model from environment or use default
model_name = os.environ.get("MODEL_NAME", "gpt4o-mini")
print(f"Using model: {model_name}")

date = datetime.now().strftime("The current date is %Y-%m-%d.")

# Check for OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    print("Please set your OpenAI API key using: export OPENAI_API_KEY='your-api-key'")
    sys.exit(1)

# Get model configuration
model_config = get_model_config(model_name)

# Create LLM instance
llm = GPTAPI(
    model_type=model_config["model_type"],
    key=model_config["key"],
    api_base=model_config["api_base"],
    max_new_tokens=model_config.get("max_new_tokens", 2048),
    temperature=model_config.get("temperature", 0.7),
)

plugins = [WebBrowser(searcher_type="DuckDuckGoSearch", topk=6)]
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
                print(f"References: {agent_return.formatted['ref2url']}")
    else:
        print("No results returned")
        
except Exception as e:
    print(f"Error during execution: {e}")
    import traceback
    traceback.print_exc()
