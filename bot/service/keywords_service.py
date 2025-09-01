from typing import List

from bot.models.keyword import KeywordType
from bot.schemas.keyword_schema import (
    KeyWordSchema,
    UpdateKeyWordSchema,
    KeyWordProposalCreateSchema,
    KeyWordProposalSchema,
    KeyWordCreateSchema,
)
from bot.service.base_service import BaseService


class KeyWordsService(BaseService):
    async def get_all(self) -> List[KeyWordSchema]:
        """
        Получает все ключевые слова из базы данных.

        :return: Список ключевых слов.
        """
        return await self.db.keywords.get_all_keywords()

    async def create(self, word: str) -> KeyWordSchema:
        """
        Создает новое ключевое слово в базе данных.

        :param word: Текст ключевого слова.
        :return: Созданное ключевое слово.
        """
        existing_keyword = await self.db.keywords.get_keyword_by_filter(text=word)
        if existing_keyword:
            return existing_keyword
        payload = KeyWordCreateSchema(
            text=word,
            type=KeywordType.WORD,
            is_active=True,
            description=None,
        )
        new_keyword = await self.db.keywords.create_keyword(payload)
        return new_keyword

    async def get_by_filter(self, **filter_by) -> KeyWordSchema | None:
        """
        Получает ключевое слово по заданным фильтрам.

        :param filter_by: Фильтры для поиска ключевого слова.
        :return: Найденное ключевое слово или None.
        """
        return await self.db.keywords.get_keyword_by_filter(**filter_by)

    async def update(self, keyword_id: int, data: UpdateKeyWordSchema) -> KeyWordSchema | None:
        """
        Обновляет существующее ключевое слово в базе данных.

        :param keyword_id: ID ключевого слова для обновления.
        :param data: Данные для обновления ключевого слова.
        :return: Обновленное ключевое слово или None, если не найдено.
        """
        existing_keyword = await self.db.keywords.get_keyword_by_filter(id=keyword_id)
        if not existing_keyword:
            return None
        updated_keyword = await self.db.keywords.update_keyword(keyword_id, data)
        return updated_keyword

    async def create_keyword_proposal(self, data: KeyWordProposalCreateSchema) -> KeyWordProposalSchema:
        """
        Создает новое предложение ключевого слова в базе данных.

        :param data: Данные для создания предложения ключевого слова.
        :return: Созданное предложение ключевого слова.
        """
        new_proposal = await self.db.keywords.create_keyword_proposal(data)
        return new_proposal

    async def update_keyword_proposal(self, proposal_id: int, data: dict) -> KeyWordProposalSchema | None:
        """
        Обновляет существующее предложение ключевого слова в базе данных.

        :param proposal_id: ID предложения ключевого слова для обновления.
        :param data: Данные для обновления предложения ключевого слова.
        :return: Обновленное предложение ключевого слова или None, если не найдено.
        """
        existing_proposal = await self.db.keywords.get_keyword_proposal_by_filter(id=proposal_id)
        if not existing_proposal:
            return None
        updated_proposal = await self.db.keywords.update_keyword_proposal(proposal_id, data)
        return updated_proposal

    async def approve_keyword_proposal(
        self, proposal_id: int, admin_comment: str | None = None
    ) -> KeyWordProposalSchema | None:
        """
        Одобряет предложение ключевого слова и создает ключевое слово, если оно не существует.

        :param proposal_id: ID предложения ключевого слова для одобрения.
        :param admin_comment: Комментарий администратора (необязательно).
        :return: Обновленное предложение ключевого слова или None, если не найдено.
        """
        proposal = await self.db.keywords.get_keyword_proposal_by_filter(id=proposal_id)
        if not proposal or proposal.status != "pending":
            return None

        # Проверяем, существует ли уже ключевое слово
        existing_keyword = await self.db.keywords.get_keyword_by_filter(text=proposal.text)
        if not existing_keyword:
            # Создаем новое ключевое слово
            created = await self.create(proposal.text)
            # можно при желании связать предложение с созданным словом
            await self.update_keyword_proposal(proposal.id, {"keyword_id": created.id})

        # Обновляем статус предложения на "approved"
        update_data = {
            "status": "approved",
            "admin_comment": admin_comment,
        }
        updated_proposal = await self.update_keyword_proposal(proposal_id, update_data)
        return updated_proposal

    async def reject_keyword_proposal(
        self, proposal_id: int, admin_comment: str | None = None
    ) -> KeyWordProposalSchema | None:
        """
        Отклоняет предложение ключевого слова.

        :param proposal_id: ID предложения ключевого слова для отклонения.
        :param admin_comment: Комментарий администратора (необязательно).
        :return: Обновленное предложение ключевого слова или None, если не найдено.
        """
        proposal = await self.db.keywords.get_keyword_proposal_by_filter(id=proposal_id)
        if not proposal or proposal.status != "pending":
            return None

        # Обновляем статус предложения на "rejected"
        update_data = {
            "status": "rejected",
            "admin_comment": admin_comment,
        }
        updated_proposal = await self.update_keyword_proposal(proposal_id, update_data)
        return updated_proposal
