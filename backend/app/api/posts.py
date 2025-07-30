from typing import List, Optional, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.post import Post
from backend.app.schemas.post import (
    Post as PostSchema,
    PostCreate,
    PostUpdate,
    PostProcessing as PostProcessingSchema,
    PostProcessingCreate,
    PostNotification as PostNotificationSchema,
)
from backend.app.services.post_service import (
    get_posts,
    get_post_by_id,
    create_post,
    update_post,
    delete_post,
)
from backend.app.services.post_processing_service import (
    get_post_processings,
    get_post_processing_by_id,
    create_post_processing,
    get_post_notifications,
    get_post_notification_by_id,
    create_post_notification,
    update_post_notification,
    delete_post_notification,
)

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("/", response_model=List[PostSchema])
async def read_posts(
    skip: int = 0,
    limit: int = 100,
    channel_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список постов с возможностью фильтрации.
    """
    filters = {}
    if channel_id is not None:
        filters["channel_id"] = channel_id
    if start_date is not None:
        filters["start_date"] = start_date
    if end_date is not None:
        filters["end_date"] = end_date
        
    posts = await get_posts(db, skip=skip, limit=limit, filters=filters)
    return posts


@router.get("/{post_id}", response_model=PostSchema)
async def read_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить пост по ID.
    """
    post = await get_post_by_id(db, post_id=post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@router.post("/", response_model=PostSchema, status_code=status.HTTP_201_CREATED)
async def create_post_api(
    post: PostCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новый пост.
    """
    return await create_post(db=db, post=post)


@router.put("/{post_id}", response_model=PostSchema)
async def update_post_api(
    post_id: int,
    post: PostUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить пост.
    """
    db_post = await get_post_by_id(db, post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return await update_post(db=db, post_id=post_id, post=post)


@router.delete("/{post_id}", response_model=PostSchema)
async def delete_post_api(
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить пост.
    """
    db_post = await get_post_by_id(db, post_id=post_id)
    if db_post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return await delete_post(db=db, post_id=post_id)


# Маршруты для обработки постов
@router.get("/processings/", response_model=List[PostProcessingSchema])
async def read_post_processings(
    skip: int = 0,
    limit: int = 100,
    post_id: Optional[int] = None,
    user_id: Optional[int] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список обработок постов с возможностью фильтрации.
    """
    filters = {}
    if post_id is not None:
        filters["post_id"] = post_id
    if user_id is not None:
        filters["user_id"] = user_id
    if status is not None:
        filters["status"] = status
        
    processings = await get_post_processings(db, skip=skip, limit=limit, filters=filters)
    return processings


@router.get("/processings/{processing_id}", response_model=PostProcessingSchema)
async def read_post_processing(
    processing_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить обработку поста по ID.
    """
    processing = await get_post_processing_by_id(db, processing_id=processing_id)
    if processing is None:
        raise HTTPException(status_code=404, detail="Post processing not found")
    return processing


@router.post("/processings/", response_model=PostProcessingSchema, status_code=status.HTTP_201_CREATED)
async def create_post_processing_api(
    processing: PostProcessingCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новую обработку поста.
    """
    return await create_post_processing(db=db, processing=processing)


# Маршруты для уведомлений о постах
@router.get("/notifications/", response_model=List[PostNotificationSchema])
async def read_post_notifications(
    skip: int = 0,
    limit: int = 100,
    post_id: Optional[int] = None,
    user_id: Optional[int] = None,
    is_sent: Optional[bool] = None,
    is_read: Optional[bool] = None,
    is_deleted: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список уведомлений о постах с возможностью фильтрации.
    """
    filters = {}
    if post_id is not None:
        filters["post_id"] = post_id
    if user_id is not None:
        filters["user_id"] = user_id
    if is_sent is not None:
        filters["is_sent"] = is_sent
    if is_read is not None:
        filters["is_read"] = is_read
    if is_deleted is not None:
        filters["is_deleted"] = is_deleted
        
    notifications = await get_post_notifications(db, skip=skip, limit=limit, filters=filters)
    return notifications


@router.get("/notifications/{notification_id}", response_model=PostNotificationSchema)
async def read_post_notification(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить уведомление о посте по ID.
    """
    notification = await get_post_notification_by_id(db, notification_id=notification_id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Post notification not found")
    return notification


@router.post("/notifications/", response_model=PostNotificationSchema, status_code=status.HTTP_201_CREATED)
async def create_post_notification_api(
    notification: PostNotificationSchema,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новое уведомление о посте.
    """
    return await create_post_notification(db=db, notification=notification)


@router.put("/notifications/{notification_id}", response_model=PostNotificationSchema)
async def update_post_notification_api(
    notification_id: int,
    notification: PostNotificationSchema,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить уведомление о посте.
    """
    db_notification = await get_post_notification_by_id(db, notification_id=notification_id)
    if db_notification is None:
        raise HTTPException(status_code=404, detail="Post notification not found")
    
    return await update_post_notification(db=db, notification_id=notification_id, notification=notification)


@router.delete("/notifications/{notification_id}", response_model=PostNotificationSchema)
async def delete_post_notification_api(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить уведомление о посте.
    """
    db_notification = await get_post_notification_by_id(db, notification_id=notification_id)
    if db_notification is None:
        raise HTTPException(status_code=404, detail="Post notification not found")
    
    return await delete_post_notification(db=db, notification_id=notification_id)
