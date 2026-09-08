import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.agents import build_agent, build_summary_agent, build_title_agent
from app.core.config import get_settings
from app.core.security import JWTService, PasswordService
from app.db.database import create_database
from app.llm.ollama import create_ollama_embeddings, create_ollama_model
from app.models.user_memory import MEMORY_EMBEDDING_DIMENSIONS
from app.schemas.user_memory import MemoryExtraction

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
    #
    # reasoning is passed explicitly rather than left to the model's default. A
    # thinking block delays the first streamed token and consumes the same
    # num_predict budget the visible answer needs.
    model = create_ollama_model(
        model=settings.OLLAMA_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        reasoning=settings.OLLAMA_AGENT_REASONING,
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
    #
    # This only helps on a model that honours it. A reasoning-only model returns
    # an empty summary instead, which is why OLLAMA_AGENT_MODEL must be a model
    # that can turn thinking off.
    summary_model = create_ollama_model(
        model=settings.OLLAMA_AGENT_MODEL,
        temperature=settings.OLLAMA_TEMPERATURE,
        timeout_seconds=settings.OLLAMA_TIMEOUT_SECONDS,
        reasoning=False,
        num_predict=settings.SUMMARY_MAX_TOKENS,
        num_ctx=settings.OLLAMA_NUM_CTX,
    )
    # Long-term memory extraction is deterministic and tool-free. Structured
    # output lets Pydantic reject malformed facts before any database work.
    memory_model = create_ollama_model(
        model=settings.OLLAMA_MEMORY_MODEL,
        temperature=0,
        timeout_seconds=settings.MEMORY_TIMEOUT_SECONDS,
        reasoning=False,
        num_predict=settings.MEMORY_EXTRACTION_MAX_TOKENS,
        num_ctx=settings.OLLAMA_NUM_CTX,
    )
    memory_embeddings = create_ollama_embeddings(
        model=settings.OLLAMA_EMBEDDING_MODEL,
        dimensions=MEMORY_EMBEDDING_DIMENSIONS,
        timeout_seconds=settings.MEMORY_TIMEOUT_SECONDS,
    )

    # Ollama model execution is the constrained resource. All agents share this
    # limit so titles, summaries, and memory work cannot overwhelm normal chat.
    app.state.agent_semaphore = asyncio.Semaphore(settings.AGENT_MAX_CONCURRENCY)
    # At most one memory job can contend for the global Ollama capacity. With
    # the default global limit of two, an interactive chat always retains room.
    app.state.memory_semaphore = asyncio.Semaphore(1)
    app.state.title_agent = build_title_agent(model=small_model)
    app.state.summary_agent = build_summary_agent(model=summary_model)
    app.state.agent = build_agent(
        model=model,
        history_max_tokens=settings.AGENT_HISTORY_MAX_TOKENS,
    )
    app.state.memory_extractor = memory_model.with_structured_output(
        MemoryExtraction,
        method="json_schema",
        include_raw=True,
    )
    app.state.memory_embeddings = memory_embeddings
    logger.info(
        "Agents initialized: max_concurrency=%s num_ctx=%s "
        "history_budget=%s tokens (row cap %s) output=%s "
        "summary=%s (trigger=%s keep_recent=%s max=%s tokens) "
        "long_memory=%s (extractor=%s embeddings=%s max_items=%s) "
        "retrieval=%s (similarity>=%.2f notes<=%s tokens<=%s)",
        settings.AGENT_MAX_CONCURRENCY,
        settings.OLLAMA_NUM_CTX,
        settings.AGENT_HISTORY_MAX_TOKENS,
        settings.AGENT_HISTORY_MAX_MESSAGES,
        settings.AGENT_MAX_OUTPUT_TOKENS,
        "on" if settings.SUMMARY_ENABLED else "off",
        settings.SUMMARY_TRIGGER_TOKENS,
        settings.SUMMARY_KEEP_RECENT_TOKENS,
        settings.SUMMARY_MAX_TOKENS,
        "on" if settings.MEMORY_ENABLED else "off",
        settings.OLLAMA_MEMORY_MODEL,
        settings.OLLAMA_EMBEDDING_MODEL,
        settings.MEMORY_MAX_ITEMS_PER_TURN,
        "on" if settings.MEMORY_RETRIEVAL_ENABLED else "off",
        settings.MEMORY_RETRIEVAL_MIN_SIMILARITY,
        settings.MEMORY_RETRIEVAL_MAX_NOTES,
        settings.MEMORY_RETRIEVAL_MAX_TOKENS,
    )

    try:
        yield
    finally:
        await engine.dispose()
        logger.info("Application resources released")
