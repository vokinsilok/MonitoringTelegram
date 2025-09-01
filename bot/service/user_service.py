from typing import List, Optional

from bot.schemas.user_schema import CreateUserSchema, UserSchema
from bot.service.base_service import BaseService
from bot.models.user_model import User

class UserService(BaseService):

    async def cheek_user_permissions(self, telegram_id: int) -> dict:
        return_dict = {
            "is_admin": False,
            "is_operator": False,
        }
        user = await self.db.user.get_user_by_filter(telegram_id=telegram_id)
        if user and user.is_admin:
            return_dict["is_admin"] = True
            return return_dict
        if user and user.is_operator:
            return_dict["is_operator"] = True
            return return_dict
        return return_dict

    async def get_or_create_user(self, telegram_id: int, data: CreateUserSchema) -> UserSchema:
        return await self.db.user.get_or_create_user(telegram_id=telegram_id, data=data)

    async def get_admins(self) -> List[User]:
        """Получить список всех администраторов"""
        return await self.db.user.get_admins()

    async def get_user_by_filter(self, **filters) -> UserSchema:
        return await self.db.user.get_user_by_filter(**filters)

    async def list_users(
        self,
        *,
        is_operator: Optional[bool] = None,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
        page: int = 1,
        per_page: int = 10,
    ) -> List[User]:
        return await self.db.user.list_users(
            is_operator=is_operator,
            is_active=is_active,
            role=role,
            page=page,
            per_page=per_page,
        )

    async def set_operator(self, user_id: int, make_operator: bool) -> User | None:
        values: dict = {"is_operator": bool(make_operator)}
        # Меняем роль только если это не админ
        user = await self.db.user.get_user_by_filter(id=user_id)
        if not user:
            return None
        if user.role != "admin":
            values["role"] = "operator" if make_operator else "user"
        updated = await self.db.user.update_user(user_id, values)
        return updated

    async def set_active(self, user_id: int, is_active: bool) -> User | None:
        return await self.db.user.update_user(user_id, {"is_active": bool(is_active)})
