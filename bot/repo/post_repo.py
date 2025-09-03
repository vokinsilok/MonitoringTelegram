from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import insert, select, and_, update, func, distinct, case
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
            .options(
                selectinload(PostProcessing.post).selectinload(Post.channel),
                selectinload(PostProcessing.post)
                    .selectinload(Post.matched_keywords)
                    .selectinload(PostKeywordMatch.keyword),
            )
            .where(PostProcessing.status == PostStatus.PENDING.value)
            .where(PostProcessing.processed_at.is_(None))
            .where(Post.published_at >= cutoff)
            .join(Post, Post.id == PostProcessing.post_id)
        )
        res = await self.session.execute(stmt)
        return res.unique().scalars().all()

    async def get_processing(self, pp_id: int) -> Optional[PostProcessing]:
        stmt = (
            select(PostProcessing)
            .where(PostProcessing.id == pp_id)
            .options(selectinload(PostProcessing.post).selectinload(Post.channel))
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def cas_update_processing_status(self, pp_id: int, new_status: str, comment: Optional[str] = None) -> Optional[PostProcessing]:
        values = {"status": new_status, "processed_at": datetime.utcnow()}
        if comment is not None:
            values["comment"] = comment
        stmt = (
            update(PostProcessing)
            .where(and_(PostProcessing.id == pp_id, PostProcessing.status == PostStatus.PENDING.value))
            .values(**values)
            .returning(PostProcessing)
        )
        res = await self.session.execute(stmt)
        obj = res.scalar_one_or_none()
        if obj:
            await self.session.commit()
        return obj

    async def update_processing_notify_meta(self, pp_id: int, chat_id: int, message_id: int) -> None:
        stmt = (
            update(PostProcessing)
            .where(PostProcessing.id == pp_id)
            .values(notify_chat_id=chat_id, notify_message_id=message_id, notify_sent_at=datetime.utcnow())
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def get_siblings_processings(self, post_id: int, exclude_pp_id: Optional[int] = None) -> List[PostProcessing]:
        stmt = select(PostProcessing).where(PostProcessing.post_id == post_id)
        if exclude_pp_id is not None:
            stmt = stmt.where(PostProcessing.id != exclude_pp_id)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def bulk_update_status_for_post(self, post_id: int, new_status: str, exclude_pp_id: Optional[int] = None) -> None:
        stmt = update(PostProcessing).where(PostProcessing.post_id == post_id)
        if exclude_pp_id is not None:
            stmt = stmt.where(PostProcessing.id != exclude_pp_id)
        stmt = stmt.values(status=new_status, processed_at=datetime.utcnow())
        await self.session.execute(stmt)
        await self.session.commit()

    # -------- Методы для отчётов --------
    async def count_distinct_posts_with_matches(self, within_hours: Optional[int] = None) -> int:
        stmt = select(func.count(distinct(Post.id))).select_from(Post).join(PostKeywordMatch, PostKeywordMatch.post_id == Post.id)
        if within_hours is not None:
            cutoff = datetime.utcnow() - timedelta(hours=within_hours)
            stmt = stmt.where(Post.published_at >= cutoff)
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def count_processing_by_status(self, status: str, within_hours: Optional[int] = None) -> int:
        stmt = select(func.count()).select_from(PostProcessing).join(Post, Post.id == PostProcessing.post_id)
        stmt = stmt.where(PostProcessing.status == status)
        if within_hours is not None:
            cutoff = datetime.utcnow() - timedelta(hours=within_hours)
            stmt = stmt.where(Post.published_at >= cutoff)
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def get_operator_stats(self, within_hours: Optional[int] = None) -> List[Tuple[int, int, int]]:
        """
        Возвращает список кортежей (operator_id, processed_count, postponed_count)
        """
        base = select(
            PostProcessing.operator_id,
            func.sum(case((PostProcessing.status == PostStatus.PROCESSED.value, 1), else_=0)).label("processed"),
            func.sum(case((PostProcessing.status == PostStatus.POSTPONED.value, 1), else_=0)).label("postponed"),
        ).select_from(PostProcessing).join(Post, Post.id == PostProcessing.post_id)
        if within_hours is not None:
            cutoff = datetime.utcnow() - timedelta(hours=within_hours)
            base = base.where(Post.published_at >= cutoff)
        base = base.group_by(PostProcessing.operator_id)
        res = await self.session.execute(base)
        rows = res.all() or []
        return [(int(r[0]), int(r[1] or 0), int(r[2] or 0)) for r in rows]

    async def get_recent_matched_posts(self, within_hours: int = 24) -> List[Post]:
        cutoff = datetime.utcnow() - timedelta(hours=within_hours)
        stmt = (
            select(Post)
            .join(PostKeywordMatch, PostKeywordMatch.post_id == Post.id)
            .where(Post.published_at >= cutoff)
            .options(
                selectinload(Post.channel),
                selectinload(Post.matched_keywords).selectinload(PostKeywordMatch.keyword),
            )
            .order_by(Post.published_at.desc())
            .limit(500)
        )
        res = await self.session.execute(stmt)
        return res.unique().scalars().all()
