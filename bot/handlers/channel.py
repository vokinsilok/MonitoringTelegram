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
    await message.answer("Пожалуйста, отправьте ссылку на Telegram-канал или его @username")
    await state.set_state(ChannelProposalForm.waiting_for_channel)


@router.message(F.text.startswith("➕ Добавить канал"))
async def cmd_propose_channel(message: Message, state: FSMContext):
    """Начать процесс предложения канала"""
    user_id = message.from_user.id
    if not user_id:
        await message.answer("Ошибка: не удалось получить ваш Telegram ID.")
        return

    async with get_atomic_db() as db:
        user_permissions = await UserService(db).cheek_user_permissions(user_id)

    if not user_permissions["is_admin"] and not user_permissions["is_operator"]:
        await message.answer("У вас нет прав для добавления каналов.")
    elif not user_permissions["is_admin"]:
        await message.answer(
            "У вас нет прав для добавления каналов. Вы можете предложить канал на добавление, и администраторы рассмотрят вашу заявку.")
    else:
        await message.answer("Пожалуйста, отправьте ссылку на Telegram-канал или его @username")
        await state.set_state(ChannelProposalForm.waiting_for_channel)


@router.message(ChannelProposalForm.waiting_for_channel)
async def process_channel(message: Message, state: FSMContext):
    """Обработать отправленный канал"""
    channel_link = message.text.strip()

    # Сохраняем данные в состоянии
    await state.update_data(channel_link=channel_link)

    # Запрашиваем комментарий
    await message.answer("Вы можете добавить комментарий к вашему предложению (или отправьте 'нет' для пропуска):")
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
        f"Вы хотите предложить канал {channel_link} для мониторинга?\n"
        f"Комментарий: {comment if comment else 'Нет комментария'}\n"
        f"Отправьте 'да' для подтверждения или 'нет' для отмены."
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
            if not user_permissions["is_admin"]:
                await message.answer("У вас нет прав для добавления каналов.")
                await state.clear()
                return

            # Добавляем канал в базу данных
            try:
                from bot.service.channel_service import ChannelService
                channel_service = ChannelService(db)
                existing_channel = await channel_service.get_channel_by_filter(invite_link=channel_link)
                if existing_channel:
                    await message.answer(f"Канал {channel_link} уже добавлен для мониторинга.")
                else:
                    channel_username = channel_link.lstrip("@").replace("https://t.me/", "").replace("http://t.me/", "")
                    title = channel_username if channel_username else "Unnamed Channel"
                    invite_link = channel_link if channel_link.startswith("http") else None
                    description = comment
                    await channel_service.add_channel_proposal(AddChannelProposal(
                        channel_username=channel_username if channel_username else None,
                        operator_id=telegram_id,
                        status="approved",
                        comment="",
                        admin_comment=comment
                    ))
                    await channel_service.create_channel(AddChannel(
                        channel_username=channel_username if channel_username else None,
                        title=title,
                        invite_link=invite_link,
                        status="active",
                        description=description,
                        is_private=False,
                        last_parsed_message_id=None,
                        last_checked=None)
                    )
                    await message.answer(f"Канал {channel_link} успешно добавлен для мониторинга.")
            except Exception as e:
                main_logger.error(f"Ошибка при добавлении канала админом: {e}")
                await message.answer("Произошла ошибка при добавлении канала. Пожалуйста, попробуйте позже.")
    else:
        await message.answer("Добавление канала отменено.")

    # Сбрасываем состояние
    await state.clear()




@router.message(ChannelProposalForm.waiting_for_channel)
async def process_channel_proposal(message: Message, state: FSMContext):
    """Обработать отправленный канал"""
    channel_link = message.text.strip()

    # Сохраняем данные в состоянии
    await state.update_data(channel_link=channel_link)

    # Запрашиваем комментарий
    await message.answer(
        "Пожалуйста, добавьте комментарий, почему этот канал стоит мониторить"
    )
    await state.set_state(ChannelProposalForm.waiting_for_comment)


@router.message(ChannelProposalForm.waiting_for_comment)
async def process_channel_comment(message: Message, state: FSMContext):
    """Обработать комментарий к предложению канала"""
    comment = message.text.strip()

    # Сохраняем данные в состоянии
    await state.update_data(comment=comment)

    # Получаем данные из состояния
    data = await state.get_data()
    channel_link = data.get("channel_link")

    # Запрашиваем подтверждение
    await message.answer(
        f"Вы хотите предложить канал {channel_link} для мониторинга?\n"
        f"Комментарий: {comment}\n\n"
        f"Отправьте 'да' для подтверждения или 'нет' для отмены."
    )
    await state.set_state(ChannelProposalForm.waiting_for_confirmation)


@router.message(ChannelProposalForm.waiting_for_confirmation)
async def process_channel_confirmation(message: Message, state: FSMContext):
    """Обработать подтверждение предложения канала"""
    confirmation = message.text.lower().strip()

    if confirmation in ["да", "yes", "y"]:
        # Получаем данные из состояния
        data = await state.get_data()
        channel_link = data.get("channel_link")

        # Обрабатываем разные форматы ссылок на каналы
        if channel_link.startswith("https://t.me/"):
            # Обработка полной ссылки на канал
            parts = channel_link.split("https://t.me/")[1].split("/")
            channel_username = parts[0]

            # Проверка на наличие дополнительных параметров в URL
            if "?" in channel_username:
                channel_username = channel_username.split("?")[0]

        elif channel_link.startswith("@"):
            channel_username = channel_link[1:]  # Убираем символ @
        else:
            channel_username = channel_link  # Предполагаем, что это просто username

        # Логируем исходную ссылку и обработанное имя канала
        main_logger.info(f"Исходная ссылка: {channel_link}, Обработанное имя канала: {channel_username}")

        try:
            # Проверяем, что имя канала не пустое
            if not channel_username or channel_username.isspace():
                await message.answer("Ошибка: Имя канала не может быть пустым")
                await state.clear()
                return

            async with get_atomic_db() as db:
                data = AddChannelProposal(
                    channel_username=channel_username,
                    operator_id=message.from_user.id,
                    comment=data.get("comment")
                )
                new_channel_proposal = await ChannelService(db).add_channel_proposal(data)

            if new_channel_proposal:
                # Отправляем сообщение пользователю
                await message.answer(
                    f"Канал @{channel_username} успешно предложен для мониторинга.\n")

                # Отправляем уведомления всем администраторам
                await notify_admins_about_channel_proposal(message.bot, new_channel_proposal,
                                                           message.from_user.username)
            else:
                await message.answer("Не удалось сохранить предложение канала. Попробуйте позже.")
        except Exception as e:
            error_msg = str(e)
            main_logger.error(error_msg)
            if "chat not found" in error_msg.lower():
                await message.answer(f"Ошибка: Канал {channel_username} не найден. Убедитесь, что:"
                                     f"\n1. Канал существует"
                                     f"\n2. Вы указали правильное имя канала (начинается с @)"
                                     f"\n3. Если канал приватный, бот должен быть добавлен в него")
            else:
                await message.answer(f"Ошибка при получении информации о канале: {error_msg}")
    else:
        await message.answer("Предложение канала отменено.")

    # Сбрасываем состояние
    await state.clear()


async def notify_admins_about_channel_proposal(bot: Bot, proposal, operator_username: str):
    """Отправить уведомления администраторам о новом предложении канала"""
    try:
        async with get_atomic_db() as db:
            # Получаем список всех администраторов
            admins = await UserService(db).get_admins()

            if not admins:
                main_logger.warning("Нет администраторов для отправки уведомления о предложении канала")
                return

            # Формируем текст уведомления
            notification_text = (
                f"📢 <b>Новое предложение канала</b>\n\n"
                f"Канал: @{proposal.channel_username}\n"
                f"Предложил: @{operator_username}\n"
                f"Комментарий: {proposal.comment or 'Отсутствует'}\n\n"
                f"Пожалуйста, рассмотрите предложение."
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
                    f"✅ Предложение канала @{proposal.channel_username} одобрено.\n"
                    f"Канал добавлен в мониторинг."
                )

                # Уведомляем оператора о подтверждении предложения
                try:
                    await callback.bot.send_message(
                        chat_id=proposal.operator_id,
                        text=f"✅ Ваше предложение канала @{proposal.channel_username} было одобрено администратором."
                    )
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления оператору {proposal.operator_id}: {str(e)}")
            else:
                await callback.message.edit_text(
                    "Не удалось обновить статус предложения. Возможно, оно уже было обработано.")
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
                        text=f"❌ Ваше предложение канала @{proposal.channel_username} было отклонено администратором."
                    )
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления оператору {proposal.operator_id}: {str(e)}")
            else:
                await callback.message.edit_text(
                    "Не удалось обновить статус предложения. Возможно, оно уже было обработано.")
    except Exception as e:
        main_logger.error(f"Ошибка при отклонении предложения канала: {str(e)}")
        await callback.message.edit_text(f"Произошла ошибка при обработке предложения: {str(e)}")
    finally:
        await callback.answer()
