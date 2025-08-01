from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Создаем роутер для команд оператора
router = Router()


class ChannelProposalForm(StatesGroup):
    """Состояния для формы предложения канала"""
    waiting_for_channel = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


class KeywordProposalForm(StatesGroup):
    """Состояния для формы предложения ключевого слова"""
    waiting_for_keyword = State()
    waiting_for_type = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


class PostProcessingForm(StatesGroup):
    """Состояния для формы обработки поста"""
    waiting_for_status = State()
    waiting_for_comment = State()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Показать справку по командам оператора"""
    help_text = """
<b>Команды оператора:</b>

/propose_channel - Предложить канал для мониторинга
/propose_keyword - Предложить ключевое слово для мониторинга
/report - Запросить отчет по обработанным постам
    """
    await message.answer(help_text)


@router.message(Command("propose_channel"))
async def cmd_propose_channel(message: Message, state: FSMContext):
    """Начать процесс предложения канала"""
    await message.answer("Пожалуйста, отправьте ссылку на Telegram-канал или его @username")
    await state.set_state(ChannelProposalForm.waiting_for_channel)


@router.message(ChannelProposalForm.waiting_for_channel)
async def process_channel_proposal(message: Message, state: FSMContext):
    """Обработать отправленный канал"""
    channel_link = message.text.strip()
    
    # Сохраняем данные в состоянии
    await state.update_data(channel_link=channel_link)
    
    # Запрашиваем комментарий
    await message.answer(
        "Пожалуйста, добавьте комментарий, почему этот канал стоит мониторить"
    )
    await state.set_state(ChannelProposalForm.waiting_for_comment)


@router.message(ChannelProposalForm.waiting_for_comment)
async def process_channel_comment(message: Message, state: FSMContext):
    """Обработать комментарий к предложению канала"""
    comment = message.text.strip()
    
    # Сохраняем данные в состоянии
    await state.update_data(comment=comment)
    
    # Получаем данные из состояния
    data = await state.get_data()
    channel_link = data.get("channel_link")
    
    # Запрашиваем подтверждение
    await message.answer(
        f"Вы хотите предложить канал {channel_link} для мониторинга?\n"
        f"Комментарий: {comment}\n\n"
        f"Отправьте 'да' для подтверждения или 'нет' для отмены."
    )
    await state.set_state(ChannelProposalForm.waiting_for_confirmation)


@router.message(ChannelProposalForm.waiting_for_confirmation)
async def process_channel_confirmation(message: Message, state: FSMContext):
    """Обработать подтверждение предложения канала"""
    confirmation = message.text.lower().strip()
    
    if confirmation in ["да", "yes", "y"]:
        # Получаем данные из состояния
        data = await state.get_data()
        channel_link = data.get("channel_link")
        comment = data.get("comment")
        
        # Получаем Telegram ID пользователя
        telegram_id = message.from_user.id
        
        try:
            # Импортируем ApiClient для работы с API
            from bot.utils.api_client import ApiClient
            
            # Сохраняем предложение канала через API
            result = await ApiClient.create_channel_proposal(
                telegram_id=telegram_id,
                channel_url=channel_link,
                comment=comment
            )
            
            # Отправляем уведомление администраторам
            from bot.utils.notification import send_admin_notification
            await send_admin_notification(
                f"Новое предложение канала от оператора {message.from_user.full_name} (ID: {telegram_id}):\n"
                f"Канал: {channel_link}\n"
                f"Комментарий: {comment}"
            )
            
            await message.answer(
                f"Ваше предложение канала {channel_link} отправлено администраторам на рассмотрение.\n"
                f"Вы получите уведомление о результате."
            )
        except Exception as e:
            await message.answer(
                f"Произошла ошибка при отправке предложения канала: {str(e)}\n"
                f"Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
    else:
        await message.answer("Предложение канала отменено.")
    
    # Сбрасываем состояние
    await state.clear()


@router.message(Command("propose_keyword"))
async def cmd_propose_keyword(message: Message, state: FSMContext):
    """Начать процесс предложения ключевого слова"""
    await message.answer("Пожалуйста, отправьте ключевое слово или фразу для мониторинга")
    await state.set_state(KeywordProposalForm.waiting_for_keyword)


@router.message(KeywordProposalForm.waiting_for_keyword)
async def process_keyword_proposal(message: Message, state: FSMContext):
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
    await state.set_state(KeywordProposalForm.waiting_for_type)


@router.message(KeywordProposalForm.waiting_for_type)
async def process_keyword_type_proposal(message: Message, state: FSMContext):
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
        
        # Запрашиваем комментарий
        await message.answer(
            "Пожалуйста, добавьте комментарий, почему это ключевое слово стоит мониторить"
        )
        await state.set_state(KeywordProposalForm.waiting_for_comment)
    else:
        await message.answer("Неверный тип. Пожалуйста, выберите 1, 2 или 3.")


@router.message(KeywordProposalForm.waiting_for_comment)
async def process_keyword_comment(message: Message, state: FSMContext):
    """Обработать комментарий к предложению ключевого слова"""
    comment = message.text.strip()
    
    # Сохраняем данные в состоянии
    await state.update_data(comment=comment)
    
    # Получаем данные из состояния
    data = await state.get_data()
    keyword = data.get("keyword")
    keyword_type = data.get("keyword_type")
    
    # Запрашиваем подтверждение
    await message.answer(
        f"Вы хотите предложить ключевое слово '{keyword}' типа '{keyword_type}'?\n"
        f"Комментарий: {comment}\n\n"
        f"Отправьте 'да' для подтверждения или 'нет' для отмены."
    )
    await state.set_state(KeywordProposalForm.waiting_for_confirmation)


@router.message(KeywordProposalForm.waiting_for_confirmation)
async def process_keyword_confirmation_proposal(message: Message, state: FSMContext):
    """Обработать подтверждение предложения ключевого слова"""
    confirmation = message.text.lower().strip()
    
    if confirmation in ["да", "yes", "y"]:
        # Получаем данные из состояния
        data = await state.get_data()
        keyword = data.get("keyword")
        keyword_type = data.get("keyword_type")
        comment = data.get("comment")
        
        # Получаем Telegram ID пользователя
        telegram_id = message.from_user.id
        
        try:
            # Импортируем ApiClient для работы с API
            from bot.utils.api_client import ApiClient
            
            # Сохраняем предложение ключевого слова через API
            result = await ApiClient.create_keyword_proposal(
                telegram_id=telegram_id,
                keyword=keyword,
                keyword_type=keyword_type,
                comment=comment
            )
            
            # Отправляем уведомление администраторам
            from bot.utils.notification import send_admin_notification
            await send_admin_notification(
                f"Новое предложение ключевого слова от оператора {message.from_user.full_name} (ID: {telegram_id}):\n"
                f"Ключевое слово: {keyword}\n"
                f"Тип: {keyword_type}\n"
                f"Комментарий: {comment}"
            )
            
            await message.answer(
                f"Ваше предложение ключевого слова '{keyword}' отправлено администраторам на рассмотрение.\n"
                f"Вы получите уведомление о результате."
            )
        except Exception as e:
            await message.answer(
                f"Произошла ошибка при отправке предложения ключевого слова: {str(e)}\n"
                f"Пожалуйста, попробуйте позже или обратитесь к администратору."
            )
    else:
        await message.answer("Предложение ключевого слова отменено.")
    
    # Сбрасываем состояние
    await state.clear()


# Обработчик для кнопки "Обработано" под постом
async def process_post_processed(callback_query: CallbackQuery, state: FSMContext):
    """Обработать нажатие кнопки 'Обработано' под постом"""
    post_id = callback_query.data.split(':')[1]
    
    # Сохраняем данные в состоянии
    await state.update_data(post_id=post_id, status="processed")
    
    # Запрашиваем комментарий
    await callback_query.message.answer("Пожалуйста, добавьте комментарий к обработанному посту")
    await state.set_state(PostProcessingForm.waiting_for_comment)
    
    # Отвечаем на callback query
    await callback_query.answer()


# Обработчик для кнопки "Отложено" под постом
async def process_post_postponed(callback_query: CallbackQuery, state: FSMContext):
    """Обработать нажатие кнопки 'Отложено' под постом"""
    post_id = callback_query.data.split(':')[1]
    
    # Сохраняем данные в состоянии
    await state.update_data(post_id=post_id, status="postponed")
    
    # Запрашиваем комментарий
    await callback_query.message.answer("Пожалуйста, добавьте комментарий к отложенному посту")
    await state.set_state(PostProcessingForm.waiting_for_comment)
    
    # Отвечаем на callback query
    await callback_query.answer()


@router.message(PostProcessingForm.waiting_for_comment)
async def process_post_comment(message: Message, state: FSMContext):
    """Обработать комментарий к посту"""
    comment = message.text.strip()
    
    # Получаем данные из состояния
    data = await state.get_data()
    post_id = data.get("post_id")
    status = data.get("status")
    
    # Получаем Telegram ID пользователя
    telegram_id = message.from_user.id
    
    try:
        # Импортируем ApiClient для работы с API
        from bot.utils.api_client import ApiClient
        
        # Сохраняем обработку поста через API
        result = await ApiClient.process_post(
            telegram_id=telegram_id,
            post_id=post_id,
            status=status,
            comment=comment
        )
        
        # Удаляем аналогичные сообщения у других операторов
        # Импортируем функцию для отправки уведомлений операторам
        from bot.utils.notification import send_operator_notification
        
        # Отправляем уведомление всем операторам о том, что пост обработан
        status_text = "обработан" if status == "processed" else "отложен"
        await send_operator_notification(
            f"Пост ID:{post_id} был {status_text} оператором {message.from_user.full_name}.\n"
            f"Комментарий: {comment}"
        )
        
        await message.answer(f"Пост успешно {status_text} с комментарием: {comment}")
    except Exception as e:
        await message.answer(
            f"Произошла ошибка при обработке поста: {str(e)}\n"
            f"Пожалуйста, попробуйте позже или обратитесь к администратору."
        )
    
    # Сбрасываем состояние
    await state.clear()


@router.message(Command("report"))
async def cmd_report(message: Message):
    """Запрос отчета по обработанным постам"""
    # TODO: Реализовать запрос параметров отчета (период, тип и т.д.)
    await message.answer("Функция формирования отчета находится в разработке.")
