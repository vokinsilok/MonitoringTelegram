from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Создаем роутер для администраторских команд
router = Router()


class ChannelForm(StatesGroup):
    """Состояния для формы добавления канала"""
    waiting_for_channel = State()
    waiting_for_confirmation = State()


class KeywordForm(StatesGroup):
    """Состояния для формы добавления ключевого слова"""
    waiting_for_keyword = State()
    waiting_for_type = State()
    waiting_for_confirmation = State()


@router.message(Command("admin_help"))
async def cmd_admin_help(message: Message):
    """Показать справку по командам администратора"""
    help_text = """
<b>Команды администратора:</b>

/add_channel - Добавить канал для мониторинга
/list_channels - Список каналов для мониторинга
/add_keyword - Добавить ключевое слово для мониторинга
/list_keywords - Список ключевых слов для мониторинга
/manage_operators - Управление операторами
/add_telethon - Добавить клиент Telethon
/list_telethon - Список клиентов Telethon
/report - Сформировать отчет
    """
    await message.answer(help_text)


@router.message(Command("add_channel"))
async def cmd_add_channel(message: Message, state: FSMContext):
    """Начать процесс добавления канала"""
    await message.answer("Пожалуйста, отправьте ссылку на Telegram-канал или его @username")
    await state.set_state(ChannelForm.waiting_for_channel)


@router.message(ChannelForm.waiting_for_channel)
async def process_channel(message: Message, state: FSMContext):
    """Обработать отправленный канал"""
    channel_link = message.text.strip()
    
    # Сохраняем данные в состоянии
    await state.update_data(channel_link=channel_link)
    
    # Запрашиваем подтверждение
    await message.answer(
        f"Вы хотите добавить канал {channel_link} для мониторинга?\n"
        f"Отправьте 'да' для подтверждения или 'нет' для отмены."
    )
    await state.set_state(ChannelForm.waiting_for_confirmation)


@router.message(ChannelForm.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Обработать подтверждение добавления канала"""
    confirmation = message.text.lower().strip()
    
    if confirmation in ["да", "yes", "y"]:
        # Получаем данные из состояния
        data = await state.get_data()
        channel_link = data.get("channel_link")
        
        # Получаем Telegram ID пользователя
        telegram_id = message.from_user.id
        
        try:
            # Импортируем ApiClient для работы с API
            from bot.utils.api_client import ApiClient
            
            # Добавляем канал через API
            result = await ApiClient.add_channel(
                telegram_id=telegram_id,
                channel_url=channel_link
            )
            
            # Отправляем уведомление операторам
            from bot.utils.notification import send_operator_notification
            await send_operator_notification(
                f"Администратор {message.from_user.full_name} добавил новый канал для мониторинга:\n"
                f"Канал: {channel_link}"
            )
            
            await message.answer(f"Канал {channel_link} успешно добавлен для мониторинга!")
        except Exception as e:
            await message.answer(
                f"Произошла ошибка при добавлении канала: {str(e)}\n"
                f"Пожалуйста, попробуйте позже."
            )
    else:
        await message.answer("Добавление канала отменено.")
    
    # Сбрасываем состояние
    await state.clear()


@router.message(Command("add_keyword"))
async def cmd_add_keyword(message: Message, state: FSMContext):
    """Начать процесс добавления ключевого слова"""
    await message.answer("Пожалуйста, отправьте ключевое слово или фразу для мониторинга")
    await state.set_state(KeywordForm.waiting_for_keyword)


@router.message(KeywordForm.waiting_for_keyword)
async def process_keyword(message: Message, state: FSMContext):
    """Обработать отправленное ключевое слово"""
    keyword = message.text.strip()
    
    # Сохраняем данные в состоянии
    await state.update_data(keyword=keyword)
    
    # Запрашиваем тип ключевого слова
    await message.answer(
        "Выберите тип ключевого слова:\n"
        "1. Слово\n"
        "2. Фраза\n"
        "3. Регулярное выражение"
    )
    await state.set_state(KeywordForm.waiting_for_type)


@router.message(KeywordForm.waiting_for_type)
async def process_keyword_type(message: Message, state: FSMContext):
    """Обработать тип ключевого слова"""
    keyword_type = message.text.strip()
    
    # Преобразуем ввод в тип
    type_mapping = {
        "1": "word",
        "2": "phrase",
        "3": "regex",
        "слово": "word",
        "фраза": "phrase",
        "регулярное выражение": "regex",
    }
    
    if keyword_type.lower() in type_mapping:
        # Сохраняем тип в состоянии
        await state.update_data(keyword_type=type_mapping[keyword_type.lower()])
        
        # Получаем данные из состояния
        data = await state.get_data()
        keyword = data.get("keyword")
        keyword_type_str = type_mapping[keyword_type.lower()]
        
        # Запрашиваем подтверждение
        await message.answer(
            f"Вы хотите добавить ключевое слово '{keyword}' типа '{keyword_type_str}'?\n"
            f"Отправьте 'да' для подтверждения или 'нет' для отмены."
        )
        await state.set_state(KeywordForm.waiting_for_confirmation)
    else:
        await message.answer("Неверный тип. Пожалуйста, выберите 1, 2 или 3.")


@router.message(KeywordForm.waiting_for_confirmation)
async def process_keyword_confirmation(message: Message, state: FSMContext):
    """Обработать подтверждение добавления ключевого слова"""
    confirmation = message.text.lower().strip()
    
    if confirmation in ["да", "yes", "y"]:
        # Получаем данные из состояния
        data = await state.get_data()
        keyword = data.get("keyword")
        keyword_type = data.get("keyword_type")
        
        # Получаем Telegram ID пользователя
        telegram_id = message.from_user.id
        
        try:
            # Импортируем ApiClient для работы с API
            from bot.utils.api_client import ApiClient
            
            # Добавляем ключевое слово через API
            result = await ApiClient.add_keyword(
                telegram_id=telegram_id,
                keyword=keyword,
                keyword_type=keyword_type
            )
            
            # Отправляем уведомление операторам
            from bot.utils.notification import send_operator_notification
            await send_operator_notification(
                f"Администратор {message.from_user.full_name} добавил новое ключевое слово для мониторинга:\n"
                f"Ключевое слово: '{keyword}'\n"
                f"Тип: {keyword_type}"
            )
            
            await message.answer(f"Ключевое слово '{keyword}' типа '{keyword_type}' успешно добавлено для мониторинга!")
        except Exception as e:
            await message.answer(
                f"Произошла ошибка при добавлении ключевого слова: {str(e)}\n"
                f"Пожалуйста, попробуйте позже."
            )
    else:
        await message.answer("Добавление ключевого слова отменено.")
    
    # Сбрасываем состояние
    await state.clear()


@router.message(Command("manage_operators"))
async def cmd_manage_operators(message: Message):
    """Управление операторами"""
    await message.answer("Функция управления операторами находится в разработке.")


@router.message(Command("report"))
async def cmd_report(message: Message):
    """Формирование отчета"""
    await message.answer("Функция формирования отчета находится в разработке.")
