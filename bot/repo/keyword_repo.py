from typing import List

from sqlalchemy import select, insert, update

from bot.models.keyword import Keyword, KeywordProposal
from bot.repo.base_repo import BaseRepository
from bot.schemas.keyword_schema import (
    KeyWordSchema,
    KeyWordCreateSchema,
    UpdateKeyWordSchema,
    KeyWordProposalCreateSchema,
    KeyWordProposalSchema,
    KeyWordProposalUpdateSchema,
)


class KeyWordRepo(BaseRepository):
    model = Keyword
    schema = KeyWordSchema

    # --------------------- Keyword ---------------------
    async def get_keyword_by_filter(self, **filter_by) -> KeyWordSchema | None:
        obj = select(self.model).filter_by(**filter_by)
        result = await self.session.execute(obj)
        return result.scalar_one_or_none()

    async def create_keyword(self, data: KeyWordCreateSchema | dict) -> KeyWordSchema:
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        if isinstance(payload.get("type"), object) and hasattr(payload["type"], "value"):
            payload["type"] = payload["type"].value
        stmt = insert(self.model).values(**payload).returning(self.model)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar()

    async def update_keyword(self, keyword_id: int, data: UpdateKeyWordSchema | dict) -> KeyWordSchema:
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        payload = {k: v for k, v in payload.items() if v is not None}
        if isinstance(payload.get("type"), object) and hasattr(payload["type"], "value"):
            payload["type"] = payload["type"].value
        update_stmt = (
            update(self.model)
            .where(self.model.id == keyword_id)
            .values(**payload)
            .returning(self.model)
        )
        update_obj = await self.session.execute(update_stmt)
        obj = update_obj.scalar()
        await self.session.commit()
        return obj

    async def get_all_keywords(self) -> List[KeyWordSchema]:
        stmt = select(self.model)
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    # --------------------- KeywordProposal ---------------------
    async def create_keyword_proposal(self, data: KeyWordProposalCreateSchema | dict) -> KeyWordProposalSchema:
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        if isinstance(payload.get("type"), object) and hasattr(payload["type"], "value"):
            payload["type"] = payload["type"].value
        stmt = insert(KeywordProposal).values(**payload).returning(KeywordProposal)
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar()

    async def get_all_keyword_proposals(self) -> List[KeyWordProposalSchema]:
        stmt = select(KeywordProposal)
        result = await self.session.execute(stmt)
        return result.unique().scalars().all()

    async def get_keyword_proposal_by_filter(self, **filter_by) -> KeyWordProposalSchema | None:
        obj = select(KeywordProposal).filter_by(**filter_by)
        result = await self.session.execute(obj)
        return result.scalar_one_or_none()

    async def update_keyword_proposal(self, proposal_id: int, data: KeyWordProposalUpdateSchema | dict) -> KeyWordProposalSchema:
        payload = data.model_dump() if hasattr(data, "model_dump") else dict(data)
        payload = {k: v for k, v in payload.items() if v is not None}
        update_stmt = (
            update(KeywordProposal)
            .where(KeywordProposal.id == proposal_id)
            .values(**payload)
            .returning(KeywordProposal)
        )
        update_obj = await self.session.execute(update_stmt)
        obj = update_obj.scalar()
        await self.session.commit()
        return obj