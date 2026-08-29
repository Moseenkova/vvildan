from datetime import date, datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field, field_validator


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
