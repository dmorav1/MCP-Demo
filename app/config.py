from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Database
    database_url: Optional[str] = None

    # OpenAI / embeddings
    openai_api_key: Optional[str] = None
    embedding_model: Optional[str] = "text-embedding-3-small"
    embedding_dimension: Optional[int] = 1536

settings = AppSettings()