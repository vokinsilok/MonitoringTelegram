from __future__ import annotations
from datetime import datetime
from typing import Optional

import pytz
import re

# Соответствие коротких кодов таймзон внутренним идентификаторам pytz
TIMEZONE_MAP = {
    "UTC": "UTC",
    "GMT": "GMT",
    "MSK": "Europe/Moscow",
    "EST": "US/Eastern",
    "PST": "US/Pacific",
    "CET": "CET",
    "IST": "Asia/Kolkata",
    "AEST": "Australia/Sydney",
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
    """Возвращает pytz таймзону по пользовательскому коду.

    Приоритеты:
    1) Если в настройках указан полный идентификатор таймзоны (например, "Europe/Berlin", "Australia/Sydney"), используем его напрямую.
    2) Иначе пытаемся сопоставить короткий код из TIMEZONE_MAP (UTC, GMT, MSK, AEST, ...).
    3) По умолчанию — GMT.
    """
    raw = (code or "GMT")
    try:
        # Прямое использование полного имени TZ, если оно валидное
        if raw in pytz.all_timezones:
            return pytz.timezone(raw)
        # Иногда передают в разном регистре
        if raw.title() in pytz.all_timezones:
            return pytz.timezone(raw.title())
    except Exception:
        pass

    # Поддержка смещений вида: UTC+10, GMT-03:30, +5, -8, +0530, +05:30
    m = re.fullmatch(r"(?:(?:UTC|GMT)\s*)?([+-])\s*(\d{1,2})(?::?(\d{2}))?", str(raw).strip(), flags=re.IGNORECASE)
    if m:
        sign, hh, mm = m.group(1), m.group(2), m.group(3)
        hours = int(hh)
        minutes = int(mm) if mm else 0
        total_min = hours * 60 + minutes
        if sign == '-':
            total_min = -total_min
        return pytz.FixedOffset(total_min)

    tz_name = TIMEZONE_MAP.get(raw.upper(), "GMT")
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
