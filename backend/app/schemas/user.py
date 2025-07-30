from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr


class UserBase(BaseModel):
    """Базовая схема пользователя"""
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: bool = False
    is_active: bool = True


class UserCreate(UserBase):
    """Схема для создания пользователя"""
    pass


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserInDB(UserBase):
    """Схема пользователя в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class User(UserInDB):
    """Схема пользователя для API"""
    pass
