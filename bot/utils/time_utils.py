from __future__ import annotations
from datetime import datetime
from typing import Optional

import pytz

# Соответствие коротких кодов таймзон внутренним идентификаторам pytz
TIMEZONE_MAP = {
    "UTC": "UTC",
    "GMT": "GMT",
    "MSK": "Europe/Moscow",
    "EST": "US/Eastern",
    "PST": "US/Pacific",
    "CET": "CET",
    "IST": "Asia/Kolkata",
}

# Рекомендуемые форматы даты/времени по языку интерфейса пользователя
# Можно расширять при необходимости.
LANG_DT_FORMATS = {
    "ru": "%d.%m.%Y %H:%M:%S",
    "en": "%Y-%m-%d %H:%M:%S",
    "es": "%d/%m/%Y %H:%M:%S",
    "fr": "%d/%m/%Y %H:%M:%S",
    "de": "%d.%m.%Y %H:%M:%S",
}

def get_dt_format(lang: Optional[str]) -> str:
    """Возвращает строку формата datetime, соответствующую языку пользователя.

    Если язык не распознан, используется дефолтный ISO-подобный формат.
    """
    if not lang:
        return "%Y-%m-%d %H:%M:%S"
    return LANG_DT_FORMATS.get(lang.lower(), "%Y-%m-%d %H:%M:%S")


def get_tz(code: Optional[str]) -> pytz.BaseTzInfo:
    tz_name = TIMEZONE_MAP.get((code or "GMT").upper(), "GMT")
    return pytz.timezone(tz_name)


def to_local(dt: Optional[datetime], code: Optional[str]) -> Optional[datetime]:
    if dt is None:
        return None
    tz = get_tz(code)
    # Если datetime наивный — считаем, что это UTC
    if dt.tzinfo is None:
        dt = pytz.UTC.localize(dt)
    return dt.astimezone(tz)


def format_dt(dt: Optional[datetime], code: Optional[str], fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    if dt is None:
        return ""
    local = to_local(dt, code)
    if local is None:
        return ""
    # Добавим метку TZ в конец
    return f"{local.strftime(fmt)} {local.tzname()}"
