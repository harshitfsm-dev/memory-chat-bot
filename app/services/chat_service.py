import asyncio
import logging
import uuid
from datetime import datetime, timezone
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from app.db.unit_of_work import UnitOfWork
from app.memory import build_prompt, count_tokens, fit_to_budget
from app.models.chat_message import ROLE_ASSISTANT, ROLE_USER, ChatMessage
from app.models.chat_thread import ChatThread
from app.models.user_memory import MEMORY_TYPE_NOTE
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_thread_repository import ChatThreadRepository
from app.services.summary_service import SummaryService
from app.services.user_memory_service import RetrievedMemory, UserMemoryService

logger = logging.getLogger(__name__)

TITLE_MAX_LENGTH = 60

# The title model sees only the start of a long message. A six-word title does
# not need more, and the whole message might not fit its context window.
TITLE_INPUT_MAX_CHARS = 2_000


class AgentExecutionError(RuntimeError):
    """Raised when the agent cannot produce a safe final response."""


class AgentTimeoutError(AgentExecutionError):
    """Raised when an agent run exceeds its total time budget."""


class ThreadNotFoundError(LookupError):
    """Raised when a thread does not exist or is not owned by the caller."""


class MessageTooLongError(ValueError):
    """Raised when a message cannot fit the model's token budget on its own.

    Answering anyway is not an option: there would be no room for the message
    itself, so the model would receive nothing useful.
    """


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
        summary_service: SummaryService,
        memory_service: UserMemoryService,
        *,
        timeout_seconds: float,
        recursion_limit: int,
        title_timeout_seconds: float,
        history_max_messages: int,
        history_max_tokens: int,
        memory_max_tokens: int,
    ):
        self.chat_message_repo = chat_message_repo
        self.chat_thread_repo = chat_thread_repo
        self.uow = uow
        self.agent = agent
        self.title_agent = title_agent
        self.agent_semaphore = agent_semaphore
        self.summary_service = summary_service
        self.memory_service = memory_service
        self.timeout_seconds = timeout_seconds
        self.recursion_limit = recursion_limit
        self.title_timeout_seconds = title_timeout_seconds
        self.history_max_messages = history_max_messages
        self.history_max_tokens = history_max_tokens
        self.memory_max_tokens = memory_max_tokens

    async def chat(
        self,
        message: str,
        user_id: str,
        thread_id: str | None = None,
    ) -> ChatResult:
        """Answer one message and persist the transcript.

        The agent itself stores nothing between requests. Memory comes from this
        method: it loads the thread's summary and recent messages and sends them
        along with the new message.

        Writes span two transactions rather than one. The first stores the
        user's turn and, in doing so, releases the pooled database connection
        before inference starts; the second stores the answer. Committing once
        at the end would hold a connection for the whole model call, including
        time spent queueing for a slot.
        """
        memories = await self._retrieve_memories(user_id=user_id, query=message)
        thread = await self._resolve_thread(
            message=message,
            user_id=user_id,
            thread_id=thread_id,
        )

        # Load short-term history before saving the new message, or the new
        # message would show up in its own history. Long-term retrieval already
        # completed and released its read transaction before thread/model work.
        messages = await self._build_prompt(thread, message, memories)

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
        user_message = await self._save_message(thread.id, ROLE_USER, message)

        try:
            # This deadline includes time waiting for an Ollama execution slot.
            async with asyncio.timeout(self.timeout_seconds):
                async with self.agent_semaphore:
                    result = await self.agent.ainvoke(
                        {"messages": messages},
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
        assistant_message = await self._save_message(
            thread.id,
            ROLE_ASSISTANT,
            answer,
        )

        logger.info(
            "Agent execution completed: run=%s thread=%s user=%s",
            run_id,
            thread.id,
            user_id,
        )

        await self._update_memories(
            user_id=user_id,
            thread=thread,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        await self._update_summary(thread)

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

        Mirrors `chat` but streams the model output, memory included. The
        transaction discipline is identical and deliberate: the user's turn is
        committed *before* inference so the pooled connection is released during
        the slow model call, and the assistant's turn is committed *after* the
        stream drains.

        Ownership and persistence failures that occur before the first token
        are raised (so the transport can still answer with an HTTP error). Once
        tokens start flowing the HTTP status is already sent, so a mid-stream
        failure is surfaced as a terminal "error" chunk instead.
        """
        memories = await self._retrieve_memories(user_id=user_id, query=message)
        thread = await self._resolve_thread(
            message=message,
            user_id=user_id,
            thread_id=thread_id,
        )
        messages = await self._build_prompt(thread, message, memories)

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
        user_message = await self._save_message(thread.id, ROLE_USER, message)

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
                    async for delta in self._stream_tokens(messages, config):
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
            assistant_message = await self._save_message(
                thread.id,
                ROLE_ASSISTANT,
                answer,
            )
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
        # Attempt memory storage before `done`, so a completed stream cannot be
        # cancelled after its terminal event but before long-term memory runs.
        await self._update_memories(
            user_id=user_id,
            thread=thread,
            user_message=user_message,
            assistant_message=assistant_message,
        )
        yield StreamChunk(type="done", text=answer)

        # Summary maintenance stays after the last chunk to avoid delaying it.
        await self._update_summary(thread)

    async def _build_prompt(
        self,
        thread: ChatThread,
        message: str,
        memories: tuple[tuple[str, ...], tuple[RetrievedMemory, ...]],
    ) -> list[BaseMessage]:
        """Build one prompt under both global and long-term-memory budgets."""
        # One date for every call below. The date lengthens the memory preamble, so
        # a value that changed mid-way would make the budget probes measure a
        # different prompt from the one actually sent.
        today = datetime.now(timezone.utc).date()

        # Summary and the current user message are mandatory. Retrieval must
        # never turn a message that previously fit into a 413 response.
        base_required = build_prompt([], message, thread.summary, today=today)
        base_tokens = count_tokens(base_required)
        if base_tokens > self.history_max_tokens:
            raise MessageTooLongError(
                f"Message needs about {base_tokens} tokens but the budget "
                f"is {self.history_max_tokens}"
            )

        retrieved_facts, retrieved_contextual = memories
        selected_facts: list[str] = []
        selected_contextual: list[RetrievedMemory] = []
        memory_budget = min(
            self.memory_max_tokens,
            self.history_max_tokens - base_tokens,
        )

        # Recount the complete required prompt for every candidate. This makes
        # the approximate-token threshold strict even after headings and the
        # assistant acknowledgement are included. Facts are pinned and consume
        # budget first; both lists arrive ranked, so the budget is spent on the
        # highest-value items rather than on whatever happens to come first.
        for fact in retrieved_facts:
            candidate_facts = (*selected_facts, fact)
            candidate = build_prompt(
                [],
                message,
                thread.summary,
                candidate_facts,
                (),
                today=today,
            )
            candidate_tokens = count_tokens(candidate)
            if (
                candidate_tokens > self.history_max_tokens
                or candidate_tokens - base_tokens > memory_budget
            ):
                # Skip rather than stop: one oversized fact must not deny the
                # remaining budget to shorter, still-important facts behind it.
                continue
            selected_facts.append(fact)

        # Notes are spent from the ranked list in order, best first.
        for item in retrieved_contextual:
            candidate_items = [*selected_contextual, item]
            candidate = build_prompt(
                [],
                message,
                thread.summary,
                tuple(selected_facts),
                self._notes_of(candidate_items),
                today=today,
            )
            candidate_tokens = count_tokens(candidate)
            if (
                candidate_tokens > self.history_max_tokens
                or candidate_tokens - base_tokens > memory_budget
            ):
                # Do not skip a more relevant memory to admit a less relevant one.
                # Retrieval order is part of the relevance guarantee.
                break
            selected_contextual.append(item)

        selected_notes = self._notes_of(selected_contextual)

        if len(selected_facts) < len(retrieved_facts) or len(selected_contextual) < len(
            retrieved_contextual
        ):
            logger.info(
                "Long-term memories dropped for token budget: thread=%s "
                "facts=%s contextual=%s max_tokens=%s",
                thread.id,
                len(retrieved_facts) - len(selected_facts),
                len(retrieved_contextual) - len(selected_contextual),
                memory_budget,
            )

        required = build_prompt(
            [],
            message,
            thread.summary,
            tuple(selected_facts),
            selected_notes,
            today=today,
        )
        required_tokens = count_tokens(required)
        history = await self.chat_message_repo.get_recent_messages(
            thread_id=thread.id,
            limit=self.history_max_messages,
            after_seq=thread.summary_up_to_seq,
        )
        kept = fit_to_budget(history, self.history_max_tokens - required_tokens)

        if len(kept) < len(history):
            logger.warning(
                "Dropped %s unsummarized message(s) for space: thread=%s "
                "summary_up_to_seq=%s",
                len(history) - len(kept),
                thread.id,
                thread.summary_up_to_seq,
            )

        prompt = build_prompt(
            kept,
            message,
            thread.summary,
            tuple(selected_facts),
            selected_notes,
            today=today,
        )
        # Defensive final check: approximate token accounting is deterministic,
        # so no assembled prompt may exceed the configured total budget.
        if count_tokens(prompt) > self.history_max_tokens:
            raise RuntimeError("Assembled chat prompt exceeded its token budget")
        return prompt

    @staticmethod
    def _notes_of(items: list[RetrievedMemory]) -> tuple[str, ...]:
        """The note contents from a ranked contextual list, order preserved.

        The contextual tier is notes only now, but the filter is kept explicit so
        the prompt cannot accidentally be fed a non-note if the retrieval shape
        ever changes again.
        """
        return tuple(item.content for item in items if item.kind == MEMORY_TYPE_NOTE)

    async def _retrieve_memories(
        self,
        *,
        user_id: str,
        query: str,
    ) -> tuple[tuple[str, ...], tuple[RetrievedMemory, ...]]:
        """Best-effort retrieval shared by streaming and non-streaming chat."""
        try:
            return await self.memory_service.retrieve_for_prompt(
                user_id=user_id,
                query=query,
            )
        except Exception:
            logger.warning(
                "Could not prepare long-term memory: user=%s",
                user_id,
                exc_info=True,
            )
            return (), ()

    async def _save_message(
        self,
        thread_id: str,
        role: str,
        content: str,
    ) -> ChatMessage:
        """Append one message, commit it, and retain its provenance ID."""
        seq = await self.chat_message_repo.next_seq(thread_id)
        saved = self.chat_message_repo.create(
            thread_id=thread_id,
            role=role,
            content=content,
            seq=seq,
        )
        await self.uow.commit()
        return saved

    async def _update_memories(
        self,
        *,
        user_id: str,
        thread: ChatThread,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        """Best-effort long-term memory after a complete durable turn."""
        try:
            await self.memory_service.process_turn(
                user_id=user_id,
                thread_id=thread.id,
                user_message=user_message,
                assistant_message=assistant_message,
            )
        except Exception:
            logger.warning(
                "Could not update long-term memory: thread=%s user=%s",
                thread.id,
                user_id,
                exc_info=True,
            )

        # Separately guarded, and deliberately after storing. Consolidation reads the
        # set this turn just added to, and a failure to tidy must not discard the
        # memory that was successfully written a moment ago.
        try:
            await self.memory_service.consolidate_if_needed(user_id=user_id)
        except Exception:
            logger.warning(
                "Could not consolidate long-term memory: user=%s",
                user_id,
                exc_info=True,
            )

    async def _update_summary(self, thread: ChatThread) -> None:
        """Refresh the thread's summary if it has grown enough.

        Runs after the turn is already saved, so a failure here costs nothing:
        it is logged, the answer still went out, and the next turn tries again.
        """
        try:
            await self.summary_service.update_if_needed(
                thread_id=thread.id,
                current_summary=thread.summary,
                summary_up_to_seq=thread.summary_up_to_seq,
            )
        except Exception:
            logger.warning(
                "Could not update summary for thread=%s", thread.id, exc_info=True
            )

    async def _stream_tokens(
        self,
        messages: list[BaseMessage],
        config: RunnableConfig,
    ) -> AsyncIterator[str]:
        """Yield model token text from the agent's streamed events.

        Uses LangChain's event stream and keeps only chat-model token chunks,
        so tool-call machinery and intermediate graph state never reach the
        client.
        """
        async for event in self.agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            if event.get("event") != "on_chat_model_stream":
                continue
            chunk = event.get("data", {}).get("chunk")
            text = getattr(chunk, "text", None)
            # `text` is normally a string, but older versions exposed a method.
            # Checking for a string first avoids the deprecated call path.
            if not isinstance(text, str) and callable(text):
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
                        {
                            "messages": [
                                HumanMessage(content=message[:TITLE_INPUT_MAX_CHARS])
                            ]
                        },
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
