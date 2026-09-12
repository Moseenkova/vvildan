from datetime import datetime

from pydantic import BaseModel, Field


class SendMatchMessageSchema(BaseModel):
    own_request_id: int
    matching_request_id: int
    body: str = Field(min_length=1, max_length=2000)


class SendMessageSchema(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class MessageSchema(BaseModel):
    id: int
    body: str
    created_at: datetime
    is_mine: bool
    is_read: bool


class DialogUserSchema(BaseModel):
    name: str
    username: str | None


class DialogSchema(BaseModel):
    id: int
    other_user: DialogUserSchema
    latest_message: MessageSchema
    unread_count: int


class DialogMessagesSchema(BaseModel):
    id: int
    other_user: DialogUserSchema
    messages: list[MessageSchema]
