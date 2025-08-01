from enum import Enum
from typing import List, Optional

from sqlalchemy import Boolean, Column, Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.db.database import Base


class UserRole(str, Enum):
    """Роли пользователей в системе"""
    ADMIN = "admin"
    OPERATOR = "operator"
    USER = "user"


class User(Base):
    """
    Модель пользователя системы.
    Может быть администратором или оператором.
    """
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default=UserRole.OPERATOR.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_operator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


    @property
    def is_admin_role(self) -> bool:
        """Проверка, является ли пользователь администратором по роли"""
        return self.role == UserRole.ADMIN.value

    @property
    def is_operator_role(self) -> bool:
        """Проверка, является ли пользователь оператором по роли"""
        return self.role == UserRole.OPERATOR.value

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
