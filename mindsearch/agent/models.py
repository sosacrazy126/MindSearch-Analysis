import os
import sys
from typing import Dict, Any

from dotenv import load_dotenv
from lagent.llms import GPTAPI

# Load environment variables from .env file
load_dotenv()

# Check for OpenAI API key in environment variables
openai_api_key = os.environ.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    print("Warning: OPENAI_API_KEY not found in environment variables.")
    print("Please set your OpenAI API key using: export OPENAI_API_KEY='your-api-key'")
    openai_api_key = "YOUR OPENAI API KEY"

# Base configuration for OpenAI models
base_openai_config = {
    "type": GPTAPI,
    "key": openai_api_key,
    "api_base": os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1/chat/completions",
    "max_new_tokens": 4096,
    "temperature": 0.7,
}

# Model configurations with specific parameters
MODEL_CONFIGS = {
    "gpt4": {
        **base_openai_config,
        "model_type": "gpt-4-turbo",
    },
    "gpt4-turbo": {
        **base_openai_config,
        "model_type": "gpt-4-turbo",
    },
    "gpt4-mini": {
        **base_openai_config,
        "model_type": "gpt-4-0125-preview",
        "max_new_tokens": 2048,  # Smaller context for mini model
    },
    "gpt35": {
        **base_openai_config,
        "model_type": "gpt-3.5-turbo",
        "max_new_tokens": 2048,
    },
    "gpt4o": {
        **base_openai_config,
        "model_type": "gpt-4o",
    },
    "gpt4o-mini": {
        **base_openai_config,
        "model_type": "gpt-4o-mini",
        "max_new_tokens": 2048,
    },
}

# Maintain backward compatibility
gpt4 = MODEL_CONFIGS["gpt4"]

def get_model_config(model_name: str) -> Dict[str, Any]:
    """Get model configuration by name.
    
    Args:
        model_name: Name of the model (e.g., 'gpt4', 'gpt35', 'gpt4-mini')
        
    Returns:
        Model configuration dictionary
    """
    if model_name not in MODEL_CONFIGS:
        print(f"Warning: Model '{model_name}' not found. Using 'gpt4' as default.")
        return MODEL_CONFIGS["gpt4"]
    return MODEL_CONFIGS[model_name]

