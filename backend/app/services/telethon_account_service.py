from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.telethon_account import TelethonAccount
from backend.app.schemas.telethon_account import TelethonAccountCreate, TelethonAccountUpdate


class TelethonAccountService:
    """Сервис для работы с аккаунтами Telethon"""

    @staticmethod
    async def create_account(db: AsyncSession, account_data: TelethonAccountCreate) -> TelethonAccount:
        """Создание нового аккаунта Telethon"""
        account = TelethonAccount(
            name=account_data.name,
            api_id=account_data.api_id,
            api_hash=account_data.api_hash,
            phone=account_data.phone,
            description=account_data.description,
            is_active=account_data.is_active
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)
        return account

    @staticmethod
    async def get_account(db: AsyncSession, account_id: int) -> Optional[TelethonAccount]:
        """Получение аккаунта Telethon по ID"""
        result = await db.execute(select(TelethonAccount).where(TelethonAccount.id == account_id))
        return result.scalars().first()

    @staticmethod
    async def get_accounts(
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        is_active: Optional[bool] = None
    ) -> List[TelethonAccount]:
        """Получение списка аккаунтов Telethon"""
        query = select(TelethonAccount)
        
        if is_active is not None:
            query = query.where(TelethonAccount.is_active == is_active)
            
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_account(
        db: AsyncSession, 
        account_id: int, 
        account_data: TelethonAccountUpdate
    ) -> Optional[TelethonAccount]:
        """Обновление аккаунта Telethon"""
        # Преобразуем данные в словарь и удаляем None значения
        update_data = account_data.dict(exclude_unset=True)
        
        if not update_data:
            # Если нет данных для обновления, просто возвращаем текущий аккаунт
            return await TelethonAccountService.get_account(db, account_id)
            
        # Выполняем обновление
        await db.execute(
            update(TelethonAccount)
            .where(TelethonAccount.id == account_id)
            .values(**update_data)
        )
        await db.commit()
        
        # Возвращаем обновленный аккаунт
        return await TelethonAccountService.get_account(db, account_id)

    @staticmethod
    async def delete_account(db: AsyncSession, account_id: int) -> bool:
        """Удаление аккаунта Telethon"""
        result = await db.execute(
            delete(TelethonAccount).where(TelethonAccount.id == account_id)
        )
        await db.commit()
        return result.rowcount > 0

    @staticmethod
    async def update_session_info(
        db: AsyncSession, 
        account_id: int, 
        is_authorized: bool, 
        session_string: Optional[str] = None
    ) -> Optional[TelethonAccount]:
        """Обновление информации о сессии Telethon"""
        update_data: Dict[str, Any] = {"is_authorized": is_authorized}
        
        if session_string is not None:
            update_data["session_string"] = session_string
            
        await db.execute(
            update(TelethonAccount)
            .where(TelethonAccount.id == account_id)
            .values(**update_data)
        )
        await db.commit()
        
        return await TelethonAccountService.get_account(db, account_id)

    @staticmethod
    async def get_active_account(db: AsyncSession) -> Optional[TelethonAccount]:
        """Получение активного аккаунта Telethon для использования"""
        result = await db.execute(
            select(TelethonAccount)
            .where(TelethonAccount.is_active == True)
            .order_by(TelethonAccount.last_used)
            .limit(1)
        )
        return result.scalars().first()
