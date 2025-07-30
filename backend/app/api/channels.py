from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.channel import Channel
from backend.app.schemas.channel import (
    Channel as ChannelSchema,
    ChannelCreate,
    ChannelUpdate,
    ChannelProposal as ChannelProposalSchema,
    ChannelProposalCreate,
    ChannelProposalUpdate,
)
from backend.app.services.channel_service import (
    get_channels,
    get_channel_by_id,
    create_channel,
    update_channel,
    delete_channel,
)
from backend.app.services.channel_proposal_service import (
    get_channel_proposals,
    get_channel_proposal_by_id,
    create_channel_proposal,
    update_channel_proposal,
    delete_channel_proposal,
)

router = APIRouter(prefix="/channels", tags=["channels"])


@router.get("/", response_model=List[ChannelSchema])
async def read_channels(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список каналов с возможностью фильтрации.
    """
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
        
    channels = await get_channels(db, skip=skip, limit=limit, filters=filters)
    return channels


@router.get("/{channel_id}", response_model=ChannelSchema)
async def read_channel(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить канал по ID.
    """
    channel = await get_channel_by_id(db, channel_id=channel_id)
    if channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.post("/", response_model=ChannelSchema, status_code=status.HTTP_201_CREATED)
async def create_channel_api(
    channel: ChannelCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новый канал.
    """
    return await create_channel(db=db, channel=channel)


@router.put("/{channel_id}", response_model=ChannelSchema)
async def update_channel_api(
    channel_id: int,
    channel: ChannelUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить канал.
    """
    db_channel = await get_channel_by_id(db, channel_id=channel_id)
    if db_channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return await update_channel(db=db, channel_id=channel_id, channel=channel)


@router.delete("/{channel_id}", response_model=ChannelSchema)
async def delete_channel_api(
    channel_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить канал.
    """
    db_channel = await get_channel_by_id(db, channel_id=channel_id)
    if db_channel is None:
        raise HTTPException(status_code=404, detail="Channel not found")
    
    return await delete_channel(db=db, channel_id=channel_id)


# Маршруты для предложений каналов
@router.get("/proposals/", response_model=List[ChannelProposalSchema])
async def read_channel_proposals(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список предложений каналов с возможностью фильтрации.
    """
    filters = {}
    if status is not None:
        filters["status"] = status
        
    proposals = await get_channel_proposals(db, skip=skip, limit=limit, filters=filters)
    return proposals


@router.get("/proposals/{proposal_id}", response_model=ChannelProposalSchema)
async def read_channel_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить предложение канала по ID.
    """
    proposal = await get_channel_proposal_by_id(db, proposal_id=proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Channel proposal not found")
    return proposal


@router.post("/proposals/", response_model=ChannelProposalSchema, status_code=status.HTTP_201_CREATED)
async def create_channel_proposal_api(
    proposal: ChannelProposalCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новое предложение канала.
    """
    return await create_channel_proposal(db=db, proposal=proposal)


@router.put("/proposals/{proposal_id}", response_model=ChannelProposalSchema)
async def update_channel_proposal_api(
    proposal_id: int,
    proposal: ChannelProposalUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить предложение канала.
    """
    db_proposal = await get_channel_proposal_by_id(db, proposal_id=proposal_id)
    if db_proposal is None:
        raise HTTPException(status_code=404, detail="Channel proposal not found")
    
    return await update_channel_proposal(db=db, proposal_id=proposal_id, proposal=proposal)


@router.delete("/proposals/{proposal_id}", response_model=ChannelProposalSchema)
async def delete_channel_proposal_api(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить предложение канала.
    """
    db_proposal = await get_channel_proposal_by_id(db, proposal_id=proposal_id)
    if db_proposal is None:
        raise HTTPException(status_code=404, detail="Channel proposal not found")
    
    return await delete_channel_proposal(db=db, proposal_id=proposal_id)
