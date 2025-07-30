from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.post import PostProcessing, PostNotification
from backend.app.schemas.post import PostProcessingCreate, PostNotificationCreate


async def get_post_processings(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[PostProcessing]:
    """
    Получение списка обработок постов с возможностью фильтрации.
    """
    query = select(PostProcessing)
    
    if filters:
        if "post_id" in filters:
            query = query.where(PostProcessing.post_id == filters["post_id"])
        if "user_id" in filters:
            query = query.where(PostProcessing.user_id == filters["user_id"])
        if "status" in filters:
            query = query.where(PostProcessing.status == filters["status"])
    
    query = query.order_by(PostProcessing.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_post_processing_by_id(db: AsyncSession, processing_id: int) -> Optional[PostProcessing]:
    """
    Получение обработки поста по ID.
    """
    query = select(PostProcessing).where(PostProcessing.id == processing_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_post_processing(db: AsyncSession, processing: PostProcessingCreate) -> PostProcessing:
    """
    Создание новой обработки поста.
    """
    db_processing = PostProcessing(
        post_id=processing.post_id,
        user_id=processing.user_id,
        status=processing.status,
        comment=processing.comment,
        created_at=datetime.now(),
    )
    db.add(db_processing)
    await db.commit()
    await db.refresh(db_processing)
    return db_processing


# Функции для работы с уведомлениями о постах
async def get_post_notifications(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[PostNotification]:
    """
    Получение списка уведомлений о постах с возможностью фильтрации.
    """
    query = select(PostNotification)
    
    if filters:
        if "post_id" in filters:
            query = query.where(PostNotification.post_id == filters["post_id"])
        if "user_id" in filters:
            query = query.where(PostNotification.user_id == filters["user_id"])
        if "is_sent" in filters:
            query = query.where(PostNotification.is_sent == filters["is_sent"])
        if "is_read" in filters:
            query = query.where(PostNotification.is_read == filters["is_read"])
        if "is_deleted" in filters:
            query = query.where(PostNotification.is_deleted == filters["is_deleted"])
    
    query = query.order_by(PostNotification.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_post_notification_by_id(db: AsyncSession, notification_id: int) -> Optional[PostNotification]:
    """
    Получение уведомления о посте по ID.
    """
    query = select(PostNotification).where(PostNotification.id == notification_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_post_notification(db: AsyncSession, notification: PostNotificationCreate) -> PostNotification:
    """
    Создание нового уведомления о посте.
    """
    db_notification = PostNotification(
        post_id=notification.post_id,
        user_id=notification.user_id,
        message_id=notification.message_id,
        is_sent=notification.is_sent,
        is_read=notification.is_read,
        is_deleted=notification.is_deleted,
        created_at=datetime.now(),
    )
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    return db_notification


async def update_post_notification(db: AsyncSession, notification_id: int, notification: dict) -> Optional[PostNotification]:
    """
    Обновление уведомления о посте.
    """
    db_notification = await get_post_notification_by_id(db, notification_id)
    if not db_notification:
        return None
    
    for key, value in notification.items():
        if hasattr(db_notification, key):
            setattr(db_notification, key, value)
    
    await db.commit()
    await db.refresh(db_notification)
    return db_notification


async def delete_post_notification(db: AsyncSession, notification_id: int) -> Optional[PostNotification]:
    """
    Удаление уведомления о посте.
    """
    db_notification = await get_post_notification_by_id(db, notification_id)
    if not db_notification:
        return None
    
    await db.delete(db_notification)
    await db.commit()
    return db_notification


async def mark_notification_as_read(db: AsyncSession, notification_id: int) -> Optional[PostNotification]:
    """
    Отметить уведомление как прочитанное.
    """
    db_notification = await get_post_notification_by_id(db, notification_id)
    if not db_notification:
        return None
    
    db_notification.is_read = True
    await db.commit()
    await db.refresh(db_notification)
    return db_notification


async def mark_notification_as_deleted(db: AsyncSession, notification_id: int) -> Optional[PostNotification]:
    """
    Отметить уведомление как удаленное.
    """
    db_notification = await get_post_notification_by_id(db, notification_id)
    if not db_notification:
        return None
    
    db_notification.is_deleted = True
    await db.commit()
    await db.refresh(db_notification)
    return db_notification


async def delete_similar_notifications(db: AsyncSession, post_id: int, exclude_user_id: int) -> int:
    """
    Удаление аналогичных уведомлений у других пользователей.
    Возвращает количество удаленных уведомлений.
    """
    query = select(PostNotification).where(
        PostNotification.post_id == post_id,
        PostNotification.user_id != exclude_user_id,
        PostNotification.is_deleted == False
    )
    result = await db.execute(query)
    notifications = list(result.scalars().all())
    
    count = 0
    for notification in notifications:
        notification.is_deleted = True
        count += 1
    
    await db.commit()
    return count
