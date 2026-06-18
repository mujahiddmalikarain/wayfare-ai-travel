"""API configuration, loaded from the environment / .env."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")

    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    embedding_model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    intent_model: str = Field("gpt-4o-mini", alias="INTENT_MODEL")
    synthesis_model: str = Field("gpt-4o-mini", alias="SYNTHESIS_MODEL")

    # Behaviour
    pool_min_size: int = Field(2, alias="POOL_MIN_SIZE")
    pool_max_size: int = Field(10, alias="POOL_MAX_SIZE")
    cache_ttl_seconds: int = Field(3600, alias="CACHE_TTL_SECONDS")
    retrieval_limit: int = Field(24, alias="RETRIEVAL_LIMIT")
    tax_rate: float = Field(0.10, alias="TAX_RATE")  # mocked taxes/fees
    cleaning_fee: float = Field(45.0, alias="CLEANING_FEE")


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()  # type: ignore[call-arg]
    return _settings
