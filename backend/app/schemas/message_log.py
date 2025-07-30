from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class MessageLogBase(BaseModel):
    """Базовая схема лога сообщений"""
    user_id: int
    message_text: str
    message_type: str  # incoming, outgoing
    direction: str  # bot_to_user, user_to_bot, system
    metadata: Optional[Dict[str, Any]] = None


class MessageLogCreate(MessageLogBase):
    """Схема для создания лога сообщений"""
    pass


class MessageLogInDB(MessageLogBase):
    """Схема лога сообщений в базе данных"""
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class MessageLog(MessageLogInDB):
    """Схема лога сообщений для API"""
    pass


class ReportBase(BaseModel):
    """Базовая схема отчета"""
    start_date: datetime
    end_date: datetime
    report_type: str  # posts, users, keywords
    filters: Optional[Dict[str, Any]] = None


class ReportCreate(ReportBase):
    """Схема для создания отчета"""
    pass


class ReportInDB(ReportBase):
    """Схема отчета в базе данных"""
    id: int
    created_at: datetime
    user_id: int
    result: Optional[Dict[str, Any]] = None
    status: str = "pending"  # pending, processing, completed, failed

    class Config:
        orm_mode = True


class Report(ReportInDB):
    """Схема отчета для API"""
    pass
