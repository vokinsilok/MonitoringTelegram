from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.post import Post
from backend.app.schemas.post import PostCreate, PostUpdate


async def get_posts(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[Post]:
    """
    Получение списка постов с возможностью фильтрации.
    """
    query = select(Post)
    
    if filters:
        if "channel_id" in filters:
            query = query.where(Post.channel_id == filters["channel_id"])
        if "start_date" in filters and isinstance(filters["start_date"], datetime):
            query = query.where(Post.created_at >= filters["start_date"])
        if "end_date" in filters and isinstance(filters["end_date"], datetime):
            query = query.where(Post.created_at <= filters["end_date"])
    
    query = query.order_by(Post.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_post_by_id(db: AsyncSession, post_id: int) -> Optional[Post]:
    """
    Получение поста по ID.
    """
    query = select(Post).where(Post.id == post_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_post_by_telegram_id(db: AsyncSession, telegram_post_id: int, channel_id: int) -> Optional[Post]:
    """
    Получение поста по Telegram ID и ID канала.
    """
    query = select(Post).where(
        Post.telegram_post_id == telegram_post_id,
        Post.channel_id == channel_id
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_post(db: AsyncSession, post: PostCreate) -> Post:
    """
    Создание нового поста.
    """
    db_post = Post(
        channel_id=post.channel_id,
        telegram_post_id=post.telegram_post_id,
        content=post.content,
        media_urls=post.media_urls,
        created_at=post.created_at or datetime.now(),
        detected_keywords=post.detected_keywords,
    )
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    return db_post


async def update_post(db: AsyncSession, post_id: int, post: PostUpdate) -> Optional[Post]:
    """
    Обновление поста.
    """
    db_post = await get_post_by_id(db, post_id)
    if not db_post:
        return None
    
    update_data = post.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_post, key, value)
    
    await db.commit()
    await db.refresh(db_post)
    return db_post


async def delete_post(db: AsyncSession, post_id: int) -> Optional[Post]:
    """
    Удаление поста.
    """
    db_post = await get_post_by_id(db, post_id)
    if not db_post:
        return None
    
    await db.delete(db_post)
    await db.commit()
    return db_post


async def get_posts_with_keywords(db: AsyncSession, keywords: List[str], skip: int = 0, limit: int = 100) -> List[Post]:
    """
    Получение постов, содержащих указанные ключевые слова.
    """
    # Для PostgreSQL можно использовать оператор @> для проверки вхождения элементов в массив
    query = select(Post).where(Post.detected_keywords.overlap(keywords))
    query = query.order_by(Post.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
