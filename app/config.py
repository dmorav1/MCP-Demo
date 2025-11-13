from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    database_url: Optional[str] = None

    # Embeddings
    openai_api_key: Optional[str] = None
    embedding_provider: str = "local"
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dimension: int = 1536  # add

    # Slack (optional)
    slack_bot_token: Optional[str] = None
    slack_channel: Optional[str] = None

    # Cache settings
    cache_enabled: bool = True
    cache_backend: str = "memory"  # "memory" or "redis"
    cache_redis_url: str = "redis://localhost:6379"
    cache_default_ttl: int = 3600  # 1 hour in seconds
    cache_max_size: int = 1000  # For in-memory cache
    
    # Cache TTL settings (in seconds)
    embedding_cache_ttl: int = 86400  # 24 hours
    search_cache_ttl: int = 1800  # 30 minutes
    llm_cache_ttl: int = 3600  # 1 hour

settings = AppSettings()