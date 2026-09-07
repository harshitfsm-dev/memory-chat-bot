from datetime import datetime

from app.db.unit_of_work import UnitOfWork
from app.models.user_memory import MEMORY_TYPE_EPISODE, MEMORY_TYPE_FACT
from app.repositories.user_memory_repository import UserMemoryRepository
from app.schemas.user_memory import MemoryItemResponse, UserMemoriesResponse


class MemoryNotFoundError(LookupError):
    """Raised when an active memory is absent or not owned by the caller."""


class MemoryChangedError(RuntimeError):
    """Raised when a memory changed after it was displayed to the user."""


class UserMemoryControlService:
    """Expose deterministic, ownership-safe memory management operations."""

    def __init__(
        self,
        repository: UserMemoryRepository,
        uow: UnitOfWork,
    ) -> None:
        self.repository = repository
        self.uow = uow

    async def list_active(self, *, user_id: str) -> UserMemoriesResponse:
        """Return the user's active facts and episodes without internal fields."""
        try:
            rows = await self.repository.get_all_active(user_id=user_id)
            facts = [
                MemoryItemResponse.model_validate(memory)
                for memory in rows
                if memory.memory_type == MEMORY_TYPE_FACT
            ]
            episodes = [
                MemoryItemResponse.model_validate(memory)
                for memory in rows
                if memory.memory_type == MEMORY_TYPE_EPISODE
            ]
            response = UserMemoriesResponse(facts=facts, episodes=episodes)
            # End the read transaction so the pooled connection is released.
            await self.uow.commit()
            return response
        except Exception:
            await self.uow.rollback()
            raise

    async def forget(
        self,
        *,
        memory_id: str,
        user_id: str,
        expected_updated_at: datetime,
    ) -> None:
        """Deactivate the exact memory version the user confirmed."""
        try:
            deactivated = await self.repository.deactivate_owned(
                memory_id,
                user_id,
                expected_updated_at=expected_updated_at,
            )
            if not deactivated:
                changed = await self.repository.active_owned_exists(
                    memory_id=memory_id,
                    user_id=user_id,
                )
                await self.uow.rollback()
                if changed:
                    raise MemoryChangedError(memory_id)
                raise MemoryNotFoundError(memory_id)
            await self.uow.commit()
        except (MemoryChangedError, MemoryNotFoundError):
            raise
        except Exception:
            await self.uow.rollback()
            raise
