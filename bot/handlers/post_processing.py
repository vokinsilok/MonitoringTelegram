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

    # Удаляем сообщения у остальных и массово проставляем статус
    await _cleanup_other_notifications(callback.bot, post_id, pp_id)
    async with get_atomic_db() as db:
        try:
            await db.post.bulk_update_status_for_post(post_id, PostStatus.PROCESSED.value, exclude_pp_id=pp_id)
        except Exception as e:
            main_logger.error(f"bulk update status failed: {e}")

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

    await _cleanup_other_notifications(callback.bot, post_id, pp_id)
    async with get_atomic_db() as db:
        try:
            await db.post.bulk_update_status_for_post(post_id, PostStatus.POSTPONED.value, exclude_pp_id=pp_id)
        except Exception as e:
            main_logger.error(f"bulk update status failed: {e}")

    try:
        await callback.message.edit_text("⏸ Отложено")
    except Exception:
        pass
    await callback.answer()

