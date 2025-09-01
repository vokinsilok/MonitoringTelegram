from typing import List

from sqlalchemy import select, insert, update

from bot.models.keyword import Keyword
from bot.repo.base_repo import BaseRepository
from bot.schemas.keyword_schema import KeyWordSchema, KeyWordCreateSchema, UpdateKeyWordSchema, \
    KeyWordProposalCreateSchema, KeyWordProposalSchema


class KeyWordRepo(BaseRepository):
    model = Keyword
    schema = KeyWordSchema

    async def get_keyword_by_filter(self, **filter_by) -> KeyWordSchema | None:
        """
        Получает ключевое слово по заданным фильтрам.

        :param filter_by: Фильтры для поиска ключевого слова.
        :return: Найденное ключевое слово или None.
        """
        obj = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(obj)
        return result.scalar()

    async def create_keyword(self, data: KeyWordCreateSchema) -> KeyWordSchema:
        """
        Создает новое ключевое слово в базе данных.

        :param data: Данные для создания ключевого слова.
        :return: Созданное ключевое слово.
        """
        stmt = insert(self.model).values(**data.model_dump()).returning(self.model)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar()

    async def update_keyword(self, keyword_id: int, data: UpdateKeyWordSchema) -> KeyWordSchema:
        """
        Обновляет существующее ключевое слово в базе данных.

        :param data: Данные для обновления ключевого слова.
        :return: Обновленное ключевое слово.
        """
        update_stmt = (
            update(self.model)
            .where(self.model.id == keyword_id)
            .values(**{k: v for k, v in data.model_dump().items() if v is not None})
            .returning(self.model)
        )
        update_obj = await self.session.execute(update_stmt)
        obj = update_obj.scalar()
        await self.session.commit()
        return obj

    async def get_all_keywords(self) -> List[KeyWordSchema]:
        """
        Получает все ключевые слова из базы данных.

        :return: Список всех ключевых слов.
        """
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    async def create_keyword_proposal(self, data: KeyWordProposalCreateSchema) -> KeyWordProposalSchema:
        """
        Создает новое предложение ключевого слова в базе данных.

        :param data: Данные для создания предложения ключевого слова.
        :return: Созданное предложение ключевого слова.
        """
        stmt = insert(self.model).values(**data.model_dump()).returning(self.model)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar()

    async def get_all_keyword_proposals(self) -> List[KeyWordProposalSchema]:
        """
        Получает все предложения ключевых слов из базы данных.

        :return: Список всех предложений ключевых слов.
        """
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    async def get_keyword_proposal_by_filter(self, **filter_by) -> KeyWordProposalSchema | None:
        """
        Получает предложение ключевого слова по заданным фильтрам.

        :param filter_by: Фильтры для поиска предложения ключевого слова.
        :return: Найденное предложение ключевого слова или None.
        """
        obj = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(obj)
        return result.scalar()

    async def update_keyword_proposal(self, proposal_id: int, data: UpdateKeyWordSchema) -> KeyWordProposalSchema:
        """
        Обновляет существующее предложение ключевого слова в базе данных.

        :param data: Данные для обновления предложения ключевого слова.
        :return: Обновленное предложение ключевого слова.
        """
        update_stmt = (
            update(self.model)
            .where(self.model.id == proposal_id)
            .values(**{k: v for k, v in data.model_dump().items() if v is not None})
            .returning(self.model)
        )
        update_obj = await self.session.execute(update_stmt)
        obj = update_obj.scalar()
        await self.session.commit()
        return obj