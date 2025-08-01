from pydantic import BaseModel


class CreateUserSchema(BaseModel):
    telegram_id: int
    username: str
    first_name: str | None = None
    last_name: str | None = None
    role: str
    is_active: bool = True
    is_admin: bool = False
    is_operator: bool = False

class UserSchema(CreateUserSchema):
    id: int