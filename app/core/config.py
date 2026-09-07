from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]

# Longest message the chat API accepts. Shared with the request schema so the
# token arithmetic below is checked against what clients can actually send.
MAX_MESSAGE_CHARS = 20_000

# Rough characters-per-token, only used for the startup sanity check.
APPROX_CHARS_PER_TOKEN = 4


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

    AGENT_HISTORY_MAX_TOKENS: int = Field(default=10_000, ge=1_024)
    """Token budget for everything we send the model: summary, replayed
    messages, and the new message together. The main memory dial.

    Measured in tokens rather than messages because message counts say nothing
    about size — twenty one-line messages and twenty pasted documents are wildly
    different prompts.

    Must leave room for the reply inside OLLAMA_NUM_CTX; checked at startup.
    """

    AGENT_HISTORY_MAX_MESSAGES: int = Field(default=40, ge=2)
    """Row cap on the history query, on top of the token budget.

    Stops the query loading thousands of rows just to throw most away. The token
    budget is what actually decides what the model sees.
    """

    SUMMARY_ENABLED: bool = True
    """Whether older messages get summarized. Off means they are simply
    forgotten once they no longer fit AGENT_HISTORY_MAX_TOKENS."""

    SUMMARY_TRIGGER_TOKENS: int = Field(default=4_000, ge=256)
    """Unsummarized tokens needed before a summary is written or refreshed.

    Must stay below AGENT_HISTORY_MAX_TOKENS minus SUMMARY_MAX_TOKENS, so
    messages get summarized while they still fit in the prompt. If it were
    higher, messages would be dropped for space before anything summarized them
    and that history would be lost for good. Checked at startup.
    """

    SUMMARY_KEEP_RECENT_TOKENS: int = Field(default=1_500, ge=128)
    """Newest tokens never folded into the summary.

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
    def token_budgets_must_add_up(self) -> "Settings":
        """Check the token arithmetic, because getting it wrong is silent.

        Every one of these mistakes produces no error at runtime — just a model
        that forgets things or ignores its instructions. Better to refuse to
        start than to debug that later.
        """
        # 1. The prompt and the reply share one context window.
        needed = self.AGENT_HISTORY_MAX_TOKENS + self.AGENT_MAX_OUTPUT_TOKENS
        if needed > self.OLLAMA_NUM_CTX:
            raise ValueError(
                f"AGENT_HISTORY_MAX_TOKENS ({self.AGENT_HISTORY_MAX_TOKENS}) plus "
                f"AGENT_MAX_OUTPUT_TOKENS ({self.AGENT_MAX_OUTPUT_TOKENS}) is "
                f"{needed}, which does not fit OLLAMA_NUM_CTX "
                f"({self.OLLAMA_NUM_CTX}). Ollama would silently cut the start "
                "off the prompt. Raise the window or lower one of the budgets."
            )

        # 2. A single request must be able to fit the prompt on its own,
        #    otherwise long messages fail instead of being answered.
        max_message_tokens = MAX_MESSAGE_CHARS // APPROX_CHARS_PER_TOKEN
        if max_message_tokens > self.AGENT_HISTORY_MAX_TOKENS:
            raise ValueError(
                f"A maximum-length message is about {max_message_tokens} tokens, "
                f"more than AGENT_HISTORY_MAX_TOKENS "
                f"({self.AGENT_HISTORY_MAX_TOKENS}). Such a message could never "
                "be answered. Raise the budget or lower MAX_MESSAGE_CHARS."
            )

        if not self.SUMMARY_ENABLED:
            return self

        # 3. Summarizing only preserves messages while they still fit the
        #    prompt. Trigger too late and they are dropped for space first, and
        #    nothing can recover them.
        room = self.AGENT_HISTORY_MAX_TOKENS - self.SUMMARY_MAX_TOKENS
        if self.SUMMARY_TRIGGER_TOKENS >= room:
            raise ValueError(
                f"SUMMARY_TRIGGER_TOKENS ({self.SUMMARY_TRIGGER_TOKENS}) must stay "
                f"below AGENT_HISTORY_MAX_TOKENS minus SUMMARY_MAX_TOKENS "
                f"({room}), otherwise messages are dropped for space before "
                "anything summarizes them and that history is lost."
            )

        # 4. Something has to be left over to summarize.
        if self.SUMMARY_KEEP_RECENT_TOKENS >= self.SUMMARY_TRIGGER_TOKENS:
            raise ValueError(
                f"SUMMARY_KEEP_RECENT_TOKENS ({self.SUMMARY_KEEP_RECENT_TOKENS}) "
                f"must be below SUMMARY_TRIGGER_TOKENS "
                f"({self.SUMMARY_TRIGGER_TOKENS}), otherwise there is never "
                "anything old enough to summarize."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
