from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from app.core.logging import main_logger
from bot.keyboards.keyboards import get_channel_proposal_keyboard, get_keyword_proposal_keyboard
from bot.models.keyword import KeywordType
from bot.schemas.keyword_schema import KeyWordProposalCreateSchema, KeyWordProposalSchema
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
async def cmd_propose_channel(message: Message, state: FSMContext):
    """Начать процесс предложения канала"""
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
        operator_id = int(message.from_user.id) if message.from_user.id else None


        try:
            async with get_atomic_db() as db:
                user = await UserService(db).get_user_by_filter(telegram_id=operator_id)
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
                await message.answer("Спасибо! Ваше предложение было принято.")
            else:
                await message.answer(
                    "Произошла ошибка при обработке вашего предложения. Пожалуйста, попробуйте снова позже.")
            main_logger.debug(f"keyword_proposal: {keyword_proposal}")
        except Exception as e:
            main_logger.error(f"Error creating keyword proposal: {e}")
            await message.answer(
                "Произошла ошибка при обработке вашего предложения. Пожалуйста, попробуйте снова позже.")
    else:
        await message.answer("Ваше предложение было отменено.")

    await state.clear()


async def notify_admins_about_keyword_proposal(self, keyword: KeyWordProposalSchema):
    """Уведомляет администраторов о новом предложении ключевого слова"""
    try:
        async with get_atomic_db() as db:
            user_service = UserService(db)
            admins = await user_service.get_admins()
            if not admins:
                main_logger.warning("No admins found to notify about keyword proposal.")
                return
            keyboards = get_keyword_proposal_keyboard(keyword.keyword_id)
            for admin in admins:
                await self.bot.send_message(
                    chat_id=admin.id,
                    text=(
                        f"📢 Новое предложение ключевого слова от пользователя {keyword.operator_id}:\n"
                        f"Ключевое слово: {keyword.text}\n"
                        f"Комментарий: {keyword.comment}\n"
                        f"Статус: {keyword.status}"
                    ),
                    keyboards=keyboards
                )
    except Exception as e:
        main_logger.error(f"Error creating keyword proposal: {e}")


@router.callback_query(F.data.startswith("approve_keyword:"))
async def approve_keyword_proposal(callback: CallbackQuery):
    """Обработчик подтверждения предложения канала администратором"""
    try:
        # Извлекаем ID предложения из callback_data
        proposal_id = int(callback.data.split(":")[1])
        admin_user_id = callback.from_user.id

        async with get_atomic_db() as db:
            # Обновляем статус предложения
            proposal = await KeyWordsService(db).approve_keyword_proposal(proposal_id,
                                                                          admin_comment="Approved by admin")

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
        admin_user_id = callback.from_user.id

        async with get_atomic_db() as db:
            # Обновляем статус предложения
            proposal = await KeyWordsService(db).reject_keyword_proposal(proposal_id, admin_comment="Rejected by admin")

            if proposal:
                await callback.message.edit_text(
                    f"❌ Предложение канала @{proposal.channel_username} отклонено.\n"
                    f"Канал не был добавлен в мониторинг."
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
