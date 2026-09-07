from datetime import datetime
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import MAX_MESSAGE_CHARS


class ChatRequest(BaseModel):
    # Shared with config so startup can check that a message this long can
    # actually fit the model's context budget.
    message: str = Field(max_length=MAX_MESSAGE_CHARS)
    thread_id: uuid.UUID | None = None

    @field_validator("thread_id", mode="before")
    @classmethod
    def empty_thread_id_means_new(cls, value: object) -> object:
        # Clients (Swagger UI included) often send "" for an unset optional
        # field. Treat blank as "start a new thread" instead of a 422.
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value


class ChatResponse(BaseModel):
    message: str
    answer: str
    thread_id: uuid.UUID
    thread_title: str


class ThreadResponse(BaseModel):
    id: uuid.UUID
    title: str | None
    summary: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
