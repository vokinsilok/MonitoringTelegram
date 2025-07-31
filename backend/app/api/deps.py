from typing import Optional

from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import settings
from backend.app.db.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.services.user_service import get_user_by_telegram_id


async def get_current_user(
    telegram_id: Optional[int] = Header(None, description="Telegram ID пользователя"),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Получение текущего пользователя по Telegram ID из заголовка запроса.
    """
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Не указан Telegram ID пользователя"
        )
    
    # Получение пользователя из базы данных по Telegram ID
    user = await get_user_by_telegram_id(db, telegram_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден"
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Проверка, что текущий пользователь является администратором.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав для выполнения операции. Требуется роль администратора."
        )
    return current_user
