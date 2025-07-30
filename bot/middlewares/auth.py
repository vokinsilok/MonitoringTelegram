from typing import Dict, Any, Callable, Awaitable

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.event.bases import CancelHandler
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируем утилиты из нашего проекта
from bot.utils.utils import is_admin
from backend.app.db.database import get_db
from backend.app.services.user_service import check_user_and_get_role


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки авторизации пользователей.
    Проверяет, имеет ли пользователь доступ к боту и определяет его роль.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Получаем пользователя из события
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        else:
            # Если тип события неизвестен, пропускаем
            return await handler(event, data)
        
        if not user:
            # Если пользователь не определен, отменяем обработку
            raise CancelHandler()
        
        # Проверяем, является ли пользователь администратором по локальным настройкам
        user_is_admin = is_admin(user.id)
        
        # Проверяем пользователя в базе данных и определяем его роль
        try:
            async for db in get_db():
                db_user, is_new = await check_user_and_get_role(
                    db=db,
                    telegram_id=user.id,
                    username=user.username,
                    first_name=user.first_name,
                    last_name=user.last_name
                )
                
                # Добавляем информацию о пользователе в данные
                data["user"] = db_user
                data["is_admin"] = db_user.role == "admin"
                data["is_new_user"] = is_new
                break
        except Exception as e:
            # В случае ошибки при работе с БД, используем локальные настройки
            data["is_admin"] = user_is_admin
            data["db_error"] = str(e)
        
        # Продолжаем обработку события
        return await handler(event, data)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware для логирования сообщений пользователей.
    Сохраняет все сообщения в базу данных.
    """
    
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Логируем только сообщения, а не callback-запросы
        if isinstance(event, Message) and event.text:
            # TODO: Добавить логирование сообщения в базу данных
            # Примерный код:
            # await log_message_to_db(
            #     user_id=event.from_user.id,
            #     username=event.from_user.username,
            #     message_text=event.text,
            #     message_type="incoming"
            # )
            pass
        
        # Продолжаем обработку события
        return await handler(event, data)
