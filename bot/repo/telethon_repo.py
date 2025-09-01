from sqlalchemy import insert, select, update

from bot.models.telethon_account import TelethonAccount
from bot.repo.base_repo import BaseRepository


class TelethonAccountRepository(BaseRepository):
    model = TelethonAccount

    async def create_account(self, values: dict) -> TelethonAccount:
        stmt = insert(self.model).values(**values).returning(self.model)
        obj = await self.session.execute(stmt)
        await self.session.commit()
        return obj.scalar()

    async def update_account(self, account_id: int, values: dict) -> TelethonAccount | None:
        stmt = (
            update(self.model)
            .where(self.model.id == account_id)
            .values(**values)
            .returning(self.model)
        )
        obj = await self.session.execute(stmt)
        await self.session.commit()
        return obj.scalar_one_or_none()

    async def get_by_filter(self, **filters) -> TelethonAccount | None:
        stmt = select(self.model).filter_by(**filters)
        obj = await self.session.execute(stmt)
        return obj.scalar_one_or_none()

    async def list_active_accounts(self) -> list[TelethonAccount]:
        stmt = select(self.model).where(self.model.is_active.is_(True), self.model.is_authorized.is_(True))
        obj = await self.session.execute(stmt)
        return obj.scalars().all()
