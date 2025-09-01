from sqlalchemy import insert, select, update
from sqlalchemy.sql import func

from bot.models.channel import ChannelProposal, Channel
from bot.repo.base_repo import BaseRepository
from bot.schemas.channel import AddChannelProposal, AddChannel


class ChannelRepository(BaseRepository):

    async def add_channel_proposal(self, data: AddChannelProposal) -> ChannelProposal:
        stmt = insert(ChannelProposal).values(data.model_dump()).returning(ChannelProposal)
        obj = await self.session.execute(stmt)
        await self.session.commit()
        return obj.scalar()
        
    async def get_channel_proposal_by_id(self, proposal_id: int) -> ChannelProposal:
        """
        Получить предложение канала по ID
        
        :param proposal_id: ID предложения канала
        :return: ChannelProposal: Предложение канала или None, если не найдено
        """
        stmt = select(ChannelProposal).where(ChannelProposal.id == proposal_id)
        obj = await self.session.execute(stmt)
        return obj.scalar_one_or_none()
        
    async def update_channel_proposal_status(self, proposal_id: int, status: str, channel_id: int = None) -> ChannelProposal:
        """
        Обновить статус предложения канала
        
        :param proposal_id: ID предложения канала
        :param status: Новый статус
        :param channel_id: ID созданного канала (если статус APPROVED)
        :return: ChannelProposal: Обновленное предложение канала
        """
        values = {"status": status}
            
        stmt = update(ChannelProposal).where(ChannelProposal.id == proposal_id).values(values).returning(ChannelProposal)
        obj = await self.session.execute(stmt)
        await self.session.commit()
        return obj.scalar_one_or_none()
        
    async def create_channel(self, data: AddChannel) -> Channel:
        """
        Создать новый канал
        
        :param data: Данные канала
        :return: Channel: Созданный канал
        """
        stmt = insert(Channel).values(data.model_dump()).returning(Channel)
        obj = await self.session.execute(stmt)
        await self.session.commit()
        return obj.scalar()

    async def get_channel_by_filter(self, **filters) -> Channel:
        stmt = select(Channel).filter_by(**filters)
        obj = await self.session.execute(stmt)
        return obj.scalar_one_or_none()

    async def list_active_channels(self) -> list[Channel]:
        stmt = select(Channel).where(Channel.status == "active")
        obj = await self.session.execute(stmt)
        return obj.scalars().all()

    async def update_last_parsed(self, channel_id: int, message_id: int):
        stmt = (
            update(Channel)
            .where(Channel.id == channel_id)
            .values(last_parsed_message_id=message_id)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def touch_checked(self, channel_id: int):
        stmt = (
            update(Channel)
            .where(Channel.id == channel_id)
            .values(last_checked=func.now())
        )
        await self.session.execute(stmt)
        await self.session.commit()
