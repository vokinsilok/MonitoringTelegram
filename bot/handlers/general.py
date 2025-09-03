from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from io import BytesIO

from app.core.logging import main_logger
from bot.keyboards.keyboards import get_operator_access_request_keyboard
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db
from bot.models.post import PostStatus

# Для генерации .docx отчёта
try:
    from docx import Document  # type: ignore
except Exception:  # библиотека может быть не установлена в рантайме
    Document = None  # type: ignore

router = Router()


def _format_requester_display(user) -> str:
    if getattr(user, "username", None):
        return f"@{user.username}"
    name_parts = [p for p in [getattr(user, 'first_name', None), getattr(user, 'last_name', None)] if p]
    visible_name = " ".join(name_parts) if name_parts else "Пользователь"
    return f"<a href=\"tg://user?id={user.telegram_id}\">{visible_name}</a>"


@router.message(F.text.in_({"📊 Отчет", "📊 Отчёт", "Отчёт", "Отчет"}))
async def show_report(message: Message):
    # Параметры окна отчёта (можно вынести в конфиг)
    within_hours = 24
    try:
        async with get_atomic_db() as db:
            total_channels = await db.channel.count_channels()
            total_keywords = len(await db.keywords.get_all_keywords())
            total_matched_posts = await db.post.count_distinct_posts_with_matches(within_hours)
            processed = await db.post.count_processing_by_status(PostStatus.PROCESSED.value, within_hours)
            postponed = await db.post.count_processing_by_status(PostStatus.POSTPONED.value, within_hours)
            pending = await db.post.count_processing_by_status(PostStatus.PENDING.value, within_hours)

            # Статистика по операторам
            op_stats_raw = await db.post.get_operator_stats(within_hours)
            op_lines = []
            for op_id, proc_cnt, postp_cnt in op_stats_raw:
                user = await db.user.get_user_by_filter(id=op_id)
                if user and getattr(user, "username", None):
                    display = f"@{user.username}"
                elif user:
                    name_parts = [p for p in [getattr(user, 'first_name', None), getattr(user, 'last_name', None)] if p]
                    visible = " ".join(name_parts) if name_parts else str(user.telegram_id)
                    display = f"<a href=\"tg://user?id={user.telegram_id}\">{visible}</a>"
                else:
                    display = "неизвестно"
                op_lines.append(f"• {display}: <b>{proc_cnt}</b> разобранных, <b>{postp_cnt}</b> отложенных")

        # Красивый текст отчёта в сообщении
        text = (
            "📊 <b>Отчёт</b> (за последние 24 часа)\n\n"
            f"1. Всего каналов: <b>{total_channels}</b>\n"
            f"2. Всего ключевых слов: <b>{total_keywords}</b>\n"
            f"3. Найдено постов по ключевым словам: <b>{total_matched_posts}</b>\n"
            f"4. Разобрано: <b>{processed}</b>\n"
            f"5. Отложенно: <b>{postponed}</b>\n"
            f"6. Ожидающие разбора: <b>{pending}</b>\n\n"
            "👤 <b>Операторы, разбиравшие инциденты:</b>\n"
            + ("\n".join(op_lines) if op_lines else "—")
        )
        await message.answer(text, disable_web_page_preview=True)

        # Генерация подробного отчёта DOCX (если доступна библиотека)
        if Document is None:
            await message.answer("⚠️ Подробный .docx отчёт недоступен (библиотека python-docx не установлена).")
            return

        # Загружаем последние посты с совпадениями
        async with get_atomic_db() as db:
            posts = await db.post.get_recent_matched_posts(within_hours)

        doc = Document()
        doc.add_heading("Отчёт по мониторингу Telegram", level=0)
        doc.add_paragraph(f"Период: последние {within_hours} ч.")
        doc.add_paragraph("")
        doc.add_paragraph(f"Всего каналов: {total_channels}")
        doc.add_paragraph(f"Всего ключевых слов: {total_keywords}")
        doc.add_paragraph(f"Найдено постов по ключевым словам: {total_matched_posts}")
        doc.add_paragraph(f"Разобрано: {processed}")
        doc.add_paragraph(f"Отложенно: {postponed}")
        doc.add_paragraph(f"Ожидающие разбора: {pending}")

        doc.add_heading("Операторы", level=1)
        if op_lines:
            for line in op_lines:
                # Уберём HTML из docx-версии
                plain = (
                    line.replace("<b>", "").replace("</b>", "")
                        .replace("<a href=\"tg://user?id=", "").replace("\">", " ")
                        .replace("</a>", "")
                )
                doc.add_paragraph(plain, style="List Bullet")
        else:
            doc.add_paragraph("—")

        doc.add_heading("Подробные посты", level=1)
        for p in posts:
            ch_title = getattr(getattr(p, "channel", None), "title", "Канал") or "Канал"
            doc.add_heading(ch_title, level=2)
            doc.add_paragraph(f"Дата: {getattr(p, 'published_at', '')}")
            if getattr(p, "url", None):
                doc.add_paragraph(f"Ссылка: {p.url}")
            # Ключевые слова
            kw_texts = []
            try:
                for mk in getattr(p, "matched_keywords", []) or []:
                    if getattr(mk, "keyword", None) and mk.keyword.text:
                        if mk.keyword.text not in kw_texts:
                            kw_texts.append(mk.keyword.text)
            except Exception:
                pass
            if kw_texts:
                doc.add_paragraph("Ключевые слова: " + ", ".join(kw_texts))
            # Текст поста
            preview = (p.text or "").strip()
            doc.add_paragraph(preview if preview else "(без текста)")
            doc.add_paragraph("")

        bio = BytesIO()
        doc.save(bio)
        bio.seek(0)
        fname = f"report_{within_hours}h.docx"
        file = BufferedInputFile(bio.read(), filename=fname)
        await message.answer_document(file, caption="Подробный отчёт")

    except Exception as e:
        main_logger.error(f"show_report error: {e}")
        await message.answer("⚠️ Не удалось сформировать отчёт. Попробуйте позже.")


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
