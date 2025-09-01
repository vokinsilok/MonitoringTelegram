from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from app.core.logging import main_logger
from bot.keyboards.keyboards import get_keyword_proposal_keyboard
from bot.models.keyword import KeywordType
from bot.schemas.keyword_schema import KeyWordProposalCreateSchema, KeyWordProposalSchema, KeyWordCreateSchema
from bot.service.keywords_service import KeyWordsService
from bot.service.user_service import UserService
from bot.utils.depend import get_atomic_db

router = Router()


class KeywordProposalForm(StatesGroup):
    """Состояния для формы предложения ключевого слова"""
    waiting_for_keyword = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()


@router.message(F.text.startswith("🔍 Предложить ключевое слово"))
async def cmd_propose_keyword(message: Message, state: FSMContext):
    """Начать процесс предложения ключевого слова"""
    if not UserService.cheek_user_permissions_static(message.from_user.id, "operator"):
        await message.answer("⚠️ <b>Недостаточно прав</b>\n\nЭта функция доступна только операторам.")
        return
    await message.answer("Пожалуйста, введите ключевое слово, которое вы хотите предложить:")
    await state.set_state(KeywordProposalForm.waiting_for_keyword)

@router.message(F.text.startswith("🔑 Добавить ключевое слово"))
async def cmd_propose_keyword(message: Message, state: FSMContext):
    """Начать процесс предложения ключевого слова"""
    if not UserService.cheek_user_permissions_static(message.from_user.id, "admin"):
        await message.answer("⚠️ <b>Недостаточно прав</b>\n\nЭта функция доступна только admin.")
        return
    await message.answer("Пожалуйста, введите ключевое слово, которое вы хотите предложить:")
    await state.set_state(KeywordProposalForm.waiting_for_keyword)


@router.message(KeywordProposalForm.waiting_for_keyword)
async def process_keyword(message: Message, state: FSMContext):
    """Обработать полученное ключевое слово"""
    await state.update_data(keyword=message.text)
    await message.answer(
        "Спасибо! Теперь, пожалуйста, введите комментарий или причину, почему вы предлагаете это ключевое слово:")
    await state.set_state(KeywordProposalForm.waiting_for_comment)


@router.message(KeywordProposalForm.waiting_for_comment)
async def process_comment(message: Message, state: FSMContext):
    """Обработать полученный комментарий"""
    await state.update_data(comment=message.text)
    data = await state.get_data()
    keyword = data['keyword']
    comment = data['comment']

    await message.answer(
        f"Вы предложили ключевое слово: {keyword}\n"
        f"Комментарий: {comment}\n\n"
        "Пожалуйста, подтвердите ваше предложение (да/нет):"
    )
    await state.set_state(KeywordProposalForm.waiting_for_confirmation)


@router.message(KeywordProposalForm.waiting_for_confirmation)
async def process_confirmation(message: Message, state: FSMContext):
    """Обработать подтверждение предложения"""
    if message.text.lower() in ["да", "yes"]:
        data = await state.get_data()
        keyword = data['keyword']
        comment = data['comment']
        operator_telegram_id = int(message.from_user.id) if message.from_user and message.from_user.id else None
        async with get_atomic_db() as db:
            user_permissions = await UserService(db).cheek_user_permissions(operator_telegram_id)
            if user_permissions.get("is_operator"):
                try:
                    user = await UserService(db).get_user_by_filter(telegram_id=operator_telegram_id)
                    data = KeyWordProposalCreateSchema(
                            keyword_id=None,
                            operator_id=user.id,
                            text=str(keyword),
                            type=KeywordType.WORD,
                            status="pending",
                            comment=comment,
                            admin_comment=None
                        )
                    keyword_service = KeyWordsService(db)
                    keyword_proposal = await keyword_service.create_keyword_proposal(data)
                    if keyword_proposal:
                        await notify_admins_about_keyword_proposal(message.bot, keyword_proposal)
                        await message.answer("Спасибо! Ваше предложение было принято.")
                    else:
                        await message.answer(
                            "Произошла ошибка при обработке вашего предложения. Пожалуйста, попробуйте снова позже.")
                    main_logger.debug(f"keyword_proposal: {keyword_proposal}")
                except Exception as e:
                    main_logger.error(f"Error creating keyword proposal: {e}")
                    await message.answer(
                        "Произошла ошибка при обработке вашего предложения. Пожалуйста, попробуйте снова позже.")
            elif user_permissions.get("is_admin"):
                # Администраторы могут сразу добавлять ключевые слова
                try:
                    await db.keywords.create_keyword(KeyWordCreateSchema(
                        text=str(keyword),
                        type=KeywordType.WORD,
                        is_active=True,
                        description=comment
                    ))
                    await message.answer(f"Ключевое слово '{keyword}' успешно добавлено.")
                except Exception as e:
                    main_logger.error(f"Error fetching user for admin keyword addition: {e}")


    else:
        await message.answer("Ваше предложение было отменено.")

    await state.clear()


async def notify_admins_about_keyword_proposal(bot: Bot, proposal: KeyWordProposalSchema):
    """Уведомляет администраторов о новом предложении ключевого слова"""
    try:
        async with get_atomic_db() as db:
            user_service = UserService(db)
            admins = await user_service.get_admins()
            if not admins:
                main_logger.warning("No admins found to notify about keyword proposal.")
                return

            # Получаем автора предложения, чтобы корректно отобразить тег/упоминание
            operator = await user_service.get_user_by_filter(id=proposal.operator_id)
            if operator and operator.username:
                operator_display = f"@{operator.username}"
            else:
                name_parts = [p for p in [getattr(operator, 'first_name', None), getattr(operator, 'last_name', None)] if p] if operator else []
                visible_name = " ".join(name_parts) if name_parts else "Пользователь"
                operator_display = f"<a href=\"tg://user?id={getattr(operator, 'telegram_id', 0)}\">{visible_name}</a>"

            keyboard = get_keyword_proposal_keyboard(proposal.id)
            for admin in admins:
                await bot.send_message(
                    chat_id=admin.telegram_id,
                    text=(
                        f"🔍 <b>Новое предложение ключевого слова</b>\n\n"
                        f"Слово: <code>{proposal.text}</code>\n"
                        f"От: {operator_display}\n"
                        f"Комментарий: {proposal.comment or '—'}\n"
                        f"Статус: {proposal.status}"
                    ),
                    reply_markup=keyboard
                )
    except Exception as e:
        main_logger.error(f"Error notifying admins about keyword proposal: {e}")


@router.callback_query(F.data.startswith("approve_keyword:"))
async def approve_keyword_proposal(callback: CallbackQuery):
    """Обработчик подтверждения предложения ключевого слова администратором"""
    try:
        proposal_id = int(callback.data.split(":")[1])

        async with get_atomic_db() as db:
            proposal = await KeyWordsService(db).approve_keyword_proposal(proposal_id, admin_comment="Approved by admin")

            if proposal:
                await callback.message.edit_text(
                    f"✅ Предложение ключевого слова '{proposal.text}' одобрено."
                )

                # Уведомляем оператора о подтверждении предложения
                try:
                    user = await UserService(db).get_user_by_filter(id=proposal.operator_id)
                    if user and user.telegram_id:
                        await callback.bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"✅ Ваше предложение ключевого слова '{proposal.text}' было одобрено администратором."
                        )
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления оператору {proposal.operator_id}: {str(e)}")
            else:
                await callback.message.edit_text(
                    "Не удалось обновить статус предложения. Возможно, оно уже было обработано.")
    except Exception as e:
        main_logger.error(f"Ошибка при подтверждении предложения ключевого слова: {str(e)}")
        await callback.message.edit_text(f"Произошла ошибка при обработке предложения: {str(e)}")
    finally:
        await callback.answer()


@router.callback_query(F.data.startswith("reject_keyword:"))
async def reject_keyword_proposal(callback: CallbackQuery):
    """Обработчик отклонения предложения ключевого слова администратором"""
    try:
        proposal_id = int(callback.data.split(":")[1])

        async with get_atomic_db() as db:
            proposal = await KeyWordsService(db).reject_keyword_proposal(proposal_id, admin_comment="Rejected by admin")

            if proposal:
                await callback.message.edit_text(
                    f"❌ Предложение ключевого слова '{proposal.text}' отклонено."
                )

                # Уведомляем оператора об отклонении предложения
                try:
                    user = await UserService(db).get_user_by_filter(id=proposal.operator_id)
                    if user and user.telegram_id:
                        await callback.bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"❌ Ваше предложение ключевого слова '{proposal.text}' было отклонено администратором."
                        )
                except Exception as e:
                    main_logger.error(f"Ошибка при отправке уведомления оператору {proposal.operator_id}: {str(e)}")
            else:
                await callback.message.edit_text(
                    "Не удалось обновить статус предложения. Возможно, оно уже было обработано.")
    except Exception as e:
        main_logger.error(f"Ошибка при отклонении предложения ключевого слова: {str(e)}")
        await callback.message.edit_text(f"Произошла ошибка при обработке предложения: {str(e)}")
    finally:
        await callback.answer()
