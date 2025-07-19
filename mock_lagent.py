"""Mock implementation of lagent modules for testing purposes."""

import os
import sys
from typing import Any, Dict, List, Optional

# Mock classes and functions
class ActionReturn:
    """Mock ActionReturn class."""
    def __init__(self, state=None, result=None, error=None):
        self.state = state
        self.result = result
        self.error = error

# Removed duplicate - see AgentStatusCode below

class WebBrowser:
    """Mock WebBrowser class."""
    def __init__(self, searcher_type="DuckDuckGoSearch", topk=6, **kwargs):
        self.searcher_type = searcher_type
        self.topk = topk
        self.kwargs = kwargs

class AsyncWebBrowser(WebBrowser):
    """Mock AsyncWebBrowser class."""
    pass

class BingBrowser(WebBrowser):
    """Mock BingBrowser class."""
    pass

class InterpreterParser:
    """Mock InterpreterParser class."""
    pass

class PluginParser:
    """Mock PluginParser class."""
    pass

def get_plugin_prompt(*args, **kwargs):
    """Mock get_plugin_prompt function."""
    return "Mock plugin prompt"

def create_object(config):
    """Mock create_object function."""
    if isinstance(config, dict) and 'type' in config:
        return config['type'](**{k: v for k, v in config.items() if k != 'type'})
    return None

# Create mock module structure
class MockModule:
    """Helper class to create mock module structure."""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

# Set up mock modules
sys.modules['lagent'] = MockModule()
sys.modules['lagent.actions'] = MockModule(
    WebBrowser=WebBrowser,
    AsyncWebBrowser=AsyncWebBrowser,
    BingBrowser=BingBrowser
)
sys.modules['lagent.agents'] = MockModule()
sys.modules['lagent.agents.stream'] = MockModule(get_plugin_prompt=get_plugin_prompt)
sys.modules['lagent.prompts'] = MockModule(
    InterpreterParser=InterpreterParser,
    PluginParser=PluginParser
)
sys.modules['lagent.utils'] = MockModule(create_object=create_object)
class AgentMessage:
    """Mock AgentMessage class."""
    def __init__(self, content="", role="user"):
        self.content = content
        self.role = role

class AgentStatusCode:
    """Mock AgentStatusCode class."""
    SUCCESS = 0
    FAILURE = 1
    
class ModelStatusCode:
    """Mock ModelStatusCode class."""
    SUCCESS = 0
    FAILURE = 1

sys.modules['lagent.schema'] = MockModule(
    ActionReturn=ActionReturn,
    ActionStatusCode=ActionStatusCode,
    AgentMessage=AgentMessage,
    AgentStatusCode=AgentStatusCode,
    ModelStatusCode=ModelStatusCode
)
# Additional mock classes
class BaseAction:
    """Mock BaseAction class."""
    def __init__(self, *args, **kwargs):
        pass

class Agent:
    """Mock Agent class."""
    def __init__(self, *args, **kwargs):
        pass

class AgentForInternLM(Agent):
    """Mock AgentForInternLM class."""
    pass

class AsyncAgent(Agent):
    """Mock AsyncAgent class."""
    pass

class AsyncAgentForInternLM(AsyncAgent):
    """Mock AsyncAgentForInternLM class."""
    pass

class GeneratorWithReturn:
    """Mock GeneratorWithReturn class."""
    def __init__(self, generator):
        self.generator = generator
        self.return_value = None

class GPTAPI:
    """Mock GPTAPI class."""
    def __init__(self, *args, **kwargs):
        pass

sys.modules['lagent.llms'] = MockModule(GPTAPI=GPTAPI)
sys.modules['lagent.agents'] = MockModule(
    Agent=Agent,
    AgentForInternLM=AgentForInternLM,
    AsyncAgent=AsyncAgent,
    AsyncAgentForInternLM=AsyncAgentForInternLM
)
sys.modules['lagent.utils'].GeneratorWithReturn = GeneratorWithReturn
sys.modules['lagent.actions'].BaseAction = BaseAction

# Also create langgraph mocks
sys.modules['langgraph'] = MockModule()
sys.modules['langgraph.checkpoint'] = MockModule()
sys.modules['langgraph.checkpoint.sqlite'] = MockModule(
    SqliteSaver=type('SqliteSaver', (), {'__init__': lambda self, *args, **kwargs: None})
)

print("Mock lagent modules loaded successfully")