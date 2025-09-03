from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, BigInteger
from sqlalchemy.orm import relationship

from app.db.database import Base


class PostStatus(str, Enum):
    """Статусы обработки постов"""
    PENDING = "pending"  # Ожидает обработки
    PROCESSED = "processed"  # Обработан
    POSTPONED = "postponed"  # Отложен
    IGNORED = "ignored"  # Игнорирован
     # Отменен


class Post(Base):
    """
    Модель поста из Telegram-канала.
    """
    __tablename__ = "post"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channel.id"), nullable=False)
    message_id = Column(Integer, nullable=False)  # ID сообщения в Telegram
    text = Column(Text, nullable=True)  # Текст поста
    html_text = Column(Text, nullable=True)  # HTML-форматированный текст поста
    media_type = Column(String, nullable=True)  # Тип медиа (photo, video, document, etc.)
    media_file_id = Column(String, nullable=True)  # ID медиа-файла в Telegram
    published_at = Column(DateTime(timezone=True), nullable=False)  # Дата публикации в канале
    url = Column(String, nullable=True)  # URL поста в канале
    
    # Отношения
    channel = relationship("Channel", back_populates="posts")
    matched_keywords = relationship("PostKeywordMatch", back_populates="post")
    processing_records = relationship("PostProcessing", back_populates="post")


class PostKeywordMatch(Base):
    """
    Модель для связи постов с ключевыми словами, которые были найдены в посте.
    """
    __tablename__ = "post_keyword_match"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    keyword_id = Column(Integer, ForeignKey("keyword.id"), nullable=False)
    
    # Отношения
    post = relationship("Post", back_populates="matched_keywords")
    keyword = relationship("Keyword", back_populates="post_matches")


class PostProcessing(Base):
    """
    Модель для хранения информации об обработке поста оператором.
    """
    __tablename__ = "post_processing"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    status = Column(String, default=PostStatus.PENDING.value, nullable=False)
    comment = Column(Text, nullable=True)  # Комментарий оператора
    processed_at = Column(DateTime(timezone=True), nullable=True)  # Дата обработки
    
    # Данные отправленного уведомления (для последующего удаления)
    notify_chat_id = Column(BigInteger, nullable=True)
    notify_message_id = Column(Integer, nullable=True)
    notify_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Отношения
    post = relationship("Post", back_populates="processing_records")
    operator = relationship("User", back_populates="processed_posts")


class Postponed(Base):
    """
    Модель для хранения отложенных постов, которые нужно будет обработать позже.
    """
    __tablename__ = "postponed"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("post.id"), nullable=False)
    operator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    at_postpone = Column(DateTime(timezone=True), nullable=False)  # Время отложения
    reason = Column(Text, nullable=True)  # Причина отложения

    # Отношения
    post = relationship("Post")
    operator = relationship("User", back_populates="postponed_posts")