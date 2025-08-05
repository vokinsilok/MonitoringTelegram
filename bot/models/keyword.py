from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.db.database import Base


class KeywordType(str, Enum):
    """Типы ключевых слов"""
    WORD = "word"  # Отдельное слово
    PHRASE = "phrase"  # Фраза (несколько слов)
    REGEX = "regex"  # Регулярное выражение


class Keyword(Base):
    """
    Модель ключевого слова или фразы для мониторинга.
    """
    __tablename__ = "keyword"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False, index=True)
    type = Column(String, default=KeywordType.WORD.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Отношения
    post_matches = relationship("PostKeywordMatch", back_populates="keyword")
    proposals = relationship("KeywordProposal", back_populates="keyword")


class KeywordProposal(Base):
    """
    Модель предложения добавления нового ключевого слова от оператора.
    """
    __tablename__ = "keyword_proposal"
    
    id = Column(Integer, primary_key=True, index=True)
    keyword_id = Column(Integer, ForeignKey("keyword.id"), nullable=True)
    operator_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    text = Column(String, nullable=False)
    type = Column(String, default=KeywordType.WORD.value, nullable=False)
    status = Column(String, default="pending", nullable=False)  # pending, approved, rejected
    comment = Column(Text, nullable=True)  # Комментарий оператора
    admin_comment = Column(Text, nullable=True)  # Комментарий администратора
    
    # Отношения
    keyword = relationship("Keyword", back_populates="proposals")
    operator = relationship("User", back_populates="proposed_keywords")
