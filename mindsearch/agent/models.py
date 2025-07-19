"""
Model configurations for MindSearch agents.

This module provides LLM configurations for different providers and models.
"""

import os
import sys
import logging
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from lagent.llms import GPTAPI

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


def get_api_key(key_name: str, service_name: str) -> Optional[str]:
    """
    Get API key from environment with proper validation.
    
    Args:
        key_name: Environment variable name
        service_name: Service name for error messages
        
    Returns:
        API key string or None if not found
    """
    api_key = os.getenv(key_name)
    if not api_key:
        logger.warning(f"{service_name} API key ({key_name}) not found in environment variables")
        return None
    
    # Validate key format (basic check)
    if len(api_key.strip()) < 10:
        logger.warning(f"Invalid {service_name} API key format")
        return None
    
    logger.info(f"Successfully loaded {service_name} API key")
    return api_key.strip()


def get_api_base(base_key: str, default_base: str, service_name: str) -> str:
    """
    Get API base URL from environment with fallback to default.
    
    Args:
        base_key: Environment variable name for API base
        default_base: Default API base URL
        service_name: Service name for logging
        
    Returns:
        API base URL
    """
    api_base = os.getenv(base_key)
    if api_base:
        logger.info(f"Using custom {service_name} API base: {api_base}")
        return api_base.strip()
    else:
        logger.info(f"Using default {service_name} API base: {default_base}")
        return default_base


def validate_model_config(config: Dict[str, Any]) -> bool:
    """
    Validate model configuration.
    
    Args:
        config: Model configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_keys = ['type', 'key']
    
    for key in required_keys:
        if key not in config:
            logger.error(f"Missing required key '{key}' in model config")
            return False
    
    if not config['key'] or config['key'] == "YOUR OPENAI API KEY":
        logger.error("Invalid or placeholder API key in model config")
        return False
    
    return True


# OpenAI Configuration
openai_api_key = get_api_key("OPENAI_API_KEY", "OpenAI")
openai_api_base = get_api_base(
    "OPENAI_API_BASE",
    "https://api.openai.com/v1/chat/completions",
    "OpenAI"
)

# Silicon Flow Configuration (alternative provider)
silicon_api_key = get_api_key("SILICON_API_KEY", "Silicon Flow")
silicon_model = os.getenv("SILICON_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct")

# Model configurations
gpt4 = {
    "type": GPTAPI,
    "model_type": "gpt-4-turbo",
    "key": openai_api_key or "MISSING_OPENAI_KEY",
    "api_base": openai_api_base,
    "max_tokens": 4000,
    "temperature": 0.1,
}

gpt4_mini = {
    "type": GPTAPI,
    "model_type": "gpt-4o-mini",
    "key": openai_api_key or "MISSING_OPENAI_KEY",
    "api_base": openai_api_base,
    "max_tokens": 4000,
    "temperature": 0.1,
}

gpt35_turbo = {
    "type": GPTAPI,
    "model_type": "gpt-3.5-turbo",
    "key": openai_api_key or "MISSING_OPENAI_KEY",
    "api_base": openai_api_base,
    "max_tokens": 4000,
    "temperature": 0.1,
}

# Silicon Flow configuration (if available)
silicon_llama = {
    "type": GPTAPI,
    "model_type": silicon_model,
    "key": silicon_api_key or "MISSING_SILICON_KEY",
    "api_base": "https://api.siliconflow.cn/v1/chat/completions",
    "max_tokens": 4000,
    "temperature": 0.1,
} if silicon_api_key else None

# Available models registry
AVAILABLE_MODELS = {
    "gpt4": gpt4,
    "gpt4_mini": gpt4_mini,
    "gpt35_turbo": gpt35_turbo,
}

# Add Silicon Flow model if available
if silicon_llama:
    AVAILABLE_MODELS["silicon_llama"] = silicon_llama

# Validate configurations
for model_name, config in AVAILABLE_MODELS.items():
    if not validate_model_config(config):
        logger.warning(f"Model configuration '{model_name}' is invalid")

# Log available models
logger.info(f"Available models: {list(AVAILABLE_MODELS.keys())}")

# Environment validation warnings
if not openai_api_key:
    logger.warning("OpenAI API key not configured. Set OPENAI_API_KEY environment variable.")
    logger.warning("Example: export OPENAI_API_KEY='your-api-key-here'")

if not silicon_api_key:
    logger.info("Silicon Flow API key not configured (optional alternative provider)")


def get_model_config(model_name: str) -> Dict[str, Any]:
    """
    Get model configuration by name.
    
    Args:
        model_name: Name of the model configuration
        
    Returns:
        Model configuration dictionary
        
    Raises:
        ValueError: If model not found or invalid
    """
    if model_name not in AVAILABLE_MODELS:
        available = ", ".join(AVAILABLE_MODELS.keys())
        raise ValueError(f"Unknown model '{model_name}'. Available models: {available}")
    
    config = AVAILABLE_MODELS[model_name].copy()
    
    if not validate_model_config(config):
        raise ValueError(f"Model configuration '{model_name}' is invalid")
    
    return config


def list_available_models() -> list:
    """
    Get list of available model names.
    
    Returns:
        List of available model names
    """
    return list(AVAILABLE_MODELS.keys())


# Backward compatibility - keep original variable names
# These are deprecated and should be replaced with get_model_config()
if openai_api_key:
    # Only expose if we have a valid key
    gpt4["key"] = openai_api_key
    gpt4_mini["key"] = openai_api_key
    gpt35_turbo["key"] = openai_api_key
else:
    logger.warning("Model configurations may not work without valid API keys")

