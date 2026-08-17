from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.dependencies.auth import auth_dependency
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.chat_service import AgentExecutionError


router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    request: Request,
    current_user: Annotated[User, Depends(auth_dependency)],
) -> ChatResponse:
    try:
        answer = await request.app.state.chat_service.chat(
            message=data.message,
            user_id=current_user.id,
        )
    except AgentExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent generation failed",
        ) from exc

    return ChatResponse(message=data.message, answer=answer)
