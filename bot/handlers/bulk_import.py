import io
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


def _split_lines(content: bytes) -> List[str]:
    text = content.decode("utf-8", errors="ignore")
    lines = [l.strip() for l in text.replace("\r", "").split("\n")]
    return [l for l in lines if l]


def _parse_channel_line(line: str) -> Tuple[str | None, str | None, str]:
    """Возвращает (channel_username, invite_link, title)."""
    raw = line.strip()
    if not raw:
        return None, None, ""
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
    if not doc or (doc.file_name and not doc.file_name.lower().endswith(".txt")):
        await message.answer("Загрузите .txt файл.")
        return
    buf = io.BytesIO()
    try:
        await message.bot.download(doc.file_id, destination=buf)
        buf.seek(0)
        lines = _split_lines(buf.getvalue())
    except Exception as e:
        main_logger.error(f"bulk channels download error: {e}")
        await message.answer("Не удалось прочитать файл.")
        return

    created = 0
    skipped = 0
    async with get_atomic_db() as db:
        for line in lines:
            username, invite, title = _parse_channel_line(line)
            if not title:
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
