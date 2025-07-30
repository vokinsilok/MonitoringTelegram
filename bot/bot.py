import asyncio
import logging
from typing import Dict, List, Union

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

# Импортируем конфигурацию из backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from backend.app.core.config import settings

# Импортируем наши модули
from bot.handlers import admin, operator
from bot.middlewares.auth import AuthMiddleware, LoggingMiddleware
from bot.keyboards.keyboards import get_main_keyboard
from bot.utils.utils import is_admin, extract_user_data

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Инициализируем бота и диспетчер с хранилищем состояний
storage = MemoryStorage()
bot = Bot(token=settings.BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher(storage=storage)


# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start.
    Приветствует пользователя и проверяет его роль.
    """
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # TODO: Проверка пользователя в базе данных и определение его роли
    user_is_admin = is_admin(user_id)
    
    # Создаем клавиатуру в зависимости от роли пользователя
    keyboard = get_main_keyboard(is_admin=user_is_admin)
    
    if user_is_admin:
        await message.answer(
            f"Здравствуйте, {first_name}! Вы вошли как администратор системы мониторинга Telegram-каналов.",
            reply_markup=keyboard
        )
        # Отправляем справку по командам администратора
        await admin.cmd_admin_help(message)
    else:
        await message.answer(
            f"Здравствуйте, {first_name}! Вы вошли как оператор системы мониторинга Telegram-каналов.",
            reply_markup=keyboard
        )
        # Отправляем справку по командам оператора
        await operator.cmd_help(message)


# Регистрация обработчиков callback-запросов
dp.callback_query.register(operator.process_post_processed, lambda c: c.data.startswith("processed:"))
dp.callback_query.register(operator.process_post_postponed, lambda c: c.data.startswith("postponed:"))

# Функция для настройки и запуска бота
async def main() -> None:
    """
    Основная функция для настройки и запуска бота.
    """
    logger.info("Configuring bot")
    
    # Регистрируем middleware
    dp.message.middleware(AuthMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    # Регистрируем роутеры
    dp.include_router(admin.router)
    dp.include_router(operator.router)
    
    logger.info("Starting bot")
    
    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
