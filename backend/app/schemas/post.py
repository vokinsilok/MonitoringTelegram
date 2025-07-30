from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class PostBase(BaseModel):
    """Базовая схема поста"""
    channel_id: int
    message_id: int
    text: str
    published_at: datetime
    url: Optional[str] = None
    media_urls: Optional[List[str]] = None
    raw_data: Optional[Dict[str, Any]] = None


class PostCreate(PostBase):
    """Схема для создания поста"""
    pass


class PostUpdate(BaseModel):
    """Схема для обновления поста"""
    text: Optional[str] = None
    published_at: Optional[datetime] = None
    url: Optional[str] = None
    media_urls: Optional[List[str]] = None
    raw_data: Optional[Dict[str, Any]] = None


class PostInDB(PostBase):
    """Схема поста в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime
    matched_keywords: Optional[List[int]] = None

    class Config:
        orm_mode = True


class Post(PostInDB):
    """Схема поста для API"""
    pass


class PostProcessingBase(BaseModel):
    """Базовая схема обработки поста"""
    post_id: int
    status: str  # processed, postponed
    comment: str


class PostProcessingCreate(PostProcessingBase):
    """Схема для создания обработки поста"""
    pass


class PostProcessingUpdate(BaseModel):
    """Схема для обновления обработки поста"""
    status: Optional[str] = None
    comment: Optional[str] = None


class PostProcessingInDB(PostProcessingBase):
    """Схема обработки поста в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int

    class Config:
        orm_mode = True


class PostProcessing(PostProcessingInDB):
    """Схема обработки поста для API"""
    pass


class PostNotificationBase(BaseModel):
    """Базовая схема уведомления о посте"""
    post_id: int
    user_id: int
    message_id: Optional[int] = None  # ID сообщения в Telegram
    is_sent: bool = False
    is_read: bool = False
    is_deleted: bool = False


class PostNotificationCreate(PostNotificationBase):
    """Схема для создания уведомления о посте"""
    pass


class PostNotificationUpdate(BaseModel):
    """Схема для обновления уведомления о посте"""
    message_id: Optional[int] = None
    is_sent: Optional[bool] = None
    is_read: Optional[bool] = None
    is_deleted: Optional[bool] = None


class PostNotificationInDB(PostNotificationBase):
    """Схема уведомления о посте в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PostNotification(PostNotificationInDB):
    """Схема уведомления о посте для API"""
    pass
