from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator


class IdNameSchema(BaseModel):
    id: Optional[int] = None
    name: str


class CountrySchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class CitySchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class RequestCreateSchema(BaseModel):
    telegram_id: int
    role: Literal["sender", "courier"]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    date: Optional[str] = None
    country_from: IdNameSchema
    city_from: IdNameSchema
    country_to: IdNameSchema
    city_to: IdNameSchema
    comment: str = ""

    @field_validator("date_from", "date_to", "date")
    @classmethod
    def validate_dd_mm_yyyy(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return v
        try:
            datetime.strptime(v, "%d.%m.%Y")
            return v
        except ValueError:
            raise ValueError("must be dd.mm.yyyy")

    @model_validator(mode="after")
    def validate_dates_by_role(self):
        if self.role == "sender":
            if not self.date_from or not self.date_to:
                raise ValueError("date_from and date_to are required for sender")
            d_from = datetime.strptime(self.date_from, "%d.%m.%Y")
            d_to = datetime.strptime(self.date_to, "%d.%m.%Y")
            if d_from > d_to:
                raise ValueError("date_from must be less than or equal to date_to")
        elif self.role == "courier":
            if not self.date:
                raise ValueError("date is required for courier")
        return self
