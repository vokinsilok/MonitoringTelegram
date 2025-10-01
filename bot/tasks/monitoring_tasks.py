import asyncio
import re
from typing import List, Set
from html import escape

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import RPCError
from telethon.tl.functions.messages import ImportChatInviteRequest, CheckChatInviteRequest

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from bot.keyboards.keyboards import get_post_keyboard

from app.core.config import settings
from app.core.logging import main_logger
from bot.models.keyword import KeywordType
from bot.utils.depend import get_atomic_db
from bot.utils.time_utils import format_dt, get_dt_format
from bot.utils.i18n import t


def _compile_keyword_patterns(keywords) -> List[tuple[int, str, re.Pattern]]:
    """Готовим паттерны в нижнем регистре, чтобы сравнивать с text.lower()."""
    patterns: List[tuple[int, str, re.Pattern]] = []
    for kw in keywords:
        if not kw.is_active:
            continue
        t = (kw.type or KeywordType.WORD.value)
        raw_text = kw.text or ""
        if not raw_text:
            continue
        text_l = raw_text.lower()
        if t == KeywordType.WORD.value:
            pat = re.compile(rf"\b{re.escape(text_l)}\b")
        elif t == KeywordType.PHRASE.value:
            pat = re.compile(re.escape(text_l))
        elif t == KeywordType.REGEX.value:
            try:
                pat = re.compile(text_l)
            except re.error:
                main_logger.error(f"Invalid regex keyword #{kw.id}: {raw_text}")
                continue
        else:
            pat = re.compile(re.escape(text_l))
        patterns.append((kw.id, text_l, pat))
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


def _clean_username(u: str | None) -> str | None:
    """Normalize a username or t.me URL to a bare username.
    Examples:
      '@channel' -> 'channel'
      'https://t.me/channel' -> 'channel'
      't.me/channel' -> 'channel'
    Returns lowercased username without '@'.
    """
    if not u:
        return None
    s = u.strip()
    # Strip message URL like https://t.me/username/123 -> username
    m = re.search(r"(?:https?://)?t\.me/([A-Za-z0-9_]+)/?", s)
    if m:
        s = m.group(1)
    if s.startswith('@'):
        s = s[1:]
    return s.lower()


def _extract_invite_hash(link: str | None) -> str | None:
    """Extract invite hash from t.me/+HASH or t.me/joinchat/HASH links."""
    if not link:
        return None
    s = link.strip()
    # Examples: https://t.me/+AbCdEfGhIj, t.me/+AbCdEf, https://t.me/joinchat/AbCd
    m = re.search(r"(?:https?://)?t\.me/(?:\+|joinchat/)([A-Za-z0-9_-]+)", s)
    if m:
        return m.group(1)
    return None


async def _resolve_channel_entity(client: TelegramClient, ch) -> object | None:
    """Resolve channel entity by username or invite link with fallbacks.
    Returns entity or None.
    """
    username = _clean_username(getattr(ch, 'channel_username', None))
    invite_link = getattr(ch, 'invite_link', None)

    # 1) Try by username first, if present
    if username:
        try:
            return await client.get_entity(username)
        except Exception as e:
            main_logger.error(f"get_entity error by username '{username}': {e}")

    # 2) Try invite link if provided
    if invite_link:
        # 2a) If it's a public t.me/username link, resolve as username
        pub_username = _clean_username(invite_link)
        if pub_username and not _extract_invite_hash(invite_link):
            try:
                return await client.get_entity(pub_username)
            except Exception as e:
                main_logger.error(f"get_entity error by public link '{invite_link}': {e}")

        # 2b) If it's a private invite link, try to check and import invite
        invite_hash = _extract_invite_hash(invite_link)
        if invite_hash:
            try:
                await client(CheckChatInviteRequest(invite_hash))
                res = await client(ImportChatInviteRequest(invite_hash))
                # res.chats typically contains the joined Chat/Channel
                if getattr(res, 'chats', None):
                    return res.chats[0]
                # fallback: try resolving again by link (now that we're a member)
                try:
                    return await client.get_entity(invite_link)
                except Exception:
                    pass
            except RPCError as e:
                main_logger.error(f"invite import failed for '{invite_link}': {e}")
            except Exception as e:
                main_logger.error(f"invite handling error for '{invite_link}': {e}")

    return None


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
                client = TelegramClient(StringSession(account.session_string or ""), int(account.api_id), account.api_hash, system_version="4.20.3-vxCUSTOM",
                                        device_model="PC", app_version="1.0.0", lang_code="ru")
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
                    entity = await _resolve_channel_entity(working_client, ch)
                    if not entity:
                        ref = ch.channel_username or ch.invite_link or 'unknown'
                        main_logger.error(f"resolve channel failed for '{ref}': not found or no access")
                        continue

                    min_id = ch.last_parsed_message_id or 0
                    max_processed_id = min_id

                    async for msg in working_client.iter_messages(entity, limit=200, min_id=min_id):
                        text = _extract_text_from_message(msg)
                        text_lower = text.lower() if text else ""
                        matched_kw_ids: List[int] = []
                        for kw_id, _, pat in patterns:
                            if pat.search(text_lower):
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
                    operator = await db.user.get_user_by_filter(id=pp.operator_id)
                    if not operator:
                        notified.add(pp.id)
                        continue
                    # Получаем настройки пользователя
                    st = await db.user.get_or_create_settings(operator.id)
                    lang = st.language
                    tz = st.time_zone
                    fmt = get_dt_format(lang)

                    post = pp.post
                    ch = post.channel if hasattr(post, "channel") else None
                    title = escape(getattr(ch, "title", "Канал") or "Канал")
                    text = post.text or "(без текста)"
                    preview = (text[:400] + "…") if len(text) > 400 else text
                    preview = escape(preview)
                    url = post.url or ""

                    # Собираем найденные ключевые слова
                    kw_texts = []
                    try:
                        for mk in getattr(post, "matched_keywords", []) or []:
                            if getattr(mk, "keyword", None) and mk.keyword.text:
                                tkw = mk.keyword.text
                                if tkw not in kw_texts:
                                    kw_texts.append(tkw)
                    except Exception:
                        pass
                    kw_line = ("\n" + t(lang, "notify_keywords", kws=", ".join(f"<code>{escape(k)}</code>" for k in kw_texts))) if kw_texts else ""

                    msg_text = (
                        f"{t(lang, 'notify_found')}\n\n"
                        f"{t(lang, 'notify_channel', title=title)}\n"
                        f"{t(lang, 'notify_date', dt=escape(format_dt(post.published_at, tz, fmt)))}\n"
                        f"{t(lang, 'notify_link', url=escape(url))}\n"
                        f"{kw_line}\n\n"
                        f"{t(lang, 'notify_text', preview=preview)}"
                    )
                    kb = get_post_keyboard(pp.id, post.id, url)
                    try:
                        sent = await bot.send_message(chat_id=operator.telegram_id, text=msg_text, reply_markup=kb, disable_web_page_preview=True)
                        await db.post.update_processing_notify_meta(pp.id, operator.telegram_id, sent.message_id)
                        notified.add(pp.id)
                    except Exception as e:
                        main_logger.error(f"notify send failed to {operator.telegram_id}: {e}")
        except Exception as e:
            main_logger.error(f"notify_loop error: {e}")
        await asyncio.sleep(interval)


def start_background_tasks(bot):
    loop = asyncio.get_event_loop()
    loop.create_task(parse_posts_loop(bot))
    loop.create_task(notify_loop(bot))
    main_logger.info("Background tasks started: parse_posts_loop, notify_loop")
