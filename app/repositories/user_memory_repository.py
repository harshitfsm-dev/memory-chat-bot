import logging
import math
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, false, func, or_, select, true, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.errors import PersistenceError
from app.models.chat_message import ChatMessage
from app.models.chat_thread import ChatThread
from app.models.user_memory import (
    MEMORY_EMBEDDING_DIMENSIONS,
    MEMORY_TYPE_FACT,
    MEMORY_TYPE_NOTE,
    UserMemory,
)

logger = logging.getLogger(__name__)

# Ceiling on one candidate fetch. Retrieval deliberately asks for more rows than
# the prompt can hold so the caller has something to re-rank, but the result is
# ranked in Python, so the set has to stay small enough to be cheap to score.
MAX_CANDIDATE_MEMORIES = 50


class UserMemoryRepository:
    """Stages user-owned long-term memory writes.

    As with the other repositories, this class never commits. The calling
    service owns the transaction through UnitOfWork.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all_active(self, *, user_id: str) -> list[UserMemory]:
        """Return every active memory owned by one user for management UI.

        Includes expired-but-not-yet-swept notes on purpose. Retrieval hides them
        from prompts, but hiding them here would mean a user could not see, or
        delete, something the system still holds.
        """
        statement = (
            select(UserMemory)
            .where(
                UserMemory.user_id == user_id,
                UserMemory.is_active.is_(True),
            )
            .order_by(
                UserMemory.memory_type.desc(),
                UserMemory.memory_key.asc().nulls_last(),
                UserMemory.category.asc().nulls_last(),
                UserMemory.updated_at.desc(),
                UserMemory.id.asc(),
            )
        )
        try:
            result = await self.db.execute(statement)
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Active memory listing failed")
            raise PersistenceError("Could not retrieve user memories") from exc
        return list(result.scalars().all())

    async def get_active_facts(self, *, user_id: str) -> list[UserMemory]:
        """Return the user's active facts, most important first.

        Active facts are the implicit pinned-memory set: the schema permits one
        current row per user and fact key, so this collection is bounded.

        Order matters because the caller spends a token sub-budget in the order
        given and stops when it runs out. Sorting by key put that decision in
        the hands of alphabetical accident; sorting by importance spends the
        budget on the facts that matter, with the key as a stable tie-break so
        the same inputs always produce the same prompt.
        """
        statement = (
            select(UserMemory)
            .where(
                UserMemory.user_id == user_id,
                UserMemory.is_active.is_(True),
                UserMemory.memory_type == MEMORY_TYPE_FACT,
            )
            .order_by(
                UserMemory.importance.desc(),
                UserMemory.memory_key.asc(),
                UserMemory.id.asc(),
            )
        )
        try:
            result = await self.db.execute(statement)
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Active fact retrieval failed")
            raise PersistenceError("Could not retrieve user memories") from exc
        return list(result.scalars().all())

    async def get_relevant_notes(
        self,
        *,
        user_id: str,
        query_embedding: Sequence[float],
        embedding_model: str,
        min_similarity: float,
        limit: int = 3,
    ) -> list[tuple[UserMemory, float]]:
        """Return the user's notes most similar to the query, best first.

        Restricting to one ``embedding_model`` is not optional: vectors from
        different models do not share a space, so comparing them yields distances
        that look valid and mean nothing. Each result carries its cosine
        similarity (1 - distance) so the caller can see how close the match was.
        """
        if not 0 <= min_similarity <= 1:
            raise ValueError("Minimum memory similarity must be between 0 and 1")
        if not 1 <= limit <= MAX_CANDIDATE_MEMORIES:
            raise ValueError(
                f"Memory candidate limit must be between 1 and {MAX_CANDIDATE_MEMORIES}"
            )
        if not embedding_model.strip():
            raise ValueError("Embedding model is required for memory retrieval")

        embedding_values = self._validated_embedding(query_embedding)
        cosine_distance = UserMemory.embedding.cosine_distance(embedding_values)
        statement = (
            select(UserMemory, cosine_distance.label("cosine_distance"))
            .where(
                UserMemory.user_id == user_id,
                UserMemory.is_active.is_(True),
                UserMemory.memory_type == MEMORY_TYPE_NOTE,
                UserMemory.embedding_model == embedding_model,
                cosine_distance <= 1.0 - min_similarity,
            )
            .order_by(cosine_distance.asc(), UserMemory.id.asc())
            .limit(limit)
        )
        try:
            result = await self.db.execute(statement)
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Note retrieval failed")
            raise PersistenceError("Could not retrieve user memories") from exc

        return [(memory, 1.0 - float(distance)) for memory, distance in result.all()]

    async def create_note(
        self,
        *,
        user_id: str,
        category: str,
        subject: str | None,
        content: str,
        embedding: Sequence[float],
        embedding_model: str,
        confidence: float = 1.0,
        importance: float = 0.5,
        source_thread_id: str | None = None,
        source_message_id: str | None = None,
    ) -> UserMemory:
        """Stage one free-text note for the user."""
        await self._validate_provenance(
            user_id=user_id,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )
        memory = UserMemory(
            user_id=user_id,
            memory_type=MEMORY_TYPE_NOTE,
            memory_key=None,
            category=category,
            subject=subject,
            content=content,
            embedding=self._validated_embedding(embedding),
            embedding_model=embedding_model,
            confidence=confidence,
            importance=importance,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )
        self.db.add(memory)
        return memory

    async def upsert_fact(
        self,
        *,
        user_id: str,
        memory_key: str,
        content: str,
        embedding: Sequence[float],
        embedding_model: str,
        confidence: float = 1.0,
        importance: float = 0.5,
        source_thread_id: str | None = None,
        source_message_id: str | None = None,
        allow_lower_confidence: bool = False,
    ) -> UserMemory | None:
        """Insert a fact, replacing weaker values or explicit corrections.

        Returns None when a stronger existing fact wins the conflict.
        """
        await self._validate_provenance(
            user_id=user_id,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
        )
        embedding_values = self._validated_embedding(embedding)
        insert_statement = insert(UserMemory).values(
            user_id=user_id,
            memory_type=MEMORY_TYPE_FACT,
            memory_key=memory_key,
            content=content,
            embedding=embedding_values,
            embedding_model=embedding_model,
            confidence=confidence,
            importance=importance,
            source_thread_id=source_thread_id,
            source_message_id=source_message_id,
            is_active=True,
        )
        active_update_allowed = (
            true()
            if allow_lower_confidence
            else insert_statement.excluded.confidence >= UserMemory.confidence
        )
        inactive_reactivation_allowed = false()
        if source_message_id is not None:
            source_created_at = (
                select(ChatMessage.created_at)
                .where(ChatMessage.id == source_message_id)
                .scalar_subquery()
            )
            inactive_reactivation_allowed = and_(
                UserMemory.is_active.is_(False),
                source_created_at > UserMemory.updated_at,
            )

        statement = insert_statement.on_conflict_do_update(
            constraint="uq_user_memories_owner_type_key",
            set_={
                "content": content,
                "embedding": embedding_values,
                "embedding_model": embedding_model,
                "confidence": confidence,
                "importance": importance,
                "source_thread_id": source_thread_id,
                "source_message_id": source_message_id,
                "is_active": True,
                "updated_at": func.clock_timestamp(),
            },
            where=or_(
                and_(UserMemory.is_active.is_(True), active_update_allowed),
                inactive_reactivation_allowed,
            ),
        ).returning(UserMemory)
        try:
            result = await self.db.execute(
                statement,
                execution_options={"populate_existing": True},
            )
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Fact upsert failed; transaction rolled back")
            raise PersistenceError("Could not store user memory") from exc
        return result.scalar_one_or_none()

    async def deactivate_owned(
        self,
        memory_id: str,
        user_id: str,
        *,
        expected_updated_at: datetime | None = None,
    ) -> bool:
        """Soft-delete an owned memory, optionally requiring the seen version."""
        conditions = [
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id,
            UserMemory.is_active.is_(True),
        ]
        if expected_updated_at is not None:
            conditions.append(UserMemory.updated_at == expected_updated_at)

        try:
            result = await self.db.execute(
                update(UserMemory)
                .where(*conditions)
                .values(is_active=False, updated_at=func.clock_timestamp())
            )
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Memory deactivation failed; transaction rolled back")
            raise PersistenceError("Could not update user memory") from exc
        return result.rowcount > 0

    async def active_owned_exists(self, *, memory_id: str, user_id: str) -> bool:
        """Check a failed versioned delete without exposing another user's row."""
        statement = select(UserMemory.id).where(
            UserMemory.id == memory_id,
            UserMemory.user_id == user_id,
            UserMemory.is_active.is_(True),
        )
        try:
            result = await self.db.execute(statement)
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Memory ownership check failed; transaction rolled back")
            raise PersistenceError("Could not update user memory") from exc
        return result.scalar_one_or_none() is not None

    async def _validate_provenance(
        self,
        *,
        user_id: str,
        source_thread_id: str | None,
        source_message_id: str | None,
    ) -> None:
        """Prove that optional source records form one user-owned transcript."""
        if source_message_id is not None and source_thread_id is None:
            raise ValueError("source_thread_id is required with source_message_id")
        if source_thread_id is None:
            return

        if source_message_id is None:
            statement = select(ChatThread.id).where(
                ChatThread.id == source_thread_id,
                ChatThread.user_id == user_id,
            )
        else:
            statement = (
                select(ChatMessage.id)
                .join(ChatThread, ChatThread.id == ChatMessage.thread_id)
                .where(
                    ChatMessage.id == source_message_id,
                    ChatMessage.thread_id == source_thread_id,
                    ChatThread.user_id == user_id,
                )
            )

        try:
            result = await self.db.execute(statement)
            source_id = result.scalar_one_or_none()
        except SQLAlchemyError as exc:
            await self.db.rollback()
            logger.exception("Provenance validation failed; transaction rolled back")
            raise PersistenceError("Could not validate memory provenance") from exc

        if source_id is None:
            raise ValueError("Memory provenance must belong to the memory owner")

    @staticmethod
    def _validated_embedding(embedding: Sequence[float]) -> list[float]:
        values = [float(value) for value in embedding]
        if len(values) != MEMORY_EMBEDDING_DIMENSIONS:
            raise ValueError(
                f"Memory embeddings must contain {MEMORY_EMBEDDING_DIMENSIONS} "
                f"values, got {len(values)}"
            )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("Memory embeddings must contain only finite values")
        if not any(value != 0.0 for value in values):
            raise ValueError("Memory embeddings cannot be a zero vector")
        return values
