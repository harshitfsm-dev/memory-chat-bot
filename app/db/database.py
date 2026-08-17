from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


SessionFactory = async_sessionmaker[AsyncSession]


def create_database(
    database_url: str,
    *,
    echo: bool = False,
) -> tuple[AsyncEngine, SessionFactory]:
    engine = create_async_engine(database_url, echo=echo)
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return engine, session_factory


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: SessionFactory = request.app.state.session_factory
    async with session_factory() as session:
        yield session
