from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class ChannelBase(BaseModel):
    """Базовая схема канала"""
    title: Optional[str] = None
    username: Optional[str] = None
    channel_id: Optional[str] = None
    url: Optional[str] = None
    is_active: bool = True
    description: Optional[str] = None


class ChannelCreate(ChannelBase):
    """Схема для создания канала"""
    pass


class ChannelUpdate(BaseModel):
    """Схема для обновления канала"""
    title: Optional[str] = None
    username: Optional[str] = None
    channel_id: Optional[str] = None
    url: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class ChannelInDB(ChannelBase):
    """Схема канала в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        orm_mode = True


class Channel(ChannelInDB):
    """Схема канала для API"""
    pass


class ChannelProposalBase(BaseModel):
    """Базовая схема предложения канала"""
    channel_url: str
    comment: str
    status: str = "pending"  # pending, approved, rejected


class ChannelProposalCreate(ChannelProposalBase):
    """Схема для создания предложения канала"""
    pass


class ChannelProposalUpdate(BaseModel):
    """Схема для обновления предложения канала"""
    status: Optional[str] = None
    admin_comment: Optional[str] = None


class ChannelProposalInDB(ChannelProposalBase):
    """Схема предложения канала в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int
    admin_id: Optional[int] = None
    admin_comment: Optional[str] = None

    class Config:
        orm_mode = True


class ChannelProposal(ChannelProposalInDB):
    """Схема предложения канала для API"""
    pass
