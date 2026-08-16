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
