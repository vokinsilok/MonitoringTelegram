from aiogram import Router
from aiogram.fsm.state import StatesGroup, State


router = Router()


class KeywordProposalForm(StatesGroup):
    """Состояния для формы предложения ключевого слова"""
    waiting_for_keyword = State()
    waiting_for_type = State()
    waiting_for_comment = State()
    waiting_for_confirmation = State()
