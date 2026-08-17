import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.agents import build_agent_graph
from app.core.config import get_settings
from app.core.security import JWTService, PasswordService
from app.db.database import create_database
from app.llm.ollama import create_ollama_model
from app.services.chat_service import ChatService


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
    )

    try:
        async with AsyncSqliteSaver.from_conn_string(
            str(settings.LANGGRAPH_CHECKPOINT_PATH)
        ) as checkpointer:
            await checkpointer.setup()
            graph = build_agent_graph(
                model=model,
                checkpointer=checkpointer,
                history_max_tokens=settings.AGENT_HISTORY_MAX_TOKENS,
            )
            app.state.chat_service = ChatService(
                graph,
                timeout_seconds=settings.AGENT_TIMEOUT_SECONDS,
                recursion_limit=settings.AGENT_RECURSION_LIMIT,
            )
            logger.info("LangGraph agent workflow initialized")
            yield
    finally:
        await engine.dispose()
        logger.info("Application resources released")
