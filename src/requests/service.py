from datetime import datetime, timezone

from fastapi import HTTPException, status
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import apaginate
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload

from src.config import Settings, get_settings
from src.database import (
    City,
    CityName,
    CountryName,
    RequestStatus,
    User,
    async_session_maker,
)
from src.database import Request as TravelRequest
from src.requests.schemas import RequestCitySchema, RequestCreateSchema, RequestSchema

cfg: Settings = get_settings()


def _city_relationships():
    return (
        selectinload(TravelRequest.departure_cities).selectinload(City.country),
        selectinload(TravelRequest.arrival_cities).selectinload(City.country),
    )


async def get_user_requests(
    user_id: int,
    request_status: RequestStatus | None = None,
    language: str = "en",
) -> Page[RequestSchema]:
    language = language.lower().replace("_", "-").split("-", 1)[0]
    async with async_session_maker() as session:
        query = (
            select(TravelRequest)
            .where(
                TravelRequest.user_id == user_id,
                *([TravelRequest.status == request_status] if request_status else []),
            )
            .options(*_city_relationships())
            .order_by(TravelRequest.created_at.desc())
        )
        page = await apaginate(session, query)

        cities = {
            city.id: city
            for request in page.items
            for city in request.departure_cities + request.arrival_cities
        }
        city_country_rows = (
            await session.execute(select(City.id, City.country_id).where(City.id.in_(cities)))
        ).all()
        country_by_city = dict(city_country_rows)
        country_ids = set(country_by_city.values())
        languages = {language, "en"}
        city_name_rows = (
            await session.execute(
                select(CityName.city_id, CityName.language_code, CityName.name).where(
                    CityName.city_id.in_(cities),
                    CityName.language_code.in_(languages),
                )
            )
        ).all()
        country_name_rows = (
            await session.execute(
                select(
                    CountryName.country_id,
                    CountryName.language_code,
                    CountryName.name,
                ).where(
                    CountryName.country_id.in_(country_ids),
                    CountryName.language_code.in_(languages),
                )
            )
        ).all()

        def names_by_language(rows):
            names = {}
            for entity_id, language_code, name in rows:
                key = (entity_id, language_code)
                names[key] = min(name, names.get(key, name))
            return names

        city_names = names_by_language(city_name_rows)
        country_names = names_by_language(country_name_rows)

        def localized_city(city: RequestCitySchema) -> RequestCitySchema:
            country_id = country_by_city[city.id]
            return city.model_copy(
                update={
                    "name": (
                        city_names.get((city.id, language))
                        or city_names.get((city.id, "en"))
                        or city.name
                    ),
                    "country_name": (
                        country_names.get((country_id, language))
                        or country_names.get((country_id, "en"))
                        or city.country_name
                    ),
                }
            )

        items = []
        for request in page.items:
            item = RequestSchema.model_validate(request)
            items.append(
                item.model_copy(
                    update={
                        "departure_cities": [
                            localized_city(city) for city in request.departure_cities
                        ],
                        "arrival_cities": [localized_city(city) for city in request.arrival_cities],
                    }
                )
            )
        return page.model_copy(update={"items": items})


async def create_user_request(
    user_id: int,
    payload: RequestCreateSchema,
) -> TravelRequest:
    city_ids = set(payload.departure_city_ids + payload.arrival_city_ids)

    async with async_session_maker() as session:
        # Serialize creation for this user so concurrent submissions cannot exceed the cap.
        await session.execute(select(User.id).where(User.id == user_id).with_for_update())
        today = datetime.now(timezone.utc).date()
        if payload.date_to is None or payload.date_to >= today:
            active_count_result = await session.execute(
                select(func.count())
                .select_from(TravelRequest)
                .where(
                    TravelRequest.user_id == user_id,
                    TravelRequest.status == RequestStatus.active,
                    or_(TravelRequest.date_to.is_(None), TravelRequest.date_to >= today),
                )
            )
            active_count = active_count_result.scalar_one()
            if active_count >= cfg.MAX_ACTIVE_REQUESTS_PER_USER:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "You can have at most 5 active requests "
                        "with no end date or an end date today or later."
                    ),
                )

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
            user_id=user_id,
            role=payload.role,
            date_from=payload.date_from,
            date_to=payload.date_to,
            departure_cities=[cities_by_id[id] for id in payload.departure_city_ids],
            arrival_cities=[cities_by_id[id] for id in payload.arrival_city_ids],
            comment=payload.comment,
        )
        session.add(request)
        await session.commit()

        return (
            await session.scalars(
                select(TravelRequest)
                .where(TravelRequest.id == request.id)
                .options(*_city_relationships())
            )
        ).one()
