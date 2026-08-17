from pydantic import BaseModel
from uuid import UUID


class ChatRequest(BaseModel):
    user_id: UUID
    session_id: UUID
    message: str