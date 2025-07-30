from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.keyword import Keyword
from backend.app.schemas.keyword import KeywordCreate, KeywordUpdate


async def get_keywords(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[Keyword]:
    """
    Получение списка ключевых слов с возможностью фильтрации.
    """
    query = select(Keyword)
    
    if filters:
        if "is_active" in filters:
            query = query.where(Keyword.is_active == filters["is_active"])
        if "type" in filters:
            query = query.where(Keyword.type == filters["type"])
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_keyword_by_id(db: AsyncSession, keyword_id: int) -> Optional[Keyword]:
    """
    Получение ключевого слова по ID.
    """
    query = select(Keyword).where(Keyword.id == keyword_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_active_keywords(db: AsyncSession) -> List[Keyword]:
    """
    Получение всех активных ключевых слов.
    """
    query = select(Keyword).where(Keyword.is_active == True)
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_keyword(db: AsyncSession, keyword: KeywordCreate) -> Keyword:
    """
    Создание нового ключевого слова.
    """
    db_keyword = Keyword(
        word=keyword.word,
        type=keyword.type,
        is_active=keyword.is_active,
        added_by_user_id=keyword.added_by_user_id,
    )
    db.add(db_keyword)
    await db.commit()
    await db.refresh(db_keyword)
    return db_keyword


async def update_keyword(db: AsyncSession, keyword_id: int, keyword: KeywordUpdate) -> Optional[Keyword]:
    """
    Обновление ключевого слова.
    """
    db_keyword = await get_keyword_by_id(db, keyword_id)
    if not db_keyword:
        return None
    
    update_data = keyword.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_keyword, key, value)
    
    await db.commit()
    await db.refresh(db_keyword)
    return db_keyword


async def delete_keyword(db: AsyncSession, keyword_id: int) -> Optional[Keyword]:
    """
    Удаление ключевого слова.
    """
    db_keyword = await get_keyword_by_id(db, keyword_id)
    if not db_keyword:
        return None
    
    await db.delete(db_keyword)
    await db.commit()
    return db_keyword


async def set_keyword_active_status(db: AsyncSession, keyword_id: int, is_active: bool) -> Optional[Keyword]:
    """
    Изменение статуса активности ключевого слова.
    """
    db_keyword = await get_keyword_by_id(db, keyword_id)
    if not db_keyword:
        return None
    
    db_keyword.is_active = is_active
    await db.commit()
    await db.refresh(db_keyword)
    return db_keyword
