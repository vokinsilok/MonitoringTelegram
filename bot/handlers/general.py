from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery

from app.core.logging import main_logger
from bot.keyboards.keyboards import get_operator_access_request_keyboard
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db

router = Router()


def _format_requester_display(user) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    name_parts = [p for p in [getattr(user, 'first_name', None), getattr(user, 'last_name', None)] if p]
    visible_name = " ".join(name_parts) if name_parts else "Пользователь"
    return f"<a href=\"tg://user?id={user.telegram_id}\">{visible_name}</a>"


@router.message(F.text.in_({"📊 Отчет", "📊 Отчёт", "Отчёт", "Отчет"}))
async def show_report(message: Message):
    text = (
        "📊 <b>Отчёты</b>\n\n"
        "Функция формирования отчётов находится в разработке.\n"
        "Мы уже работаем над красивыми и информативными дашбордами.\n\n"
        "🔔 <i>Следите за обновлениями!</i>"
    )
    await message.answer(text)


@router.message(F.text == "📝 Получить доступ оператора")
async def request_operator_access(message: Message):
    """Обычный пользователь запрашивает роль оператора: уведомляем всех админов."""
    try:
        async with get_atomic_db() as db:
            user_service = UserService(db)
            user = await user_service.get_user_by_filter(telegram_id=message.from_user.id)
            if not user:
                await message.answer("❌ Не удалось определить пользователя. Попробуйте /start.")
                return

            admins = await user_service.get_admins()
            if not admins:
                await message.answer("⚠️ Нет доступных администраторов. Попробуйте позже.")
                return

            display = _format_requester_display(user)
            text = (
                "📝 <b>Запрос на доступ оператора</b>\n\n"
                f"Запрос от: {display}\n"
                "Нажмите, чтобы выдать доступ или отклонить."
            )
            kb = get_operator_access_request_keyboard(user.id)

            sent = 0
            for admin in admins:
                try:
                    await message.bot.send_message(admin.telegram_id, text, reply_markup=kb)
                    sent += 1
                except Exception as e:
                    main_logger.error(f"send admin op-access request error to {admin.telegram_id}: {e}")

        if sent:
            await message.answer(
                "✅ <b>Запрос отправлен!</b>\n\n"
                "Администраторы получили ваше обращение.\n"
                "Вы получите уведомление после принятия решения."
            )
        else:
            await message.answer(
                "❌ <b>Не удалось отправить запрос</b>\n\n"
                "Попробуйте позже или свяжитесь с поддержкой."
            )
    except Exception as e:
        main_logger.error(f"request_operator_access error: {e}")
        await message.answer("⚠️ Произошла ошибка. Попробуйте позже.")


@router.callback_query(F.data.startswith("approve_operator:"))
async def approve_operator(callback: CallbackQuery):
    # Проверка прав администратора
    async with get_atomic_db() as db:
        perms = await UserService(db).cheek_user_permissions(callback.from_user.id)
        if not perms.get("is_admin"):
            await callback.answer("Нет прав", show_alert=False)
            return

    try:
        user_id = int(callback.data.split(":")[1])
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
            updated = await svc.set_operator(user_id, True)
            # Уведомляем целевого пользователя
            try:
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        "✅ <b>Доступ оператора выдан</b>\n\n"
                        "Перезапустите бота командой /start, чтобы обновить меню."
                    )
                )
            except Exception as e:
                main_logger.error(f"notify user grant operator failed {user.telegram_id}: {e}")
    except Exception as e:
        main_logger.error(f"approve_operator error: {e}")
        await callback.answer("Ошибка", show_alert=False)
        return

    try:
        await callback.message.edit_text("✅ Запрос обработан: доступ выдан.")
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data.startswith("reject_operator:"))
async def reject_operator(callback: CallbackQuery):
    # Проверка прав администратора
    async with get_atomic_db() as db:
        perms = await UserService(db).cheek_user_permissions(callback.from_user.id)
        if not perms.get("is_admin"):
            await callback.answer("Нет прав", show_alert=False)
            return

    try:
        user_id = int(callback.data.split(":")[1])
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
            # Можно уведомить пользователя
            try:
                await callback.bot.send_message(
                    chat_id=user.telegram_id,
                    text="❌ Ваш запрос на доступ оператора отклонён."
                )
            except Exception as e:
                main_logger.error(f"notify user reject operator failed {user.telegram_id}: {e}")
    except Exception as e:
        main_logger.error(f"reject_operator error: {e}")
        await callback.answer("Ошибка", show_alert=False)
        return

    try:
        await callback.message.edit_text("❌ Запрос отклонён.")
    except Exception:
        pass
    await callback.answer()


@router.message(F.text == "💬 Обратная связь")
async def show_feedback(message: Message):
    text = (
        "💬 <b>Обратная связь</b>\n\n"
        "Связь с поддержкой:\n"
        "• Telegram: <a href=\"https://t.me/support\">@support</a>\n"
        "• Email: <code>support@example.com</code>\n\n"
        "🕘 График: пн–пт, 10:00–19:00 (МСК)"
    )
    await message.answer(text)


@router.message(F.text.in_({"❓О системе", "❓ О системе"}))
async def about_system(message: Message):
    text = (
        "❓ <b>О системе</b>\n\n"
        "Система мониторинга Telegram‑каналов помогает команде оперативно работать с контентом:\n\n"
        "• 📢 Добавление и модерация каналов.\n"
        "• 🔍 Поиск по ключевым словам (предложения операторов, подтверждение админами).\n"
        "• 👤 Роли и права: администратор и оператор.\n"
        "• 🔔 Уведомления и удобные панели управления прямо в чате.\n\n"
        "💡 Чтобы начать — воспользуйтесь кнопками меню ниже."
    )
    await message.answer(text)
