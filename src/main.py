from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi_pagination import Page, add_pagination
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.database import (
    async_session_maker,
    City,
    CityName,
    Country,
    CountryName,
    Request as TravelRequest,
    RequestStatus,
)
from src.schemas import (
    CitySearchResultSchema,
    RequestCreateSchema,
    RequestSchema,
)
from src.auth.routers import auth_router
from src.deps import get_current_user

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/requests", response_model=Page[RequestSchema])
async def get_my_requests(
    status: RequestStatus | None = Query(None),
    user=Depends(get_current_user),
):
    departure_load = selectinload(TravelRequest.departure_cities).selectinload(City.country)
    arrival_load = selectinload(TravelRequest.arrival_cities).selectinload(City.country)
    async with async_session_maker() as session:
        query = (
            select(TravelRequest)
            .where(
                TravelRequest.user_id == user.id,
                *([TravelRequest.status == status] if status else []),
            )
            .options(departure_load, arrival_load)
            .order_by(TravelRequest.created_at.desc())
        )
        return await apaginate(session, query)


@app.post(
    "/api/requests",
    response_model=RequestSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    payload: RequestCreateSchema,
    user=Depends(get_current_user),
):
    city_ids = set(payload.departure_city_ids + payload.arrival_city_ids)
    async with async_session_maker() as session:
        cities = (
            await session.scalars(
                select(City).where(City.id.in_(city_ids)).options(selectinload(City.country))
            )
        ).all()
        cities_by_id = {city.id: city for city in cities}
        missing_city_ids = sorted(city_ids - cities_by_id.keys())
        if missing_city_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"missing_city_ids": missing_city_ids},
            )

        request = TravelRequest(
            user_id=user.id,
            role=payload.role,
            date_from=payload.date_from,
            date_to=payload.date_to,
            departure_cities=[cities_by_id[id] for id in payload.departure_city_ids],
            arrival_cities=[cities_by_id[id] for id in payload.arrival_city_ids],
            comment=payload.comment,
        )
        session.add(request)
        await session.commit()
        await session.refresh(request)
        return request


@app.get("/api/city-search", response_model=list[CitySearchResultSchema])
async def search_cities(
    q: str = Query(..., min_length=1, description="City or country name"),
    language: str = Query("en", min_length=2, max_length=16),
    user=Depends(get_current_user),
):
    term = q.strip()
    if not term:
        return []
    search = f"%{term}%"
    language = language.lower().replace("_", "-").split("-", 1)[0]

    localized_city_name = (
        select(func.min(CityName.name))
        .where(CityName.city_id == City.id, CityName.language_code == language)
        .correlate(City)
        .scalar_subquery()
    )
    english_city_name = (
        select(func.min(CityName.name))
        .where(CityName.city_id == City.id, CityName.language_code == "en")
        .correlate(City)
        .scalar_subquery()
    )
    english_country_name = (
        select(func.min(CountryName.name))
        .where(
            CountryName.country_id == Country.id,
            CountryName.language_code == "en",
        )
        .correlate(Country)
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
                City.id,
                func.coalesce(localized_city_name, english_city_name, City.name).label(
                    "name"
                ),
                Country.id.label("country_id"),
                func.coalesce(
                    localized_country_name,
                    english_country_name,
                    Country.name,
                ).label("country_name"),
            )
            .join(Country, City.country_id == Country.id)
            .where(
                or_(
                    City.name.ilike(search),
                    Country.name.ilike(search),
                    City.localized_names.any(CityName.name.ilike(search)),
                    Country.localized_names.any(CountryName.name.ilike(search)),
                )
            )
            .order_by(
                City.population.desc(),
                "country_name",
                "name",
            )
            .limit(50)
        )
        result = await session.execute(query)
        return result.mappings().all()


add_pagination(app)
