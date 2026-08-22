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
