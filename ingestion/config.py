"""Configuration. Single source of truth, loaded from the environment / .env."""
from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = Field(..., alias="DATABASE_URL")

    # OpenAI
    openai_api_key: str = Field(..., alias="OPENAI_API_KEY")
    embedding_model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    summary_model: str = Field("gpt-4o-mini", alias="SUMMARY_MODEL")

    # Data layout
    data_dir: Path = Field(Path("./data"), alias="DATA_DIR")
    # NoDecode: pydantic-settings would otherwise JSON-decode this list field from
    # the env var before validators run, so "lisbon,barcelona" fails. NoDecode hands
    # the raw string to _split_cities below instead.
    cities: Annotated[list[str], NoDecode] = Field(default_factory=list, alias="CITIES")

    # Load tuning — calendar window in days (forward from today, inclusive).
    # 7 days × ~43K listings ≈ 300K rows; enough for availability demos.
    calendar_days: int = Field(7, alias="CALENDAR_DAYS")
    max_reviews_per_listing: int = Field(40, alias="MAX_REVIEWS_PER_LISTING")
    detect_language: bool = Field(True, alias="DETECT_LANGUAGE")

    # Enrichment tuning
    embed_batch_size: int = Field(256, alias="EMBED_BATCH_SIZE")
    summary_min_reviews: int = Field(3, alias="SUMMARY_MIN_REVIEWS")
    summary_reviews_per_prompt: int = Field(20, alias="SUMMARY_REVIEWS_PER_PROMPT")
    summary_concurrency: int = Field(8, alias="SUMMARY_CONCURRENCY")
    # Cost guardrail: cap how many listings get an LLM review summary in one run.
    # 0 = no cap (summarize every eligible listing). When set, the most-reviewed
    # listings are prioritized, so a bounded demo run still covers what surfaces.
    summary_max_listings: int = Field(0, alias="SUMMARY_MAX_LISTINGS")

    @field_validator("cities", mode="before")
    @classmethod
    def _split_cities(cls, v: object) -> object:
        if isinstance(v, str):
            return [c.strip().lower() for c in v.split(",") if c.strip()]
        return v

    def city_file(self, city: str, name: str) -> Path:
        """Path to a city's CSV, e.g. city_file('lisbon', 'listings').

        Accepts either the gzipped Inside Airbnb download (name.csv.gz) or an
        already-decompressed name.csv. When both exist, plain .csv wins — trim/fill
        scripts write processed data there. Falls back to .csv.gz for fresh downloads.
        """
        base = self.data_dir / city
        gz, plain = base / f"{name}.csv.gz", base / f"{name}.csv"
        if plain.exists():
            return plain
        if gz.exists():
            return gz
        return gz
