from datetime import date, datetime
from html import escape
from typing import Optional

from pydantic import (
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.database import RequestRole


class RequestCitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_name: str = Field(validation_alias=AliasPath("country", "name"))


class RequestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    date_from: date | None
    date_to: date | None
    departure_cities: list[RequestCitySchema]
    arrival_cities: list[RequestCitySchema]
    comment: str | None
    status: str
    created_at: datetime

    @field_validator("role", "status", mode="before")
    @classmethod
    def enum_value(cls, value: object) -> object:
        return getattr(value, "value", value)


class RequestCreateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: RequestRole
    date_from: date | None = Field(default=None, alias="dateFrom")
    date_to: date | None = Field(default=None, alias="dateTo")
    departure_city_ids: list[int] = Field(alias="departureCityIds", min_length=1, max_length=5)
    arrival_city_ids: list[int] = Field(alias="arrivalCityIds", min_length=1, max_length=5)
    comment: Optional[str] = Field(None, alias="baggageComments", max_length=512)

    @field_validator("comment")
    @classmethod
    def escape_comment_html(cls, value: str) -> str:
        return escape(value, quote=True)

    @model_validator(mode="after")
    def validate_request(self) -> "RequestCreateSchema":
        if self.role == RequestRole.courier and (
            self.date_from is None or self.date_to != self.date_from
        ):
            raise ValueError("courier requests require dateTo to equal dateFrom")
        if self.role == RequestRole.sender and self.date_from is None and self.date_to is None:
            raise ValueError("sender requests require dateFrom or dateTo")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError("dateFrom must be on or before dateTo")
        if len(set(self.departure_city_ids)) != len(self.departure_city_ids):
            raise ValueError("departureCityIds must not contain duplicates")
        if len(set(self.arrival_city_ids)) != len(self.arrival_city_ids):
            raise ValueError("arrivalCityIds must not contain duplicates")
        if self.role == RequestRole.courier and (
            len(self.departure_city_ids) != 1 or len(self.arrival_city_ids) != 1
        ):
            raise ValueError("courier requests require one departure and one arrival city")
        return self
