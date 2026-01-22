from fastapi import FastAPI
from sqlalchemy import select
from database import async_session_maker, Country

app = FastAPI()


@app.get("/countries")
async def get_countries():
    async with async_session_maker() as session:
        countries = await session.execute(select(Country))
        countries = countries.scalars().all()
        return countries
