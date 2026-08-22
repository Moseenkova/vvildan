from datetime import date, datetime

from pydantic import BaseModel


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
    id: int
    name: str
    iata_code: str | None
    city_name: str
    country_name: str


class RequestSchema(BaseModel):
    id: int
    role: str
    date_from: date
    date_to: date
    departure_airports: list[RequestAirportSchema]
    arrival_airports: list[RequestAirportSchema]
    comment: str
    status: str
    created_at: datetime
