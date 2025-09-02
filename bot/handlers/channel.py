from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from app.core.logging import main_logger
from bot.keyboards.keyboards import get_channel_proposal_keyboard
from bot.schemas.channel import AddChannelProposal, AddChannel
from bot.service.channel_service import ChannelService
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db

router = Router()


class ChannelProposalForm(StatesGroup):
    """Состояния для формы предложения канала"""
    waiting_for_channel = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


@router.message(F.text.startswith("📢 Предложить канал"))
async def cmd_propose_channel(message: Message, state: FSMContext):
    """Начать процесс предложения канала"""
    if not await UserService.cheek_user_permissions_static(message.from_user.id, "operator"):
        await message.answer("⚠️ <b>Недостаточно прав</b>\n\nЭта функция доступна только операторам.")
        return
    await message.answer("📢 <b>Предложить канал</b>\n\nОтправьте ссылку на канал или его @username:")
    await state.set_state(ChannelProposalForm.waiting_for_channel)


@router.message(F.text.startswith("➕ Добавить канал"))
async def cmd_propose_channel(message: Message, state: FSMContext):
    """Начать процесс предложения канала"""
    user_id = message.from_user.id
    if not await UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ <b>Недостаточно прав</b>\n\nЭта функция доступна только admin.")
        return
    if not user_id:
        await message.answer("Ошибка: не удалось получить ваш Telegram ID.")
        return

    async with get_atomic_db() as db:
        user_permissions = await UserService(db).cheek_user_permissions(user_id)

    if not user_permissions["is_admin"] and not user_permissions["is_operator"]:
        await message.answer("⚠️ <b>Недостаточно прав</b>\n\nЭта функция доступна операторам и администраторам.")
    elif not user_permissions["is_admin"]:
        await message.answer(
            "⚠️ У вас нет прав для прямого добавления.\n\nВы можете <b>предложить</b> канал, и администраторы рассмотрят заявку."
        )
    else:
        await message.answer("➕ <b>Добавление канала</b>\n\nОтправьте ссылку на канал или его @username:")
        await state.set_state(ChannelProposalForm.waiting_for_channel)


@router.message(ChannelProposalForm.waiting_for_channel)
async def process_channel(message: Message, state: FSMContext):
    """Обработать отправленный канал"""
    channel_link = message.text.strip()

    # Сохраняем данные в состоянии
    await state.update_data(channel_link=channel_link)

    # Запрашиваем комментарий
    await message.answer("✏️ Добавьте комментарий к предложению (или отправьте 'нет' для пропуска):")
    await state.set_state(ChannelProposalForm.waiting_for_comment)


@router.message(ChannelProposalForm.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработать комментарий к предложению"""
    comment = message.text.strip()
    if comment.lower() == "нет":
        comment = None

    # Сохраняем комментарий в состоянии
    await state.update_data(comment=comment)

    # Получаем данные из состояния
    data = await state.get_data()
    channel_link = data.get("channel_link")

    # Запрашиваем подтверждение
    await message.answer(
        "🧾 <b>Подтверждение</b>\n\n" \
        f"Канал: <code>{channel_link}</code>\n" \
        f"Комментарий: {comment if comment else '—'}\n\n" \
        "Отправьте 'да' для подтверждения или 'нет' для отмены."
    )
    await state.set_state(ChannelProposalForm.waiting_for_confirmation)


@router.message(ChannelProposalForm.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Обработать подтверждение предложения канала"""
    confirmation = message.text.lower().strip()

    if confirmation in ["да", "yes", "y"]:
        # Получаем данные из состояния
        data = await state.get_data()
        channel_link = data.get("channel_link")
        comment = data.get("comment")

        # Получаем Telegram ID пользователя
        telegram_id = message.from_user.id

        async with get_atomic_db() as db:
            user_permissions = await UserService(db).cheek_user_permissions(telegram_id)

            # Проверяем, является ли пользователь оператором или администратором
            if user_permissions["is_operator"]:
                # Если пользователь - оператор, создаем предложение на добавление канала и сам канал
                try:
                    from bot.service.channel_service import ChannelService
                    channel_service = ChannelService(db)
                    existing_channel = await channel_service.get_channel_by_filter(invite_link=channel_link)
                    if existing_channel:
                        await message.answer(f"ℹ️ Канал <code>{channel_link}</code> уже добавлен для мониторинга.")
                    else:
                        channel_username = channel_link.lstrip("@").replace("https://t.me/", "").replace("http://t.me/", "")
                        title = channel_username if channel_username else "Unnamed Channel"
                        invite_link = channel_link if channel_link.startswith("http") else None
                        description = comment
                        new_channel = await channel_service.create_channel(AddChannel(
                            channel_username=channel_username if channel_username else None,
                            title=title,
                            invite_link=invite_link,
                            status="disabled",
                            description=description,
                            is_private=False,
                            last_parsed_message_id=None,
                            last_checked=None)
                        )

                        channel_proposal = await channel_service.add_channel_proposal(AddChannelProposal(
                            channel_id=new_channel.id,
                            channel_username=channel_username if channel_username else None,
                            operator_id=telegram_id,
                            status="pending",
                            comment="",
                            admin_comment=comment
                        ))

                        await notify_admins_about_channel_proposal(message.bot, channel_proposal,
                                                                   message.from_user.username)
                        await message.answer("✅ <b>Заявка отправлена</b>\n\nКанал передан на рассмотрение администраторам.")
                except Exception as e:
                    main_logger.error(f"Ошибка при добавлении канала админом: {e}")
                    await message.answer("⚠️ Произошла ошибка при добавлении. Попробуйте позже.")
            elif user_permissions["is_admin"]:
                # Если пользователь - администратор, создаем только сам канал
                try:
                    from bot.service.channel_service import ChannelService
                    channel_service = ChannelService(db)
                    existing_channel = await channel_service.get_channel_by_filter(invite_link=channel_link)
                    if existing_channel:
                        await message.answer(f"ℹ️ Канал <code>{channel_link}</code> уже добавлен для мониторинга.")
                    else:
                        channel_username = channel_link.lstrip("@").replace("https://t.me/", "").replace("http://t.me/", "")
                        title = channel_username if channel_username else "Unnamed Channel"
                        invite_link = channel_link if channel_link.startswith("http") else None
                        description = comment
                        new_channel = await channel_service.create_channel(AddChannel(
                            channel_username=channel_username if channel_username else None,
                            title=title,
                            invite_link=invite_link,
                            status="active",
                            description=description,
                            is_private=False,
                            last_parsed_message_id=None,
                            last_checked=None)
                        )
                        if new_channel:
                            main_logger.info(f"Канал {channel_link} успешно добавлен администратором {telegram_id}")
                            await message.answer("✅ Канал успешно добавлен для мониторинга.")
                        else:
                            await message.answer("⚠️ Произошла ошибка при добавлении. Попробуйте позже.")
                except Exception as e:
                    main_logger.error(f"Ошибка при добавлении канала админом: {e}")
                    await message.answer("⚠️ Произошла ошибка при добавлении. Попробуйте позже.")
            else:
                await message.answer("⚠️ У вас нет прав для добавления каналов.")
    else:
        await message.answer("❌ Операция отменена.")

    await state.clear()


async def notify_admins_about_channel_proposal(bot: Bot, proposal, operator_username: str):
    """Отправить уведомления администраторам о новом предложении канала"""
    try:
        async with get_atomic_db() as db:
            # Получаем список всех администраторов
            user_service = UserService(db)
            admins = await user_service.get_admins()

            if not admins:
                main_logger.warning("Нет администраторов для отправки уведомления о предложении канала")
                return

            # Определяем отображение автора предложения
            operator_user = await user_service.get_user_by_filter(telegram_id=proposal.operator_id)
            if operator_user and operator_user.username:
                operator_display = f"@{operator_user.username}"
            else:
                # Формируем видимое имя и кликабельную ссылку
                name_parts = [p for p in [getattr(operator_user, 'first_name', None), getattr(operator_user, 'last_name', None)] if p] if operator_user else []
                visible_name = " ".join(name_parts) if name_parts else "Пользователь"
                operator_display = f"<a href=\"tg://user?id={proposal.operator_id}\">{visible_name}</a>"

            # Формируем текст уведомления
            notification_text = (
                "📢 <b>Новое предложение канала</b>\n\n"
                f"Канал: @{proposal.channel_username}\n"
                f"Предложил: {operator_display}\n"
                f"Комментарий: {proposal.comment or 'Отсутствует'}\n\n"
                "Пожалуйста, рассмотрите предложение."
            )

            # Создаем клавиатуру для подтверждения/отклонения
            keyboard = get_channel_proposal_keyboard(proposal.id)

            # Отправляем уведомление каждому администратору
            for admin in admins:
                try:
                    await bot.send_message(
                        chat_id=admin.telegram_id,
                        text=notification_text,
                        reply_markup=keyboard
                    )
                    main_logger.info(f"Уведомление о предложении канала отправлено администратору {admin.telegram_id}")
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления администратору {admin.telegram_id}: {str(e)}")
    except Exception as e:
        main_logger.error(f"Ошибка при отправке уведомлений администраторам: {str(e)}")


@router.callback_query(F.data.startswith("approve_channel:"))
async def approve_channel_proposal(callback: CallbackQuery):
    """Обработчик подтверждения предложения канала администратором"""
    try:
        # Извлекаем ID предложения из callback_data
        proposal_id = int(callback.data.split(":")[1])

        async with get_atomic_db() as db:
            # Обновляем статус предложения
            proposal = await ChannelService(db).approve_channel_proposal(proposal_id)

            if proposal:
                await callback.message.edit_text(
                    f"✅ Предложение канала @{proposal.channel_username} одобрено.\nКанал добавлен в мониторинг."
                )

                # Уведомляем оператора о подтверждении предложения
                try:
                    await callback.bot.send_message(
                        chat_id=proposal.operator_id,
                        text=f"✅ Ваше предложение канала @{proposal.channel_username} одобрено."
                    )
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления оператору {proposal.operator_id}: {str(e)}")
            else:
                await callback.message.edit_text("⚠️ Не удалось обновить статус предложения. Возможно, оно уже обработано.")
    except Exception as e:
        main_logger.error(f"Ошибка при подтверждении предложения канала: {str(e)}")
        await callback.message.edit_text(f"Произошла ошибка при обработке предложения: {str(e)}")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("reject_channel:"))
async def reject_channel_proposal(callback: CallbackQuery):
    """Обработчик отклонения предложения канала администратором"""
    try:
        # Извлекаем ID предложения из callback_data
        proposal_id = int(callback.data.split(":")[1])

        async with get_atomic_db() as db:
            # Обновляем статус предложения
            proposal = await ChannelService(db).reject_channel_proposal(proposal_id)

            if proposal:
                await callback.message.edit_text(
                    f"❌ Предложение канала @{proposal.channel_username} отклонено."
                )

                # Уведомляем оператора об отклонении предложения
                try:
                    await callback.bot.send_message(
                        chat_id=proposal.operator_id,
                        text=f"❌ Ваше предложение канала @{proposal.channel_username} отклонено."
                    )
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления оператору {proposal.operator_id}: {str(e)}")
            else:
                await callback.message.edit_text("⚠️ Не удалось обновить статус предложения. Возможно, оно уже обработано.")
    except Exception as e:
        main_logger.error(f"Ошибка при отклонении предложения канала: {str(e)}")
        await callback.message.edit_text(f"Произошла ошибка при обработке предложения: {str(e)}")
    finally:
        await callback.answer()
