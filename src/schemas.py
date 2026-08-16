from pydantic import BaseModel


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


class AirportSchema(BaseModel):
    id: int
    name: str
    iata_code: str | None
    icao_code: str | None

    class Config:
        from_attributes = True


class AirportSearchResultSchema(BaseModel):
    id: int
    name: str
    iata_code: str | None
    icao_code: str | None
    city_id: int
    city_name: str
    country_id: int
    country_name: str
