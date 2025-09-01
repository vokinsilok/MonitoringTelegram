from typing import List

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