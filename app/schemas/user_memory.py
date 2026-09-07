from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_EXTRACTED_MEMORIES = 12

MemoryKey = Literal[
    "preferred_response_style",
    "preferred_explanation_level",
    "preferred_programming_language",
    "preferred_framework",
    "preferred_library",
    "preferred_tool",
    "preferred_operating_system",
    "preferred_code_style",
    "current_technical_goal",
    "current_technical_project",
    "recurring_technical_constraint",
]
CanonicalMemoryValue = Literal[
    "concise",
    "brief",
    "detailed",
    "step_by_step",
    "example_driven",
    "direct",
    "beginner",
    "intermediate",
    "advanced",
    "python",
    "javascript",
    "typescript",
    "java",
    "kotlin",
    "swift",
    "rust",
    "cpp",
    "csharp",
    "ruby",
    "php",
    "fastapi",
    "django",
    "flask",
    "react",
    "vue",
    "angular",
    "nextjs",
    "spring",
    "express",
    "nestjs",
    "langchain",
    "langgraph",
    "sqlalchemy",
    "pydantic",
    "numpy",
    "pandas",
    "docker",
    "kubernetes",
    "git",
    "ollama",
    "kiro",
    "vscode",
    "bun",
    "uv",
    "macos",
    "linux",
    "windows",
    "typed",
    "functional",
    "object_oriented",
    "asynchronous",
    "documented",
    "test_driven",
    "apis",
    "backend",
    "frontend",
    "databases",
    "postgresql",
    "mysql",
    "sqlite",
    "sql",
    "language_models",
    "machine_learning",
    "generative_ai",
    "chatbots",
    "cloud",
    "testing",
]
EpisodeKind = Literal["decision", "started", "completed", "deployed", "milestone"]


class ExtractedMemory(BaseModel):
    """One bounded memory candidate produced from a completed chat turn."""

    memory_type: Literal["fact", "episode"]
    memory_key: MemoryKey | None = Field(
        description="Canonical fact key; null for episodes",
    )
    canonical_values: list[CanonicalMemoryValue] = Field(
        min_length=1,
        max_length=8,
        description="Only explicitly affirmed values from the allowed vocabulary",
    )
    content: str = Field(
        default="",
        exclude=True,
        description=(
            "Internal canonical sentence; extractor-provided values are ignored and "
            "the application always overwrites it before persistence"
        ),
    )
    episode_kind: EpisodeKind | None = Field(
        default=None,
        description="Technical event kind; null for facts",
    )
    confidence: float = Field(default=0.8, ge=0, le=1)
    importance: float = Field(default=0.5, ge=0, le=1)
    is_correction: bool = Field(
        default=False,
        description=(
            "True only when the user explicitly corrects or replaces an older "
            "value for the same fact"
        ),
    )

    @model_validator(mode="after")
    def fields_match_memory_type(self) -> "ExtractedMemory":
        if self.memory_type == "fact":
            if self.memory_key is None:
                raise ValueError("facts require a memory_key")
            self.episode_kind = None
        else:
            self.memory_key = None
            self.is_correction = False
            if self.episode_kind is None:
                self.episode_kind = "milestone"
        return self


class MemoryExtraction(BaseModel):
    """Structured result returned by the post-turn memory extractor."""

    memories: list[ExtractedMemory] = Field(
        max_length=MAX_EXTRACTED_MEMORIES,
        description="Durable memories from this turn; empty when nothing qualifies",
    )


class MemoryItemResponse(BaseModel):
    """User-visible memory fields; embeddings and provenance stay private."""

    id: UUID
    memory_key: MemoryKey | None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserMemoriesResponse(BaseModel):
    """All active long-term memories grouped by their user-facing meaning."""

    facts: list[MemoryItemResponse]
    episodes: list[MemoryItemResponse]
