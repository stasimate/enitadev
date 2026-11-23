"""Application settings, read from environment / .env (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent

Provider = Literal["openai", "google", "anthropic", "ollama"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(BACKEND_DIR.parent / ".env", BACKEND_DIR / ".env"),
        env_prefix="ENITA_",
        extra="ignore",
    )

    provider: Provider = "openai"
    model: str = "gpt-4o-mini"
    llm_timeout_s: float = 20.0
    db_path: Path = BACKEND_DIR / "data" / "enita.db"
    content_dir: Path = BACKEND_DIR.parent / "content" / "en" / "topics"
    # The Angular build. When the directory exists, FastAPI serves it at "/".
    static_dir: Path = BACKEND_DIR.parent / "frontend" / "dist" / "enita" / "browser"


@lru_cache
def get_settings() -> Settings:
    return Settings()
