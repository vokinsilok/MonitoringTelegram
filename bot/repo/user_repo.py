from pydantic import BaseModel
from sqlalchemy import select, insert, update
from typing import List, Optional

from bot.models.user_model import User, UserRole, UserSettings, TimeZone, Language
from bot.repo.base_repo import BaseRepository


class UserRepository(BaseRepository):
    model = User
    schema = None

    async def get_user_by_filter(self, **filters):
        stmt = select(User).filter_by(**filters)
        obj = await self.session.execute(stmt)
        return obj.scalar()

    async def get_or_create_user(self, telegram_id: int, data: BaseModel):
        stmt = select(User).where(User.telegram_id == telegram_id)
        obj = await self.session.execute(stmt)
        user = obj.scalar()
        if user:
            # гарантируем наличие настроек
            await self.get_or_create_settings(user.id)
            return user
        else:
            new_user = await self.session.execute(insert(User).values(data.model_dump()).returning(User))
            user = new_user.scalar()
            # создаём настройки по умолчанию
            if user:
                await self.create_settings(user.id)
            return user

    async def get_admins(self) -> List[User]:
        """Получить список всех администраторов"""
        stmt = select(User).where(User.role == UserRole.ADMIN.value)
        obj = await self.session.execute(stmt)
        return obj.scalars().all()

    async def list_users(
        self,
        *,
        is_operator: Optional[bool] = None,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> List[User]:
        stmt = select(User)
        if is_operator is not None:
            stmt = stmt.where(User.is_operator == is_operator)
        if is_active is not None:
            stmt = stmt.where(User.is_active == is_active)
        if role is not None:
            stmt = stmt.where(User.role == role)
        stmt = stmt.order_by(User.id).offset((page - 1) * per_page).limit(per_page)
        obj = await self.session.execute(stmt)
        return obj.scalars().all()

    async def get_operators(self, page: int = 1, per_page: int = 10) -> List[User]:
        return await self.list_users(is_operator=True, page=page, per_page=per_page)

    async def update_user(self, user_id: int, values: dict) -> User | None:
        upd = (
            update(User)
            .where(User.id == user_id)
            .values(**values)
            .returning(User)
        )
        obj = await self.session.execute(upd)
        user = obj.scalar()
        if user:
            await self.session.commit()
        return user

    # -------- Работа с настройками пользователя --------
    async def get_settings(self, user_id: int) -> Optional[UserSettings]:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        obj = await self.session.execute(stmt)
        return obj.scalar_one_or_none()

    async def create_settings(
        self,
        user_id: int,
        *,
        time_zone: Optional[str] = None,
        language: Optional[str] = None,
    ) -> UserSettings:
        payload = {
            "user_id": user_id,
            "time_zone": time_zone or TimeZone.GMT.value,
            "language": language or Language.RU.value,
        }
        res = await self.session.execute(
            insert(UserSettings).values(**payload).returning(UserSettings)
        )
        await self.session.commit()
        return res.scalar()

    async def get_or_create_settings(self, user_id: int) -> UserSettings:
        st = await self.get_settings(user_id)
        if st:
            return st
        return await self.create_settings(user_id)

    async def update_settings(self, user_id: int, values: dict) -> Optional[UserSettings]:
        upd = (
            update(UserSettings)
            .where(UserSettings.user_id == user_id)
            .values(**values)
            .returning(UserSettings)
        )
        obj = await self.session.execute(upd)
        st = obj.scalar_one_or_none()
        if st:
            await self.session.commit()
        return st
