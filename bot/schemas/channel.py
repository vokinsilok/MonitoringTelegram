from pydantic import BaseModel


class AddChannelProposal(BaseModel):
    channel_username: str | None = None
    operator_id: int
    status: str = "pending"
    comment: str
    admin_comment: str | None = None


class AddChannel(BaseModel):
    channel_username: str | None = None
    title: str
    invite_link: str | None = None
    status: str = "active"
    description: str | None = None
    is_private: bool = False
    last_parsed_message_id: int | None = None
    last_checked: str | None = None  # ISO format datetime string