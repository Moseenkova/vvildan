from datetime import datetime, date as date_
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator
from datetime import date, datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator


class AirportSearchResultSchema(BaseModel):
    id: int
    name: str
    iata_code: str | None
    icao_code: str | None
    city_id: int
    city_name: str
    country_id: int
    country_name: str


class RequestCreateSchema(BaseModel):
    telegram_id: int
    role: Literal["sender", "courier"]
    date_from: Optional[date_] = None
    date_to: Optional[date_] = None
    date: Optional[date_] = None
    airport_from_id: int
    airport_to_id: int
    comment: Optional[str] = None

    @model_validator(mode="after")
    def validate_dates_by_role(self):
        if self.role == "sender":
            if not self.date_from or not self.date_to:
                raise ValueError("date_from and date_to are required for sender")
            if self.date_from > self.date_to:
                raise ValueError("date_from must be less than or equal to date_to")
        elif self.role == "courier":
            if not self.date:
                raise ValueError("date is required for courier")
        return self

class RequestAirportSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    iata_code: str | None
    city_name: str = Field(validation_alias=AliasPath("city", "name"))
    country_name: str = Field(
        validation_alias=AliasPath("city", "country", "name")
    )


class RequestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    date_from: date
    date_to: date
    departure_airports: list[RequestAirportSchema]
    arrival_airports: list[RequestAirportSchema]
    comment: str
    status: str
    created_at: datetime

    @field_validator("role", "status", mode="before")
    @classmethod
    def enum_value(cls, value: object) -> object:
        return getattr(value, "value", value)
