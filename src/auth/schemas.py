from pydantic import BaseModel


class TelegramLoginSchema(BaseModel):
    init_data: str
