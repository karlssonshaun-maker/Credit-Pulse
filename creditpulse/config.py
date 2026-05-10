from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = Field(default="development", alias="ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+asyncpg://creditpulse:creditpulse_dev_only@localhost:5432/creditpulse",
        alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        default="postgresql+psycopg2://creditpulse:creditpulse_dev_only@localhost:5432/creditpulse",
        alias="SYNC_DATABASE_URL",
    )

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_secret_key: str = Field(default="dev_secret_change_me", alias="API_SECRET_KEY")

    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        alias="CORS_ORIGINS",
    )

    enrichment_timeout_seconds: float = Field(default=5.0, alias="ENRICHMENT_TIMEOUT_SECONDS")
    cipc_cache_ttl_seconds: int = Field(default=86400, alias="CIPC_CACHE_TTL_SECONDS")
    sars_cache_ttl_seconds: int = Field(default=604800, alias="SARS_CACHE_TTL_SECONDS")
    bureau_cache_ttl_seconds: int = Field(default=3600, alias="BUREAU_CACHE_TTL_SECONDS")

    rate_limit_per_minute: int = Field(default=120, alias="RATE_LIMIT_PER_MINUTE")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
