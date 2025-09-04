from enum import Enum

from sqlalchemy import Boolean, String, BigInteger, Integer, ForeignKey
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
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, index=True)
    first_name: Mapped[str] = mapped_column(String)
    last_name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String, default=UserRole.OPERATOR.value, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_operator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Отношения
    proposed_channels = relationship("ChannelProposal", back_populates="operator")
    proposed_keywords = relationship("KeywordProposal", back_populates="operator")
    processed_posts = relationship("PostProcessing", back_populates="operator")
    postponed_posts = relationship("Postponed", back_populates="operator")
    # Новая связь с настройками пользователя (1:1)
    settings = relationship("UserSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

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


class TimeZone(str, Enum):
    """Временные зоны"""
    UTC = "UTC"
    MSK = "MSK"
    EST = "EST"
    PST = "PST"
    CET = "CET"
    IST = "IST"
    GMT = "GMT"


class Language(str, Enum):
    """Языки интерфейса"""
    EN = "en"
    RU = "ru"
    ES = "es"
    FR = "fr"
    DE = "de"
    CN = "cn"
    JP = "jp"


class UserSettings(Base):
    """
    Модель настроек пользователя.
    Хранит настройки уведомлений и другие пользовательские предпочтения.
    """
    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Привязываем к user.id и используем совместимый тип Integer
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("user.id"), nullable=False, unique=True)
    time_zone: Mapped[str] = mapped_column(String, default=TimeZone.GMT.value, nullable=False)
    language: Mapped[str] = mapped_column(String, default=Language.RU.value, nullable=False)

    # Отношение к пользователю
    user = relationship("User", back_populates="settings", uselist=False)


class UserWhiteList(Base):
    """
    Модель белого списка пользователей.
    Хранит Telegram ID пользователей, которым разрешен доступ к системе.
    """
    __tablename__ = "user_whitelist"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, index=True, nullable=True)
