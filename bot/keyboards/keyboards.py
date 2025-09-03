from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from typing import Optional
from bot.utils.i18n import t


def get_post_keyboard(pp_id: int, post_id: int, post_url: str) -> InlineKeyboardMarkup:
    """
    Клавиатура для уведомления об отклике на пост.
    callback_data содержит идентификатор записи PostProcessing для атомарной обработки.

    Args:
        pp_id: ID записи PostProcessing
        post_id: ID поста в базе данных
        post_url: URL поста в Telegram
    
    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для поста
    """
    # Кнопка для перехода к первоисточнику
    source_button = InlineKeyboardButton(text="🔗 Первоисточник", url=post_url)

    # Кнопка для показа полного поста
    show_full_button = InlineKeyboardButton(
        text="📄 Показать полностью",
        callback_data=f"show_full:{post_id}"
    )
    
    # Кнопки для установки статуса
    processed_button = InlineKeyboardButton(
        text="✅ Обработать",
        callback_data=f"processed:{pp_id}"
    )
    
    postponed_button = InlineKeyboardButton(
        text="🗓 Отложить",
        callback_data=f"postponed:{pp_id}"
    )
    
    # Создаем клавиатуру с обязательным полем inline_keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [source_button, show_full_button],
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

def get_keyword_proposal_keyboard(proposal_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для подтверждения или отклонения предложения ключевого слова.

    Args:
        proposal_id: ID предложения ключевого слова

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для подтверждения/отклонения
    """
    # Кнопки для подтверждения или отклонения предложения
    approve_button = InlineKeyboardButton(
        text="✅ Подтвердить",
        callback_data=f"approve_keyword:{proposal_id}"
    )

    reject_button = InlineKeyboardButton(
        text="❌ Отклонить",
        callback_data=f"reject_keyword:{proposal_id}"
    )

    # Создаем клавиатуру с обязательным полем inline_keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])

    return keyboard


def get_main_keyboard(lang: Optional[str] = None, *, is_admin: bool = False, is_operator: bool = False) -> ReplyKeyboardMarkup:
    """
    Создает основную клавиатуру для пользователя с учётом языка.
    """
    # Общие кнопки
    report_button = KeyboardButton(text=t(lang, "btn_report"))
    settings_button = KeyboardButton(text=t(lang, "btn_settings"))

    if is_admin:
        # Кнопки для администратора
        add_channel_button = KeyboardButton(text=t(lang, "btn_add_channel"))
        add_keyword_button = KeyboardButton(text=t(lang, "btn_add_keyword"))
        manage_operators_button = KeyboardButton(text=t(lang, "btn_manage_operators"))
        add_telethon_button = KeyboardButton(text=t(lang, "btn_add_telethon"))
        # Пакетная загрузка
        bulk_channels_button = KeyboardButton(text=t(lang, "btn_bulk_channels"))
        bulk_keywords_button = KeyboardButton(text=t(lang, "btn_bulk_keywords"))

        keyboard_buttons = [
            [add_channel_button, add_keyword_button],
            [manage_operators_button, add_telethon_button],
            [bulk_channels_button, bulk_keywords_button],
            [report_button, settings_button],
        ]
    elif is_operator:
        propose_channel_button = KeyboardButton(text=t(lang, "btn_propose_channel"))
        propose_keyword_button = KeyboardButton(text=t(lang, "btn_propose_keyword"))
        keyboard_buttons = [
            [propose_channel_button, propose_keyword_button],
            [report_button, settings_button],
        ]
    else:
        new_request_button = KeyboardButton(text=t(lang, "btn_request_operator"))
        feedback_button = KeyboardButton(text=t(lang, "btn_feedback"))
        help_button = KeyboardButton(text=t(lang, "btn_help"))
        keyboard_buttons = [
            [new_request_button],
            [feedback_button, help_button],
            [report_button, settings_button],
        ]

    return ReplyKeyboardMarkup(keyboard=keyboard_buttons, resize_keyboard=True)


def get_operator_access_request_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для запроса доступа оператора.

    Args:
        user_id: ID пользователя, которому предлагается доступ оператора

    Returns:
        InlineKeyboardMarkup: Клавиатура с кнопками для одобрения/отклонения доступа
    """
    approve_button = InlineKeyboardButton(
        text="✅ Выдать доступ",
        callback_data=f"approve_operator:{user_id}"
    )
    reject_button = InlineKeyboardButton(
        text="❌ Отклонить",
        callback_data=f"reject_operator:{user_id}"
    )
    return InlineKeyboardMarkup(inline_keyboard=[[approve_button, reject_button]])
