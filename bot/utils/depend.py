from typing import AsyncGenerator
from contextlib import asynccontextmanager
from app.db.database import async_session_maker, async_session_maker_null_pool
from bot.utils.db_manager import DBManager


@asynccontextmanager
async def get_atomic_db():
    async with DBManager(session_factory=async_session_maker) as db:
        async with db.transaction():
            yield db


@asynccontextmanager
async def get_atomic_db_null_pull() -> AsyncGenerator[DBManager, None]:
    async with DBManager(session_factory=async_session_maker_null_pool) as db:
        async with db.transaction():
            yield db