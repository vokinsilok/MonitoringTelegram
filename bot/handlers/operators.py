from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from app.core.logging import main_logger
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db

router = Router()

PAGE_SIZE = 8


def _build_ops_keyboard(users, page: int, has_next: bool) -> InlineKeyboardMarkup:
    rows = []
    for u in users:
        # Текст на кнопке: тег, иначе имя (без показа ID)
        if u.username:
            btn_title = f"@{u.username}"
        else:
            name_parts = [p for p in [getattr(u, 'first_name', None), getattr(u, 'last_name', None)] if p]
            btn_title = " ".join(name_parts) if name_parts else "Без тега"
        op_flag = "✅" if u.is_operator else "❌"
        act_flag = "✅" if u.is_active else "❌"
        rows.append([
            InlineKeyboardButton(text=btn_title, callback_data=f"ops:none:{u.id}:{page}"),
        ])
        rows.append([
            InlineKeyboardButton(text=f"Оператор {op_flag}", callback_data=f"ops:toggle_op:{u.id}:{page}"),
            InlineKeyboardButton(text=f"Активен {act_flag}", callback_data=f"ops:toggle_active:{u.id}:{page}"),
        ])
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"ops:list:{page-1}"))
    nav.append(InlineKeyboardButton(text="🔄 Обновить", callback_data=f"ops:list:{page}"))
    if has_next:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"ops:list:{page+1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text="🔄 Обновить", callback_data=f"ops:list:{page}")]])


async def _render_ops_page(message_or_cb, page: int):
    async with get_atomic_db() as db:
        user_service = UserService(db)
        # Проверяем права
        actor_tg_id = message_or_cb.from_user.id
        perms = await user_service.cheek_user_permissions(actor_tg_id)
        if not perms.get("is_admin"):
            text = "Нет прав."
            if isinstance(message_or_cb, Message):
                await message_or_cb.answer(text)
            else:
                try:
                    await message_or_cb.message.edit_text(text)
                except TelegramBadRequest:
                    pass
                await message_or_cb.answer()
            return

        # Берем пользователей (кроме админов)
        users = await user_service.list_users(page=page, per_page=PAGE_SIZE)
        users = [u for u in users if not u.is_admin]
        has_next = len(await user_service.list_users(page=page+1, per_page=PAGE_SIZE)) > 0

    if not users:
        text = "Пользователи не найдены."
        kb = _build_ops_keyboard([], page, has_next=False)
    else:
        lines = ["👥 Управление операторами", f"Стр. {page}", ""]
        for u in users:
            if u.username:
                display = f"@{u.username}"
            else:
                name_parts = [p for p in [getattr(u, 'first_name', None), getattr(u, 'last_name', None)] if p]
                visible_name = " ".join(name_parts) if name_parts else "Пользователь"
                # Кликабельное упоминание без показа ID в тексте
                display = f"<a href=\"tg://user?id={u.telegram_id}\">{visible_name}</a>"
            role = "operator" if u.is_operator else "user"
            act = "✅" if u.is_active else "❌"
            lines.append(f"• {display} | роль: {role} | активен: {act}")
        text = "\n".join(lines)
        kb = _build_ops_keyboard(users, page, has_next)

    if isinstance(message_or_cb, Message):
        await message_or_cb.answer(text, reply_markup=kb)
    else:
        try:
            await message_or_cb.message.edit_text(text, reply_markup=kb)
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                try:
                    await message_or_cb.message.edit_reply_markup(reply_markup=kb)
                except TelegramBadRequest:
                    pass
            else:
                main_logger.error(f"edit_text error: {e}")
        finally:
            await message_or_cb.answer()


@router.message(F.text.startswith("👥 Управление операторами"))
async def manage_ops(message: Message):
    if not UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ <b>Недостаточно прав</b>\n\nЭта функция доступна только admin.")
        return
    await _render_ops_page(message, page=1)


@router.callback_query(F.data.startswith("ops:list:"))
async def ops_list(callback: CallbackQuery):
    try:
        page = int(callback.data.split(":")[2])
    except Exception:
        page = 1
    await _render_ops_page(callback, page=page)


@router.callback_query(F.data.startswith("ops:toggle_op:"))
async def toggle_operator(callback: CallbackQuery):
    try:
        _, _, user_id_str, page_str = callback.data.split(":")
        user_id = int(user_id_str)
        page = int(page_str)
    except Exception:
        await callback.answer("Некорректные данные", show_alert=False)
        return

    try:
        async with get_atomic_db() as db:
            svc = UserService(db)
            user = await svc.get_user_by_filter(id=user_id)
            if not user:
                await callback.answer("Пользователь не найден", show_alert=False)
                return
            # Инвертируем
            make_operator = not bool(user.is_operator)
            await svc.set_operator(user_id, make_operator)
    except Exception as e:
        main_logger.error(f"toggle_operator error: {e}")
        await callback.answer("Ошибка", show_alert=False)
        return

    await _render_ops_page(callback, page=page)


@router.callback_query(F.data.startswith("ops:toggle_active:"))
async def toggle_active(callback: CallbackQuery):
    try:
        _, _, user_id_str, page_str = callback.data.split(":")
        user_id = int(user_id_str)
        page = int(page_str)
    except Exception:
        await callback.answer("Некорректные данные", show_alert=False)
        return

    try:
        async with get_atomic_db() as db:
            svc = UserService(db)
            user = await svc.get_user_by_filter(id=user_id)
            if not user:
                await callback.answer("Пользователь не найден", show_alert=False)
                return
            await svc.set_active(user_id, not bool(user.is_active))
    except Exception as e:
        main_logger.error(f"toggle_active error: {e}")
        await callback.answer("Ошибка", show_alert=False)
        return

    await _render_ops_page(callback, page=page)
