from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.db.errors import PersistenceError
from app.dependencies.auth import auth_dependency
from app.dependencies.memory import get_user_memory_control_service
from app.models.user import User
from app.schemas.user_memory import UserMemoriesResponse
from app.services.user_memory_control_service import (
    MemoryChangedError,
    MemoryNotFoundError,
    UserMemoryControlService,
)

router = APIRouter(prefix="/memories", tags=["Memories"])


@router.get("", response_model=UserMemoriesResponse)
async def list_memories(
    response: Response,
    current_user: Annotated[User, Depends(auth_dependency)],
    service: Annotated[
        UserMemoryControlService,
        Depends(get_user_memory_control_service),
    ],
) -> UserMemoriesResponse:
    """Show all active long-term memories owned by the authenticated user."""
    response.headers["Cache-Control"] = "no-store"
    try:
        return await service.list_active(user_id=current_user.id)
    except PersistenceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Memories could not be loaded. Try again.",
        ) from exc


@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def forget_memory(
    memory_id: UUID,
    updated_at: datetime,
    current_user: Annotated[User, Depends(auth_dependency)],
    service: Annotated[
        UserMemoryControlService,
        Depends(get_user_memory_control_service),
    ],
) -> Response:
    """Forget one memory without revealing whether another user owns its ID."""
    try:
        await service.forget(
            memory_id=str(memory_id),
            user_id=current_user.id,
            expected_updated_at=updated_at,
        )
    except MemoryChangedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Memory changed. Refresh and try again.",
        ) from exc
    except MemoryNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Memory not found",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
