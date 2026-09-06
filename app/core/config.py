from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    SQL_ECHO: bool = False

    OLLAMA_AGENT_MODEL: str = "deepseek-r1:14b"
    OLLAMA_SMALL_AGENT_MODEL: str = "llama3.2:3b"
    OLLAMA_TEMPERATURE: float = Field(default=0.7, ge=0, le=2)
    OLLAMA_TIMEOUT_SECONDS: float = Field(default=30, gt=0)

    OLLAMA_NUM_CTX: int = Field(default=16_384, ge=1_024)
    """How many tokens the model can read at once, prompt and reply together.

    Worth setting explicitly: Ollama's own default is 4096 no matter what the
    model supports, and if the prompt is longer it quietly cuts the beginning
    off — including the system prompt — without any error. That looks like a
    model ignoring its instructions.

    Bigger is not free: Ollama reserves memory for the full size up front.
    """

    AGENT_TIMEOUT_SECONDS: float = Field(default=90, gt=0)
    AGENT_MAX_CONCURRENCY: int = Field(default=2, ge=1, le=64)
    AGENT_MAX_OUTPUT_TOKENS: int = Field(default=4_096, ge=64, le=32_768)
    AGENT_TITLE_TIMEOUT_SECONDS: float = Field(default=15, gt=0)
    AGENT_TITLE_MAX_TOKENS: int = Field(default=24, ge=8, le=256)
    AGENT_RECURSION_LIMIT: int = Field(default=8, ge=2, le=50)
    AGENT_HISTORY_MAX_TOKENS: int = Field(default=4_000, ge=256)
    """Token ceiling for the messages sent to the model, enforced by
    TrimHistoryMiddleware as a safety net."""

    AGENT_HISTORY_MAX_MESSAGES: int = Field(default=20, ge=2)
    """How many recent messages to replay. The main memory dial.

    Raise it and the model remembers more but every request costs more; lower it
    and replies get cheaper but shorter-sighted.
    """

    SUMMARY_ENABLED: bool = True
    """Whether older messages get summarized. Off means they are just forgotten
    once they fall outside AGENT_HISTORY_MAX_MESSAGES."""

    SUMMARY_TRIGGER_MESSAGES: int = Field(default=12, ge=4)
    """Unsummarized messages needed before a summary is written or refreshed.

    Keep it below AGENT_HISTORY_MAX_MESSAGES so messages are summarized while
    they are still being replayed. If it were higher, messages would drop out of
    the replay window before anything summarized them, and they would be lost.
    """

    SUMMARY_KEEP_RECENT_MESSAGES: int = Field(default=6, ge=2)
    """Newest messages never folded into the summary.

    Follow-up questions point at recent messages ("that one", "make it 5"), and
    those references stop making sense once reworded.
    """

    SUMMARY_MAX_TOKENS: int = Field(default=512, ge=64)
    """Length limit for a summary. It is sent with every later request, so an
    unlimited one would eat the space it is meant to save."""

    DATABASE_URL: str

    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, gt=0)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        extra="ignore",
    )

    @model_validator(mode="after")
    def summary_must_run_before_messages_are_forgotten(self) -> "Settings":
        """Catch a settings combination that would silently lose history.

        Summarizing only helps while the messages are still being replayed. If
        the trigger is higher than the replay window, messages scroll out of the
        window before anything summarizes them and they are gone for good.
        """
        if self.SUMMARY_ENABLED and (
            self.SUMMARY_TRIGGER_MESSAGES > self.AGENT_HISTORY_MAX_MESSAGES
        ):
            raise ValueError(
                f"SUMMARY_TRIGGER_MESSAGES ({self.SUMMARY_TRIGGER_MESSAGES}) must "
                f"not exceed AGENT_HISTORY_MAX_MESSAGES "
                f"({self.AGENT_HISTORY_MAX_MESSAGES}), otherwise messages are "
                "forgotten before they are ever summarized."
            )
        if self.SUMMARY_ENABLED and (
            self.SUMMARY_KEEP_RECENT_MESSAGES >= self.SUMMARY_TRIGGER_MESSAGES
        ):
            raise ValueError(
                f"SUMMARY_KEEP_RECENT_MESSAGES ({self.SUMMARY_KEEP_RECENT_MESSAGES}) "
                f"must be below SUMMARY_TRIGGER_MESSAGES "
                f"({self.SUMMARY_TRIGGER_MESSAGES}), otherwise there is never "
                "anything left to summarize."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
