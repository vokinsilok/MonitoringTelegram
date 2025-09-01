from pydantic import BaseModel

from bot.models.keyword import KeywordType


class KeyWordCreateSchema(BaseModel):
    text: str
    type: KeywordType
    is_active: bool = True
    description: str | None = None

class KeyWordSchema(KeyWordCreateSchema):
    id: int


class UpdateKeyWordSchema(BaseModel):
    text: str | None = None
    type: KeywordType | None = None
    is_active: bool | None = None
    description: str | None = None

