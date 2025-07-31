from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import NullPool

from backend.app.core.config import settings

# Создаем асинхронный движок SQLAlchemy с пулом соединений
engine = create_async_engine(
    settings.db_url,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=20,
    pool_timeout=60,
    pool_pre_ping=True,
    connect_args={"server_settings": {"client_encoding": "utf8"}}
)

# Создаем асинхронный движок без пула соединений
engine_null_pool = create_async_engine(
    settings.db_url, 
    poolclass=NullPool,
    connect_args={"server_settings": {"client_encoding": "utf8"}}
)

# Создаем фабрики сессий
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
async_session_maker_null_pool = async_sessionmaker(bind=engine_null_pool, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Зависимость для получения сессии базы данных.
    Используется в FastAPI endpoint-ах.
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
