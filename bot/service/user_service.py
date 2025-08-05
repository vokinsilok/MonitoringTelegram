from typing import List

from bot.schemas.user_schema import CreateUserSchema, UserSchema
from bot.service.base_service import BaseService
from bot.models.user_model import User

class UserService(BaseService):

    async def get_or_create_user(self, telegram_id: int, data: CreateUserSchema) -> UserSchema:
        return await self.db.user.get_or_create_user(telegram_id=telegram_id, data=data)

    async def get_admins(self) -> List[User]:
        """Получить список всех администраторов"""
        return await self.db.user.get_admins()