from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.user import User
from backend.app.schemas.user import User as UserSchema, UserCreate, UserUpdate
from backend.app.services.user_service import (
    get_users,
    get_user_by_id,
    get_user_by_telegram_id,
    create_user,
    update_user,
    delete_user,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=List[UserSchema])
async def read_users(
    skip: int = 0,
    limit: int = 100,
    is_admin: Optional[bool] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список пользователей с возможностью фильтрации.
    """
    filters = {}
    if is_admin is not None:
        filters["is_admin"] = is_admin
    if is_active is not None:
        filters["is_active"] = is_active
        
    users = await get_users(db, skip=skip, limit=limit, filters=filters)
    return users


@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить пользователя по ID.
    """
    user = await get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/telegram/{telegram_id}", response_model=UserSchema)
async def read_user_by_telegram_id(
    telegram_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить пользователя по Telegram ID.
    """
    user = await get_user_by_telegram_id(db, telegram_id=telegram_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user_api(
    user: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать нового пользователя.
    """
    db_user = await get_user_by_telegram_id(db, telegram_id=user.telegram_id)
    if db_user:
        raise HTTPException(status_code=400, detail="User with this Telegram ID already exists")
    
    return await create_user(db=db, user=user)


@router.put("/{user_id}", response_model=UserSchema)
async def update_user_api(
    user_id: int,
    user: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить пользователя.
    """
    db_user = await get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await update_user(db=db, user_id=user_id, user=user)


@router.delete("/{user_id}", response_model=UserSchema)
async def delete_user_api(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить пользователя.
    """
    db_user = await get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await delete_user(db=db, user_id=user_id)
