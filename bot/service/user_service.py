from bot.schemas.user_schema import CreateUserSchema, UserSchema
from bot.service.base_service import BaseService


class UserService(BaseService):

    async def get_or_create_user(self, telegram_id: int, data: CreateUserSchema) -> UserSchema:
        return await self.db.user.get_or_create_user(telegram_id=telegram_id, data=data)