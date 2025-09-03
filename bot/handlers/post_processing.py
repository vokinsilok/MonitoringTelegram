from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime

from app.core.logging import main_logger
from bot.models.post import PostStatus
from bot.utils.depend import get_atomic_db

router = Router()


async def _cleanup_other_notifications(bot, post_id: int, exclude_pp_id: int):
    async with get_atomic_db() as db:
        siblings = await db.post.get_siblings_processings(post_id, exclude_pp_id)
    for s in siblings:
        if s.notify_chat_id and s.notify_message_id:
            try:
                await bot.delete_message(chat_id=s.notify_chat_id, message_id=s.notify_message_id)
            except Exception as e:
                main_logger.warning(f"delete notify message failed chat={s.notify_chat_id} msg={s.notify_message_id}: {e}")


def _split_chunks(text: str, size: int = 4000):
    for i in range(0, len(text), size):
        yield text[i:i + size]


@router.callback_query(F.data.startswith("show_full:"))
async def cb_show_full(callback: CallbackQuery):
    try:
        post_id = int(callback.data.split(":")[1])
    except Exception:
        await callback.answer("Некорректные данные", show_alert=False)
        return

    async with get_atomic_db() as db:
        post = await db.post.get(post_id)
    if not post:
        await callback.answer("Пост не найден", show_alert=False)
        return

    # Предпочтительно отправляем html_text, если есть. Иначе — обычный текст, отключая parse_mode.
    header = "📄 Полный текст поста\n"
    if getattr(post, "url", None):
        header += f"Ссылка: {post.url}\n\n"

    try:
        if getattr(post, "html_text", None):
            text = post.html_text
            # Отправляем как HTML, разобьём по частям
            first = True
            for chunk in _split_chunks(text, 3500):
                await callback.message.answer((header if first else "") + chunk)
                first = False
        elif getattr(post, "text", None):
            text = post.text
            first = True
            for chunk in _split_chunks(text, 4000):
                # Отключаем parse_mode для сырых сообщений, чтобы не ломать спецсимволы
                await callback.message.bot.send_message(
                    chat_id=callback.message.chat.id,
                    text=(header if first else "") + chunk,
                    parse_mode=None,
                    disable_web_page_preview=True,
                )
                first = False
        else:
            await callback.answer("Текст отсутствует", show_alert=False)
            return
    except Exception as e:
        main_logger.error(f"show_full send error: {e}")
        await callback.answer("Ошибка отправки", show_alert=False)
        return

    await callback.answer()


@router.callback_query(F.data.startswith("processed:"))
async def cb_processed(callback: CallbackQuery):
    try:
        pp_id = int(callback.data.split(":")[1])
    except Exception:
        await callback.answer("Некорректные данные", show_alert=False)
        return

    async with get_atomic_db() as db:
        # CAS: только если ещё pending
        updated = await db.post.cas_update_processing_status(pp_id, PostStatus.PROCESSED.value)
        if not updated:
            await callback.answer("Уже обработано/отложено", show_alert=False)
            return
        post_id = updated.post_id

    # Удаляем сообщения у остальных
    await _cleanup_other_notifications(callback.bot, post_id, pp_id)

    # Всем остальным по этому посту проставляем IGNORED
    async with get_atomic_db() as db:
        try:
            await db.post.bulk_update_status_for_post(post_id, PostStatus.IGNORED.value, exclude_pp_id=pp_id)
        except Exception as e:
            main_logger.error(f"bulk update status to IGNORED failed: {e}")

    # Подтверждаем действие пользователю
    try:
        await callback.message.edit_text("✅ Отмечено как обработано")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("postponed:"))
async def cb_postponed(callback: CallbackQuery):
    try:
        pp_id = int(callback.data.split(":")[1])
    except Exception:
        await callback.answer("Некорректные данные", show_alert=False)
        return

    async with get_atomic_db() as db:
        updated = await db.post.cas_update_processing_status(pp_id, PostStatus.POSTPONED.value)
        if not updated:
            await callback.answer("Уже обработано/отложено", show_alert=False)
            return
        post_id = updated.post_id

    # Удаляем сообщения у остальных
    await _cleanup_other_notifications(callback.bot, post_id, pp_id)

    # Всем остальным по этому посту проставляем IGНОRED
    async with get_atomic_db() as db:
        try:
            await db.post.bulk_update_status_for_post(post_id, PostStatus.IGNORED.value, exclude_pp_id=pp_id)
        except Exception as e:
            main_logger.error(f"bulk update status to IGNORED failed: {e}")

    try:
        await callback.message.edit_text("⏸ Отложено")
    except Exception:
        pass
    await callback.answer()
