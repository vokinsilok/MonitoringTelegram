from __future__ import annotations
from typing import Dict
import re
import html

# Очень простой словарь переводов. Можно расширять.
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    "ru": {
        "report_title": "📊 Отчёт (за последние {hours} часа)",
        "total_channels": "1. Всего каналов: <b>{n}</b>",
        "total_keywords": "2. Всего ключевых слов: <b>{n}</b>",
        "found_posts": "3. Найдено постов по ключевым словам: <b>{n}</b>",
        "processed": "4. Разобрано: <b>{n}</b>",
        "postponed": "5. Отложенно: <b>{n}</b>",
        "pending": "6. Ожидающие разбора: <b>{n}</b>",
        "operators_header": "\n\n👤 <b>Операторы, разбиравшие инциденты:</b>",
        "dash": "—",
        "detailed_report_caption": "Подробный отчёт",
        "settings_title": "⚙️ <b>Настройки</b>",
        "settings_main": "Выберите раздел настроек ниже.",
        "settings_lang": "Язык интерфейса: <b>{lang_code}</b>",
        "settings_tz": "Часовой пояс: <b>{tz}</b>",
        "settings_choose": "Выберите новые значения ниже.",
        "choose_lang_title": "🌐 Выбор языка",
        "choose_tz_title": "🕒 Выбор часового пояса",
        "btn_lang": "🌐 Язык",
        "btn_tz": "🕒 Часовой пояс",
        "back": "⬅️ Назад",
        "saved": "Сохранено",
        "invalid_language": "Недопустимый язык",
        "invalid_tz": "Недопустимая TZ",
        "notify_found": "🔍 <b>Найден пост по ключевым словам</b>",
        "notify_channel": "📢 <b>Канал:</b> {title}",
        "notify_date": "🕒 <b>Дата:</b> {dt}",
        "notify_link": "🔗 <b>Ссылка:</b> {url}",
        "notify_keywords": "<b>Ключевые слова:</b> {kws}",
        "notify_text": "<b>Текст:</b>\n{preview}",
        "btn_report": "📊 Отчет",
        "btn_settings": "⚙️ Настройки",
        "btn_add_channel": "➕ Добавить канал",
        "btn_add_keyword": "🔑 Добавить ключевое слово",
        "btn_manage_operators": "👥 Управление операторами",
        "btn_add_telethon": "🔐 Добавить Telethon",
        "btn_bulk_channels": "📥 Добавить каналы",
        "btn_bulk_keywords": "📥 Добавить ключевые слова",
        "btn_propose_channel": "📢 Предложить канал",
        "btn_propose_keyword": "🔍 Предложить ключевое слово",
        "btn_request_operator": "📝 Получить доступ оператора",
        "btn_feedback": "💬 Обратная связь",
        "btn_help": "❓О системе",
    },
    "en": {
        "report_title": "📊 Report (last {hours} hours)",
        "total_channels": "1. Total channels: <b>{n}</b>",
        "total_keywords": "2. Total keywords: <b>{n}</b>",
        "found_posts": "3. Posts matched: <b>{n}</b>",
        "processed": "4. Processed: <b>{n}</b>",
        "postponed": "5. Postponed: <b>{n}</b>",
        "pending": "6. Pending: <b>{n}</b>",
        "operators_header": "\n\n👤 <b>Operators who handled incidents:</b>",
        "dash": "—",
        "detailed_report_caption": "Detailed report",
        "settings_title": "⚙️ <b>Settings</b>",
        "settings_main": "Choose a settings section below.",
        "settings_lang": "Interface language: <b>{lang_code}</b>",
        "settings_tz": "Time zone: <b>{tz}</b>",
        "settings_choose": "Choose new values below.",
        "choose_lang_title": "🌐 Language selection",
        "choose_tz_title": "🕒 Time zone selection",
        "btn_lang": "🌐 Language",
        "btn_tz": "🕒 Time zone",
        "back": "⬅️ Back",
        "saved": "Saved",
        "invalid_language": "Invalid language",
        "invalid_tz": "Invalid TZ",
        "notify_found": "🔍 <b>Post matched by keywords</b>",
        "notify_channel": "📢 <b>Channel:</b> {title}",
        "notify_date": "🕒 <b>Date:</b> {dt}",
        "notify_link": "🔗 <b>Link:</b> {url}",
        "notify_keywords": "<b>Keywords:</b> {kws}",
        "notify_text": "<b>Text:</b>\n{preview}",
        "btn_report": "📊 Report",
        "btn_settings": "⚙️ Settings",
        "btn_add_channel": "➕ Add channel",
        "btn_add_keyword": "🔑 Add keyword",
        "btn_manage_operators": "👥 Manage operators",
        "btn_add_telethon": "🔐 Add Telethon",
        "btn_bulk_channels": "📥 Import channels",
        "btn_bulk_keywords": "📥 Import keywords",
        "btn_propose_channel": "📢 Propose channel",
        "btn_propose_keyword": "🔍 Propose keyword",
        "btn_request_operator": "📝 Request operator access",
        "btn_feedback": "💬 Feedback",
        "btn_help": "❓About",
    },
}


def t(lang: str | None, key: str, **kwargs) -> str:
    lang = (lang or "ru").lower()
    data = TRANSLATIONS.get(lang) or TRANSLATIONS["ru"]
    template = data.get(key) or TRANSLATIONS["ru"].get(key) or key
    try:
        return template.format(**kwargs)
    except Exception:
        return template


# Утилиты для преобразования HTML-текста (телеграм) в простой текст для DOCX
_def_tag_block = re.compile(r"<[^>]+>")

def strip_html(text: str) -> str:
    if not text:
        return ""
    # Переводы строк
    text = text.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    # Ссылки: сохраняем внутренний текст
    text = re.sub(r"<a\b[^>]*>(.*?)</a>", r"\1", text, flags=re.IGNORECASE | re.DOTALL)
    # Простые теги форматирования удаляем, оставляя содержимое
    text = re.sub(r"</?(b|strong|i|em|u|s|code|pre|blockquote)>", "", text, flags=re.IGNORECASE)
    # Удаляем остальные теги, если остались
    text = re.sub(r"<[^>]+>", "", text)
    # Декодируем HTML-сущности
    return html.unescape(text)


def t_plain(lang: str | None, key: str, **kwargs) -> str:
    """Возвращает локализованную строку без HTML-тегов (для DOCX)."""
    return strip_html(t(lang, key, **kwargs))
