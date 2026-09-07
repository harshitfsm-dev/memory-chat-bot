import json
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.db.errors import PersistenceError
from app.dependencies.auth import auth_dependency
from app.dependencies.chat import get_chat_service
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, MessageResponse, ThreadResponse
from app.services.chat_service import (
    AgentExecutionError,
    AgentTimeoutError,
    ChatService,
    MessageTooLongError,
    StreamChunk,
    ThreadNotFoundError,
)


router = APIRouter(prefix="/chat", tags=["Chat"])


def _sse(chunk: StreamChunk) -> str:
    """Serialize a stream chunk as one Server-Sent Events frame.

    The event name lets the client branch (meta/delta/done/error) without
    inspecting the payload; the data line is JSON.
    """
    payload: dict[str, str] = {}
    if chunk.text:
        payload["text"] = chunk.text
    if chunk.thread_id is not None:
        payload["thread_id"] = chunk.thread_id
    if chunk.thread_title is not None:
        payload["thread_title"] = chunk.thread_title
    return f"event: {chunk.type}\ndata: {json.dumps(payload)}\n\n"


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
    except MessageTooLongError as exc:
        # The message cannot fit the model's budget even on its own. Say so,
        # rather than sending an unusable prompt and failing on the far side.
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Message is too long for the model. Please shorten it.",
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


@router.post("/stream")
async def chat_stream(
    data: ChatRequest,
    current_user: Annotated[User, Depends(auth_dependency)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> StreamingResponse:
    """Stream a chat response as Server-Sent Events.

    Emits `meta` (thread info), then `delta` frames per token, then a terminal
    `done` frame with the full answer. Failures before the first token become
    HTTP errors; failures once streaming has begun arrive as an `error` frame,
    since the response status is already sent by then.
    """
    generator = service.stream_chat(
        message=data.message,
        user_id=current_user.id,
        thread_id=str(data.thread_id) if data.thread_id else None,
    )

    # Advance to the first chunk here so thread resolution and the user-turn
    # commit run before the response starts. This lets a bad thread or a failed
    # write surface as a normal HTTP error instead of a broken stream.
    try:
        first = await anext(generator)
    except ThreadNotFoundError as exc:
        await generator.aclose()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        ) from exc
    except MessageTooLongError as exc:
        await generator.aclose()
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Message is too long for the model. Please shorten it.",
        ) from exc
    except PersistenceError as exc:
        await generator.aclose()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The request could not be stored. Please retry.",
        ) from exc

    async def event_stream() -> AsyncIterator[str]:
        yield _sse(first)
        async for chunk in generator:
            yield _sse(chunk)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/threads", response_model=list[ThreadResponse])
async def list_threads(
    current_user: Annotated[User, Depends(auth_dependency)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[ThreadResponse]:
    return await service.get_user_threads(user_id=current_user.id)


@router.get("/messages", response_model=list[MessageResponse])
async def list_messages(
    thread_id: str,
    current_user: Annotated[User, Depends(auth_dependency)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[MessageResponse]:
    try:
        return await service.get_thread_messages(
            thread_id=thread_id,
            user_id=current_user.id,
        )
    except ThreadNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thread not found",
        ) from exc
