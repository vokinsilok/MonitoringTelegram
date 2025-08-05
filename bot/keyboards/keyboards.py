from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton


def get_post_keyboard(post_id: str, post_url: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для сообщения с постом.
    
    Args:
        post_id: ID поста в базе данных
        post_url: URL поста в Telegram
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для поста
    """
    # Кнопка для перехода к первоисточнику
    source_button = InlineKeyboardButton(text="Перейти к первоисточнику", url=post_url)
    
    # Кнопка для показа полного поста
    show_full_button = InlineKeyboardButton(
        text="Показать полностью", 
        callback_data=f"show_full:{post_id}"
    )
    
    # Кнопки для установки статуса
    processed_button = InlineKeyboardButton(
        text="Обработано", 
        callback_data=f"processed:{post_id}"
    )
    
    postponed_button = InlineKeyboardButton(
        text="Отложено", 
        callback_data=f"postponed:{post_id}"
    )
    
    # Создаем клавиатуру с обязательным полем inline_keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [source_button],
        [show_full_button],
        [processed_button, postponed_button]
    ])
    
    return keyboard


def get_channel_proposal_keyboard(proposal_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для подтверждения или отклонения предложения канала.
    
    Args:
        proposal_id: ID предложения канала
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для подтверждения/отклонения
    """
    # Кнопки для подтверждения или отклонения предложения
    approve_button = InlineKeyboardButton(
        text="✅ Подтвердить", 
        callback_data=f"approve_channel:{proposal_id}"
    )
    
    reject_button = InlineKeyboardButton(
        text="❌ Отклонить", 
        callback_data=f"reject_channel:{proposal_id}"
    )
    
    # Создаем клавиатуру с обязательным полем inline_keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])
    
    return keyboard


def get_main_keyboard(is_admin: bool = False, is_operator: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру для пользователя.
    
    Args:
        is_admin: Является ли пользователь администратором
        is_operator: Является ли пользователь оператором
    
    Returns:
        ReplyKeyboardMarkup: Основная клавиатура
    """
    # Создаем кнопки
    # Общие кнопки для всех пользователей
    report_button = KeyboardButton(text="📊 Отчет")
    
    if is_admin:
        # Кнопки для администратора
        add_channel_button = KeyboardButton(text="➕ Добавить канал")
        add_keyword_button = KeyboardButton(text="🔑 Добавить ключевое слово")
        manage_operators_button = KeyboardButton(text="👥 Управление операторами")
        add_telethon_button = KeyboardButton(text="🔐 Добавить Telethon")
        view_requests_button = KeyboardButton(text="📝 Обращения")
        
        # Создаем массив кнопок для клавиатуры
        keyboard_buttons = [
            [add_channel_button, add_keyword_button],
            [manage_operators_button, add_telethon_button],
            [report_button, view_requests_button]
        ]
    elif is_operator:
        # Кнопки для оператора
        propose_channel_button = KeyboardButton(text="📢 Предложить канал")
        propose_keyword_button = KeyboardButton(text="🔍 Предложить ключевое слово")

        
        # Создаем массив кнопок для клавиатуры
        keyboard_buttons = [
            [propose_channel_button, propose_keyword_button],
            [report_button]
        ]
    else:
        # Кнопки для обычного пользователя (клиента)
        new_request_button = KeyboardButton(text="📝 Новое обращение")
        my_requests_button = KeyboardButton(text="🔍 Мои обращения")
        feedback_button = KeyboardButton(text="💬 Обратная связь")
        help_button = KeyboardButton(text="❓ Помощь")
        
        # Создаем массив кнопок для клавиатуры
        keyboard_buttons = [
            [new_request_button, my_requests_button],
            [feedback_button, help_button]
        ]
    
    # Создаем клавиатуру с обязательным полем keyboard
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
    
    return keyboard


