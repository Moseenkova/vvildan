from pydantic import BaseModel, Field


class TelegramLoginSchema(BaseModel):
    init_data: str


class TelegramBrowserLoginSchema(BaseModel):
    id_token: str = Field(min_length=1, max_length=16384)
