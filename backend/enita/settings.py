"""Application settings, read from environment / .env (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
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
    model: str = "gpt-4.1-mini"
    # Optional model routing (RF-31). Empty: the agent uses `model`.
    writer_model: str | None = None
    verifier_model: str | None = None
    # Timeouts (RNF-06). The generation is the critical AI tool: writer + verifier + retries.
    generation_timeout_s: float = 45.0
    mcp_timeout_s: int = 10
    # The writer makes a new draft when the verifier rejects one. This is the maximum attempts.
    max_writer_attempts: int = 3

    # Provider keys use the standard names, without the ENITA_ prefix.
    openai_api_key: SecretStr | None = Field(None, validation_alias="OPENAI_API_KEY")
    google_api_key: SecretStr | None = Field(None, validation_alias="GOOGLE_API_KEY")
    anthropic_api_key: SecretStr | None = Field(None, validation_alias="ANTHROPIC_API_KEY")
    ollama_base_url: str = Field("http://localhost:11434/v1", validation_alias="OLLAMA_BASE_URL")
    db_path: Path = BACKEND_DIR / "data" / "enita.db"
    content_dir: Path = BACKEND_DIR.parent / "content" / "en" / "topics"
    # The Angular build. When the directory exists, FastAPI serves it at "/".
    static_dir: Path = BACKEND_DIR.parent / "frontend" / "dist" / "enita" / "browser"


@lru_cache
def get_settings() -> Settings:
    return Settings()
