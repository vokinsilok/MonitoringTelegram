from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
from backend.app.schemas.user import UserCreate, UserUpdate


async def get_users(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[User]:
    """
    Получение списка пользователей с возможностью фильтрации.
    """
    query = select(User)
    
    if filters:
        if "role" in filters:
            query = query.where(User.role == filters["role"])
        if "is_active" in filters:
            query = query.where(User.is_active == filters["is_active"])
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Получение пользователя по ID.
    """
    query = select(User).where(User.id == user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """
    Получение пользователя по Telegram ID.
    """
    query = select(User).where(User.telegram_id == telegram_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """
    Создание нового пользователя.
    """
    db_user = User(
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role,
        is_active=user.is_active,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def update_user(db: AsyncSession, user_id: int, user: UserUpdate) -> Optional[User]:
    """
    Обновление пользователя.
    """
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def delete_user(db: AsyncSession, user_id: int) -> Optional[User]:
    """
    Удаление пользователя.
    """
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    await db.delete(db_user)
    await db.commit()
    return db_user


async def set_user_active_status(db: AsyncSession, user_id: int, is_active: bool) -> Optional[User]:
    """
    Изменение статуса активности пользователя.
    """
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.is_active = is_active
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def set_user_role(db: AsyncSession, user_id: int, role: str) -> Optional[User]:
    """
    Изменение роли пользователя.
    """
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    db_user.role = role
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def check_user_and_get_role(db: AsyncSession, telegram_id: int, username: Optional[str] = None, 
                               first_name: Optional[str] = None, last_name: Optional[str] = None) -> tuple[User, bool]:
    """
    Проверка пользователя в базе данных и определение его роли.
    Если пользователь не найден, создает нового пользователя с ролью по умолчанию.
    
    Args:
        db: Сессия базы данных
        telegram_id: Telegram ID пользователя
        username: Имя пользователя в Telegram
        first_name: Имя пользователя
        last_name: Фамилия пользователя
    
    Returns:
        tuple[User, bool]: Пользователь и флаг, указывающий, был ли пользователь создан (True) или уже существовал (False)
    """
    # Проверяем, есть ли пользователь в базе
    user = await get_user_by_telegram_id(db, telegram_id)
    
    # Если пользователь найден, обновляем его данные и возвращаем
    if user:
        # Обновляем данные пользователя, если они изменились
        if username and user.username != username:
            user.username = username
        if first_name and user.first_name != first_name:
            user.first_name = first_name
        if last_name and user.last_name != last_name:
            user.last_name = last_name
            
        # Если были изменения, сохраняем их
        await db.commit()
        await db.refresh(user)
        return user, False
    
    # Если пользователь не найден, создаем нового с ролью по умолчанию
    from backend.app.core.config import settings
    
    # Проверяем, является ли пользователь администратором
    role = "admin" if telegram_id in settings.get_admin_ids() else "operator"
    
    # Создаем нового пользователя
    user_data = UserCreate(
        telegram_id=telegram_id,
        username=username or "",
        first_name=first_name or "",
        last_name=last_name or "",
        role=role,
        is_active=True
    )
    
    new_user = await create_user(db, user_data)
    return new_user, True
