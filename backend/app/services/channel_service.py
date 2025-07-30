from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.channel import Channel
from backend.app.schemas.channel import ChannelCreate, ChannelUpdate


async def get_channels(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[Channel]:
    """
    Получение списка каналов с возможностью фильтрации.
    """
    query = select(Channel)
    
    if filters:
        if "is_active" in filters:
            query = query.where(Channel.is_active == filters["is_active"])
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_channel_by_id(db: AsyncSession, channel_id: int) -> Optional[Channel]:
    """
    Получение канала по ID.
    """
    query = select(Channel).where(Channel.id == channel_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_channel_by_username(db: AsyncSession, username: str) -> Optional[Channel]:
    """
    Получение канала по username.
    """
    query = select(Channel).where(Channel.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_channel(db: AsyncSession, channel: ChannelCreate) -> Channel:
    """
    Создание нового канала.
    """
    db_channel = Channel(
        title=channel.title,
        username=channel.username,
        channel_id=channel.channel_id,
        description=channel.description,
        is_active=channel.is_active,
        added_by_user_id=channel.added_by_user_id,
    )
    db.add(db_channel)
    await db.commit()
    await db.refresh(db_channel)
    return db_channel


async def update_channel(db: AsyncSession, channel_id: int, channel: ChannelUpdate) -> Optional[Channel]:
    """
    Обновление канала.
    """
    db_channel = await get_channel_by_id(db, channel_id)
    if not db_channel:
        return None
    
    update_data = channel.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_channel, key, value)
    
    await db.commit()
    await db.refresh(db_channel)
    return db_channel


async def delete_channel(db: AsyncSession, channel_id: int) -> Optional[Channel]:
    """
    Удаление канала.
    """
    db_channel = await get_channel_by_id(db, channel_id)
    if not db_channel:
        return None
    
    await db.delete(db_channel)
    await db.commit()
    return db_channel


async def set_channel_active_status(db: AsyncSession, channel_id: int, is_active: bool) -> Optional[Channel]:
    """
    Изменение статуса активности канала.
    """
    db_channel = await get_channel_by_id(db, channel_id)
    if not db_channel:
        return None
    
    db_channel.is_active = is_active
    await db.commit()
    await db.refresh(db_channel)
    return db_channel
