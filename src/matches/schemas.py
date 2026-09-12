from datetime import datetime

from pydantic import BaseModel

from src.requests.schemas import RequestSchema


class MatchUserSchema(BaseModel):
    name: str
    username: str | None


class MatchSchema(BaseModel):
    id: int
    status: str
    created_at: datetime
    is_new: bool
    own_request: RequestSchema
    matching_request: RequestSchema
    matching_user: MatchUserSchema
