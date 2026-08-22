# uvicorn src.main:app --reload --reload-dir src --host 0.0.0.0 --port 8001

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_, select

from .database import (
    Airport,
    AirportName,
    async_session_maker,
    City,
    CityName,
    Country,
    CountryName,
)
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


@app.post("/api/requests")
async def create_request(body: RequestCreateSchema):
    print(body)
    """Accept request creation from the web form."""
    # For now, return the validated payload. Wire to DB (Request, UserCity, etc.) as needed.
    return {"ok": True, "data": body.model_dump()}


'''
1 создать страны и города если нет в списке
2 найти пользователя через тг айди и добавить если не было
3 создать заявку


пример данных
{
  "role":"sender",
  "date_from":"09.08.2026",
  "date_to":"10.08.2026",
  "date":null,
  "country_from": {
    "id":2, айди если есть в базе
    "name":"United Kingdom"
  },
  "city_from":{
    "id":null, если айди нет - то надо добавить этот город к стране
    "name":"London"
  },
  "country_to":{
    "id":null, нет айди страны - добавить страну
    "name":"Россия"
  },
  "city_to":{
    "id":null, нет айди города - добавить годор к добавленной стране
    "name":"Уфа" 
  },
  "comment":"",
  "telegram_id":5875912525 что бы найти пользователя
}


'''
