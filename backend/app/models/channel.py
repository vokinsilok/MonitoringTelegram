from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, BigInteger, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.app.models.base import Base


class ChannelStatus(str, Enum):
    """Статусы Telegram-каналов в системе"""
    ACTIVE = "active"  # Активный канал, мониторится
    PAUSED = "paused"  # Приостановлен, временно не мониторится
    DISABLED = "disabled"  # Отключен, не мониторится


class Channel(Base):
    """
    Модель Telegram-канала для мониторинга.
    """
    channel_id = Column(Integer, nullable=True)  # Telegram channel ID (может быть null для приватных каналов)
    username = Column(String, index=True, nullable=True)  # @username канала (может быть null)
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
    posts = relationship("Post", back_populates="channel")
    proposals = relationship("ChannelProposal", back_populates="channel")


class ChannelProposal(Base):
    """
    Модель предложения добавления нового канала от оператора.
    """
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=True)
    operator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    comment = Column(Text, nullable=True)  # Комментарий оператора
    admin_comment = Column(Text, nullable=True)  # Комментарий администратора
    
    # Отношения
    channel = relationship("Channel", back_populates="proposals")
    operator = relationship("User", back_populates="proposed_channels")


# Модель TelethonClient удалена, теперь используется только TelethonAccount из модуля telethon_account.py
