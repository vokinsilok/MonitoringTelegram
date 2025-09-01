from contextlib import asynccontextmanager

from bot.repo.chammel_repo import ChannelRepository
from bot.repo.keyword_repo import KeyWordRepo
from bot.repo.user_repo import UserRepository
from bot.repo.telethon_repo import TelethonAccountRepository


class DBManager:
    def __init__(self, session_factory):
        self.session_factory = session_factory


    async def __aenter__(self):
        self.session = self.session_factory()
        self.user = UserRepository(self.session)
        self.channel = ChannelRepository(self.session)
        self.keywords = KeyWordRepo(self.session)
        self.telethon = TelethonAccountRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.session.rollback()
        await self.session.close()

    async def commit_db(self):
        await self.session.commit()

    @asynccontextmanager
    async def transaction(self):
        """Контекстный менеджер для атомарных транзакций.
        
        Пример использования:
        ```python
        async with db.transaction():
            # Все операции в этом блоке будут выполнены атомарно
            await db.player.update_player(player_data)
            await db.fraction.update_fraction(fraction_data)
        ```
        
        Если внутри блока возникнет исключение, все изменения будут отменены.
        Если блок выполнится успешно, изменения будут зафиксированы.
        """
        try:
            yield
            await self.session.commit()
        except Exception as e:
            await self.session.rollback()
            raise e
