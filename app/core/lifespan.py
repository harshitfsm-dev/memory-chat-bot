import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents import build_agent, build_summary_agent, build_title_agent
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

    # num_ctx is passed explicitly: Ollama otherwise uses its own default and
    # silently trims anything longer off the front of the prompt.
    model = create_ollama_model(
        model=settings.OLLAMA_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        num_predict=settings.AGENT_MAX_OUTPUT_TOKENS,
        num_ctx=settings.OLLAMA_NUM_CTX,
    )
    small_model = create_ollama_model(
        model=settings.OLLAMA_SMALL_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        reasoning=False,
        num_predict=settings.AGENT_TITLE_MAX_TOKENS,
        # Titles are tiny, and the input is capped before it is sent.
        num_ctx=4_096,
    )
    # Summaries stand in for messages the model can no longer see, so they use
    # the main model rather than the small one. Same num_ctx keeps Ollama from
    # loading a second copy of it.
    #
    # reasoning=False matters here. num_predict is only SUMMARY_MAX_TOKENS, and a
    # reasoning model will spend that budget thinking and return nothing at all.
    # Summarizing needs no reasoning: it is copying facts out of a transcript.
    summary_model = create_ollama_model(
        model=settings.OLLAMA_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        reasoning=False,
        num_predict=settings.SUMMARY_MAX_TOKENS,
        num_ctx=settings.OLLAMA_NUM_CTX,
    )

    # Ollama model execution is the constrained resource. All agents share this
    # limit so titles and summaries cannot overwhelm normal chat responses.
    app.state.agent_semaphore = asyncio.Semaphore(settings.AGENT_MAX_CONCURRENCY)
    app.state.title_agent = build_title_agent(model=small_model)
    app.state.summary_agent = build_summary_agent(model=summary_model)
    app.state.agent = build_agent(
        model=model,
        history_max_tokens=settings.AGENT_HISTORY_MAX_TOKENS,
    )
    logger.info(
        "Agents initialized: max_concurrency=%s num_ctx=%s "
        "history_budget=%s tokens (row cap %s) output=%s "
        "summary=%s (trigger=%s keep_recent=%s max=%s tokens)",
        settings.AGENT_MAX_CONCURRENCY,
        settings.OLLAMA_NUM_CTX,
        settings.AGENT_HISTORY_MAX_TOKENS,
        settings.AGENT_HISTORY_MAX_MESSAGES,
        settings.AGENT_MAX_OUTPUT_TOKENS,
        "on" if settings.SUMMARY_ENABLED else "off",
        settings.SUMMARY_TRIGGER_TOKENS,
        settings.SUMMARY_KEEP_RECENT_TOKENS,
        settings.SUMMARY_MAX_TOKENS,
    )

    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Application resources released")
