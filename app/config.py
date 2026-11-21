"""QUANT-X Engine Configuration."""
from functools import lru_cache
from pathlib import Path
from typing import Optional, Union, List, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "quantx"
    POSTGRES_USER: str = "quantx_user"
    POSTGRES_PASSWORD: str = "change_me_in_production"

    # SQLite mode — default ON for HF Spaces (no PostgreSQL)
    USE_SQLITE: bool = True
    SQLITE_PATH: str = "/app/data/quantx.db"

    # Engine — Render injects $PORT dynamically; default 10000
    ENGINE_HOST: str = "0.0.0.0"
    ENGINE_PORT: int = 10000
    ENGINE_WORKERS: int = 1

    # Storage — Render container paths
    PARQUET_DATA_DIR: str = "/app/datasets"
    REPORTS_DIR: str = "/app/reports"
    LOG_DIR: str = "/app/logs"

    # API
    API_VERSION: str = "v1"
    CORS_ORIGINS: Union[str, list[str]] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"

    @property
    def DATABASE_URL(self) -> str:
        if self.USE_SQLITE:
            return f"sqlite+aiosqlite:///{self.SQLITE_PATH}"
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @field_validator("CORS_ORIGINS")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return ["*"]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
