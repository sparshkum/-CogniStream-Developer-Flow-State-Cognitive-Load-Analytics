"""Backend settings, loaded from environment variables (see docker-compose.yml
and .env.example). Kept independent from the data-engineering package so the
API can be deployed as its own lightweight container per the Week 4 plan
("build a lightweight backend to serve aggregated ClickHouse schema").
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    clickhouse_host: str = "localhost"
    clickhouse_port: int = 8123
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_secure: bool = False

    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()
