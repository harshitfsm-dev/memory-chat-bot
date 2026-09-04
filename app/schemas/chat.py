import uuid
from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(max_length=20_000)
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
