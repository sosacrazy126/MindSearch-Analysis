import os
from copy import deepcopy
from datetime import datetime

from lagent.actions import AsyncWebBrowser, WebBrowser
from lagent.agents.stream import get_plugin_prompt
from lagent.prompts import InterpreterParser, PluginParser
from lagent.utils import create_object

from . import models as llm_factory
from .mindsearch_agent import AsyncMindSearchAgent, MindSearchAgent
from .mindsearch_prompt import (
    FINAL_RESPONSE_EN,
    GRAPH_PROMPT_EN,
    searcher_context_template_en,
    searcher_input_template_en,
    searcher_system_prompt_en,
)
from .tavily_search import TavilySearch, AsyncTavilySearch

LLM = {}


def init_agent(model_format="gpt4",
               search_engine="DuckDuckGoSearch",
               use_async=False):
    mode = "async" if use_async else "sync"
    llm = LLM.get(model_format, {}).get(mode)
    if llm is None:
        # Use the new get_model_config function
        if hasattr(llm_factory, 'get_model_config'):
            llm_cfg = deepcopy(llm_factory.get_model_config(model_format))
        else:
            # Fallback to old method for backward compatibility
            llm_cfg = deepcopy(getattr(llm_factory, model_format, None))
            if llm_cfg is None:
                raise NotImplementedError(f"Model format '{model_format}' is not supported")
        
        if use_async:
            cls_name = (
                llm_cfg["type"].split(".")[-1] if isinstance(
                    llm_cfg["type"], str) else llm_cfg["type"].__name__)
            llm_cfg["type"] = f"lagent.llms.Async{cls_name}"
        llm = create_object(llm_cfg)
        LLM.setdefault(model_format, {}).setdefault(mode, llm)

    date = datetime.now().strftime("The current date is %Y-%m-%d.")
    
    # Configure search plugin based on search engine
    if search_engine == "TavilySearch":
        plugins = [dict(
            type=AsyncTavilySearch if use_async else TavilySearch,
            api_key=os.getenv("TAVILY_API_KEY"),
            search_depth="advanced",
            include_answer=True,
            max_results=6
        )]
    elif search_engine == "TencentSearch":
        plugins = [dict(
            type=AsyncWebBrowser if use_async else WebBrowser,
            searcher_type=search_engine,
            topk=6,
            secret_id=os.getenv("TENCENT_SEARCH_SECRET_ID"),
            secret_key=os.getenv("TENCENT_SEARCH_SECRET_KEY"),
        )]
    else:
        plugins = [dict(
            type=AsyncWebBrowser if use_async else WebBrowser,
            searcher_type=search_engine,
            topk=6,
            api_key=os.getenv("WEB_SEARCH_API_KEY"),
        )]
    
    agent = (AsyncMindSearchAgent if use_async else MindSearchAgent)(
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
    return agent
