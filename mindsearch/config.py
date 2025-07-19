"""
Configuration management for MindSearch.

This module provides centralized configuration management for the MindSearch system,
supporting environment variables, configuration files, and default values.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


@dataclass
class APIConfig:
    """API server configuration."""
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    docs_enabled: bool = False
    
    @classmethod
    def from_env(cls) -> 'APIConfig':
        """Create API config from environment variables."""
        return cls(
            host=os.getenv("MINDSEARCH_HOST", cls.host),
            port=int(os.getenv("MINDSEARCH_PORT", cls.port)),
            debug=os.getenv("MINDSEARCH_DEBUG", "false").lower() == "true",
            cors_origins=os.getenv("MINDSEARCH_CORS_ORIGINS", "*").split(","),
            docs_enabled=os.getenv("MINDSEARCH_DOCS_ENABLED", "false").lower() == "true",
        )


@dataclass
class LLMConfig:
    """LLM configuration."""
    provider: str = "openai"
    model_name: str = "gpt-4-turbo"
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 60
    
    @classmethod
    def from_env(cls, provider: str = "openai") -> 'LLMConfig':
        """Create LLM config from environment variables."""
        if provider == "openai":
            return cls(
                provider="openai",
                model_name=os.getenv("OPENAI_MODEL", "gpt-4-turbo"),
                api_key=os.getenv("OPENAI_API_KEY"),
                api_base=os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1/chat/completions"),
                max_tokens=int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("OPENAI_TEMPERATURE", "0.1")),
                timeout=int(os.getenv("OPENAI_TIMEOUT", "60")),
            )
        elif provider == "silicon":
            return cls(
                provider="silicon",
                model_name=os.getenv("SILICON_MODEL", "meta-llama/Meta-Llama-3.1-8B-Instruct"),
                api_key=os.getenv("SILICON_API_KEY"),
                api_base=os.getenv("SILICON_API_BASE", "https://api.siliconflow.cn/v1/chat/completions"),
                max_tokens=int(os.getenv("SILICON_MAX_TOKENS", "4000")),
                temperature=float(os.getenv("SILICON_TEMPERATURE", "0.1")),
                timeout=int(os.getenv("SILICON_TIMEOUT", "60")),
            )
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")
    
    def is_valid(self) -> bool:
        """Check if the configuration is valid."""
        return (
            self.api_key is not None and 
            len(self.api_key.strip()) > 10 and
            self.api_key != "YOUR_API_KEY_HERE"
        )


@dataclass
class SearchConfig:
    """Search engine configuration."""
    engine_type: str = "DuckDuckGoSearch"
    api_key: Optional[str] = None
    secret_id: Optional[str] = None
    secret_key: Optional[str] = None
    topk: int = 6
    timeout: int = 30
    
    @classmethod
    def from_env(cls, engine_type: str = "DuckDuckGoSearch") -> 'SearchConfig':
        """Create search config from environment variables."""
        if engine_type == "DuckDuckGoSearch":
            return cls(
                engine_type="DuckDuckGoSearch",
                api_key=os.getenv("WEB_SEARCH_API_KEY"),  # Optional for DuckDuckGo
                topk=int(os.getenv("SEARCH_TOPK", "6")),
                timeout=int(os.getenv("SEARCH_TIMEOUT", "30")),
            )
        elif engine_type == "TencentSearch":
            return cls(
                engine_type="TencentSearch",
                secret_id=os.getenv("TENCENT_SEARCH_SECRET_ID"),
                secret_key=os.getenv("TENCENT_SEARCH_SECRET_KEY"),
                topk=int(os.getenv("SEARCH_TOPK", "6")),
                timeout=int(os.getenv("SEARCH_TIMEOUT", "30")),
            )
        else:
            raise ValueError(f"Unknown search engine: {engine_type}")
    
    def is_valid(self) -> bool:
        """Check if the search configuration is valid."""
        if self.engine_type == "DuckDuckGoSearch":
            return True  # DuckDuckGo doesn't require credentials
        elif self.engine_type == "TencentSearch":
            return (
                self.secret_id is not None and 
                self.secret_key is not None and
                len(self.secret_id.strip()) > 0 and
                len(self.secret_key.strip()) > 0
            )
        return False


@dataclass
class AgentConfig:
    """Agent configuration."""
    language: str = "en"
    max_turns: int = 10
    use_async: bool = False
    session_timeout: int = 3600  # 1 hour
    memory_limit: int = 100  # Max messages per session
    
    @classmethod
    def from_env(cls) -> 'AgentConfig':
        """Create agent config from environment variables."""
        return cls(
            language=os.getenv("MINDSEARCH_LANGUAGE", "en"),
            max_turns=int(os.getenv("MINDSEARCH_MAX_TURNS", "10")),
            use_async=os.getenv("MINDSEARCH_USE_ASYNC", "false").lower() == "true",
            session_timeout=int(os.getenv("MINDSEARCH_SESSION_TIMEOUT", "3600")),
            memory_limit=int(os.getenv("MINDSEARCH_MEMORY_LIMIT", "100")),
        )
    
    def validate(self) -> bool:
        """Validate agent configuration."""
        return (
            self.language in ["en", "cn"] and
            1 <= self.max_turns <= 20 and
            0 < self.session_timeout <= 86400 and  # Max 24 hours
            0 < self.memory_limit <= 1000
        )


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Optional[str] = None
    max_file_size: int = 10485760  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Create logging config from environment variables."""
        return cls(
            level=os.getenv("MINDSEARCH_LOG_LEVEL", "INFO").upper(),
            format=os.getenv("MINDSEARCH_LOG_FORMAT", cls.format),
            file_path=os.getenv("MINDSEARCH_LOG_FILE"),
            max_file_size=int(os.getenv("MINDSEARCH_LOG_MAX_SIZE", str(cls.max_file_size))),
            backup_count=int(os.getenv("MINDSEARCH_LOG_BACKUP_COUNT", str(cls.backup_count))),
        )


@dataclass
class MindSearchConfig:
    """Complete MindSearch configuration."""
    api: APIConfig = field(default_factory=APIConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    
    @classmethod
    def from_env(cls, 
                 llm_provider: str = "openai",
                 search_engine: str = "DuckDuckGoSearch") -> 'MindSearchConfig':
        """Create complete config from environment variables."""
        return cls(
            api=APIConfig.from_env(),
            llm=LLMConfig.from_env(llm_provider),
            search=SearchConfig.from_env(search_engine),
            agent=AgentConfig.from_env(),
            logging=LoggingConfig.from_env(),
        )
    
    def validate(self) -> Dict[str, List[str]]:
        """
        Validate the complete configuration.
        
        Returns:
            Dictionary with validation errors by component
        """
        errors = {}
        
        # Validate LLM config
        if not self.llm.is_valid():
            errors.setdefault("llm", []).append(
                f"Invalid or missing API key for {self.llm.provider}"
            )
        
        # Validate search config
        if not self.search.is_valid():
            errors.setdefault("search", []).append(
                f"Invalid configuration for {self.search.engine_type}"
            )
        
        # Validate agent config
        if not self.agent.validate():
            errors.setdefault("agent", []).append("Invalid agent configuration")
        
        return errors
    
    def get_environment_status(self) -> Dict[str, Any]:
        """Get status of environment configuration."""
        return {
            "api": {
                "host": self.api.host,
                "port": self.api.port,
                "debug": self.api.debug,
            },
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model_name,
                "has_key": bool(self.llm.api_key),
                "valid": self.llm.is_valid(),
            },
            "search": {
                "engine": self.search.engine_type,
                "valid": self.search.is_valid(),
            },
            "agent": {
                "language": self.agent.language,
                "max_turns": self.agent.max_turns,
                "async": self.agent.use_async,
            },
        }


def load_config(llm_provider: str = "openai", 
                search_engine: str = "DuckDuckGoSearch") -> MindSearchConfig:
    """
    Load and validate MindSearch configuration.
    
    Args:
        llm_provider: LLM provider to use
        search_engine: Search engine to use
        
    Returns:
        Validated MindSearchConfig instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    config = MindSearchConfig.from_env(llm_provider, search_engine)
    
    # Validate configuration
    errors = config.validate()
    if errors:
        error_msg = "Configuration validation failed:\n"
        for component, error_list in errors.items():
            error_msg += f"  {component}: {', '.join(error_list)}\n"
        
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    logger.info("Configuration loaded successfully")
    logger.debug(f"Config status: {config.get_environment_status()}")
    
    return config


def setup_logging(config: LoggingConfig) -> None:
    """
    Setup logging based on configuration.
    
    Args:
        config: Logging configuration
    """
    import logging.handlers
    
    level = getattr(logging, config.level, logging.INFO)
    
    # Create formatter
    formatter = logging.Formatter(config.format)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if config.file_path:
        file_handler = logging.handlers.RotatingFileHandler(
            config.file_path,
            maxBytes=config.max_file_size,
            backupCount=config.backup_count
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    logger.info(f"Logging configured: level={config.level}, file={config.file_path}")


# Default configuration instance
DEFAULT_CONFIG = MindSearchConfig()


def get_default_config() -> MindSearchConfig:
    """Get the default configuration instance."""
    return DEFAULT_CONFIG