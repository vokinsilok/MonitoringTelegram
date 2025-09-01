from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import insert, select, and_
from sqlalchemy.orm import selectinload

from bot.models.post import Post, PostKeywordMatch, PostProcessing, PostStatus
from bot.repo.base_repo import BaseRepository


class PostRepository(BaseRepository):
    model = Post

    async def get_post_by_channel_message(self, channel_id: int, message_id: int) -> Optional[Post]:
        stmt = select(Post).where(Post.channel_id == channel_id, Post.message_id == message_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_post(self, values: dict) -> Post:
        stmt = insert(Post).values(**values).returning(Post)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.scalar()

    async def create_keyword_match(self, post_id: int, keyword_id: int) -> PostKeywordMatch:
        stmt = insert(PostKeywordMatch).values(post_id=post_id, keyword_id=keyword_id).returning(PostKeywordMatch)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.scalar()

    async def get_processing_for_post_operator(self, post_id: int, operator_id: int) -> Optional[PostProcessing]:
        stmt = select(PostProcessing).where(
            and_(PostProcessing.post_id == post_id, PostProcessing.operator_id == operator_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_processing(self, post_id: int, operator_id: int) -> PostProcessing:
        payload = {
            "post_id": post_id,
            "operator_id": operator_id,
            "status": PostStatus.PENDING.value,
            "comment": None,
            "processed_at": None,
        }
        stmt = insert(PostProcessing).values(**payload).returning(PostProcessing)
        res = await self.session.execute(stmt)
        await self.session.commit()
        return res.scalar()

    async def get_pending_processing(self, within_hours: int = 24) -> List[PostProcessing]:
        cutoff = datetime.utcnow() - timedelta(hours=within_hours)
        stmt = (
            select(PostProcessing)
            .options(selectinload(PostProcessing.post).selectinload(Post.channel))
            .where(PostProcessing.status == PostStatus.PENDING.value)
            .where(PostProcessing.processed_at.is_(None))
            .where(Post.published_at >= cutoff)
            .join(Post, Post.id == PostProcessing.post_id)
        )
        res = await self.session.execute(stmt)
        return res.unique().scalars().all()
