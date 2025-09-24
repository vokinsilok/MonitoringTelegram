import io
import re
from typing import List, Tuple, cast

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message

from app.core.logging import main_logger
from bot.schemas.channel import AddChannel
from bot.schemas.keyword_schema import KeyWordCreateSchema
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db
from bot.models.keyword import KeywordType

router = Router()


class BulkImportChannels(StatesGroup):
    waiting_for_file = State()


class BulkImportKeywords(StatesGroup):
    waiting_for_file = State()


def _is_probably_binary(data: bytes) -> bool:
    """Грубая эвристика: бинарный файл, если содержит NUL в первых байтах или zip-магик."""
    head = data[:4096]
    if b"\x00" in head:
        return True
    # xlsx/docx/pdf/zip
    if head.startswith(b"PK\x03\x04"):
        return True
    return False


def _sanitize_text(s: str) -> str:
    """Удаляет NUL и управляющие символы, обрезает пробелы."""
    if not s:
        return ""
    # удалить NUL
    s = s.replace("\x00", "")
    # удалить прочие управляющие, кроме \t\n\r
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)
    return s.strip()


def _split_lines(content: bytes) -> List[str]:
    # Если это бинарный файл (xlsx/zip) — вернём пустой список, выше обработаем это сообщением
    text = content.decode("utf-8", errors="ignore")
    # нормализуем переносы строк
    text = text.replace("\r", "")
    # очищаем управляющие символы и NUL
    text = _sanitize_text(text)
    lines = [l.strip() for l in text.split("\n")]
    # отфильтруем пустые строки
    return [l for l in lines if l]


def _extract_username(link_or_username: str | None) -> str | None:
    """Возвращает чистый username без @ и ссылок t.me, если возможно."""
    if not link_or_username:
        return None
    s = link_or_username.strip()
    if s.startswith("http://") or s.startswith("https://"):
        if "t.me/" in s:
            try:
                part = s.split("t.me/")[1]
                s = part.split("/")[0].split("?")[0]
            except Exception:
                pass
    if s.startswith("@"):
        s = s[1:]
    return s or None


async def _resolve_real_title(bot, link_or_username: str | None) -> str | None:
    """Пытается получить реальный title канала через Bot API по username/ссылке."""
    try:
        username = _extract_username(link_or_username or "")
        if not username:
            return None
        # Для Bot API предпочтительно передавать '@username'
        chat_id = username if username.startswith("@") else f"@{username}"
        chat = await bot.get_chat(chat_id)
        title = getattr(chat, "title", None)
        return title or None
    except Exception:
        return None


def _parse_channel_line(line: str) -> Tuple[str | None, str | None, str]:
    """Возвращает (channel_username, invite_link, title) из строки.
    Поддерживает форматы:
    - простой: "@username" | "https://t.me/username" | "Название канала"
    - CSV: "username,title,link,status,description,is_private,..."
    """
    raw = line.strip()
    if not raw:
        return None, None, ""

    # Попытка CSV: split по запятым (простая, без кавычек)
    if "," in raw:
        parts = [p.strip() for p in raw.split(",")]
        # ожидаем минимум 3 поля: username, title, link
        if len(parts) >= 3:
            csv_username = parts[0].lstrip("@") or None
            csv_title = parts[1] or ""
            csv_link = parts[2] or None
            # нормализуем username из ссылки при необходимости
            if (not csv_username) and (csv_link and "t.me/" in csv_link):
                try:
                    part = csv_link.split("t.me/")[1]
                    csv_username = part.split("/")[0].split("?")[0]
                except Exception:
                    pass
            return (csv_username or None), (csv_link or None), csv_title

    # Простой формат
    if raw.startswith("@"):
        username = raw.lstrip("@").split()[0]
        return username, None, username
    if "t.me/" in raw:
        # https://t.me/username or http://t.me/username/123
        try:
            part = raw.split("t.me/")[1]
            username = part.split("/")[0].split("?")[0]
            username = username.replace("+", "")  # для joinchat ссылки оставим как приглашающую ссылку
        except Exception:
            username = None
        return username or None, raw, username or raw
    # Иначе считаем это заголовком
    return None, None, raw


@router.message(F.text == "📥 Добавить каналы")
async def start_bulk_channels(message: Message, state: FSMContext):
    if not await UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ Недостаточно прав. Функция доступна только администраторам.")
        return
    await message.answer("Пришлите .txt файл с каналами (каждая строка — @username, ссылка t.me/... или название канала).")
    await state.set_state(BulkImportChannels.waiting_for_file)


@router.message(BulkImportChannels.waiting_for_file, F.document)
async def handle_bulk_channels_file(message: Message, state: FSMContext):
    if not await UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ Нет прав.")
        return
    doc = message.document
    if not doc or (doc.file_name and not (doc.file_name.lower().endswith(".txt") or doc.file_name.lower().endswith(".csv"))):
        await message.answer("Загрузите .txt или .csv файл.")
        return
    buf = io.BytesIO()
    try:
        await message.bot.download(doc.file_id, destination=buf)
        buf.seek(0)
        data = buf.getvalue()
        # Проверка на бинарные форматы (часто пользователи присылают .xlsx)
        if _is_probably_binary(data):
            await message.answer("Файл выглядит как бинарный (например, .xlsx/.docx). Пожалуйста, пришлите простой .txt файл, где каждая строка — @username, ссылка t.me/... или название канала.")
            return
        lines = _split_lines(data)
    except Exception as e:
        main_logger.error(f"bulk channels download error: {e}")
        await message.answer("Не удалось прочитать файл.")
        return

    created = 0
    skipped = 0
    async with get_atomic_db() as db:
        for line in lines:
            username, invite, title = _parse_channel_line(line)
            # Санитизируем поля
            if username:
                username = _sanitize_text(username)
            if invite:
                invite = _sanitize_text(invite)
            title = _sanitize_text(title)
            # Попробуем получить реальный title по username/ссылке
            if (username or invite) and not title:
                real_title = await _resolve_real_title(message.bot, username or invite)
                if real_title:
                    title = _sanitize_text(real_title)
            elif (username or invite):
                real_title = await _resolve_real_title(message.bot, username or invite)
                if real_title:
                    title = _sanitize_text(real_title)
            # Базовые валидации
            if not title:
                skipped += 1
                continue
            if len(title) > 200:
                # подозрительно длинная строка — вероятно мусор из бинарного
                skipped += 1
                continue
            # Проверка существования
            exists = None
            if username:
                exists = await db.channel.get_channel_by_filter(channel_username=username)
            if not exists:
                exists = await db.channel.get_channel_by_filter(title=title)
            if exists:
                skipped += 1
                continue
            try:
                await db.channel.create_channel(AddChannel(
                    channel_username=username,
                    title=title,
                    invite_link=invite,
                    status="disabled",
                    description=None,
                    is_private=False,
                    last_parsed_message_id=None,
                    last_checked=None,
                ))
                created += 1
            except Exception as e:
                main_logger.error(f"create channel failed for line '{line}': {e}")
                skipped += 1

    await state.clear()
    await message.answer(f"Готово. Добавлено каналов: {created}. Пропущено: {skipped}.")


@router.message(F.text == "📥 Добавить ключевые слова")
async def start_bulk_keywords(message: Message, state: FSMContext):
    if not await UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ Недостаточно прав. Функция доступна только администраторам.")
        return
    await message.answer("Пришлите .txt файл с ключевыми словами (каждая строка — одно слово/фраза/регэксп).")
    await state.set_state(BulkImportKeywords.waiting_for_file)


@router.message(BulkImportKeywords.waiting_for_file, F.document)
async def handle_bulk_keywords_file(message: Message, state: FSMContext):
    if not await UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ Нет прав.")
        return
    doc = message.document
    if not doc or (doc.file_name and not doc.file_name.lower().endswith(".txt")):
        await message.answer("Загрузите .txt файл.")
        return
    buf = io.BytesIO()
    try:
        await message.bot.download(doc.file_id, destination=buf)
        buf.seek(0)
        lines = _split_lines(buf.getvalue())
    except Exception as e:
        main_logger.error(f"bulk keywords download error: {e}")
        await message.answer("Не удалось прочитать файл.")
        return

    # Загружаем существующие в lower для де-дупликации
    existing_lower = set()
    async with get_atomic_db() as db:
        all_kw = await db.keywords.get_all_keywords()
        existing_lower = { (k.text or "").strip().lower() for k in all_kw }

    to_create: List[KeyWordCreateSchema] = []
    for line in lines:
        norm = line.strip()
        if not norm:
            continue
        if norm.lower() in existing_lower:
            continue
        to_create.append(KeyWordCreateSchema(text=cast(str, norm), type=KeywordType.WORD, is_active=True))
        existing_lower.add(norm.lower())

    created = 0
    async with get_atomic_db() as db:
        for payload in to_create:
            try:
                await db.keywords.create_keyword(payload)
                created += 1
            except Exception as e:
                main_logger.error(f"create keyword failed for '{payload.text}': {e}")

    await state.clear()
    await message.answer(f"Готово. Добавлено ключевых слов: {created}. Пропущено: {len(lines) - created}.")
