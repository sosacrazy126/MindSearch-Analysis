import os
import sys
from datetime import datetime

from lagent.actions import WebBrowser
from lagent.agents.stream import get_plugin_prompt
from lagent.llms import GPTAPI
from lagent.prompts import InterpreterParser, PluginParser

from mindsearch.agent.mindsearch_agent import MindSearchAgent
from mindsearch.agent.mindsearch_prompt import (
    FINAL_RESPONSE_CN,
    FINAL_RESPONSE_EN,
    GRAPH_PROMPT_CN,
    GRAPH_PROMPT_EN,
    searcher_context_template_cn,
    searcher_context_template_en,
    searcher_input_template_cn,
    searcher_input_template_en,
    searcher_system_prompt_cn,
    searcher_system_prompt_en,
)

lang = "en"
date = datetime.now().strftime("The current date is %Y-%m-%d.")
# Check for OpenAI API key
openai_api_key = os.environ.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Error: OPENAI_API_KEY not found in environment variables.")
    print("Please set your OpenAI API key using: export OPENAI_API_KEY='your-api-key'")
    sys.exit(1)

llm = GPTAPI(
    model_type="gpt-4.0-mini",
    key=openai_api_key,
    api_base=os.environ.get("OPENAI_API_BASE") or os.getenv("OPENAI_API_BASE") or "https://api.openai.com/v1/chat/completions",
)
plugins = [WebBrowser(searcher_type="DuckDuckGoSearch", topk=6)]
agent = MindSearchAgent(
    llm=llm,
    template=date,
    output_format=InterpreterParser(template=GRAPH_PROMPT_CN if lang == "cn" else GRAPH_PROMPT_EN),
    searcher_cfg=dict(
        llm=llm,
        plugins=plugins,
        template=date,
        output_format=PluginParser(
            template=searcher_system_prompt_cn if lang == "cn" else searcher_system_prompt_en,
            tool_info=get_plugin_prompt(plugins),
        ),
        user_input_template=searcher_input_template_cn
        if lang == "cn"
        else searcher_input_template_en,
        user_context_template=searcher_context_template_cn
        if lang == "cn"
        else searcher_context_template_en,
    ),
    summary_prompt=FINAL_RESPONSE_CN if lang == "cn" else FINAL_RESPONSE_EN,
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
