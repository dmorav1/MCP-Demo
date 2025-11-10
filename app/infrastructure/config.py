"""
Infrastructure configuration - Centralized configuration management.

This module handles configuration from environment variables and provides
type-safe access to application settings.
"""
from typing import Optional, Literal
from pydantic import BaseModel, Field
try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    # Fallback for older pydantic versions
    from pydantic import BaseSettings
    SettingsConfigDict = None


class DatabaseConfig(BaseModel):
    """Database configuration settings."""
    url: str = Field(..., description="Database connection URL")
    echo: bool = Field(default=False, description="Enable SQL query logging")
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max pool overflow")


class EmbeddingConfig(BaseModel):
    """Embedding service configuration."""
    provider: Literal["local", "openai", "fastembed"] = Field(default="local")
    model: str = Field(default="all-MiniLM-L6-v2")
    dimension: int = Field(default=1536)
    batch_size: int = Field(default=32, description="Batch size for embedding generation")
    api_key: Optional[str] = Field(default=None, description="API key for external providers")


class SlackConfig(BaseModel):
    """Slack integration configuration."""
    bot_token: Optional[str] = Field(default=None)
    channel: Optional[str] = Field(default=None)
    enabled: bool = Field(default=False, description="Enable Slack integration")


class SearchConfig(BaseModel):
    """Search configuration settings."""
    default_top_k: int = Field(default=10, description="Default number of search results")
    max_top_k: int = Field(default=50, description="Maximum allowed search results")
    relevance_threshold: float = Field(default=0.7, description="Default relevance threshold")
    enable_caching: bool = Field(default=False, description="Enable search result caching")


class ChunkingConfig(BaseModel):
    """Conversation chunking configuration."""
    max_chunk_size: int = Field(default=1000, description="Maximum chunk size in characters")
    split_on_speaker_change: bool = Field(default=True, description="Split chunks on speaker change")
    preserve_message_boundaries: bool = Field(default=True, description="Preserve message boundaries")
    min_chunk_word_count: int = Field(default=3, description="Minimum words per chunk")


class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    enable_file_logging: bool = Field(default=False)
    log_file_path: Optional[str] = Field(default=None)


class RAGConfig(BaseModel):
    """RAG (Retrieval-Augmented Generation) configuration."""
    # Provider selection
    provider: Literal["openai", "anthropic", "local"] = Field(default="openai")
    model: str = Field(default="gpt-3.5-turbo", description="Model name for the selected provider")
    
    # API keys
    openai_api_key: Optional[str] = Field(default=None)
    anthropic_api_key: Optional[str] = Field(default=None)
    
    # Generation parameters
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2000, gt=0, le=8000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    
    # Retrieval configuration
    top_k: int = Field(default=5, gt=0, le=50, description="Number of chunks to retrieve")
    score_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    
    # Chain configuration
    chain_type: Literal["stuff", "map_reduce", "refine", "map_rerank"] = Field(default="stuff")
    enable_streaming: bool = Field(default=True)
    enable_conversation_memory: bool = Field(default=True)
    
    # Context management
    max_context_tokens: int = Field(default=3500, gt=0)
    max_history_messages: int = Field(default=10, ge=0)
    
    # Performance and caching
    enable_cache: bool = Field(default=True)
    cache_ttl_seconds: int = Field(default=3600, gt=0)
    
    # Error handling
    max_retries: int = Field(default=3, ge=0)
    timeout_seconds: int = Field(default=60, gt=0)
    
    # Observability
    enable_token_tracking: bool = Field(default=True)
    enable_latency_tracking: bool = Field(default=True)


class AppSettings(BaseSettings):
    """
    Main application settings.
    
    Loads configuration from environment variables with validation.
    """
    if SettingsConfigDict:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
            env_nested_delimiter="__"
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "ignore"
    
    # Core settings
    environment: Literal["development", "testing", "production"] = Field(default="development")
    debug: bool = Field(default=False)
    
    # Component configurations
    database: DatabaseConfig = Field(default_factory=lambda: DatabaseConfig(url="sqlite:///./test.db"))
    embedding: EmbeddingConfig = Field(default_factory=EmbeddingConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)
    search: SearchConfig = Field(default_factory=SearchConfig)
    chunking: ChunkingConfig = Field(default_factory=ChunkingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    rag: RAGConfig = Field(default_factory=RAGConfig)
    
    # Legacy compatibility fields (for backward compatibility with existing code)
    database_url: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    embedding_provider: str = Field(default="local")
    embedding_model: str = Field(default="all-MiniLM-L6-v2")
    embedding_dimension: int = Field(default=1536)
    slack_bot_token: Optional[str] = Field(default=None)
    slack_channel: Optional[str] = Field(default=None)
    
    def model_post_init(self, __context) -> None:
        """Post-initialization to handle legacy compatibility."""
        # Update component configs from legacy fields if provided
        if self.database_url:
            self.database.url = self.database_url
        
        if self.openai_api_key:
            self.embedding.api_key = self.openai_api_key
        
        self.embedding.provider = self.embedding_provider
        self.embedding.model = self.embedding_model
        self.embedding.dimension = self.embedding_dimension
        
        if self.slack_bot_token:
            self.slack.bot_token = self.slack_bot_token
            self.slack.enabled = True
        
        if self.slack_channel:
            self.slack.channel = self.slack_channel
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.environment == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.environment == "testing"


# Global settings instance
settings = AppSettings()


def get_settings() -> AppSettings:
    """Get the global application settings."""
    return settings


def get_database_config() -> DatabaseConfig:
    """Get database configuration."""
    return settings.database


def get_embedding_config() -> EmbeddingConfig:
    """Get embedding configuration."""
    return settings.embedding


def get_slack_config() -> SlackConfig:
    """Get Slack configuration."""
    return settings.slack


def get_search_config() -> SearchConfig:
    """Get search configuration."""
    return settings.search


def get_chunking_config() -> ChunkingConfig:
    """Get chunking configuration."""
    return settings.chunking


def get_logging_config() -> LoggingConfig:
    """Get logging configuration."""
    return settings.logging


def get_rag_config() -> RAGConfig:
    """Get RAG configuration."""
    return settings.rag