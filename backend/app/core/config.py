from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "Shlokantara API"
    api_v1_prefix: str = "/api/v1"
    frontend_origin: str = "http://localhost:5173"
    database_url: str | None = None
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.8-flash"

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
