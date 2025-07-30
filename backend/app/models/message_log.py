from enum import Enum
from typing import List, Optional

from sqlalchemy import Column, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from backend.app.models.base import Base


class MessageType(str, Enum):
    """Типы сообщений в системе"""
    NOTIFICATION = "notification"  # Уведомление
    POST = "post"  # Пост из канала
    PROPOSAL = "proposal"  # Предложение (канала или ключевого слова)
    REPORT = "report"  # Отчет


class MessageLog(Base):
    """
    Модель для логирования всех отправленных сообщений в системе.
    """
    recipient_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=True)  # Может быть null, если отправитель - система
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)  # Текст сообщения
    metadata = Column(JSON, nullable=True)  # Дополнительные данные (в формате JSON)
    
    # Связи с другими сущностями (опционально)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=True)
    channel_proposal_id = Column(Integer, ForeignKey("channelproposal.id"), nullable=True)
    keyword_proposal_id = Column(Integer, ForeignKey("keywordproposal.id"), nullable=True)
    
    # Отношения
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])
    post = relationship("Post", foreign_keys=[post_id])
    channel_proposal = relationship("ChannelProposal", foreign_keys=[channel_proposal_id])
    keyword_proposal = relationship("KeywordProposal", foreign_keys=[keyword_proposal_id])
