from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship

from backend.app.models.base import Base


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    ADMIN = "admin"
    OPERATOR = "operator"


class User(Base):
    """
    Модель пользователя системы.
    Может быть администратором или оператором.
    """
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String, index=True)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(String, default=UserRole.OPERATOR.value, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Отношения
    processed_posts = relationship("PostProcessing", back_populates="operator")
    proposed_channels = relationship("ChannelProposal", back_populates="operator")
    proposed_keywords = relationship("KeywordProposal", back_populates="operator")
    
    @property
    def is_admin(self) -> bool:
        """Проверка, является ли пользователь администратором"""
        return self.role == UserRole.ADMIN.value
    
    @property
    def full_name(self) -> str:
        """Полное имя пользователя"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.username:
            return self.username
        return str(self.telegram_id)
