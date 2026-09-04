import asyncio
import logging
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from app.db.unit_of_work import UnitOfWork
from app.models.chat_message import ChatMessage
from app.models.chat_thread import ChatThread
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_thread_repository import ChatThreadRepository

logger = logging.getLogger(__name__)

TITLE_MAX_LENGTH = 60

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"


class AgentExecutionError(RuntimeError):
    """Raised when the agent cannot produce a safe final response."""


class AgentTimeoutError(AgentExecutionError):
    """Raised when an agent run exceeds its total time budget."""


class ThreadNotFoundError(LookupError):
    """Raised when a thread does not exist or is not owned by the caller."""


@dataclass(frozen=True)
class ChatResult:
    """Everything the transport layer needs to build a chat response."""

    answer: str
    thread_id: str
    thread_title: str


@dataclass(frozen=True)
class StreamChunk:
    """One event in a streaming chat response.

    `type` is one of:
      - "meta":  thread resolved; `thread_id` / `thread_title` are set.
      - "delta": a token chunk; `text` holds the incremental text.
      - "done":  generation finished and persisted; `text` holds the full answer.
      - "error": generation failed mid-stream; `text` holds a safe message.
    """

    type: str
    text: str = ""
    thread_id: str | None = None
    thread_title: str | None = None


class ChatService:
    def __init__(
        self,
        chat_message_repo: ChatMessageRepository,
        chat_thread_repo: ChatThreadRepository,
        uow: UnitOfWork,
        agent: CompiledStateGraph[Any, Any, Any, Any],
        title_agent: CompiledStateGraph[Any, Any, Any, Any],
        agent_semaphore: asyncio.Semaphore,
        *,
        timeout_seconds: float,
        recursion_limit: int,
        title_timeout_seconds: float,
    ):
        self.chat_message_repo = chat_message_repo
        self.chat_thread_repo = chat_thread_repo
        self.uow = uow
        self.agent = agent
        self.title_agent = title_agent
        self.agent_semaphore = agent_semaphore
        self.timeout_seconds = timeout_seconds
        self.recursion_limit = recursion_limit
        self.title_timeout_seconds = title_timeout_seconds

    async def chat(
        self,
        message: str,
        user_id: str,
        thread_id: str | None = None,
    ) -> ChatResult:
        """Answer one message and persist the transcript.

        The agent is intentionally stateless for now. `thread_id` groups the
        durable SQL transcript and enforces ownership, but previous turns are
        not sent to the model.

        Writes span two transactions rather than one. The first stores the
        user's turn and, in doing so, releases the pooled database connection
        before inference starts; the second stores the answer. Committing once
        at the end would hold a connection for the whole model call, including
        time spent queueing for a slot.
        """
        thread = await self._resolve_thread(
            message=message,
            user_id=user_id,
            thread_id=thread_id,
        )
        run_id = str(uuid.uuid4())
        config: RunnableConfig = {
            "recursion_limit": self.recursion_limit,
            "run_name": "chat-response",
            "tags": ["chat"],
            "metadata": {
                "run_id": run_id,
                "thread_id": thread.id,
                "user_id": user_id,
            },
        }

        # A new thread is still unsaved here, so this commit makes the thread
        # and its opening message durable together: no empty threads if the
        # insert fails. Committing before generation also deliberately keeps
        # the user's turn when the agent later fails, so the transcript
        # reflects what they submitted.
        self.chat_message_repo.create(
            thread_id=thread.id,
            role=ROLE_USER,
            content=message,
        )
        await self.uow.commit()

        try:
            # This deadline includes time waiting for an Ollama execution slot.
            async with asyncio.timeout(self.timeout_seconds):
                async with self.agent_semaphore:
                    result = await self.agent.ainvoke(
                        {"messages": [HumanMessage(content=message)]},
                        config=config,
                    )
            answer = self._final_answer(result)
        except TimeoutError as exc:
            logger.warning(
                "Agent timed out: run=%s thread=%s user=%s",
                run_id,
                thread.id,
                user_id,
            )
            raise AgentTimeoutError("Agent execution timed out") from exc
        except Exception as exc:
            logger.exception(
                "Agent execution failed: run=%s thread=%s user=%s",
                run_id,
                thread.id,
                user_id,
            )
            raise AgentExecutionError("Agent execution failed") from exc

        # A failure here raises PersistenceError rather than returning the
        # answer, so the caller is never told a turn was stored when it wasn't.
        self.chat_message_repo.create(
            thread_id=thread.id,
            role=ROLE_ASSISTANT,
            content=answer,
        )
        await self.uow.commit()

        logger.info(
            "Agent execution completed: run=%s thread=%s user=%s",
            run_id,
            thread.id,
            user_id,
        )

        return ChatResult(
            answer=answer,
            thread_id=thread.id,
            thread_title=thread.title or self._fallback_title(message),
        )

    async def stream_chat(
        self,
        message: str,
        user_id: str,
        thread_id: str | None = None,
    ) -> AsyncIterator[StreamChunk]:
        """Answer one message as a stream of token chunks and persist the turn.

        Mirrors `chat` but streams the model output. The transaction discipline
        is identical and deliberate: the user's turn is committed *before*
        inference so the pooled connection is released during the slow model
        call, and the assistant's turn is committed *after* the stream drains.

        Ownership and persistence failures that occur before the first token
        are raised (so the transport can still answer with an HTTP error). Once
        tokens start flowing the HTTP status is already sent, so a mid-stream
        failure is surfaced as a terminal "error" chunk instead.
        """
        thread = await self._resolve_thread(
            message=message,
            user_id=user_id,
            thread_id=thread_id,
        )
        run_id = str(uuid.uuid4())
        config: RunnableConfig = {
            "recursion_limit": self.recursion_limit,
            "run_name": "chat-response-stream",
            "tags": ["chat", "stream"],
            "metadata": {
                "run_id": run_id,
                "thread_id": thread.id,
                "user_id": user_id,
            },
        }

        # Commit the user's turn (and any new thread) before inference, exactly
        # as the non-streaming path does. A failure here propagates before the
        # stream opens, so the transport can still return an HTTP error.
        self.chat_message_repo.create(
            thread_id=thread.id,
            role=ROLE_USER,
            content=message,
        )
        await self.uow.commit()

        # Announce the resolved thread before tokens so the client can attach
        # them to the right (possibly brand-new) thread.
        yield StreamChunk(
            type="meta",
            thread_id=thread.id,
            thread_title=thread.title or self._fallback_title(message),
        )

        parts: list[str] = []
        try:
            async with asyncio.timeout(self.timeout_seconds):
                async with self.agent_semaphore:
                    async for delta in self._stream_tokens(message, config):
                        parts.append(delta)
                        yield StreamChunk(type="delta", text=delta)
        except TimeoutError:
            logger.warning(
                "Agent stream timed out: run=%s thread=%s user=%s",
                run_id,
                thread.id,
                user_id,
            )
            yield StreamChunk(type="error", text="Agent generation timed out")
            return
        except Exception:
            logger.exception(
                "Agent stream failed: run=%s thread=%s user=%s",
                run_id,
                thread.id,
                user_id,
            )
            yield StreamChunk(type="error", text="Agent generation failed")
            return

        answer = "".join(parts).strip()
        if not answer:
            logger.warning(
                "Agent stream produced no text: run=%s thread=%s user=%s",
                run_id,
                thread.id,
                user_id,
            )
            yield StreamChunk(type="error", text="Agent generation failed")
            return

        # Persist the assistant turn after the stream drains. If this fails the
        # client already has the text; log and still close with an error chunk
        # so the client knows the turn was not saved.
        try:
            self.chat_message_repo.create(
                thread_id=thread.id,
                role=ROLE_ASSISTANT,
                content=answer,
            )
            await self.uow.commit()
        except Exception:
            logger.exception(
                "Failed to persist streamed answer: run=%s thread=%s user=%s",
                run_id,
                thread.id,
                user_id,
            )
            yield StreamChunk(type="error", text="Response was not saved")
            return

        logger.info(
            "Agent stream completed: run=%s thread=%s user=%s",
            run_id,
            thread.id,
            user_id,
        )
        yield StreamChunk(type="done", text=answer)

    async def _stream_tokens(
        self,
        message: str,
        config: RunnableConfig,
    ) -> AsyncIterator[str]:
        """Yield model token text from the agent's streamed events.

        Uses LangChain's event stream and keeps only chat-model token chunks,
        so tool-call machinery and intermediate graph state never reach the
        client.
        """
        async for event in self.agent.astream_events(
            {"messages": [HumanMessage(content=message)]},
            config=config,
            version="v2",
        ):
            if event.get("event") != "on_chat_model_stream":
                continue
            chunk = event.get("data", {}).get("chunk")
            text = getattr(chunk, "text", None)
            # `text` can be a str or (older) a method; normalize and skip empties.
            if callable(text):
                text = text()
            if isinstance(text, str) and text:
                yield text

    async def _resolve_thread(
        self,
        message: str,
        user_id: str,
        thread_id: str | None,
    ) -> ChatThread:
        if thread_id is None:
            # Generate the title before staging the row so no transaction is
            # open across that model call.
            title = await self._generate_title(message)
            return await self.chat_thread_repo.create(
                user_id=user_id,
                title=title,
            )

        thread = await self.chat_thread_repo.get_owned(thread_id, user_id)
        if thread is None:
            logger.warning(
                "Rejected thread access: thread=%s user=%s",
                thread_id,
                user_id,
            )
            raise ThreadNotFoundError("Thread not found")
        return thread

    async def _generate_title(self, message: str) -> str:
        """Name a new thread, falling back without blocking chat on failure."""
        config: RunnableConfig = {
            "run_name": "generate-thread-title",
            "tags": ["chat", "title"],
        }
        try:
            async with asyncio.timeout(self.title_timeout_seconds):
                async with self.agent_semaphore:
                    result = await self.title_agent.ainvoke(
                        {"messages": [HumanMessage(content=message)]},
                        config=config,
                    )
            title = self._final_answer(result)
        except Exception:
            logger.warning("Title generation failed; using fallback", exc_info=True)
            return self._fallback_title(message)

        return self._clean_title(title) or self._fallback_title(message)

    @staticmethod
    def _clean_title(title: str) -> str:
        return " ".join(title.split()).strip("\"'").strip()[:TITLE_MAX_LENGTH]

    @staticmethod
    def _fallback_title(message: str) -> str:
        title = " ".join(message.split())[:TITLE_MAX_LENGTH].strip()
        return title or "New conversation"

    @staticmethod
    def _final_answer(result: dict) -> str:
        messages = result.get("messages", [])
        if not messages or not isinstance(messages[-1], AIMessage):
            raise AgentExecutionError("Agent returned no final message")

        answer = messages[-1].text
        if not answer.strip():
            raise AgentExecutionError("Agent returned no answer text")
        return answer

    async def get_user_threads(self, user_id: str) -> list[ChatThread]:
        return await self.chat_thread_repo.get_all_threads(user_id=user_id)

    async def get_thread_messages(
        self,
        thread_id: str,
        user_id: str,
    ) -> list[ChatMessage]:
        # Thread ids arrive from the client, so prove ownership before
        # returning a transcript — otherwise any user could read any thread.
        thread = await self.chat_thread_repo.get_owned(thread_id, user_id)
        if thread is None:
            raise ThreadNotFoundError(thread_id)
        return await self.chat_message_repo.get_all_messages(thread_id=thread_id)
