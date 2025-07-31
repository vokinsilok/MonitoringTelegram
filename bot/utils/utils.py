import datetime
from typing import List, Optional, Union

from aiogram.types import Message, User as TelegramUser

# Импортируем конфигурацию из backend
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from backend.app.core.config import settings


def is_admin(user_id: int) -> bool:
    """
    Проверяет, является ли пользователь администратором.
    
    Args:
        user_id: Telegram ID пользователя
    
    Returns:
        bool: True, если пользователь является администратором, иначе False
    """
    return user_id in settings.get_admin_ids()


async def format_post_message(post: dict) -> str:
    """
    Форматирует сообщение с постом для отправки оператору.
    
    Args:
        post: Словарь с данными поста
    
    Returns:
        str: Отформатированное сообщение
    """
    channel_title = post.get("channel_title", "Неизвестный канал")
    published_at = post.get("published_at", datetime.datetime.now())
    text = post.get("text", "")
    
    # Ограничиваем длину текста для предварительного просмотра
    preview_text = text[:300] + "..." if len(text) > 300 else text
    
    message = (
        f"<b>Новый пост из канала:</b> {channel_title}\n"
        f"<b>Дата публикации:</b> {published_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"{preview_text}"
    )
    
    return message


async def format_full_post_message(post: dict) -> str:
    """
    Форматирует полное сообщение с постом для показа оператору.
    
    Args:
        post: Словарь с данными поста
    
    Returns:
        str: Отформатированное сообщение
    """
    channel_title = post.get("channel_title", "Неизвестный канал")
    published_at = post.get("published_at", datetime.datetime.now())
    text = post.get("text", "")
    url = post.get("url", "")
    
    message = (
        f"<b>Полный пост из канала:</b> {channel_title}\n"
        f"<b>Дата публикации:</b> {published_at.strftime('%d.%m.%Y %H:%M')}\n"
        f"<b>Ссылка:</b> {url}\n\n"
        f"{text}"
    )
    
    return message


async def format_report_message(reports: List[dict], start_date: datetime.date, end_date: datetime.date) -> str:
    """
    Форматирует отчет по обработанным постам.
    
    Args:
        reports: Список словарей с данными отчетов
        start_date: Начальная дата отчета
        end_date: Конечная дата отчета
    
    Returns:
        str: Отформатированное сообщение с отчетом
    """
    if not reports:
        return f"Отчет за период {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}: нет данных"
    
    message = f"<b>Отчет за период {start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}:</b>\n\n"
    
    for i, report in enumerate(reports, 1):
        operator_comment = report.get("comment", "Нет комментария")
        source = report.get("channel_title", "Неизвестный источник")
        published_at = report.get("published_at", datetime.datetime.now())
        status = report.get("status", "Неизвестно")
        processed_at = report.get("processed_at", datetime.datetime.now())
        operator_name = report.get("operator_name", "Неизвестный оператор")
        url = report.get("url", "")
        
        message += (
            f"{i}. <b>Комментарий:</b> {operator_comment}\n"
            f"   <b>Источник:</b> {source}\n"
            f"   <b>Дата публикации:</b> {published_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   <b>Статус:</b> {status}\n"
            f"   <b>Дата обработки:</b> {processed_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"   <b>Оператор:</b> {operator_name}\n"
            f"   <b>Ссылка:</b> {url}\n\n"
        )
    
    return message


def extract_user_data(telegram_user: TelegramUser) -> dict:
    """
    Извлекает данные пользователя из объекта TelegramUser.
    
    Args:
        telegram_user: Объект пользователя Telegram
    
    Returns:
        dict: Словарь с данными пользователя
    """
    return {
        "telegram_id": telegram_user.id,
        "username": telegram_user.username,
        "first_name": telegram_user.first_name,
        "last_name": telegram_user.last_name,
    }
