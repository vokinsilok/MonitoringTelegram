from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.user import UserRole
from backend.app.schemas.telethon_account import (
    TelethonAccountCreate, 
    TelethonAccountUpdate, 
    TelethonAccountResponse,
    TelethonAccountListResponse
)
from backend.app.services.telethon_account_service import TelethonAccountService
from backend.app.api.deps import get_current_user, get_current_admin_user


router = APIRouter(
    prefix="/telethon-accounts",
    tags=["telethon-accounts"],
    dependencies=[Depends(get_current_admin_user)]  # Только администраторы могут управлять аккаунтами Telethon
)


@router.post("/", response_model=TelethonAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_telethon_account(
    account_data: TelethonAccountCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Создание нового аккаунта Telethon.
    Только для администраторов.
    """
    account = await TelethonAccountService.create_account(db, account_data)
    return account


@router.get("/", response_model=TelethonAccountListResponse)
async def get_telethon_accounts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Получение списка аккаунтов Telethon.
    Только для администраторов.
    """
    accounts = await TelethonAccountService.get_accounts(db, skip, limit, is_active)
    total = len(accounts)  # В реальном проекте здесь должен быть отдельный запрос для подсчета общего количества
    return {"total": total, "items": accounts}


@router.get("/{account_id}", response_model=TelethonAccountResponse)
async def get_telethon_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Получение аккаунта Telethon по ID.
    Только для администраторов.
    """
    account = await TelethonAccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Аккаунт Telethon с ID {account_id} не найден"
        )
    return account


@router.put("/{account_id}", response_model=TelethonAccountResponse)
async def update_telethon_account(
    account_id: int,
    account_data: TelethonAccountUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Обновление аккаунта Telethon.
    Только для администраторов.
    """
    account = await TelethonAccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Аккаунт Telethon с ID {account_id} не найден"
        )
    
    updated_account = await TelethonAccountService.update_account(db, account_id, account_data)
    return updated_account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_telethon_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Удаление аккаунта Telethon.
    Только для администраторов.
    """
    account = await TelethonAccountService.get_account(db, account_id)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Аккаунт Telethon с ID {account_id} не найден"
        )
    
    success = await TelethonAccountService.delete_account(db, account_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ошибка при удалении аккаунта Telethon"
        )
