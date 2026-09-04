import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents import build_agent, build_title_agent
from app.core.config import get_settings
from app.core.security import JWTService, PasswordService
from app.db.database import create_database
from app.llm.ollama import create_ollama_model

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    )

    engine, session_factory = create_database(
        settings.DATABASE_URL,
        echo=settings.SQL_ECHO,
    )
    app.state.session_factory = session_factory
    app.state.password_service = PasswordService()
    app.state.jwt_service = JWTService(
        secret_key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
        expire_minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    model = create_ollama_model(
        model=settings.OLLAMA_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        num_predict=settings.AGENT_MAX_OUTPUT_TOKENS,
    )
    small_model = create_ollama_model(
        model=settings.OLLAMA_SMALL_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        reasoning=False,
        num_predict=settings.AGENT_TITLE_MAX_TOKENS,
    )

    # Ollama model execution is the constrained resource. Both agents share
    # this limit so title generation cannot overwhelm normal chat responses.
    app.state.agent_semaphore = asyncio.Semaphore(settings.AGENT_MAX_CONCURRENCY)
    app.state.title_agent = build_title_agent(model=small_model)
    app.state.agent = build_agent(
        model=model,
        history_max_tokens=settings.AGENT_HISTORY_MAX_TOKENS,
    )
    logger.info(
        "Stateless LangChain agents initialized (max_concurrency=%s)",
        settings.AGENT_MAX_CONCURRENCY,
    )

    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Application resources released")
