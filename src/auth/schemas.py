from pydantic import BaseModel, Field


class TelegramLoginSchema(BaseModel):
    init_data: str


class TelegramWidgetLoginSchema(BaseModel):
    model_config = {"extra": "forbid"}

    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    photo_url: str | None = None
    auth_date: int
    hash: str = Field(pattern=r"^[0-9a-f]{64}$")
