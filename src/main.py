from fastapi import FastAPI
from sqlalchemy import select
from database import async_session_maker, Country
from schemas import CountrySchema

app = FastAPI()


@app.get("/countries", response_model=list[CountrySchema])
async def get_countries():
    async with async_session_maker() as session:
        query = select(Country).order_by(Country.name.asc())
        countries = await session.execute(query)
        countries = countries.scalars().all()
        return countries
