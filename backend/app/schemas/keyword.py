from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class KeywordBase(BaseModel):
    """Базовая схема ключевого слова"""
    text: str
    type: str  # word, phrase, regex
    is_active: bool = True
    description: Optional[str] = None


class KeywordCreate(KeywordBase):
    """Схема для создания ключевого слова"""
    pass


class KeywordUpdate(BaseModel):
    """Схема для обновления ключевого слова"""
    text: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class KeywordInDB(KeywordBase):
    """Схема ключевого слова в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        orm_mode = True


class Keyword(KeywordInDB):
    """Схема ключевого слова для API"""
    pass


class KeywordProposalBase(BaseModel):
    """Базовая схема предложения ключевого слова"""
    text: str
    type: str  # word, phrase, regex
    comment: str
    status: str = "pending"  # pending, approved, rejected


class KeywordProposalCreate(KeywordProposalBase):
    """Схема для создания предложения ключевого слова"""
    pass


class KeywordProposalUpdate(BaseModel):
    """Схема для обновления предложения ключевого слова"""
    status: Optional[str] = None
    admin_comment: Optional[str] = None


class KeywordProposalInDB(KeywordProposalBase):
    """Схема предложения ключевого слова в базе данных"""
    id: int
    created_at: datetime
    updated_at: datetime
    user_id: int
    admin_id: Optional[int] = None
    admin_comment: Optional[str] = None

    class Config:
        orm_mode = True


class KeywordProposal(KeywordProposalInDB):
    """Схема предложения ключевого слова для API"""
    pass
