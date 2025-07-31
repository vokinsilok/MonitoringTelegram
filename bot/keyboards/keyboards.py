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
    keyboard = InlineKeyboardMarkup(row_width=2)
    
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
    
    # Добавляем кнопки в клавиатуру
    keyboard.add(source_button)
    keyboard.add(show_full_button)
    keyboard.row(processed_button, postponed_button)
    
    return keyboard


def get_proposal_keyboard(proposal_id: str, proposal_type: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для сообщения с предложением (канала или ключевого слова).
    
    Args:
        proposal_id: ID предложения в базе данных
        proposal_type: Тип предложения ('channel' или 'keyword')
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для предложения
    """
    keyboard = InlineKeyboardMarkup(row_width=3)
    
    # Кнопка для просмотра подробной информации
    details_button = InlineKeyboardButton(
        text="Посмотреть подробно", 
        callback_data=f"details:{proposal_type}:{proposal_id}"
    )
    
    # Кнопки для принятия/отклонения предложения
    approve_button = InlineKeyboardButton(
        text="Подтвердить", 
        callback_data=f"approve:{proposal_type}:{proposal_id}"
    )
    
    reject_button = InlineKeyboardButton(
        text="Отклонить", 
        callback_data=f"reject:{proposal_type}:{proposal_id}"
    )
    
    # Добавляем кнопки в клавиатуру
    keyboard.add(details_button)
    keyboard.row(approve_button, reject_button)
    
    return keyboard


def get_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру для пользователя.
    
    Args:
        is_admin: Является ли пользователь администратором
    
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
        
        # Создаем массив кнопок для клавиатуры
        keyboard_buttons = [
            [add_channel_button, add_keyword_button],
            [manage_operators_button, report_button]
        ]
    else:
        # Кнопки для оператора
        propose_channel_button = KeyboardButton(text="📢 Предложить канал")
        propose_keyword_button = KeyboardButton(text="🔍 Предложить ключевое слово")
        
        # Создаем массив кнопок для клавиатуры
        keyboard_buttons = [
            [propose_channel_button, propose_keyword_button],
            [report_button]
        ]
    
    # Создаем клавиатуру с обязательным полем keyboard
    keyboard = ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)
    
    return keyboard
