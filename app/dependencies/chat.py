from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_session
from app.db.unit_of_work import UnitOfWork, get_unit_of_work
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_thread_repository import ChatThreadRepository
from app.services.chat_service import ChatService


def get_chat_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ChatService:
    """Build ChatService per request.

    The repositories need the request-scoped session, so the service cannot
    live on `app.state`. The compiled stateless agents are safe to reuse for
    the application lifetime.

    `get_session` is cached per request by FastAPI, so the unit of work and
    both repositories share one session and therefore one transaction.
    """
    settings = get_settings()
    return ChatService(
        chat_message_repo=ChatMessageRepository(db),
        chat_thread_repo=ChatThreadRepository(db),
        uow=uow,
        agent=request.app.state.agent,
        title_agent=request.app.state.title_agent,
        agent_semaphore=request.app.state.agent_semaphore,
        timeout_seconds=settings.AGENT_TIMEOUT_SECONDS,
        recursion_limit=settings.AGENT_RECURSION_LIMIT,
        title_timeout_seconds=settings.AGENT_TITLE_TIMEOUT_SECONDS,
    )
