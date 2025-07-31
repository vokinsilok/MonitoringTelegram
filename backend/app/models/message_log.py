from enum import Enum
from typing import List, Optional
from datetime import datetime

from sqlalchemy import Column, ForeignKey, Integer, String, Text, JSON, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

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
    __tablename__ = "message_log"
    
    id = Column(Integer, primary_key=True, index=True)
    recipient_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("user.id"), nullable=True)  # Может быть null, если отправитель - система
    message_type = Column(String, nullable=False)
    content = Column(Text, nullable=False)  # Текст сообщения
    meta_data = Column(JSON, nullable=True)  # Дополнительные данные (в формате JSON)
    
    # Связи с другими сущностями (опционально)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=True)
    channel_proposal_id = Column(Integer, ForeignKey("channel_proposal.id"), nullable=True)
    keyword_proposal_id = Column(Integer, ForeignKey("keyword_proposal.id"), nullable=True)
    
    # Отношения
    recipient = relationship("User", foreign_keys=[recipient_id])
    sender = relationship("User", foreign_keys=[sender_id])
    post = relationship("Post", foreign_keys=[post_id])
    channel_proposal = relationship("ChannelProposal", foreign_keys=[channel_proposal_id])
    keyword_proposal = relationship("KeywordProposal", foreign_keys=[keyword_proposal_id])


class Report(Base):
    """
    Модель для хранения отчетов в системе.
    """
    __tablename__ = "report"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    report_type = Column(String, nullable=False)  # posts, users, keywords
    parameters = Column(JSON, nullable=True)  # Параметры отчета в формате JSON
    status = Column(String, default="pending", nullable=False)  # pending, processing, completed, failed
    result_file_path = Column(String, nullable=True)  # Путь к файлу с результатом отчета
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Отношения
    user = relationship("User", foreign_keys=[user_id])
