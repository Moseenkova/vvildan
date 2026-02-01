from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .database import async_session_maker, Country
from .schemas import CountrySchema

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/countries", response_model=list[CountrySchema])
async def get_countries(q: str = Query("", description="Search countries by name")):
    async with async_session_maker() as session:
        query = select(Country).order_by(Country.name.asc())
        if q.strip():
            query = query.where(Country.name.ilike(f"%{q.strip()}%"))
        result = await session.execute(query)
        countries = result.scalars().all()
        return countries
