import asyncio

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from bot.handlers.channel import router as router_channel
from bot.handlers.keyword import router as router_keyword
from bot.handlers.operators import router as router_operators
from bot.handlers.general import router as router_general
from bot.handlers.telethon import router as router_telethon
from bot.handlers.post_processing import router as router_post_processing
from bot.handlers.bulk_import import router as router_bulk_import
from app.core.config import settings
from app.core.logging import main_logger
from bot.keyboards.keyboards import get_main_keyboard
from bot.models.user_model import UserRole
from bot.schemas.user_schema import CreateUserSchema
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db
from bot.tasks.monitoring_tasks import start_background_tasks

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
    user_id = message.from_user.id

    async with get_atomic_db() as db:
        user_service = UserService(db)
        if not await user_service.user_in_white_list(user_id):
            main_logger.info(await user_service.user_in_white_list(user_id))
            await message.answer(
                "❌ <b>Доступ запрещён.</b>\n\n"
                "Ваш Telegram ID не находится в белом списке. Пожалуйста, свяжитесь с администратором для получения доступа."
            )
            return

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
        # получаем язык интерфейса пользователя
        st = None
        try:
            st = await db.user.get_or_create_settings(user.id)
        except Exception:
            pass
        lang = getattr(st, "language", None)

    name = user.first_name or user.username or str(user.telegram_id)
    if user and user.role == "user":
        await message.answer(
            "👋 <b>Здравствуйте, {name}!</b>\n\n"
            "Я ваш помощник по мониторингу Telegram‑каналов.\n"
            "Ваша роль — <b>Пользователь</b>.\n\n"
            "Вы можете запросить доступ оператора с помощью кнопки \"📝 Получить доступ оператора\" ниже.".format(
                name=name
            ),
            reply_markup=get_main_keyboard(lang, is_admin=False, is_operator=False)
        )
    elif user and user.role == "admin":
        await message.answer(
            "👋 <b>Здравствуйте, {name}!</b>\n\n"
            "Ваша роль — <b>Администратор</b>.\n"
            "Используйте меню ниже для управления каналами, ключевыми словами, операторами и Telethon‑аккаунтами.".format(
                name=name
            ),
            reply_markup=get_main_keyboard(lang, is_admin=True)
        )
    elif user and user.role == "operator":
        await message.answer(
            "👋 <b>Здравствуйте, {name}!</b>\n\n"
            "Ваша роль — <b>Оператор</b>.\n"
            "Используйте кнопки ниже, чтобы предлагать каналы и ключевые слова, а также смотреть отчёты.".format(
                name=name
            ),
            reply_markup=get_main_keyboard(lang, is_operator=True)
        )
    else:
        await message.answer(
            "⚠️ <b>Ваша роль не определена.</b>\n\n"
            "Возможно, возникла временная ошибка. Попробуйте повторить запрос позже."
        )


async def main() -> None:
    """
    Основная функция для настройки и запуска бота.
    """
    main_logger.info("Configuring bot")

    # Регистрируем роутеры
    dp.include_router(router=router_channel)
    dp.include_router(router=router_keyword)
    dp.include_router(router=router_operators)
    dp.include_router(router=router_general)
    dp.include_router(router=router_telethon)
    dp.include_router(router_post_processing)
    dp.include_router(router=router_bulk_import)

    # Запускаем фоновые задачи
    start_background_tasks(bot)

    main_logger.info("Starting bot")

    # Запускаем бота
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
