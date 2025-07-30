from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.message_log import MessageLog
from backend.app.schemas.message_log import MessageLogCreate


async def get_message_logs(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[MessageLog]:
    """
    Получение списка логов сообщений с возможностью фильтрации.
    """
    query = select(MessageLog)
    
    if filters:
        if "user_id" in filters:
            query = query.where(MessageLog.user_id == filters["user_id"])
        if "message_type" in filters:
            query = query.where(MessageLog.message_type == filters["message_type"])
        if "direction" in filters:
            query = query.where(MessageLog.direction == filters["direction"])
        if "start_date" in filters and isinstance(filters["start_date"], datetime):
            query = query.where(MessageLog.created_at >= filters["start_date"])
        if "end_date" in filters and isinstance(filters["end_date"], datetime):
            query = query.where(MessageLog.created_at <= filters["end_date"])
    
    query = query.order_by(MessageLog.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_message_log_by_id(db: AsyncSession, log_id: int) -> Optional[MessageLog]:
    """
    Получение лога сообщения по ID.
    """
    query = select(MessageLog).where(MessageLog.id == log_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_message_log(db: AsyncSession, log: MessageLogCreate) -> MessageLog:
    """
    Создание нового лога сообщения.
    """
    db_log = MessageLog(
        user_id=log.user_id,
        message_type=log.message_type,
        message_text=log.message_text,
        direction=log.direction,
        telegram_message_id=log.telegram_message_id,
        created_at=datetime.now(),
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log


async def get_user_message_history(
    db: AsyncSession,
    user_id: int,
    limit: int = 100,
    message_type: Optional[str] = None
) -> List[MessageLog]:
    """
    Получение истории сообщений пользователя.
    """
    query = select(MessageLog).where(MessageLog.user_id == user_id)
    
    if message_type:
        query = query.where(MessageLog.message_type == message_type)
    
    query = query.order_by(MessageLog.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())
