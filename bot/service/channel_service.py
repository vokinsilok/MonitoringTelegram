from bot.schemas.channel import AddChannelProposal, AddChannel, ChannelSchema
from bot.service.base_service import BaseService
from bot.models.channel import ChannelProposal, Channel, ProposalStatus


class ChannelService(BaseService):

    async def add_channel_proposal(self, data: AddChannelProposal):
        """
        Добавляет предложение о канале в базу данных.

        :param data: Данные предложения о канале.
        :return: ChannelProposal: Созданное предложение канала
        """
        return await self.db.channel.add_channel_proposal(data)
        
    async def approve_channel_proposal(self, proposal_id: int):
        """
        Подтверждает предложение канала и создает новый канал для мониторинга.
        
        :param proposal_id: ID предложения канала
        :return: ChannelProposal: Обновленное предложение канала
        """
        # Получаем предложение канала по ID
        proposal = await self.db.channel.get_channel_proposal_by_id(proposal_id)
        
        if not proposal:
            return None
            
        # Если предложение уже обработано, возвращаем его без изменений
        if proposal.status != ProposalStatus.PENDING.value:
            return proposal
            
        channel = await self.db.channel.get_channel_by_filter(id=proposal.channel_id)
        if not channel:
            return None

        channel.status = "active"
        proposal.status = ProposalStatus.APPROVED.value
        await self.db.session.commit()
            
        return proposal
        
    async def reject_channel_proposal(self, proposal_id: int):
        """
        Отклоняет предложение канала.
        
        :param proposal_id: ID предложения канала
        :return: ChannelProposal: Обновленное предложение канала
        """
        # Получаем предложение канала по ID
        proposal = await self.db.channel.get_channel_proposal_by_id(proposal_id)
        
        if not proposal:
            return None
            
        # Если предложение уже обработано, возвращаем его без изменений
        if proposal.status != ProposalStatus.PENDING.value:
            return proposal
            
        # Обновляем статус предложения на REJECTED
        proposal = await self.db.channel.update_channel_proposal_status(
            proposal_id, 
            ProposalStatus.REJECTED.value
        )
            
        return proposal

    async def get_channel_by_filter(self, **filters) -> ChannelSchema | None:
        """
        Получает канал по заданным фильтрам.

        :param filters: Фильтры для поиска канала.
        :return: Channel | None: Найденный канал или None, если не найден.
        """
        return await self.db.channel.get_channel_by_filter(**filters)

    async def create_channel(self, data: AddChannel) -> ChannelSchema:
        """
        Создает новый канал в базе данных.

        :param data: Данные нового канала.
        :return: Channel: Созданный канал.
        """
        return await self.db.channel.create_channel(data)