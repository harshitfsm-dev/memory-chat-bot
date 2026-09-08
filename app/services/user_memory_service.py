"""Long-term user memory: a deliberately small, learning-oriented implementation.

Two tiers, one idea each:

- Facts are a fixed set of profile fields (name, occupation, preferences, ...).
  One row per key per user, pinned into every prompt.
- Notes are free-text things worth remembering, retrieved by semantic similarity
  to the current message.

This is intentionally bare-bones. There is no note consolidation, no expiry, no
privacy/injection filtering, and no weighted ranking — notes come back in plain
cosine-similarity order. It keeps the two interesting patterns (pinned facts +
semantic retrieval) visible without production scaffolding.
"""

import asyncio
import json
import logging
from typing import Any, NamedTuple

from langchain_core.embeddings import Embeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import Runnable

from app.db.unit_of_work import UnitOfWork
from app.models.chat_message import ROLE_ASSISTANT, ROLE_USER, ChatMessage
from app.repositories.user_memory_repository import UserMemoryRepository
from app.schemas.user_memory import (
    FACT_KEYS,
    FACT_TEMPLATES,
    MAX_FACT_VALUE_CHARS,
    MAX_NOTE_CONTENT_CHARS,
    MAX_NOTE_SUBJECT_CHARS,
    ExtractedMemory,
    MemoryExtraction,
)
from app.services.user_memory_prompts import MEMORY_EXTRACTION_PROMPT, looks_unsafe

logger = logging.getLogger(__name__)


class RetrievedMemory(NamedTuple):
    """One note that was retrieved for the prompt, copied out of its ORM row."""

    content: str
    similarity: float


class UserMemoryService:
    """Extract, embed, store, and retrieve user memories. Deliberately minimal."""

    def __init__(
        self,
        repository: UserMemoryRepository,
        uow: UnitOfWork,
        extractor: Runnable[Any, dict[str, Any]],
        embeddings: Embeddings,
        agent_semaphore: asyncio.Semaphore,
        memory_semaphore: asyncio.Semaphore,
        *,
        enabled: bool,
        retrieval_enabled: bool,
        embedding_model: str,
        max_items_per_turn: int,
        retrieval_min_similarity: float,
        retrieval_max_notes: int,
        timeout_seconds: float,
    ):
        self.repository = repository
        self.uow = uow
        self.extractor = extractor
        self.embeddings = embeddings
        self.agent_semaphore = agent_semaphore
        self.memory_semaphore = memory_semaphore
        self.enabled = enabled
        self.retrieval_enabled = retrieval_enabled
        self.embedding_model = embedding_model
        self.max_items_per_turn = max_items_per_turn
        self.retrieval_min_similarity = retrieval_min_similarity
        self.retrieval_max_notes = retrieval_max_notes
        self.timeout_seconds = timeout_seconds

    async def retrieve_for_prompt(
        self,
        *,
        user_id: str,
        query: str,
    ) -> tuple[tuple[str, ...], tuple[RetrievedMemory, ...]]:
        """Return pinned facts and the notes most similar to the query.

        Facts are pinned, so they load unconditionally. Notes are retrieved by
        cosine similarity to the current message. Best-effort: any failure logs a
        warning and returns whatever was gathered, leaving the session reusable.
        """
        if not self.retrieval_enabled:
            return (), ()

        query_embedding: list[float] | None = None
        if self.retrieval_max_notes > 0:
            try:
                async with asyncio.timeout(self.timeout_seconds):
                    async with self.memory_semaphore:
                        async with self.agent_semaphore:
                            query_embedding = await self.embeddings.aembed_query(query)
            except Exception:
                logger.warning(
                    "Could not embed memory query: user=%s", user_id, exc_info=True
                )

        try:
            fact_rows = await self.repository.get_active_facts(user_id=user_id)
            facts = tuple(row.content for row in fact_rows)

            notes: list[RetrievedMemory] = []
            if query_embedding is not None and self.retrieval_max_notes > 0:
                rows = await self.repository.get_relevant_notes(
                    user_id=user_id,
                    query_embedding=query_embedding,
                    embedding_model=self.embedding_model,
                    min_similarity=self.retrieval_min_similarity,
                    limit=self.retrieval_max_notes,
                )
                # The repository already ordered these by similarity; copy the
                # values out so a later rollback cannot expire them.
                notes = [
                    RetrievedMemory(content=row.content, similarity=similarity)
                    for row, similarity in rows
                ]
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            logger.warning(
                "Could not retrieve user memory: user=%s", user_id, exc_info=True
            )
            return (), ()

        logger.info(
            "Memory retrieved: user=%s facts=%s notes=%s",
            user_id,
            len(facts),
            len(notes),
        )
        return facts, tuple(notes)

    async def process_turn(
        self,
        *,
        user_id: str,
        thread_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> int:
        """Extract memories from one turn, embed them, and store them.

        Returns how many were written.
        """
        if not self.enabled:
            return 0
        self._validate_turn(thread_id, user_message, assistant_message)

        extracted = await self._extract(user_message.content, assistant_message.content)
        memories = [
            normalized
            for memory in extracted
            if (normalized := self._normalize(memory)) is not None
        ][: self.max_items_per_turn]
        if not memories:
            return 0

        embeddings = await self._embed([memory.content for memory in memories])
        if len(embeddings) != len(memories):
            raise RuntimeError("Ollama returned the wrong number of embeddings")

        try:
            for memory, embedding in zip(memories, embeddings, strict=True):
                common = {
                    "user_id": user_id,
                    "content": memory.content,
                    "embedding": embedding,
                    "embedding_model": self.embedding_model,
                    "confidence": memory.confidence,
                    "importance": memory.importance,
                    "source_thread_id": thread_id,
                    "source_message_id": user_message.id,
                }
                if memory.memory_type == "fact":
                    await self.repository.upsert_fact(
                        memory_key=memory.memory_key or "",
                        allow_lower_confidence=memory.is_correction,
                        **common,
                    )
                else:
                    await self.repository.create_note(
                        category=memory.category or "other",
                        subject=memory.subject or None,
                        **common,
                    )
            await self.uow.commit()
        except Exception:
            await self.uow.rollback()
            raise

        logger.info(
            "Memory stored: user=%s thread=%s count=%s",
            user_id,
            thread_id,
            len(memories),
        )
        return len(memories)

    async def consolidate_if_needed(self, *, user_id: str) -> int:
        """No-op. Kept so callers need not change.

        The production build tidied notes (dedup, expiry, a cap). This learning
        build lets notes accumulate; add consolidation back if it ever matters.
        """
        return 0

    async def _extract(
        self,
        user_content: str,
        assistant_content: str,
    ) -> list[ExtractedMemory]:
        turn = json.dumps(
            {"user_message": user_content, "assistant_message": assistant_content},
            ensure_ascii=False,
        )
        async with asyncio.timeout(self.timeout_seconds):
            async with self.memory_semaphore:
                async with self.agent_semaphore:
                    result = await self.extractor.ainvoke(
                        [
                            SystemMessage(content=MEMORY_EXTRACTION_PROMPT),
                            HumanMessage(
                                content=(
                                    f"Extract at most {self.max_items_per_turn} "
                                    f"memories from this turn JSON:\n{turn}"
                                )
                            ),
                        ]
                    )

        if not isinstance(result, dict):
            raise RuntimeError("Memory extractor returned an unexpected result")
        parsed = result.get("parsed")
        if result.get("parsing_error") is not None or parsed is None:
            logger.warning("Memory extraction produced invalid output")
            return []
        if not isinstance(parsed, MemoryExtraction):
            raise RuntimeError("Memory extractor returned the wrong schema")
        return parsed.memories

    async def _embed(self, contents: list[str]) -> list[list[float]]:
        async with asyncio.timeout(self.timeout_seconds):
            async with self.memory_semaphore:
                async with self.agent_semaphore:
                    return await self.embeddings.aembed_documents(contents)

    def _normalize(self, memory: ExtractedMemory) -> ExtractedMemory | None:
        """Build the stored sentence for a candidate, or drop it.

        Light-touch: collapse whitespace, bound length, and run the stored text
        past a small unsafe-pattern net (credentials, contact details, injected
        instructions). The net is the backstop for the extraction prompt, which a
        small model does not always obey.
        """
        if memory.memory_type == "fact":
            key = memory.memory_key or ""
            if key not in FACT_KEYS:
                return None
            value = " ".join(memory.value.split())
            if not value or len(value) > MAX_FACT_VALUE_CHARS:
                return None
            content = FACT_TEMPLATES[key].format(value=value)
        else:
            if memory.category is None:
                return None
            content = " ".join(memory.content.split())
            if not content or len(content) > MAX_NOTE_CONTENT_CHARS:
                return None

        if looks_unsafe(content):
            logger.info("Memory rejected by safety net: type=%s", memory.memory_type)
            return None

        if memory.memory_type == "fact":
            return memory.model_copy(update={"content": content})
        subject = " ".join(memory.subject.split())[:MAX_NOTE_SUBJECT_CHARS]
        return memory.model_copy(update={"content": content, "subject": subject})

    @staticmethod
    def _validate_turn(
        thread_id: str,
        user_message: ChatMessage,
        assistant_message: ChatMessage,
    ) -> None:
        if user_message.role != ROLE_USER or assistant_message.role != ROLE_ASSISTANT:
            raise ValueError("Memory extraction requires a user/assistant turn")
        if (
            user_message.thread_id != thread_id
            or assistant_message.thread_id != thread_id
        ):
            raise ValueError("Memory source messages must belong to the same thread")
        if not user_message.id or not assistant_message.id:
            raise ValueError("Memory source messages must already be persisted")
