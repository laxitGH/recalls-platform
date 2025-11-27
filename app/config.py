from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    port: int = 8000
    host: str = "0.0.0.0"

    gemini_api_key: Optional[str] = None  # env: GEMINI_API_KEY
    gemini_model: str = "models/gemini-2.0-flash"  # env: GEMINI_MODEL


def get_settings() -> Settings:
    return Settings()
