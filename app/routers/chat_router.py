from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.models.user import User
from app.services.chat_service import ChatService
from app.dependencies.auth import auth_dependency

router = APIRouter(
    prefix="/chat",
    tags=["Chat"],
)


@router.post("/")
async def chat(
    request: Request,
    message: str,
    current_user: Annotated[
        User,
        Depends(auth_dependency),
    ],
):
    try:
        agent = request.app.state.agent
        service = ChatService(agent)
        answer = await service.chat(message)
        return {
            "message": message,
            "answer": answer,
            "user": current_user
        }
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Agent generation failed",
        ) from exc
