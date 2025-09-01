import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.handlers.channel import router as router_channel
from bot.handlers.keyword import router as router_keyword
from app.core.config import settings
from app.core.logging import main_logger
from bot.keyboards.keyboards import get_main_keyboard
from bot.models.user_model import UserRole
from bot.schemas.user_schema import CreateUserSchema
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db

# Инициализируем бота и диспетчер с хранилищем состояний
storage = MemoryStorage()
bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)


# Обработчик команды /start
@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Обработчик команды /start.
    Приветствует пользователя и проверяет его роль.
    """
    # if settings.SUPER_ADMIN == message.from_user.id:
    #     async with get_atomic_db() as db:
    #         user = await UserService(db).get_or_create_user(message.from_user.id, CreateUserSchema(
    #             telegram_id=message.from_user.id,
    #             username=message.from_user.username if message.from_user.username else "",
    #             first_name=message.from_user.first_name if message.from_user.first_name else "",
    #             last_name=message.from_user.last_name if message.from_user.last_name else "",
    #             role=UserRole.USER.value,
    #             is_active=True,
    #             is_admin=False,
    #             is_operator=False
    #         ))
    #     await message.answer(
    #         f"Здравствуйте, {user.first_name}! Я ваш помошник в мониторинга Telegram-каналов.\n"
    #         f"Ваша роль - СУПЕР АДМИН.",
    #         reply_markup=get_main_keyboard()
    #     )

    async with get_atomic_db() as db:
        user = await UserService(db).get_or_create_user(message.from_user.id, CreateUserSchema(
            telegram_id=message.from_user.id,
            username=message.from_user.username if message.from_user.username else "",
            first_name=message.from_user.first_name if message.from_user.first_name else "",
            last_name=message.from_user.last_name if message.from_user.last_name else "",
            role=UserRole.USER.value,
            is_active=True,
            is_admin=False,
            is_operator=False
        ))
    if user and user.role == "user":
        await message.answer(
            f"Здравствуйте, {user.first_name}! Я ваш помошник в мониторинга Telegram-каналов.\n"
            f"Ваша роль - Пользователь. Вы можете оставить заявку на получение роли Оператора. Для этого воспользуйтесь клавиатурой ниже.",
            reply_markup=get_main_keyboard()
        )
    elif user and user.role == "admin":
        await message.answer(
            f"Здравствуйте, {user.first_name}! Я ваш помошник в мониторинга Telegram-каналов.\n"
            f"Ваша роль - Администратор.\n"
            f"Возпользуйтесь экранной клавиатурой для управления системой!",
            reply_markup=get_main_keyboard(is_admin=True)
        )
    elif user and user.role == "operator":
        await message.answer(
            f"Здравствуйте, {user.first_name}! Я ваш помошник в мониторинга Telegram-каналов.\n"
            f"Ваша роль - Оператор.\n"
            f"Возпользуйтесь экранной клавиатурой для управления системой!",
            reply_markup=get_main_keyboard(is_operator=True)
        )
    else:
        await message.answer(f"Здравствуйте, {user.first_name}! Я ваш помошник в мониторинга Telegram-каналов.\n"
                             f"Ваша роль не определенна.\n"
                             f"Видимо какая то проблема на сервере, тех=специалисты ее уже решают!")


async def main() -> None:
    """
    Основная функция для настройки и запуска бота.
    """
    main_logger.info("Configuring bot")

    # Регистрируем роутеры
    dp.include_router(router=router_channel)
    dp.include_router(router=router_keyword)
    main_logger.info("Starting bot")

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
