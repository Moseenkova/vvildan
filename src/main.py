from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import or_, select

from .database import Airport, async_session_maker, City, Country
from .schemas import (
    AirportSearchResultSchema,
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
