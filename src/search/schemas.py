from pydantic import BaseModel


class CitySearchResultSchema(BaseModel):
    id: int
    name: str
    country_id: int
    country_name: str
