from typing import List

from bot.models.keyword import KeywordType
from bot.schemas.keyword_schema import KeyWordSchema, UpdateKeyWordSchema
from bot.service.base_service import BaseService


class KeyWordsService(BaseService):

    async def get_all(self) -> List[KeyWordSchema]:
        """
        Получает все ключевые слова из базы данных.

        :return: Список ключевых слов.
        """
        return await self.db.keywords.get_all()

    async def create(self, word: str) -> KeyWordSchema:
        """
        Создает новое ключевое слово в базе данных.

        :param word: Текст ключевого слова.
        :return: Созданное ключевое слово.
        """
        existing_keyword = await self.db.keywords.get_keyword_by_filter(text=word)
        if existing_keyword:
            return existing_keyword
        new_keyword = await self.db.keywords.create_keyword(
            {
                "text": word,
                "type": KeywordType.WORD.value,
                "is_active": True,
                "description": None
            }
        )
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