from pydantic import BaseModel
from sqlalchemy import select, insert
from typing import List

from bot.models.user_model import User, UserRole
from bot.repo.base_repo import BaseRepository


class UserRepository(BaseRepository):
    model = User
    schema = None

    async def get_or_create_user(self, telegram_id: int, data: BaseModel):
        stmt = select(User).where(User.telegram_id == telegram_id)
        obj = await self.session.execute(stmt)
        user = obj.scalar()
        if user:
            return user
        else:
            new_user = await self.session.execute(insert(User).values(data.model_dump()).returning(User))
            return new_user.scalar()

    async def get_admins(self) -> List[User]:
        """Получить список всех администраторов"""
        stmt = select(User).where(User.role == UserRole.ADMIN.value)
        obj = await self.session.execute(stmt)
        return obj.scalars().all()