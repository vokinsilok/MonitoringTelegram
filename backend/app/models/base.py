from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, func
from sqlalchemy.ext.declarative import as_declarative, declared_attr


@as_declarative()
class Base:
    """
    Базовый класс для всех моделей SQLAlchemy.
    Автоматически добавляет имя таблицы и колонки id.
    """
    id: Any
    __name__: str
    
    # Автоматически генерируем имя таблицы из имени класса
    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()
    
    # Общие колонки для всех таблиц
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
