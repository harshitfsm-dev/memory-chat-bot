from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.database import get_session
from app.db.unit_of_work import UnitOfWork, get_unit_of_work
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_thread_repository import ChatThreadRepository
from app.repositories.user_memory_repository import UserMemoryRepository
from app.services.chat_service import ChatService
from app.services.summary_service import SummaryService
from app.services.user_memory_service import UserMemoryService


def get_chat_service(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_session)],
    uow: Annotated[UnitOfWork, Depends(get_unit_of_work)],
) -> ChatService:
    """Build ChatService per request.

    The repositories need the request-scoped session, so the service cannot
    live on `app.state`. The compiled stateless agents and model clients are
    safe to reuse for the application lifetime.

    `get_session` is cached per request by FastAPI, so the unit of work and all
    repositories share one session and therefore one transaction. Post-turn
    memory and summary processing must remain sequential.
    """
    settings = get_settings()
    chat_message_repo = ChatMessageRepository(db)
    chat_thread_repo = ChatThreadRepository(db)

    summary_service = SummaryService(
        chat_message_repo=chat_message_repo,
        chat_thread_repo=chat_thread_repo,
        uow=uow,
        summary_agent=request.app.state.summary_agent,
        agent_semaphore=request.app.state.agent_semaphore,
        enabled=settings.SUMMARY_ENABLED,
        trigger_tokens=settings.SUMMARY_TRIGGER_TOKENS,
        keep_recent_tokens=settings.SUMMARY_KEEP_RECENT_TOKENS,
        max_messages_per_run=settings.AGENT_HISTORY_MAX_MESSAGES,
        timeout_seconds=settings.AGENT_TIMEOUT_SECONDS,
    )
    memory_service = UserMemoryService(
        repository=UserMemoryRepository(db),
        uow=uow,
        extractor=request.app.state.memory_extractor,
        embeddings=request.app.state.memory_embeddings,
        agent_semaphore=request.app.state.agent_semaphore,
        memory_semaphore=request.app.state.memory_semaphore,
        enabled=settings.MEMORY_ENABLED,
        retrieval_enabled=settings.MEMORY_RETRIEVAL_ENABLED,
        embedding_model=settings.OLLAMA_EMBEDDING_MODEL,
        max_items_per_turn=settings.MEMORY_MAX_ITEMS_PER_TURN,
        retrieval_min_similarity=settings.MEMORY_RETRIEVAL_MIN_SIMILARITY,
        retrieval_max_notes=settings.MEMORY_RETRIEVAL_MAX_NOTES,
        timeout_seconds=settings.MEMORY_TIMEOUT_SECONDS,
    )

    return ChatService(
        chat_message_repo=chat_message_repo,
        chat_thread_repo=chat_thread_repo,
        uow=uow,
        agent=request.app.state.agent,
        title_agent=request.app.state.title_agent,
        agent_semaphore=request.app.state.agent_semaphore,
        summary_service=summary_service,
        memory_service=memory_service,
        timeout_seconds=settings.AGENT_TIMEOUT_SECONDS,
        recursion_limit=settings.AGENT_RECURSION_LIMIT,
        title_timeout_seconds=settings.AGENT_TITLE_TIMEOUT_SECONDS,
        history_max_messages=settings.AGENT_HISTORY_MAX_MESSAGES,
        history_max_tokens=settings.AGENT_HISTORY_MAX_TOKENS,
        memory_max_tokens=settings.MEMORY_RETRIEVAL_MAX_TOKENS,
    )
