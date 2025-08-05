from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.database import Base


class ChannelStatus(str, Enum):
    """Статусы Telegram-каналов в системе"""
    ACTIVE = "active"  # Активный канал, мониторится
    PAUSED = "paused"  # Приостановлен, временно не мониторится
    DISABLED = "disabled"  # Отключен, не мониторится


class ProposalStatus(str, Enum):
    """Статусы предложений каналов от операторов"""
    PENDING = "pending"  # Ожидает рассмотрения
    APPROVED = "approved"  # Одобрено администратором
    REJECTED = "rejected"  # Отклонено администратором


class Channel(Base):
    """
    Модель Telegram-канала для мониторинга.
    """
    __tablename__ = "channel"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_username = Column(String, index=True, nullable=True)  # @username канала (может быть null)
    title = Column(String, nullable=False)  # Название канала
    invite_link = Column(String, nullable=True)  # Ссылка-приглашение для приватных каналов
    status = Column(String, default=ChannelStatus.ACTIVE.value, nullable=False)
    description = Column(Text, nullable=True)  # Описание канала
    is_private = Column(Boolean, default=False, nullable=False)  # Приватный ли канал
    
    # ID последнего обработанного сообщения из канала
    last_parsed_message_id = Column(BigInteger, nullable=True)
    
    # Время последней проверки канала
    last_checked = Column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    # posts = relationship("Post", back_populates="channel")


class ChannelProposal(Base):
    """
    Модель предложения добавления нового канала от оператора.
    """
    __tablename__ = "channel_proposal"
    
    id = Column(Integer, primary_key=True, index=True)

    channel_username = Column(String, nullable=True)  # @username канала (если есть)
    operator_id = Column(BigInteger, ForeignKey("user.telegram_id"), nullable=False)
    status = Column(String, default=ProposalStatus.PENDING.value, nullable=False)  # pending, approved, rejected
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=True)  # ID созданного канала (если одобрено)
    comment = Column(Text, nullable=True)  # Комментарий оператора
    admin_comment = Column(Text, nullable=True)  # Комментарий администратора
    
    # Отношения
    operator = relationship("User", back_populates="proposed_channels")


# Модель TelethonClient удалена, теперь используется только TelethonAccount из модуля telethon_account.py
