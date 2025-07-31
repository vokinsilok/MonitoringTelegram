from typing import List, Optional, Dict, Any, Tuple, Set
from datetime import datetime
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.post import Post, PostProcessing, PostKeywordMatch
from backend.app.models.keyword import Keyword
from backend.app.schemas.post import PostProcessingCreate, PostNotificationCreate, PostNotification


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


async def process_post_with_keywords(db: AsyncSession, post_id: int) -> Tuple[bool, Set[int], List[PostKeywordMatch]]:
    """
    Обработка поста с ключевыми словами.
    
    Проверяет содержимое поста на наличие ключевых слов и создает соответствующие записи PostKeywordMatch.
    
    Args:
        db: Асинхронная сессия базы данных
        post_id: ID поста для обработки
        
    Returns:
        Tuple содержащий:
        - bool: True, если найдены совпадения с ключевыми словами
        - Set[int]: Набор ID ключевых слов, которые были найдены в посте
        - List[PostKeywordMatch]: Список созданных объектов PostKeywordMatch
    """
    # Получаем пост из базы данных
    post_query = select(Post).where(Post.id == post_id)
    post_result = await db.execute(post_query)
    post = post_result.scalar_one_or_none()
    
    if not post:
        return False, set(), []
    
    # Получаем все активные ключевые слова
    keywords_query = select(Keyword).where(Keyword.is_active == True)
    keywords_result = await db.execute(keywords_query)
    keywords = list(keywords_result.scalars().all())
    
    # Проверяем наличие ключевых слов в тексте поста
    matched_keywords = []
    matched_keyword_ids = set()
    post_content = post.content.lower() if post.content else ""
    
    for keyword in keywords:
        keyword_text = keyword.text.lower()
        if keyword_text in post_content:
            # Создаем запись о совпадении
            match = PostKeywordMatch(
                post_id=post.id,
                keyword_id=keyword.id,
                created_at=datetime.now()
            )
            db.add(match)
            matched_keywords.append(match)
            matched_keyword_ids.add(keyword.id)
    
    if matched_keywords:
        await db.commit()
        # Обновляем все объекты после коммита
        for match in matched_keywords:
            await db.refresh(match)
    
    return bool(matched_keywords), matched_keyword_ids, matched_keywords
