from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings
from sqlalchemy import NullPool

DATABASE_URL = settings.db_url
engine = create_async_engine(
    DATABASE_URL,
    pool_size=5,  # Увеличиваем размер пула для 8 воркеров (5 * 8 = 40 базовых соединений)
    max_overflow=8,  # Увеличиваем максимальное переполнение (8 * 8 = 64 дополнительных соединений)
    pool_timeout=30,  # Увеличиваем время ожидания соединения
    pool_pre_ping=True,  # Проверка соединения перед использованием
    pool_recycle=300,  # Переиспользование соединений каждые 5 минут
    echo=False,  # Отключаем вывод SQL запросов в лог
    connect_args={"server_settings": {"client_encoding": "utf8"}}
)
engine_null_pool = create_async_engine(DATABASE_URL, poolclass=NullPool,
                                       connect_args={"server_settings": {"client_encoding": "utf8"}})
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
async_session_maker_null_pool = async_sessionmaker(bind=engine_null_pool, expire_on_commit=False)


class Base(DeclarativeBase):
    pass
