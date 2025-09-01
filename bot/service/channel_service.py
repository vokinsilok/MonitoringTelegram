from bot.schemas.channel import AddChannelProposal, AddChannel
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
            
        # Создаем новый канал на основе предложения
        channel_data = {
            "username": proposal.channel_username,
            "is_active": True
        }
        
        # Создаем канал
        new_channel = await self.db.channel.create_channel(AddChannel(
            channel_username=proposal.channel_username
            if proposal.channel_username else None,
            title=proposal.channel_username if proposal.channel_username else "Unnamed Channel",
            invite_link=None,  # При необходимости можно добавить логику для invite_link
            status="active",
            description=None,  # При необходимости можно добавить логику для description
            is_private=False,  # При необходимости можно добавить логику для is_private
            last_parsed_message_id=None,  # При необходимости можно добавить логику для last_parsed_message_id
            last_checked=None  # При необходимости можно добавить логику для last_checked
        ))
        
        if new_channel:
            # Обновляем статус предложения на APPROVED
            proposal = await self.db.channel.update_channel_proposal_status(
                proposal_id, 
                ProposalStatus.APPROVED.value
            )
            
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

    async def get_channel_by_filter(self, **filters) -> Channel | None:
        """
        Получает канал по заданным фильтрам.

        :param filters: Фильтры для поиска канала.
        :return: Channel | None: Найденный канал или None, если не найден.
        """
        return await self.db.channel.get_channel_by_filter(**filters)

    async def create_channel(self, data: AddChannel) -> Channel:
        """
        Создает новый канал в базе данных.

        :param data: Данные нового канала.
        :return: Channel: Созданный канал.
        """
        return await self.db.channel.create_channel(data)