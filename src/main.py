from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select

from .database import Airport, async_session_maker, City, Country
from .schemas import (
    AirportSchema,
    AirportSearchResultSchema,
    CitySchema,
    CountrySchema,
)
from .auth.routers import auth_router
from .deps import get_current_user
from fastapi import Depends

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/api/airport-search", response_model=list[AirportSearchResultSchema])
async def search_airports(
    q: str = Query(..., min_length=1, description="Airport, city, or country name"),
    user=Depends(get_current_user),
):
    search = f"%{q.strip()}%"
    if not q.strip():
        return []

    async with async_session_maker() as session:
        query = (
            select(
                Airport.id,
                Airport.name,
                Airport.iata_code,
                Airport.icao_code,
                City.id.label("city_id"),
                City.name.label("city_name"),
                Country.id.label("country_id"),
                Country.name.label("country_name"),
            )
            .join(City, Airport.city_id == City.id)
            .join(Country, City.country_id == Country.id)
            .where(
                or_(
                    Airport.name.ilike(search),
                    Airport.iata_code.ilike(search),
                    Airport.icao_code.ilike(search),
                    City.name.ilike(search),
                    Country.name.ilike(search),
                )
            )
            .order_by(Country.name.asc(), City.name.asc(), Airport.name.asc())
        )
        result = await session.execute(query)
        return result.mappings().all()


@app.get("/api/countries", response_model=list[CountrySchema])
async def get_countries(
    q: str = Query("", description="Search countries by name"),
    user=Depends(get_current_user)
):
    async with async_session_maker() as session:
        query = select(Country).order_by(Country.name.asc())
        if q.strip():
            query = query.where(Country.name.ilike(f"%{q.strip()}%"))
        result = await session.execute(query)
        countries = result.scalars().all()
        return countries


@app.get("/api/cities", response_model=list[CitySchema])
async def get_cities(
    country_id: int = Query(..., description="Country ID"),
    q: str = Query("", description="Search cities by name"),
    user=Depends(get_current_user)
):
    async with async_session_maker() as session:
        query = (
            select(City)
            .where(City.country_id == country_id)
            .order_by(City.name.asc())
        )
        if q.strip():
            query = query.where(City.name.ilike(f"%{q.strip()}%"))
        result = await session.execute(query)
        cities = result.scalars().all()
        return cities


@app.get("/api/airports", response_model=list[AirportSchema])
async def get_airports(
    city_id: int = Query(..., description="City ID"),
    q: str = Query("", description="Search airports by name or code"),
    user=Depends(get_current_user),
):
    async with async_session_maker() as session:
        query = (
            select(Airport)
            .where(Airport.city_id == city_id)
            .order_by(Airport.scheduled_service.desc(), Airport.name.asc())
        )
        if q.strip():
            search = f"%{q.strip()}%"
            query = query.where(
                or_(
                    Airport.name.ilike(search),
                    Airport.iata_code.ilike(search),
                    Airport.icao_code.ilike(search),
                )
            )
        result = await session.execute(query)
        return result.scalars().all()
