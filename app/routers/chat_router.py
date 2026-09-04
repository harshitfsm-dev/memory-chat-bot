from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import auth_dependency
from app.dependencies.chat import get_chat_service
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import (
    AgentExecutionError,
    AgentTimeoutError,
    ChatService,
    ThreadNotFoundError,
)


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: Annotated[User, Depends(auth_dependency)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    try:
        result = await service.chat(
            message=data.message,
            user_id=current_user.id,
            # IDs are stored as String(36), so normalize the validated UUID.
            thread_id=str(data.thread_id) if data.thread_id else None,
        )
    except ThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        ) from exc
    except AgentTimeoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Agent generation timed out",
        ) from exc
    except AgentExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent generation failed",
        ) from exc

    return ChatResponse(
        message=data.message,
        answer=result.answer,
        thread_id=result.thread_id,
        thread_title=result.thread_title,
    )
