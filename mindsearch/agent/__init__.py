import os
import logging
from copy import deepcopy
from datetime import datetime

from lagent.actions import AsyncWebBrowser, WebBrowser
from lagent.agents.stream import get_plugin_prompt
from lagent.prompts import InterpreterParser, PluginParser
from lagent.utils import create_object

from . import models as llm_factory
from .mindsearch_agent import AsyncMindSearchAgent, MindSearchAgent
from .mindsearch_prompt import (
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

LLM = {}


def validate_environment():
    """Validate required environment variables and dependencies."""
    required_vars = []
    
    # Check for API keys
    if not os.getenv("OPENAI_API_KEY"):
        required_vars.append("OPENAI_API_KEY")
    
    if required_vars:
        logger.warning(f"Missing environment variables: {required_vars}")
        return False
    return True


def create_search_plugins(search_engine="DuckDuckGoSearch", use_async=False):
    """Create and configure search plugins with proper error handling."""
    try:
        if search_engine == "TencentSearch":
            secret_id = os.getenv("TENCENT_SEARCH_SECRET_ID")
            secret_key = os.getenv("TENCENT_SEARCH_SECRET_KEY")
            
            if not secret_id or not secret_key:
                logger.warning("TencentSearch credentials not found, falling back to DuckDuckGo")
                search_engine = "DuckDuckGoSearch"
            else:
                plugin_config = dict(
                    type=AsyncWebBrowser if use_async else WebBrowser,
                    searcher_type=search_engine,
                    topk=6,
                    secret_id=secret_id,
                    secret_key=secret_key,
                )
        
        if search_engine == "DuckDuckGoSearch":
            plugin_config = dict(
                type=AsyncWebBrowser if use_async else WebBrowser,
                searcher_type=search_engine,
                topk=6,
                api_key=os.getenv("WEB_SEARCH_API_KEY"),  # Optional for DuckDuckGo
            )
        
        # Create plugin instance
        plugin_class = plugin_config.pop("type")
        plugin = plugin_class(**plugin_config)
        
        logger.info(f"Successfully created {search_engine} plugin (async: {use_async})")
        return [plugin]
        
    except Exception as e:
        logger.error(f"Failed to create search plugin: {e}")
        # Fallback to basic DuckDuckGo without optional parameters
        try:
            plugin_class = AsyncWebBrowser if use_async else WebBrowser
            plugin = plugin_class(searcher_type="DuckDuckGoSearch", topk=6)
            logger.info("Created fallback DuckDuckGo plugin")
            return [plugin]
        except Exception as fallback_error:
            logger.error(f"Fallback plugin creation failed: {fallback_error}")
            raise RuntimeError(f"Unable to create any search plugins: {fallback_error}")


def init_agent(lang="cn",
               model_format="gpt4",
               search_engine="DuckDuckGoSearch",
               use_async=False):
    """
    Initialize MindSearch agent with proper configuration and error handling.
    
    Args:
        lang (str): Language setting - "cn" for Chinese, "en" for English
        model_format (str): Model configuration key from models.py
        search_engine (str): Search engine type
        use_async (bool): Whether to use async version
        
    Returns:
        MindSearchAgent: Configured agent instance
        
    Raises:
        RuntimeError: If agent initialization fails
    """
    try:
        # Validate environment
        if not validate_environment():
            logger.warning("Environment validation failed, proceeding with available configuration")
        
        # Get or create LLM instance
        mode = "async" if use_async else "sync"
        llm = LLM.get(model_format, {}).get(mode)
        
        if llm is None:
            llm_cfg = deepcopy(getattr(llm_factory, model_format, None))
            if llm_cfg is None:
                raise ValueError(f"Unknown model format: {model_format}")
            
            if use_async:
                cls_name = (
                    llm_cfg["type"].split(".")[-1] if isinstance(
                        llm_cfg["type"], str) else llm_cfg["type"].__name__)
                llm_cfg["type"] = f"lagent.llms.Async{cls_name}"
            
            try:
                llm = create_object(llm_cfg)
                LLM.setdefault(model_format, {}).setdefault(mode, llm)
                logger.info(f"Created LLM instance: {model_format} ({mode})")
            except Exception as e:
                raise RuntimeError(f"Failed to create LLM instance: {e}")

        # Create search plugins with error handling
        plugins = create_search_plugins(search_engine, use_async)

        # Prepare date context
        date = datetime.now().strftime("The current date is %Y-%m-%d.")

        # Select appropriate templates based on language
        templates = {
            "graph_prompt": GRAPH_PROMPT_CN if lang == "cn" else GRAPH_PROMPT_EN,
            "searcher_system": searcher_system_prompt_cn if lang == "cn" else searcher_system_prompt_en,
            "searcher_input": searcher_input_template_cn if lang == "cn" else searcher_input_template_en,
            "searcher_context": searcher_context_template_cn if lang == "cn" else searcher_context_template_en,
            "final_response": FINAL_RESPONSE_CN if lang == "cn" else FINAL_RESPONSE_EN,
        }

        # Create agent with improved configuration
        agent_class = AsyncMindSearchAgent if use_async else MindSearchAgent
        agent = agent_class(
            llm=llm,
            template=date,
            output_format=InterpreterParser(template=templates["graph_prompt"]),
            searcher_cfg=dict(
                llm=llm,
                plugins=plugins,
                template=date,
                output_format=PluginParser(
                    template=templates["searcher_system"],
                    tool_info=get_plugin_prompt(plugins),
                ),
                user_input_template=templates["searcher_input"],
                user_context_template=templates["searcher_context"],
            ),
            summary_prompt=templates["final_response"],
            max_turn=10,
        )
        
        logger.info(f"Successfully initialized {agent_class.__name__} with {search_engine}")
        return agent
        
    except Exception as e:
        logger.error(f"Agent initialization failed: {e}")
        raise RuntimeError(f"Failed to initialize MindSearch agent: {e}")
