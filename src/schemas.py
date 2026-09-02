from html import escape
from datetime import date, datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator, model_validator

from src.database import RequestRole


class CitySearchResultSchema(BaseModel):
    id: int
    name: str
    country_id: int
    country_name: str


class RequestCitySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country_name: str = Field(validation_alias=AliasPath("country", "name"))


class RequestSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    date_from: date
    date_to: date
    departure_cities: list[RequestCitySchema]
    arrival_cities: list[RequestCitySchema]
    comment: str
    status: str
    created_at: datetime

    @field_validator("role", "status", mode="before")
    @classmethod
    def enum_value(cls, value: object) -> object:
        return getattr(value, "value", value)


class RequestCreateSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    role: RequestRole
    date_from: date = Field(alias="dateFrom")
    date_to: date = Field(alias="dateTo")
    departure_city_ids: list[int] = Field(
        alias="departureCityIds", min_length=1, max_length=5
    )
    arrival_city_ids: list[int] = Field(
        alias="arrivalCityIds", min_length=1, max_length=5
    )
    comment: str = Field(default="", alias="baggageComments", max_length=512)

    @field_validator("comment")
    @classmethod
    def escape_comment_html(cls, value: str) -> str:
        return escape(value, quote=True)

    @model_validator(mode="after")
    def validate_request(self) -> "RequestCreateSchema":
        if self.date_from > self.date_to:
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
