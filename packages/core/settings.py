"""Application configuration, loaded from environment (.env in local dev)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: str = "local"

    database_url: str = "postgresql+asyncpg://tanba:tanba@localhost:5432/tanba"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "dev-secret-change-me"
    jwt_access_ttl: int = 900
    jwt_refresh_ttl: int = 1_209_600

    route_cache_ttl: int = 300
    public_base_url: str = "http://localhost:8001"

    event_stream: str = "tanba:events"
    geoip_db_path: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached singleton so config is parsed once per process."""
    return Settings()
