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

settings = AppSettings()