from pydantic import BaseModel


class CountrySchema(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True
