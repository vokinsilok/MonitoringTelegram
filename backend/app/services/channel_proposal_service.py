from typing import List, Optional, Dict, Any
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.channel import ChannelProposal
from backend.app.schemas.channel import ChannelProposalCreate, ChannelProposalUpdate


async def get_channel_proposals(
    db: AsyncSession, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[Dict[str, Any]] = None
) -> List[ChannelProposal]:
    """
    Получение списка предложений каналов с возможностью фильтрации.
    """
    query = select(ChannelProposal)
    
    if filters:
        if "status" in filters:
            query = query.where(ChannelProposal.status == filters["status"])
        if "user_id" in filters:
            query = query.where(ChannelProposal.user_id == filters["user_id"])
    
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_channel_proposal_by_id(db: AsyncSession, proposal_id: int) -> Optional[ChannelProposal]:
    """
    Получение предложения канала по ID.
    """
    query = select(ChannelProposal).where(ChannelProposal.id == proposal_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_channel_proposal(db: AsyncSession, proposal: ChannelProposalCreate) -> ChannelProposal:
    """
    Создание нового предложения канала.
    """
    db_proposal = ChannelProposal(
        title=proposal.title,
        username=proposal.username,
        channel_id=proposal.channel_id,
        description=proposal.description,
        user_id=proposal.user_id,
        status="pending",
        comment=proposal.comment,
    )
    db.add(db_proposal)
    await db.commit()
    await db.refresh(db_proposal)
    return db_proposal


async def update_channel_proposal(db: AsyncSession, proposal_id: int, proposal: ChannelProposalUpdate) -> Optional[ChannelProposal]:
    """
    Обновление предложения канала.
    """
    db_proposal = await get_channel_proposal_by_id(db, proposal_id)
    if not db_proposal:
        return None
    
    update_data = proposal.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_proposal, key, value)
    
    await db.commit()
    await db.refresh(db_proposal)
    return db_proposal


async def delete_channel_proposal(db: AsyncSession, proposal_id: int) -> Optional[ChannelProposal]:
    """
    Удаление предложения канала.
    """
    db_proposal = await get_channel_proposal_by_id(db, proposal_id)
    if not db_proposal:
        return None
    
    await db.delete(db_proposal)
    await db.commit()
    return db_proposal


async def approve_channel_proposal(db: AsyncSession, proposal_id: int, admin_id: int, comment: Optional[str] = None) -> Optional[ChannelProposal]:
    """
    Одобрение предложения канала.
    """
    db_proposal = await get_channel_proposal_by_id(db, proposal_id)
    if not db_proposal:
        return None
    
    db_proposal.status = "approved"
    db_proposal.reviewed_by_user_id = admin_id
    if comment:
        db_proposal.admin_comment = comment
    
    await db.commit()
    await db.refresh(db_proposal)
    return db_proposal


async def reject_channel_proposal(db: AsyncSession, proposal_id: int, admin_id: int, comment: Optional[str] = None) -> Optional[ChannelProposal]:
    """
    Отклонение предложения канала.
    """
    db_proposal = await get_channel_proposal_by_id(db, proposal_id)
    if not db_proposal:
        return None
    
    db_proposal.status = "rejected"
    db_proposal.reviewed_by_user_id = admin_id
    if comment:
        db_proposal.admin_comment = comment
    
    await db.commit()
    await db.refresh(db_proposal)
    return db_proposal
