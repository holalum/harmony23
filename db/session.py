from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from db.models import Base

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def init_db(database_url: str) -> None:
    """Инициализирует engine/session factory. Вызывается один раз при старте бота."""
    global _engine, _session_factory
    _engine = create_async_engine(database_url, future=True)
    _session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def create_all_tables() -> None:
    if _engine is None:
        raise RuntimeError("init_db() должен быть вызван до create_all_tables()")
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    if _session_factory is None:
        raise RuntimeError("init_db() должен быть вызван до get_session()")
    async with _session_factory() as session:
        yield session
