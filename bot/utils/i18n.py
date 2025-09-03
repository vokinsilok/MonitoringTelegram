from __future__ import annotations
from typing import Dict

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
        "settings_lang": "Язык интерфейса: <b>{lang}</b>",
        "settings_tz": "Часовой пояс: <b>{tz}</b>",
        "settings_choose": "Выберите новые значения ниже.",
        "saved": "Сохранено",
        "invalid_language": "Недопустимый язык",
        "invalid_tz": "Недопустимая TZ",
        "notify_found": "🔍 <b>Найден пост по ключевым словам</b>",
        "notify_channel": "📢 <b>Канал:</b> {title}",
        "notify_date": "🕒 <b>Дата:</b> {dt}",
        "notify_link": "🔗 <b>Ссылка:</b> {url}",
        "notify_keywords": "<b>Ключевые слова:</b> {kws}",
        "notify_text": "<b>Текст:</b>\n{preview}",
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
        "settings_lang": "Interface language: <b>{lang}</b>",
        "settings_tz": "Time zone: <b>{tz}</b>",
        "settings_choose": "Choose new values below.",
        "saved": "Saved",
        "invalid_language": "Invalid language",
        "invalid_tz": "Invalid TZ",
        "notify_found": "🔍 <b>Post matched by keywords</b>",
        "notify_channel": "📢 <b>Channel:</b> {title}",
        "notify_date": "🕒 <b>Date:</b> {dt}",
        "notify_link": "🔗 <b>Link:</b> {url}",
        "notify_keywords": "<b>Keywords:</b> {kws}",
        "notify_text": "<b>Text:</b>\n{preview}",
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

