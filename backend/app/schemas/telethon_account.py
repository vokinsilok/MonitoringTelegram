from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TelethonAccountBase(BaseModel):
    """Базовая схема для аккаунта Telethon"""
    name: str = Field(..., description="Название аккаунта для идентификации")
    description: Optional[str] = Field(None, description="Описание аккаунта")
    is_active: bool = Field(True, description="Активен ли аккаунт")


class TelethonAccountCreate(TelethonAccountBase):
    """Схема для создания аккаунта Telethon"""
    api_id: str = Field(..., description="API ID от Telegram")
    api_hash: str = Field(..., description="API Hash от Telegram")
    phone: str = Field(..., description="Номер телефона аккаунта Telegram")


class TelethonAccountUpdate(BaseModel):
    """Схема для обновления аккаунта Telethon"""
    name: Optional[str] = Field(None, description="Название аккаунта для идентификации")
    api_id: Optional[str] = Field(None, description="API ID от Telegram")
    api_hash: Optional[str] = Field(None, description="API Hash от Telegram")
    phone: Optional[str] = Field(None, description="Номер телефона аккаунта Telegram")
    description: Optional[str] = Field(None, description="Описание аккаунта")
    is_active: Optional[bool] = Field(None, description="Активен ли аккаунт")


class TelethonAccountInDB(TelethonAccountBase):
    """Схема для аккаунта Telethon из БД"""
    id: int
    api_id: str
    api_hash: str
    phone: str
    is_authorized: bool = False
    last_used: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode = True


class TelethonAccountResponse(TelethonAccountInDB):
    """Схема для ответа с аккаунтом Telethon"""
    pass


class TelethonAccountListResponse(BaseModel):
    """Схема для ответа со списком аккаунтов Telethon"""
    total: int
    items: list[TelethonAccountResponse]

    class Config:
        orm_mode = True
