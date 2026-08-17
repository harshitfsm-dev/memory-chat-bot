from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    SQL_ECHO: bool = False

    OLLAMA_AGENT_MODEL: str = "qwen3.5:2b-mlx"
    OLLAMA_TEMPERATURE: float = Field(default=0.7, ge=0, le=2)
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=30, gt=0)

    LANGGRAPH_CHECKPOINT_PATH: Path = BASE_DIR / "langgraph_checkpoints.db"
    AGENT_TIMEOUT_SECONDS: float = Field(default=90, gt=0)
    AGENT_RECURSION_LIMIT: int = Field(default=8, ge=2, le=50)
    AGENT_HISTORY_MAX_TOKENS: int = Field(default=4_000, ge=256)

    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
