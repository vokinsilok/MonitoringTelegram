from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.database import get_db
from backend.app.models.keyword import Keyword
from backend.app.schemas.keyword import (
    Keyword as KeywordSchema,
    KeywordCreate,
    KeywordUpdate,
    KeywordProposal as KeywordProposalSchema,
    KeywordProposalCreate,
    KeywordProposalUpdate,
)
from backend.app.services.keyword_service import (
    get_keywords,
    get_keyword_by_id,
    create_keyword,
    update_keyword,
    delete_keyword,
)
from backend.app.services.keyword_proposal_service import (
    get_keyword_proposals,
    get_keyword_proposal_by_id,
    create_keyword_proposal,
    update_keyword_proposal,
    delete_keyword_proposal,
)

router = APIRouter(prefix="/keywords", tags=["keywords"])


@router.get("/", response_model=List[KeywordSchema])
async def read_keywords(
    skip: int = 0,
    limit: int = 100,
    is_active: Optional[bool] = None,
    type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список ключевых слов с возможностью фильтрации.
    """
    filters = {}
    if is_active is not None:
        filters["is_active"] = is_active
    if type is not None:
        filters["type"] = type
        
    keywords = await get_keywords(db, skip=skip, limit=limit, filters=filters)
    return keywords


@router.get("/{keyword_id}", response_model=KeywordSchema)
async def read_keyword(
    keyword_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить ключевое слово по ID.
    """
    keyword = await get_keyword_by_id(db, keyword_id=keyword_id)
    if keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    return keyword


@router.post("/", response_model=KeywordSchema, status_code=status.HTTP_201_CREATED)
async def create_keyword_api(
    keyword: KeywordCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новое ключевое слово.
    """
    return await create_keyword(db=db, keyword=keyword)


@router.put("/{keyword_id}", response_model=KeywordSchema)
async def update_keyword_api(
    keyword_id: int,
    keyword: KeywordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить ключевое слово.
    """
    db_keyword = await get_keyword_by_id(db, keyword_id=keyword_id)
    if db_keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    
    return await update_keyword(db=db, keyword_id=keyword_id, keyword=keyword)


@router.delete("/{keyword_id}", response_model=KeywordSchema)
async def delete_keyword_api(
    keyword_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить ключевое слово.
    """
    db_keyword = await get_keyword_by_id(db, keyword_id=keyword_id)
    if db_keyword is None:
        raise HTTPException(status_code=404, detail="Keyword not found")
    
    return await delete_keyword(db=db, keyword_id=keyword_id)


# Маршруты для предложений ключевых слов
@router.get("/proposals/", response_model=List[KeywordProposalSchema])
async def read_keyword_proposals(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить список предложений ключевых слов с возможностью фильтрации.
    """
    filters = {}
    if status is not None:
        filters["status"] = status
        
    proposals = await get_keyword_proposals(db, skip=skip, limit=limit, filters=filters)
    return proposals


@router.get("/proposals/{proposal_id}", response_model=KeywordProposalSchema)
async def read_keyword_proposal(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Получить предложение ключевого слова по ID.
    """
    proposal = await get_keyword_proposal_by_id(db, proposal_id=proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Keyword proposal not found")
    return proposal


@router.post("/proposals/", response_model=KeywordProposalSchema, status_code=status.HTTP_201_CREATED)
async def create_keyword_proposal_api(
    proposal: KeywordProposalCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новое предложение ключевого слова.
    """
    return await create_keyword_proposal(db=db, proposal=proposal)


@router.put("/proposals/{proposal_id}", response_model=KeywordProposalSchema)
async def update_keyword_proposal_api(
    proposal_id: int,
    proposal: KeywordProposalUpdate,
    db: AsyncSession = Depends(get_db),
):
    """
    Обновить предложение ключевого слова.
    """
    db_proposal = await get_keyword_proposal_by_id(db, proposal_id=proposal_id)
    if db_proposal is None:
        raise HTTPException(status_code=404, detail="Keyword proposal not found")
    
    return await update_keyword_proposal(db=db, proposal_id=proposal_id, proposal=proposal)


@router.delete("/proposals/{proposal_id}", response_model=KeywordProposalSchema)
async def delete_keyword_proposal_api(
    proposal_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Удалить предложение ключевого слова.
    """
    db_proposal = await get_keyword_proposal_by_id(db, proposal_id=proposal_id)
    if db_proposal is None:
        raise HTTPException(status_code=404, detail="Keyword proposal not found")
    
    return await delete_keyword_proposal(db=db, proposal_id=proposal_id)
