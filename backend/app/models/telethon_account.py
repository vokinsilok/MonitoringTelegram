from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func

from backend.app.models.base import Base


class TelethonAccount(Base):
    """
    Модель для хранения данных аккаунта Telethon.
    Используется для мониторинга Telegram-каналов.
    Аккаунты не связаны с каналами напрямую, распределение происходит динамически.
    """
    __tablename__ = "telethon_account"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    api_id = Column(String, nullable=False)
    api_hash = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    description = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Дополнительные поля для отслеживания статуса аккаунта
    last_used = Column(DateTime(timezone=True), nullable=True)
    is_authorized = Column(Boolean, default=False)
    session_string = Column(String, nullable=True)  # Для хранения строки сессии после авторизации
    
    def __repr__(self):
        return f"<TelethonAccount {self.name} ({self.phone})>"
