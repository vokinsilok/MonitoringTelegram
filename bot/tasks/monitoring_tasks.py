import asyncio
import re
from typing import List, Set

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.config import settings
from app.core.logging import main_logger
from bot.models.keyword import KeywordType
from bot.utils.depend import get_atomic_db


def _compile_keyword_patterns(keywords) -> List[tuple[int, str, re.Pattern]]:
    patterns: List[tuple[int, str, re.Pattern]] = []
    for kw in keywords:
        if not kw.is_active:
            continue
        t = (kw.type or KeywordType.WORD.value)
        text = kw.text or ""
        if not text:
            continue
        if t == KeywordType.WORD.value:
            pat = re.compile(rf"\b{re.escape(text)}\b", re.IGNORECASE)
        elif t == KeywordType.PHRASE.value:
            pat = re.compile(re.escape(text), re.IGNORECASE)
        elif t == KeywordType.REGEX.value:
            try:
                pat = re.compile(text, re.IGNORECASE)
            except re.error:
                main_logger.error(f"Invalid regex keyword #{kw.id}: {text}")
                continue
        else:
            pat = re.compile(re.escape(text), re.IGNORECASE)
        patterns.append((kw.id, text, pat))
    return patterns


async def _iter_active_channels_and_keywords():
    async with get_atomic_db() as db:
        channels = await db.channel.list_active_channels()
        keywords = await db.keywords.get_all_keywords()
        active_keywords = [k for k in keywords if getattr(k, "is_active", True)]
    return channels, active_keywords


async def _select_telethon_accounts():
    async with get_atomic_db() as db:
        return await db.telethon.list_active_accounts()


async def _select_telethon_account():
    async with get_atomic_db() as db:
        accs = await db.telethon.list_active_accounts()
        return accs[0] if accs else None


def _extract_text_from_message(msg) -> str:
    try:
        # Telethon Message supports .message or .text
        return (msg.message or msg.raw_text or "")
    except Exception:
        return ""


def _detect_media_type(msg) -> str | None:
    try:
        if msg.photo:
            return "photo"
        if msg.video:
            return "video"
        if msg.document:
            return "document"
        if msg.audio:
            return "audio"
        if msg.voice:
            return "voice"
    except Exception:
        pass
    return None


async def _notify_admins_account_problem(account, bot, error_text: str, notified_accounts: Set[int]):
    if account.id in notified_accounts:
        return
    try:
        async with get_atomic_db() as db:
            admins = await db.user.get_admins()
        if not admins:
            return
        kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Восстановить аккаунт", callback_data=f"telethon_repair:{account.id}")]
            ]
        )
        msg = (
            "⚠️ Проблема с Telethon-аккаунтом\n\n"
            f"Имя: {account.name}\n"
            f"Телефон: {account.phone}\n"
            f"Описание: {account.description or '-'}\n\n"
            f"Ошибка: {error_text}\n\n"
            "Нажмите кнопку ниже, чтобы начать восстановление авторизации."
        )
        sent_any = False
        for admin in admins:
            try:
                await bot.send_message(admin.telegram_id, msg, reply_markup=kb)
                sent_any = True
            except Exception as e:
                main_logger.error(f"send admin account problem to {admin.telegram_id} failed: {e}")
        if sent_any:
            notified_accounts.add(account.id)
    except Exception as e:
        main_logger.error(f"_notify_admins_account_problem error: {e}")


async def parse_posts_loop(bot):
    """Фоновая задача: парсит посты по активным каналам и создаёт Post/Matches/PostProcessing.
    При проблемах с аккаунтом помечает его как неавторизованный, уведомляет админов и пытается следующий аккаунт."""
    interval = int(getattr(settings, "PARSE_TASK_INTERVAL_SEC", 60))
    notified_accounts: Set[int] = set()
    while True:
        try:
            accounts = await _select_telethon_accounts()
            if not accounts:
                main_logger.warning("Нет доступных авторизованных Telethon-аккаунтов. Ожидаю…")
                await asyncio.sleep(interval)
                continue

            # Перебираем аккаунты, пока не найдём рабочий
            working_client = None
            working_account = None
            for account in accounts:
                client = TelegramClient(StringSession(account.session_string or ""), int(account.api_id), account.api_hash)
                try:
                    await client.connect()
                    if not await client.is_user_authorized():
                        raise RuntimeError("Аккаунт не авторизован")
                    working_client = client
                    working_account = account
                    break
                except Exception as e:
                    # Помечаем аккаунт как неавторизованный и уведомляем админов
                    err = f"auth/connect error: {e}"
                    main_logger.error(f"Account {account.phone} unusable: {err}")
                    try:
                        async with get_atomic_db() as db:
                            await db.telethon.update_account(account.id, {"is_authorized": False})
                    except Exception as up_err:
                        main_logger.error(f"mark account unauthorized failed: {up_err}")
                    await _notify_admins_account_problem(account, bot, err, notified_accounts)
                    try:
                        await client.disconnect()
                    except Exception:
                        pass
                    continue

            if not working_client or not working_account:
                # Все аккаунты не подошли
                main_logger.warning("Все Telethon-аккаунты недоступны. Ожидаю появления рабочего…")
                await asyncio.sleep(interval)
                continue

            # Есть рабочий клиент — загружаем данные и парсим
            channels, keywords = await _iter_active_channels_and_keywords()
            if not channels or not keywords:
                try:
                    await working_client.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(interval)
                continue

            patterns = _compile_keyword_patterns(keywords)
            if not patterns:
                try:
                    await working_client.disconnect()
                except Exception:
                    pass
                await asyncio.sleep(interval)
                continue

            try:
                for ch in channels:
                    entity_ref = ch.channel_username or ch.invite_link
                    if not entity_ref:
                        continue
                    try:
                        entity = await working_client.get_entity(entity_ref)
                    except RPCError as e:
                        main_logger.error(f"get_entity failed for channel {entity_ref}: {e}")
                        continue
                    except Exception as e:
                        main_logger.error(f"get_entity error for channel {entity_ref}: {e}")
                        continue

                    min_id = ch.last_parsed_message_id or 0
                    max_processed_id = min_id

                    async for msg in working_client.iter_messages(entity, limit=200, min_id=min_id):
                        text = _extract_text_from_message(msg)
                        if not text:
                            # Если нет текста — можем проверять подписи/медиа при желании
                            text = ""
                        matched_kw_ids: List[int] = []
                        for kw_id, _, pat in patterns:
                            if pat.search(text):
                                matched_kw_ids.append(kw_id)
                        if not matched_kw_ids:
                            max_processed_id = max(max_processed_id, msg.id)
                            continue

                        # Найдено совпадение — сохраняем пост и связи
                        async with get_atomic_db() as db:
                            # Проверяем, не создан ли уже пост
                            existing = await db.post.get_post_by_channel_message(ch.id, msg.id)
                            if existing:
                                post = existing
                            else:
                                url = None
                                if ch.channel_username:
                                    url = f"https://t.me/{ch.channel_username}/{msg.id}"
                                media_type = _detect_media_type(msg)
                                post_values = {
                                    "channel_id": ch.id,
                                    "message_id": msg.id,
                                    "text": text,
                                    "html_text": None,
                                    "media_type": media_type,
                                    "media_file_id": None,
                                    "published_at": msg.date,
                                    "url": url,
                                }
                                post = await db.post.create_post(post_values)

                            # Связи с ключевыми словами
                            for kid in matched_kw_ids:
                                try:
                                    await db.post.create_keyword_match(post.id, kid)
                                except Exception:
                                    pass

                            # Назначаем PostProcessing всем операторам и админам
                            operators = await db.user.get_operators(page=1, per_page=1000)
                            admins = await db.user.get_admins()
                            recipients = list({u.id: u for u in [*operators, *admins]}.values())
                            for u in recipients:
                                exists_proc = await db.post.get_processing_for_post_operator(post.id, u.id)
                                if not exists_proc:
                                    try:
                                        await db.post.create_processing(post.id, u.id)
                                    except Exception:
                                        pass

                        max_processed_id = max(max_processed_id, msg.id)

                    if max_processed_id > (ch.last_parsed_message_id or 0):
                        async with get_atomic_db() as db:
                            await db.channel.update_last_parsed(ch.id, max_processed_id)
                            await db.channel.touch_checked(ch.id)

            finally:
                try:
                    await working_client.disconnect()
                except Exception:
                    pass
        except Exception as e:
            main_logger.error(f"parse_posts_loop error: {e}")
        await asyncio.sleep(interval)


async def notify_loop(bot):
    """Фоновая задача: рассылает уведомления по PostProcessing операторам/админам."""
    interval = int(getattr(settings, "NOTIFY_TASK_INTERVAL_SEC", 120))
    lookback_h = int(getattr(settings, "NOTIFY_LOOKBACK_HOURS", 24))
    notified: Set[int] = set()  # in-memory защита от повторной отправки за сессию процесса

    while True:
        try:
            async with get_atomic_db() as db:
                items = await db.post.get_pending_processing(within_hours=lookback_h)
                for pp in items:
                    if pp.id in notified:
                        continue
                    # Загружаем пользователя, чтобы получить telegram_id
                    operator = await db.user.get_user_by_filter(id=pp.operator_id)
                    if not operator:
                        notified.add(pp.id)
                        continue
                    post = pp.post
                    ch = post.channel if hasattr(post, "channel") else None
                    title = getattr(ch, "title", "Канал")
                    user_display = operator.full_name if hasattr(operator, "full_name") else str(operator.telegram_id)
                    text = post.text or "(без текста)"
                    preview = (text[:400] + "…") if len(text) > 400 else text
                    url = post.url or ""
                    msg = (
                        f"🔍 Найден пост по ключевым словам\n\n"
                        f"Канал: {title}\n"
                        f"Дата: {post.published_at:%Y-%m-%d %H:%M:%S}\n"
                        f"Ссылка: {url}\n\n"
                        f"Текст:\n{preview}"
                    )
                    try:
                        await bot.send_message(chat_id=operator.telegram_id, text=msg, disable_web_page_preview=True)
                        notified.add(pp.id)
                    except Exception as e:
                        main_logger.error(f"notify send failed to {operator.telegram_id}: {e}")
                        # Не помечаем как отправленное, попробуем позже
        except Exception as e:
            main_logger.error(f"notify_loop error: {e}")
        await asyncio.sleep(interval)


def start_background_tasks(bot):
    loop = asyncio.get_event_loop()
    loop.create_task(parse_posts_loop(bot))
    loop.create_task(notify_loop(bot))
    main_logger.info("Background tasks started: parse_posts_loop, notify_loop")
