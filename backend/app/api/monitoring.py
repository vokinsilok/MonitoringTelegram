from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.user import UserRole
from backend.app.services.channel_monitoring_service import channel_monitoring_service
from backend.app.api.deps import get_current_user, get_current_admin_user


router = APIRouter(
    prefix="/monitoring",
    tags=["monitoring"]
)


@router.post("/authorize/{account_id}", response_model=Dict[str, Any])
async def authorize_telethon_client(
    account_id: int,
    code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)  # Только администраторы могут авторизовать клиент
):
    """
    Авторизация клиента Telethon.
    Если код не указан, отправляет запрос на получение кода авторизации.
    Если код указан, выполняет авторизацию с использованием этого кода.
    """
    result = await channel_monitoring_service.authorize_client(db, account_id, code)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.get("/channel-info/{account_id}", response_model=Dict[str, Any])
async def get_channel_info(
    account_id: int,
    channel_username: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)  # Только администраторы могут получать информацию о каналах
):
    """
    Получение информации о канале по его username.
    """
    result = await channel_monitoring_service.get_channel_info(db, account_id, channel_username)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.post("/fetch-posts/{account_id}/{channel_id}", response_model=Dict[str, Any])
async def fetch_channel_posts(
    account_id: int,
    channel_id: int,
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)  # Только администраторы могут запускать парсинг постов
):
    """
    Получение последних сообщений из канала и сохранение их в БД.
    """
    result = await channel_monitoring_service.fetch_channel_posts(db, account_id, channel_id, limit)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result


@router.post("/monitor-all", response_model=Dict[str, Any])
async def monitor_all_channels(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)  # Только администраторы могут запускать мониторинг
):
    """
    Запуск мониторинга всех активных каналов.
    Выполняется в фоновом режиме.
    """
    # Запускаем мониторинг в фоновом режиме
    background_tasks.add_task(channel_monitoring_service.monitor_channels, db)
    
    return {
        "success": True,
        "message": "Мониторинг каналов запущен в фоновом режиме"
    }


@router.post("/monitor-all-sync", response_model=Dict[str, Any])
async def monitor_all_channels_sync(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_admin_user)  # Только администраторы могут запускать мониторинг
):
    """
    Синхронный запуск мониторинга всех активных каналов.
    Блокирует запрос до завершения мониторинга.
    """
    result = await channel_monitoring_service.monitor_channels(db)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return result
