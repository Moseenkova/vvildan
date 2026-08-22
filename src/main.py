from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from .database import (
    Airport,
    AirportName,
    async_session_maker,
    City,
    CityName,
    Country,
    CountryName,
    Request as TravelRequest,
)
from .schemas import (
    AirportSearchResultSchema,
    RequestSchema,
)
from .auth.routers import auth_router
from .deps import get_current_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/api/requests", response_model=Page[RequestSchema])
async def get_my_requests(user=Depends(get_current_user)):
    airport_load = selectinload(TravelRequest.departure_airports).selectinload(Airport.city).selectinload(City.country)
    arrival_load = selectinload(TravelRequest.arrival_airports).selectinload(Airport.city).selectinload(City.country)
    async with async_session_maker() as session:
        return await paginate(
            session,
            select(TravelRequest)
            .where(TravelRequest.user_id == user.id)
            .options(airport_load, arrival_load)
            .order_by(TravelRequest.created_at.desc()),
        )


@app.get("/api/airport-search", response_model=list[AirportSearchResultSchema])
async def search_airports(
    q: str = Query(..., min_length=1, description="Airport, city, or country name"),
    language: str = Query("en", min_length=2, max_length=16),
    user=Depends(get_current_user),
):
    term = q.strip()
    if not term:
        return []
    search = f"%{term}%"
    language = language.lower().replace("_", "-").split("-", 1)[0]
    search_languages = {language, "en"}

    localized_airport_name = (
        select(func.min(AirportName.name))
        .where(
            AirportName.airport_id == Airport.id,
            AirportName.language_code == language,
        )
        .correlate(Airport)
        .scalar_subquery()
    )
    localized_city_name = (
        select(func.min(CityName.name))
        .where(CityName.city_id == City.id, CityName.language_code == language)
        .correlate(City)
        .scalar_subquery()
    )
    localized_country_name = (
        select(func.min(CountryName.name))
        .where(
            CountryName.country_id == Country.id,
            CountryName.language_code == language,
        )
        .correlate(Country)
        .scalar_subquery()
    )

    async with async_session_maker() as session:
        query = (
            select(
                Airport.id,
                func.coalesce(localized_airport_name, Airport.name).label("name"),
                Airport.iata_code,
                Airport.icao_code,
                City.id.label("city_id"),
                func.coalesce(localized_city_name, City.name).label("city_name"),
                Country.id.label("country_id"),
                func.coalesce(localized_country_name, Country.name).label("country_name"),
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
                    Airport.localized_names.any(
                        AirportName.language_code.in_(search_languages)
                        & AirportName.name.ilike(search)
                    ),
                    City.localized_names.any(
                        CityName.language_code.in_(search_languages)
                        & CityName.name.ilike(search)
                    ),
                    Country.localized_names.any(
                        CountryName.language_code.in_(search_languages)
                        & CountryName.name.ilike(search)
                    ),
                )
            )
            .order_by(
                City.population.desc(),
                "country_name",
                "city_name",
                "name",
            )
            .limit(50)
        )
        result = await session.execute(query)
        return result.mappings().all()


add_pagination(app)
